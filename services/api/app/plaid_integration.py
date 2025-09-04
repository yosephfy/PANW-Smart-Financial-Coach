import os
import hashlib
from datetime import date, timedelta
from typing import List, Dict, Optional

from plaid import ApiClient
from plaid.api import plaid_api
from plaid.model.products import Products
from plaid.model.country_code import CountryCode
from plaid.model.item_public_token_exchange_request import ItemPublicTokenExchangeRequest
from plaid.model.link_token_create_request import LinkTokenCreateRequest
from plaid.model.transactions_get_request import TransactionsGetRequest
from plaid.model.accounts_get_request import AccountsGetRequest

from . import db as db_mod
import base64
import logging


def _cipher():
    """Return a (encrypt, decrypt) pair using Fernet if available and key present.

    If not available, return (None, None) signaling plaintext storage.
    """
    key = os.getenv("PLAID_ENC_KEY")
    if not key:
        return (None, None)
    try:
        from cryptography.fernet import Fernet

        # Accept raw 32-byte urlsafe base64 key or passphrase to derive (dev only)
        if len(key) != 44:  # not a base64 fernet key
            # Derive a 32-byte key from passphrase (dev convenience)
            import hashlib

            d = hashlib.sha256(key.encode("utf-8")).digest()
            key_b64 = base64.urlsafe_b64encode(d)
        else:
            key_b64 = key.encode("utf-8")
        f = Fernet(key_b64)
        return (lambda s: f.encrypt(s.encode("utf-8")).decode("utf-8"),
                lambda s: f.decrypt(s.encode("utf-8")).decode("utf-8"))
    except Exception:
        logging.getLogger(__name__).warning(
            "cryptography not available; storing Plaid tokens in plaintext")
        return (None, None)


def _seal(token: str) -> str:
    enc, _dec = _cipher()
    if enc:
        return "enc:" + enc(token)
    return "plain:" + token


def _unseal(stored: str) -> str:
    prefix, _, val = stored.partition(":")
    if prefix == "enc":
        _enc, dec = _cipher()
        if not dec:
            raise RuntimeError(
                "PLAID_ENC_KEY or cryptography missing; cannot decrypt tokens")
        return dec(val)
    # Treat unknown/legacy as plaintext
    if prefix == "plain":
        return val
    return stored
from .ingest import categorize_with_provenance


def _client() -> plaid_api.PlaidApi:
    configuration = ApiClient.configuration
    configuration.host = os.getenv("PLAID_HOST", "https://sandbox.plaid.com")
    configuration.api_key['PLAID-CLIENT-ID'] = os.getenv("PLAID_CLIENT_ID", "")
    configuration.api_key['PLAID-SECRET'] = os.getenv("PLAID_SECRET", "")
    return plaid_api.PlaidApi(ApiClient(configuration))


def _plaid_enabled() -> bool:
    return bool(os.getenv("PLAID_CLIENT_ID") and os.getenv("PLAID_SECRET"))


def plaid_hash(user_id: str, item_id: str) -> str:
    return hashlib.sha1(f"{user_id}|{item_id}".encode("utf-8")).hexdigest()


def create_link_token(user_id: str) -> Dict:
    if not _plaid_enabled():
        raise RuntimeError("PLAID_CLIENT_ID/PLAID_SECRET not set")
    client = _client()
    req = LinkTokenCreateRequest(
        products=[Products('transactions')],
        client_name="Smart Financial Coach",
        country_codes=[CountryCode('US')],
        language='en',
        user={'client_user_id': user_id},
    )
    res = client.link_token_create(req)
    return res.to_dict()


def exchange_public_token(user_id: str, public_token: str) -> Dict:
    if not _plaid_enabled():
        raise RuntimeError("PLAID_CLIENT_ID/PLAID_SECRET not set")
    client = _client()
    req = ItemPublicTokenExchangeRequest(public_token=public_token)
    res = client.item_public_token_exchange(req).to_dict()
    access_token = res['access_token']
    item_id = res['item_id']
    sid = plaid_hash(user_id, item_id)
    with db_mod.get_connection() as conn:
        conn.execute("INSERT OR IGNORE INTO users (id) VALUES (?)", (user_id,))
        conn.execute(
            "INSERT OR REPLACE INTO plaid_items (id, user_id, item_id, access_token) VALUES (?, ?, ?, ?)",
            (sid, user_id, item_id, _seal(access_token)),
        )
    return {"item_id": item_id}


def _accounts_for(conn, access_token: str) -> List[Dict]:
    client = _client()
    res = client.accounts_get(AccountsGetRequest(access_token=access_token)).to_dict()
    return res.get('accounts', [])


def import_transactions_for_user(user_id: str, start: Optional[str] = None, end: Optional[str] = None) -> Dict:
    if not _plaid_enabled():
        raise RuntimeError("PLAID_CLIENT_ID/PLAID_SECRET not set")
    start_date = start or (date.today() - timedelta(days=30)).isoformat()
    end_date = end or date.today().isoformat()

    client = _client()
    inserted = 0
    skipped = 0
    imported = 0

    with db_mod.get_connection() as conn:
        items = conn.execute("SELECT access_token, item_id FROM plaid_items WHERE user_id = ?", (user_id,)).fetchall()
        if not items:
            return {"error": "no_plaid_items_for_user", "user_id": user_id}

        for row in items:
            access_token = row['access_token']
            # Fetch accounts to map account_id to our accounts table
            accounts = _accounts_for(conn, _unseal(access_token))
            for a in accounts:
                acc_id = a['account_id']
                name = a.get('name') or a.get('official_name') or 'Plaid Account'
                conn.execute(
                    "INSERT OR IGNORE INTO accounts (id, user_id, name, type, institution, mask) VALUES (?, ?, ?, ?, ?, ?)",
                    (acc_id, user_id, name, a.get('type'), a.get('institution_id'), a.get('mask')),
                )

            # Paginate transactions.get (simplified for hackathon)
            request = TransactionsGetRequest(access_token=access_token, start_date=start_date, end_date=end_date)
            response = client.transactions_get(request).to_dict()
            txs = response.get('transactions', [])
            imported += len(txs)

            for t in txs:
                # Map to our schema
                tid = t['transaction_id']
                date_iso = t['date']
                amount = float(t['amount'])
                # Signed amount: treat INCOME_* as inflow, else expense
                pfc = (t.get('personal_finance_category') or {}).get('primary')
                if pfc and pfc.upper().startswith('INCOME'):
                    signed_amount = abs(amount)
                else:
                    signed_amount = -abs(amount)

                merchant = t.get('merchant_name') or t.get('name')
                description = t.get('name')
                provided_cat = None
                if pfc:
                    provided_cat = pfc.lower()

                category, category_source, category_prov, _rule = categorize_with_provenance(
                    merchant, description, None, provided_cat
                )

                try:
                    conn.execute(
                        """
                        INSERT OR IGNORE INTO transactions (
                          id, user_id, account_id, date, amount, merchant, description,
                          category, category_source, category_provenance, is_recurring, mcc, source
                        ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
                        """,
                        (
                            tid, user_id, t.get('account_id'), date_iso, signed_amount, merchant, description,
                            category, category_source or 'plaid_pfc', category_prov or (f"pfc:{pfc}" if pfc else None),
                            False, None, 'plaid',
                        ),
                    )
                    if conn.total_changes > 0:
                        inserted += 1
                    else:
                        skipped += 1
                except Exception:
                    skipped += 1

    return {
        "user_id": user_id,
        "imported": imported,
        "inserted": inserted,
        "skipped": skipped,
        "start_date": start_date,
        "end_date": end_date,
    }
