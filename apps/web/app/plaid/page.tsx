"use client";

import { useEffect, useState } from 'react';

const API = process.env.NEXT_PUBLIC_API_URL || 'http://127.0.0.1:8000';

declare global {
  interface Window { Plaid?: any }
}

export default function PlaidPage() {
  const [userId, setUserId] = useState('u_demo');
  const [linkReady, setLinkReady] = useState(false);
  const [linkOpen, setLinkOpen] = useState<null | (() => void)>(null);
  const [message, setMessage] = useState<string>('');

  useEffect(() => {
    // Load Plaid script if not present
    if (!window.Plaid) {
      const s = document.createElement('script');
      s.src = 'https://cdn.plaid.com/link/v2/stable/link-initialize.js';
      s.async = true;
      s.onload = () => setLinkReady(true);
      s.onerror = () => setMessage('Failed to load Plaid Link script');
      document.body.appendChild(s);
    } else {
      setLinkReady(true);
    }
  }, []);

  const startLink = async () => {
    setMessage('');
    try {
      const res = await fetch(`${API}/plaid/link/token/create`, {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ user_id: userId }),
      });
      const json = await res.json();
      const link_token = json.link_token;
      if (!link_token || !window.Plaid) {
        setMessage('Could not obtain link_token. Check backend env.');
        return;
      }
      const handler = window.Plaid.create({
        token: link_token,
        onSuccess: async (public_token: string) => {
          setMessage('Exchanging public_token...');
          const r = await fetch(`${API}/plaid/link/public_token/exchange`, {
            method: 'POST',
            headers: { 'Content-Type': 'application/json' },
            body: JSON.stringify({ user_id: userId, public_token }),
          });
          const j = await r.json();
          if ((j && j.item_id) || r.ok) {
            setMessage('Linked! You can now import transactions.');
          } else {
            setMessage('Token exchange failed: ' + JSON.stringify(j));
          }
        },
        onExit: () => {
          setMessage('Link exited.');
        },
      });
      setLinkOpen(() => handler.open);
      handler.open();
    } catch (e: any) {
      setMessage('Error: ' + e?.message || String(e));
    }
  };

  const importTx = async () => {
    setMessage('Importing last 30 days from Plaid...');
    const r = await fetch(`${API}/plaid/transactions/import`, {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({ user_id: userId }),
    });
    const j = await r.json();
    setMessage('Import done: ' + JSON.stringify(j));
  };

  return (
    <div className="space-y-4">
      <h2 className="text-lg font-semibold">Plaid Sandbox</h2>
      <div className="flex gap-3 items-end">
        <label className="text-sm">
          <div className="text-slate-300">User ID</div>
          <input className="mt-1 rounded border border-slate-600 bg-slate-100 px-2 py-1" value={userId} onChange={(e) => setUserId(e.target.value)} />
        </label>
        <button onClick={startLink} disabled={!linkReady} className="rounded bg-emerald-500 text-white px-3 py-1 disabled:opacity-50">
          {linkReady ? 'Connect Sandbox Bank' : 'Loading Link…'}
        </button>
        <button onClick={importTx} className="rounded bg-blue-500 text-white px-3 py-1">
          Import Transactions (30d)
        </button>
      </div>
      {message && <pre className="text-xs bg-slate-900/70 p-3 rounded overflow-auto">{message}</pre>}

      <p className="text-slate-400 text-sm">
        Tip: In Sandbox, pick Test credentials in Plaid Link, then use the Import button to pull transactions into the database.
      </p>
    </div>
  );
}

