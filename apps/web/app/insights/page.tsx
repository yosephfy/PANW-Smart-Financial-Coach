"use client";

import { useEffect, useState } from 'react';
import { Badge } from '../../components/Badge';

const API = process.env.NEXT_PUBLIC_API_URL || 'http://127.0.0.1:8000';

type Insight = {
  id: string
  type: string
  title: string
  body: string
  severity: 'info' | 'warn' | 'critical' | string
  data_json?: string
  created_at?: string
}

function severityVariant(sev?: string) {
  switch (sev) {
    case 'critical': return 'danger'
    case 'warn': return 'warning'
    case 'info': return 'info'
    default: return 'neutral'
  }
}

export default function InsightsPage() {
  const [userId, setUserId] = useState('u_demo');
  const [rows, setRows] = useState<Insight[]>([]);
  const [busy, setBusy] = useState(false);
  const [genBusy, setGenBusy] = useState(false);

  const load = async () => {
    setBusy(true);
    try {
      const res = await fetch(`${API}/users/${encodeURIComponent(userId)}/insights`)
      const json = await res.json()
      setRows(Array.isArray(json) ? json : [])
    } finally {
      setBusy(false)
    }
  }

  const generate = async () => {
    setGenBusy(true)
    try {
      await fetch(`${API}/insights/generate`, {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ user_id: userId }),
      })
      await load()
    } finally {
      setGenBusy(false)
    }
  }

  useEffect(() => { load() }, [])

  return (
    <div className="space-y-4">
      <h2 className="text-lg font-semibold">Insights</h2>
      <div className="flex gap-3 items-end">
        <label className="text-sm">
          <div className="text-slate-300">User ID</div>
          <input className="mt-1 rounded border border-slate-600 bg-slate-100 px-2 py-1" value={userId} onChange={(e) => setUserId(e.target.value)} />
        </label>
        <button onClick={load} disabled={busy} className="rounded bg-blue-500 text-white px-3 py-1 disabled:opacity-50">{busy ? 'Loading…' : 'Refresh'}</button>
        <button onClick={generate} disabled={genBusy} className="rounded bg-emerald-500 text-white px-3 py-1 disabled:opacity-50">{genBusy ? 'Generating…' : 'Generate'}</button>
      </div>

      <div className="grid gap-3">
        {rows.map(r => (
          <div key={r.id} className="border border-slate-700 rounded p-3">
            <div className="flex items-start gap-2">
              <Badge variant={severityVariant(r.severity)}>{r.severity}</Badge>
              <div className="font-semibold">{r.title}</div>
              <div className="ml-auto text-xs text-slate-400">{r.created_at}</div>
            </div>
            <div className="text-slate-300 mt-1 text-sm">{r.body}</div>
            {r.data_json && (
              <details className="mt-2">
                <summary className="cursor-pointer text-xs text-slate-400">Details</summary>
                <pre className="text-xs bg-slate-900/70 p-3 rounded overflow-auto mt-1">{JSON.stringify(JSON.parse(r.data_json), null, 2)}</pre>
              </details>
            )}
          </div>
        ))}
        {rows.length === 0 && (
          <div className="text-center text-slate-400 border border-slate-700 rounded py-10">No insights yet</div>
        )}
      </div>
    </div>
  )
}

