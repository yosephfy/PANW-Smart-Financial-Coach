"use client";

import { useEffect, useState } from 'react';

const API = process.env.NEXT_PUBLIC_API_URL || 'http://127.0.0.1:8000';

type Tx = {
  id: string;
  date: string;
  amount: number;
  merchant?: string;
  description?: string;
  category?: string | null;
  category_source?: string | null;
  category_provenance?: string | null;
  is_recurring?: boolean;
  mcc?: string | null;
  account_id?: string | null;
};

export default function TransactionsPage() {
  const [userId, setUserId] = useState('u_demo');
  const [limit, setLimit] = useState(50);
  const [rows, setRows] = useState<Tx[]>([]);
  const [busy, setBusy] = useState(false);

  const load = async () => {
    setBusy(true);
    try {
      const res = await fetch(`${API}/users/${encodeURIComponent(userId)}/transactions?limit=${limit}`);
      const json = await res.json();
      setRows(Array.isArray(json) ? json : []);
    } finally {
      setBusy(false);
    }
  };

  useEffect(() => {
    load();
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, []);

  return (
    <div className="space-y-4">
      <h2 className="text-lg font-semibold">Transactions</h2>
      <div className="flex gap-3 items-end">
        <label className="text-sm">
          <div className="text-slate-300">User ID</div>
          <input className="mt-1 rounded border border-slate-600 bg-slate-100 px-2 py-1" value={userId} onChange={(e) => setUserId(e.target.value)} />
        </label>
        <label className="text-sm">
          <div className="text-slate-300">Limit</div>
          <input type="number" className="mt-1 w-24 rounded border border-slate-600 bg-slate-100 px-2 py-1" value={limit} onChange={(e) => setLimit(parseInt(e.target.value || '50', 10))} />
        </label>
        <button onClick={load} disabled={busy} className="rounded bg-blue-500 text-white px-3 py-1 disabled:opacity-50">{busy ? 'Loading…' : 'Refresh'}</button>
      </div>

      <div className="overflow-auto border border-slate-700 rounded">
        <table className="min-w-full text-sm">
          <thead className="bg-slate-800/60">
            <tr className="text-left">
              <th className="px-3 py-2">Date</th>
              <th className="px-3 py-2">Merchant</th>
              <th className="px-3 py-2">Description</th>
              <th className="px-3 py-2">Amount</th>
              <th className="px-3 py-2">Category</th>
              <th className="px-3 py-2">Source</th>
              <th className="px-3 py-2">Provenance</th>
            </tr>
          </thead>
          <tbody>
            {rows.map((r) => (
              <tr key={r.id} className="border-t border-slate-700/60">
                <td className="px-3 py-2 whitespace-nowrap">{r.date}</td>
                <td className="px-3 py-2">{r.merchant || '-'}</td>
                <td className="px-3 py-2 text-slate-300">{r.description || '-'}</td>
                <td className={`px-3 py-2 whitespace-nowrap ${r.amount < 0 ? 'text-red-300' : 'text-green-300'}`}>{r.amount.toFixed(2)}</td>
                <td className="px-3 py-2">{r.category || '-'}</td>
                <td className="px-3 py-2 text-slate-400">{r.category_source || '-'}</td>
                <td className="px-3 py-2 text-slate-400">{r.category_provenance || '-'}</td>
              </tr>
            ))}
            {rows.length === 0 && (
              <tr>
                <td colSpan={7} className="px-3 py-6 text-center text-slate-400">No transactions</td>
              </tr>
            )}
          </tbody>
        </table>
      </div>
    </div>
  );
}

