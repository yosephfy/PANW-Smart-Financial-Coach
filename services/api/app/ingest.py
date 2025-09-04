import csv
import io
import re
import uuid
from datetime import datetime
from typing import Dict, List, Optional
import hashlib


def _to_bool(val) -> bool:
    if isinstance(val, bool):
        return val
    if val is None:
        return False
    s = str(val).strip().lower()
    return s in {"1", "true", "yes", "y"}


def _parse_amount(s) -> float:
    if s is None or s == "":
        return 0.0
    if isinstance(s, (int, float)):
        return float(s)
    s = str(s)
    s = s.replace(",", "").replace("$", "").strip()
    try:
        return float(s)
    except ValueError:
        # Fallback: extract first float-looking segment
        m = re.search(r"-?\d+\.?\d*", s)
        return float(m.group(0)) if m else 0.0


def _parse_date(s) -> str:
    if not s:
        return datetime.utcnow().date().isoformat()
    s = str(s).strip()
    # Try common formats
    fmts = ["%Y-%m-%d", "%m/%d/%Y", "%d/%m/%Y", "%Y/%m/%d"]
    for fmt in fmts:
        try:
            return datetime.strptime(s, fmt).date().isoformat()
        except ValueError:
            continue
    # As last resort, return as-is if it looks like an ISO date
    return s


def categorize_with_provenance(
    merchant: Optional[str], description: Optional[str], mcc: Optional[str], provided_category: Optional[str]
) -> (Optional[str], str, str, str):
    """
    Returns: (category, source, provenance, rule)
      - source: csv|mcc|regex|fallback
      - provenance: a short tag like 'csv:groceries', 'mcc:5411', 'regex:spotify'
      - rule: coarse rule id like 'csv' | 'mcc' | 'streaming' | 'coffee' | 'fallback'
    """
    # If CSV provides a category, respect it
    if provided_category and str(provided_category).strip():
        cat = str(provided_category).strip()
        return cat, "csv", f"csv:{cat}", "csv"

    text = f"{merchant or ''} {description or ''}".lower()

    # MCC mapping (partial)
    mcc_map = {
        "5411": "groceries",
        "5812": "restaurants",
        "5814": "fast_food",
        "4111": "transport",
        "4121": "rideshare",
        "5541": "gas",
        "4812": "telecom",
        "4899": "streaming",
        "5912": "pharmacy",
        "5943": "office_supplies",
        "6300": "insurance",
    }
    if mcc and mcc in mcc_map:
        return mcc_map[mcc], "mcc", f"mcc:{mcc}", "mcc"

    # Merchant/description regex rules with rule ids
    mapping = [
        (r"\b(spotify|netflix|hulu|apple\s*music|disney\+|prime\s*video|hbo|max|youtube\s*premium|paramount)\b",
         "subscriptions", "streaming"),
        (r"\b(starbucks|dunkin|philz|blue\s*bottle|peet'?s|coffee\s*shop)\b",
         "coffee", "coffee"),
        (r"\b(uber\s*eats|doordash|grubhub|postmates)\b",
         "food_delivery", "food_delivery"),
        (r"\b(uber|lyft)\b", "rideshare", "rideshare"),
        (r"\b(whole\s*foods|trader\s*joe'?s?|safeway|kroger|aldi|costco|walmart\s*market|grocer|grocery)\b",
         "groceries", "groceries"),
        (r"\b(chipotle|mcdonald'?s?|wendy'?s?|taco\s*bell|kfc|popeyes|panera|subway|shake\s*shack|five\s*guys)\b",
         "fast_food", "fast_food"),
        (r"\b(airbnb|marriott|hilton|hyatt|booking\.com|expedia)\b",
         "travel", "lodging_travel"),
        (r"\b(aa\s*|delta|united|southwest|jetblue|alaska\s*air)\b", "airfare", "airlines"),
        (r"\b(shell|chevron|exxon|bp|speedway|valero)\b", "gas", "gas"),
        (r"\b(comcast|xfinity|verizon|att|t-?mobile|spectrum)\b",
         "utilities", "telecom_utilities"),
        (r"\b(gym|fitness|planet\s*fitness|equino?x|orange\s*theory)\b",
         "fitness", "fitness"),
        (r"\b(amazon|amzn)\b", "shopping", "amazon"),
        (r"\b(pharmacy|walgreens|cvs|rite\s*aid)\b", "pharmacy", "pharmacy"),
        (r"\b(rent|landlord|property\s*management)\b", "rent", "rent"),
        (r"\b(interest|fee|overdraft|atm\s*fee)\b", "bank_fees", "bank_fees"),
        (r"\b(venmo|cash\s*app|paypal|zelle)\b", "p2p", "p2p"),
    ]
    for pat, cat, rule_id in mapping:
        m = re.search(pat, text)
        if m:
            token = m.group(1) if m.groups() else m.group(0)
            return cat, "regex", f"regex:{rule_id}:{token}", rule_id
    return None, "fallback", "none", "fallback"


def parse_csv_transactions(
    content: bytes, *, user_id: str, default_account_id: Optional[str] = None
) -> List[Dict]:
    text = content.decode("utf-8", errors="ignore")
    reader = csv.DictReader(io.StringIO(text))
    out: List[Dict] = []
    for row in reader:
        # Field mapping and normalization
        r_date = row.get("date") or row.get(
            "transaction_date") or row.get("posted_date")
        r_amount = row.get("amount") or row.get(
            "transaction_amount") or row.get("debit") or row.get("credit")
        r_merchant = row.get("merchant") or row.get("name") or ""
        r_desc = row.get("description") or row.get(
            "details") or row.get("memo") or r_merchant
        r_cat = row.get("category")
        r_mcc = row.get("mcc")
        r_acc = row.get("account_id") or default_account_id

        # If CSV has separate debit/credit columns, combine
        if row.get("debit") and not row.get("amount"):
            r_amount = f"-{row.get('debit')}"
        if row.get("credit") and not row.get("amount"):
            r_amount = row.get("credit")

        norm_amount = _parse_amount(r_amount)
        norm_date = _parse_date(r_date)
        merchant = (r_merchant or "").strip() or None
        description = (r_desc or "").strip() or merchant

        category, category_source, category_prov, _rule = categorize_with_provenance(
            merchant, description, r_mcc, r_cat)

        # If CSV did not provide a category, try the trained ML categorizer (if available)
        # and only accept its top prediction when confidence >= 0.7 to preserve heuristics.
        try:
            if (not r_cat or not str(r_cat).strip()):
                # import locally to avoid hard importing sklearn when not needed
                from ai_categorizer import has_model, predict_for_user

                if has_model(user_id):
                    preds = predict_for_user(
                        user_id, merchant, description, top_k=1)
                    tops = preds.get("predictions") or []
                    if tops:
                        top = tops[0]
                        prob = float(top.get("prob", 0.0))
                        if prob >= 0.7:
                            category = top.get("label")
                            category_source = "ml"
                            category_prov = f"ml:{category}:{prob:.2f}"
        except Exception:
            # If ML is not available or prediction fails, fall back to the existing mapping
            pass

        # If CSV didn't provide is_recurring, apply a small heuristic to detect subscriptions
        # (streaming/known vendors or keywords). This is a lightweight fallback when there's
        # no explicit column; for stronger detection one could add a trained model later.
        if row.get("is_recurring") is None:
            rec_keywords = [
                r"subscription", r"monthly", r"annual", r"recurring", r"renewal", r"membership",
            ]
            rec_vendors = [
                "spotify", "netflix", "hulu", "apple music", "prime video", "amazon", "patreon",
            ]
            text_low = (f"{merchant or ''} {description or ''}".lower())
            is_rec = False
            for kw in rec_keywords:
                if re.search(kw, text_low):
                    is_rec = True
                    break
            if not is_rec:
                for v in rec_vendors:
                    if v in text_low:
                        is_rec = True
                        break
            is_recurring = bool(is_rec)
        else:
            is_recurring = _to_bool(row.get("is_recurring"))

        # Parse optional balance column
        balance = row.get("balance")
        try:
            balance = float(str(balance).replace(",", "").replace("$", "").strip()) if balance not in (None, "") else None
        except Exception:
            balance = None

        # Generate a stable natural ID to avoid collisions from CSV-provided ids
        # Use user_id|account_id|date|amount_cents|merchant|description
        cents = int(round(norm_amount * 100))
        natural_key = f"{user_id}|{r_acc or ''}|{norm_date}|{cents}|{(merchant or '').lower()}|{(description or '').lower()}"
        tx_id = hashlib.sha1(natural_key.encode("utf-8")).hexdigest()

        rec: Dict = {
            "id": tx_id,
            "user_id": user_id,
            "account_id": r_acc,
            "date": norm_date,
            "amount": norm_amount,
            "merchant": merchant,
            "description": description,
            "category": category,
            "category_source": category_source,
            "category_provenance": category_prov,
            "is_recurring": is_recurring,
            "mcc": r_mcc,
            "source": "csv",
            "balance": balance,
        }

        out.append(rec)
    return out


def dupe_hash(user_id: str, date: str, amount: float, merchant: Optional[str]) -> str:
    # Normalize values: lower merchant, round to cents
    m = (merchant or "").strip().lower()
    cents = int(round(float(amount) * 100))
    key = f"{user_id}|{date}|{cents}|{m}"
    return hashlib.sha1(key.encode("utf-8")).hexdigest()
