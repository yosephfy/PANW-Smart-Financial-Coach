"use client";

import { useEffect, useState } from 'react';
import { useUser } from '../../components/Providers';

const API = process.env.NEXT_PUBLIC_API_URL || 'http://localhost:8000';

declare global {
  interface Window { Plaid?: any }
}

export default function PlaidPage() {
  const { userId } = useUser();
  const [linkReady, setLinkReady] = useState(false);
  const [linkOpen, setLinkOpen] = useState<null | (() => void)>(null);
  const [message, setMessage] = useState<string>('');
  const [items, setItems] = useState<{item_id:string; institution_name?:string; created_at?:string}[]>([]);

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
            await loadItems();
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

  const loadItems = async () => {
    if (!userId) return;
    const r = await fetch(`${API}/plaid/items/me`, { headers: { 'X-User-Id': userId } });
    const j = await r.json();
    if (Array.isArray(j)) setItems(j);
  };

  const deleteItem = async (item_id: string) => {
    if (!userId) return;
    await fetch(`${API}/plaid/items/${encodeURIComponent(item_id)}`, { method:'DELETE', headers: { 'X-User-Id': userId } });
    await loadItems();
  };

  useEffect(() => { loadItems(); }, [userId]);

  return (
    <div className="space-y-4">
      <h2 className="text-lg font-semibold">Plaid Sandbox</h2>
      <div className="flex gap-3 items-end">
        <button onClick={startLink} disabled={!linkReady || !userId} className="rounded bg-emerald-500 text-white px-3 py-1 disabled:opacity-50">
          {linkReady ? 'Connect Sandbox Bank' : 'Loading Link…'}
        </button>
        <button onClick={importTx} disabled={!userId} className="rounded bg-blue-500 text-white px-3 py-1 disabled:opacity-50">
          Import Transactions (30d)
        </button>
        <button onClick={loadItems} disabled={!userId} className="rounded bg-slate-600 text-white px-3 py-1 disabled:opacity-50">Refresh Items</button>
      </div>
      {message && <pre className="text-xs bg-slate-900/70 p-3 rounded overflow-auto">{message}</pre>}

      <p className="text-slate-400 text-sm">
        Tip: In Sandbox, pick Test credentials in Plaid Link, then use the Import button to pull transactions into the database.
      </p>

      <div className="mt-4">
        <div className="text-sm font-semibold mb-2">Linked Items</div>
        {items.length === 0 ? (
          <div className="text-sm text-slate-400">No items linked.</div>
        ) : (
          <table className="min-w-full text-sm border border-slate-700">
            <thead className="bg-slate-800/60">
              <tr className="text-left">
                <th className="px-3 py-2">Item ID</th>
                <th className="px-3 py-2">Institution</th>
                <th className="px-3 py-2">Created</th>
                <th className="px-3 py-2">Actions</th>
              </tr>
            </thead>
            <tbody>
              {items.map(i => (
                <tr key={i.item_id} className="border-t border-slate-700/60">
                  <td className="px-3 py-2">{i.item_id}</td>
                  <td className="px-3 py-2">{i.institution_name || '-'}</td>
                  <td className="px-3 py-2">{i.created_at || '-'}</td>
                  <td className="px-3 py-2">
                    <button onClick={()=>deleteItem(i.item_id)} className="px-2 py-0.5 rounded bg-red-700 text-white text-xs">Delete</button>
                  </td>
                </tr>
              ))}
            </tbody>
          </table>
        )}
      </div>
    </div>
  );
}
