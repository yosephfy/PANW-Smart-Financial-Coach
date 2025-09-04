"use client";

import { useEffect, useState } from 'react'
import { useUser } from '../../components/Providers'

const API = process.env.NEXT_PUBLIC_API_URL || 'http://localhost:8000';

type Plan = {
  target_date: string
  months_left: number
  current_surplus_monthly: number
  required_monthly: number
  gap: number
  on_track: boolean
  suggested_plan: { category: string; forecast_spend: number; suggested_cut: number; cut_pct: number; forecast_model?: string; max_cut_pct?: number }[]
  total_potential?: number
  feasible?: boolean
  shortfall?: number
}

type Goal = {
  id: string
  name: string
  target_amount: number
  target_date: string
  status: string
  plan?: Plan
}

export default function GoalsPage() {
  const ctx = useUser()
  const [name, setName] = useState('Save $3000 for down payment')
  const [amount, setAmount] = useState(3000)
  const [date, setDate] = useState('2025-12-31')
  const [busy, setBusy] = useState(false)
  const [goals, setGoals] = useState<Goal[]>([])

  const load = async () => {
    setBusy(true)
    try {
      if (!ctx.userId) {
        setGoals([])
        return
      }
      if (!ctx.userId) return
      const res = await fetch(`${API}/users/${encodeURIComponent(ctx.userId)}/goals`)
      const json = await res.json()
      setGoals(Array.isArray(json) ? json : [])
    } finally { setBusy(false) }
  }

  const createGoal = async (e: React.FormEvent) => {
    e.preventDefault()
    setBusy(true)
    try {
      if (!ctx.userId) {
        ctx.showToast('Sign in to create goals', 'warning')
        return
      }
      const res = await fetch(`${API}/goals`, { method: 'POST', headers: { 'Content-Type': 'application/json' }, body: JSON.stringify({ user_id: ctx.userId, name, target_amount: amount, target_date: date }) })
      if (!res.ok) {
        const j = await res.json().catch(()=>null)
        throw new Error(j?.detail || 'Failed to create goal')
      }
      const created = await res.json()
      ctx.showToast('Goal created', 'success')
      // Optimistically update list with the created goal
      setGoals(prev => [created, ...prev])
      // Also refresh from server to ensure consistency
      await load()
    } finally { setBusy(false) }
  }

  useEffect(() => { load() }, [ctx.userId])

  return (
    <div className="space-y-4">
      <h2 className="text-lg font-semibold">Goals</h2>
      <form onSubmit={createGoal} className="border border-slate-700 rounded p-4 space-y-3">
        <div className="grid md:grid-cols-3 gap-3">
          <label className="text-sm md:col-span-2">
            <div className="text-slate-300">Goal Name</div>
            <input className="mt-1 w-full rounded border border-slate-600 bg-slate-100 px-2 py-1" value={name} onChange={e=>setName(e.target.value)} />
          </label>
          <label className="text-sm">
            <div className="text-slate-300">Target Amount</div>
            <input type="number" className="mt-1 w-full rounded border border-slate-600 bg-slate-100 px-2 py-1" value={amount} onChange={e=>setAmount(parseFloat(e.target.value || '0'))} />
          </label>
          <label className="text-sm">
            <div className="text-slate-300">Target Date</div>
            <input type="date" className="mt-1 w-full rounded border border-slate-600 bg-slate-100 px-2 py-1" value={date} onChange={e=>setDate(e.target.value)} />
          </label>
        </div>
        <div className="flex gap-3">
          <button className="rounded bg-emerald-500 text-white px-3 py-1 disabled:opacity-50" disabled={busy}>Create Goal</button>
          <button type="button" className="rounded bg-blue-500 text-white px-3 py-1 disabled:opacity-50" disabled={busy} onClick={load}>{busy ? 'Loading…' : 'Refresh'}</button>
        </div>
      </form>

      {!ctx.userId && (
        <div className="text-sm text-amber-300 border border-amber-700/50 rounded p-3">
          Sign in to view and create goals.
        </div>
      )}

      <div className="grid gap-3">
        {goals.map(g => (
          <div key={g.id} className="border border-slate-700 rounded p-4">
            <div className="flex items-center gap-3">
              <div className="font-semibold">{g.name}</div>
              <div className="text-sm text-slate-400">Target: ${g.target_amount} by {g.target_date}</div>
              <div className={`ml-auto text-xs ${g.plan?.on_track ? 'text-emerald-300' : 'text-amber-300'}`}>{g.plan?.on_track ? 'On Track' : 'Needs Adjustments'}</div>
            </div>
            <div className="mt-2 text-xs flex gap-2">
              <span className="text-slate-400">Status: {g.status || 'active'}</span>
              <button
                onClick={async()=>{ await fetch(`${API}/goals/${encodeURIComponent(g.id)}`, { method:'PATCH', headers:{'Content-Type':'application/json'}, body: JSON.stringify({ status: 'active' })}); await load(); }}
                className="px-2 py-0.5 rounded bg-slate-700"
              >Active</button>
              <button
                onClick={async()=>{ await fetch(`${API}/goals/${encodeURIComponent(g.id)}`, { method:'PATCH', headers:{'Content-Type':'application/json'}, body: JSON.stringify({ status: 'paused' })}); await load(); }}
                className="px-2 py-0.5 rounded bg-slate-700"
              >Pause</button>
              <button
                onClick={async()=>{ await fetch(`${API}/goals/${encodeURIComponent(g.id)}`, { method:'PATCH', headers:{'Content-Type':'application/json'}, body: JSON.stringify({ status: 'achieved' })}); await load(); }}
                className="px-2 py-0.5 rounded bg-emerald-700"
              >Mark Achieved</button>
              <button
                onClick={async()=>{ await fetch(`${API}/goals/${encodeURIComponent(g.id)}`, { method:'PATCH', headers:{'Content-Type':'application/json'}, body: JSON.stringify({ status: 'canceled' })}); await load(); }}
                className="px-2 py-0.5 rounded bg-red-700"
              >Cancel</button>
            </div>
            {g.plan && (
              <div className="mt-2 grid md:grid-cols-4 gap-3 text-sm">
                <div className="rounded border border-slate-600 p-2">
                  <div className="text-slate-400">Months Left</div>
                  <div className="font-semibold">{g.plan.months_left}</div>
                </div>
                <div className="rounded border border-slate-600 p-2">
                  <div className="text-slate-400">Required Monthly</div>
                  <div className="font-semibold">${g.plan.required_monthly.toFixed(0)}</div>
                </div>
                <div className="rounded border border-slate-600 p-2">
                  <div className="text-slate-400">Current Surplus</div>
                  <div className="font-semibold">${g.plan.current_surplus_monthly.toFixed(0)}</div>
                </div>
                <div className="rounded border border-slate-600 p-2">
                  <div className="text-slate-400">Gap</div>
                  <div className="font-semibold">${g.plan.gap.toFixed(0)}</div>
                </div>
              </div>
            )}
            {g.plan && g.plan.feasible === false && (
              <div className="mt-2 text-sm text-amber-300">
                Plan may be unrealistic. Even with aggressive cuts, shortfall is ${g.plan.shortfall?.toFixed(0)} next month. Consider extending the target date or increasing income.
              </div>
            )}
            {g.plan?.suggested_plan?.length ? (
              <div className="mt-3">
                <div className="text-sm text-slate-300 mb-1">Suggested Cuts (variable, based on forecast and category realism):</div>
                <div className="grid md:grid-cols-3 gap-2 text-sm">
                  {g.plan.suggested_plan.map(sp => (
                    <div key={sp.category} className="rounded border border-slate-600 p-2">
                      <div className="font-semibold">{sp.category}</div>
                      <div className="text-slate-400">Forecast: ${sp.forecast_spend.toFixed(0)}{sp.forecast_model ? ` (${sp.forecast_model})` : ''}</div>
                      {typeof sp.max_cut_pct === 'number' && (
                        <div className="text-slate-500 text-xs">Max cut: {(sp.max_cut_pct*100).toFixed(0)}%</div>
                      )}
                      <div className="text-amber-300">Cut: -${sp.suggested_cut.toFixed(0)} ({(sp.cut_pct*100).toFixed(0)}%)</div>
                    </div>
                  ))}
                </div>
              </div>
            ) : (
              <div className="text-sm text-slate-400 mt-2">No cuts suggested (you may already be on track).</div>
            )}
          </div>
        ))}
        {goals.length === 0 && (
          <div className="text-center text-slate-400 border border-slate-700 rounded py-10">No goals yet</div>
        )}
      </div>
    </div>
  )
}
