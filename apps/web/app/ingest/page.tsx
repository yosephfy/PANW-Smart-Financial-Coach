"use client";

import { useState } from 'react';

const API = process.env.NEXT_PUBLIC_API_URL || 'http://127.0.0.1:8000';

export default function IngestPage() {
  const [userId, setUserId] = useState('u_demo');
  const [accountId, setAccountId] = useState('a_checking');
  const [file, setFile] = useState<File | null>(null);
  const [result, setResult] = useState<any>(null);
  const [busy, setBusy] = useState(false);

  const submit = async (e: React.FormEvent) => {
    e.preventDefault();
    if (!file) return;
    setBusy(true);
    setResult(null);
    try {
      const form = new FormData();
      form.append('file', file);
      form.append('user_id', userId);
      if (accountId) form.append('default_account_id', accountId);
      const res = await fetch(`${API}/ingest/csv`, {
        method: 'POST',
        body: form,
      });
      const json = await res.json();
      setResult(json);
    } catch (err) {
      setResult({ error: String(err) });
    } finally {
      setBusy(false);
    }
  };

  return (
    <div className="space-y-4">
      <h2 className="text-lg font-semibold">CSV Ingestion</h2>
      <form onSubmit={submit} className="space-y-3 border border-slate-700 p-4 rounded">
        <div className="grid md:grid-cols-3 gap-4">
          <label className="block text-sm">
            <span className="text-slate-300">User ID</span>
            <input className="mt-1 w-full rounded border border-slate-600 bg-slate-100 px-2 py-1" value={userId} onChange={(e) => setUserId(e.target.value)} />
          </label>
          <label className="block text-sm">
            <span className="text-slate-300">Default Account ID</span>
            <input className="mt-1 w-full rounded border border-slate-600 bg-slate-100 px-2 py-1" value={accountId} onChange={(e) => setAccountId(e.target.value)} />
          </label>
          <label className="block text-sm">
            <span className="text-slate-300">CSV File</span>
            <input className="mt-1 w-full text-slate-200" type="file" accept=".csv" onChange={(e) => setFile(e.target.files?.[0] || null)} />
          </label>
        </div>
        <button disabled={busy || !file} className="rounded bg-blue-500 text-white px-3 py-1 disabled:opacity-50">
          {busy ? 'Uploading…' : 'Upload & Ingest'}
        </button>
      </form>

      {result && (
        <pre className="text-xs bg-slate-900/70 p-3 rounded overflow-auto">{JSON.stringify(result, null, 2)}</pre>
      )}
    </div>
  );
}

