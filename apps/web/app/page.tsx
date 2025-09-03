"use client";

import { useEffect, useState } from 'react'

const API = process.env.NEXT_PUBLIC_API_URL || 'http://127.0.0.1:8000';

type ForecastItem = { category: string; forecast_next_month: number }

export default function Home() {
  const [userId, setUserId] = useState('u_demo')
  const [busy, setBusy] = useState(false)
  const [items, setItems] = useState<ForecastItem[]>([])

  const load = async () => {
    setBusy(true)
    try {
      const res = await fetch(`${API}/forecast/categories`, { method: 'POST', headers: { 'Content-Type': 'application/json' }, body: JSON.stringify({ user_id: userId, months_history: 6, top_k: 3 }) })
      const json = await res.json()
      setItems(json?.forecasts || [])
    } finally { setBusy(false) }
  }

  useEffect(() => { load() }, [])

  return (
    <div className="space-y-4">
      <h2 className="text-lg font-semibold">Welcome</h2>
      <p className="text-slate-300">Use the links above to upload a CSV, view transactions, subscriptions, and insights. Below is a quick forecast preview for next month.</p>

      <div className="border border-slate-700 rounded p-4">
        <div className="flex items-end gap-3 mb-3">
          <label className="text-sm">
            <div className="text-slate-300">User ID</div>
            <input className="mt-1 rounded border border-slate-600 bg-slate-100 px-2 py-1" value={userId} onChange={(e) => setUserId(e.target.value)} />
          </label>
          <button onClick={load} disabled={busy} className="rounded bg-blue-500 text-white px-3 py-1 disabled:opacity-50">{busy ? 'Loading…' : 'Refresh Forecast'}</button>
        </div>
        <div className="grid md:grid-cols-3 gap-3">
          {items.map((it) => (
            <div key={it.category} className="rounded border border-slate-600 p-3">
              <div className="text-sm text-slate-400">Category</div>
              <div className="font-semibold">{it.category}</div>
              <div className="mt-2 text-sm">Forecast next month: <span className="text-emerald-300">${it.forecast_next_month.toFixed(0)}</span></div>
              <div className="text-xs text-slate-400">Suggestion: aim to trim ~20% if discretionary → save ~${Math.round(it.forecast_next_month * 0.2)}</div>
            </div>
          ))}
          {items.length === 0 && (
            <div className="text-slate-400 text-sm">No forecast yet. Ingest some transactions first.</div>
          )}
        </div>
      </div>

      <div className="grid md:grid-cols-3 gap-4 mt-2">
        <a href="/ingest" className="block rounded border border-slate-700 p-4 hover:bg-slate-800/40">
          <h3 className="font-semibold mb-1">CSV Ingest</h3>
          <p className="text-sm text-slate-400">Upload CSV for a user and import transactions.</p>
        </a>
        <a href="/transactions" className="block rounded border border-slate-700 p-4 hover:bg-slate-800/40">
          <h3 className="font-semibold mb-1">Transactions</h3>
          <p className="text-sm text-slate-400">View the latest transactions by user.</p>
        </a>
        <a href="/subscriptions" className="block rounded border border-slate-700 p-4 hover:bg-slate-800/40">
          <h3 className="font-semibold mb-1">Subscriptions</h3>
          <p className="text-sm text-slate-400">Detect and list recurring subscriptions.</p>
        </a>
      </div>
    </div>
  )
}
