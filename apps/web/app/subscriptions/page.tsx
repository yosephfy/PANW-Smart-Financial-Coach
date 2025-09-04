"use client";

import { useEffect, useMemo, useState } from "react";
import { useUser } from "../../components/Providers";
import { Badge } from "../../components/Badge";
import { fmtCurrency, fmtPct } from "../../components/format";
import {
  ResponsiveContainer,
  BarChart,
  XAxis,
  YAxis,
  Tooltip,
  Bar,
  Cell,
} from "recharts";

const API = process.env.NEXT_PUBLIC_API_URL || "http://localhost:8000";

type Sub = {
  merchant: string;
  avg_amount: number;
  cadence: string;
  last_seen: string;
  status: string;
  price_change_pct?: number | null;
  trial_converted?: boolean;
};

export default function SubscriptionsPage() {
  const ctx = useUser();
  const [rows, setRows] = useState<Sub[]>([]);
  const [busy, setBusy] = useState(false);
  const [detecting, setDetecting] = useState(false);
  const [updating, setUpdating] = useState<string | null>(null);

  const chartData = useMemo(() => {
    return rows
      .map((r) => ({ name: r.merchant, value: r.avg_amount }))
      .sort((a, b) => b.value - a.value)
      .slice(0, 10);
  }, [rows]);

  const load = async () => {
    setBusy(true);
    try {
      const res = await fetch(
        `${API}/me/subscriptions`, { headers: ctx.userId ? { 'X-User-Id': ctx.userId } : undefined }
      );
      const json = await res.json();
      setRows(Array.isArray(json) ? json : []);
    } catch (err) {
      ctx.showToast(String(err), "error");
    } finally {
      setBusy(false);
    }
  };

  const detect = async () => {
    setDetecting(true);
    try {
      await fetch(`${API}/subscriptions/detect`, {
        method: "POST",
        headers: { "Content-Type": "application/json", ...(ctx.userId ? { 'X-User-Id': ctx.userId } : {}) },
        body: JSON.stringify({}),
      });
      await load();
      ctx.showToast("Subscription detection completed", "success");
    } finally {
      setDetecting(false);
    }
  };

  useEffect(() => {
    if (ctx.userId) load();
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [ctx.userId]);

  const setStatus = async (merchant: string, status: 'active'|'paused'|'canceled') => {
    if (!ctx.userId) return;
    setUpdating(merchant);
    try {
      const res = await fetch(`${API}/subscriptions/${encodeURIComponent(merchant)}`, {
        method: 'PATCH',
        headers: { 'Content-Type': 'application/json', 'X-User-Id': ctx.userId },
        body: JSON.stringify({ status }),
      });
      if (!res.ok) {
        const j = await res.json().catch(()=>null);
        throw new Error(j?.detail || 'Update failed');
      }
      await load();
      ctx.showToast(`Marked ${merchant} as ${status}`,'success');
    } catch (e:any) {
      ctx.showToast(e?.message || String(e), 'error');
    } finally {
      setUpdating(null);
    }
  };

  return (
    <div className="space-y-4">
      <h2 className="text-lg font-semibold">Subscriptions</h2>
      <div className="flex gap-3 items-end">
        <button
          onClick={load}
          disabled={busy}
          className="rounded bg-blue-500 text-white px-3 py-1 disabled:opacity-50"
        >
          {busy ? "Loading…" : "Refresh"}
        </button>
        <button
          onClick={detect}
          disabled={detecting}
          className="rounded bg-emerald-500 text-white px-3 py-1 disabled:opacity-50"
        >
          {detecting ? "Detecting…" : "Run Detection"}
        </button>
      </div>

      {!!chartData.length && (
        <div className="border border-slate-700 rounded p-3">
          <div className="flex items-center justify-between mb-2">
            <div className="font-semibold">Top Subscriptions</div>
            <div className="text-xs text-slate-400">By average amount</div>
          </div>
          <div className="h-64">
            <ResponsiveContainer width="100%" height="100%">
              <BarChart data={chartData}>
                <XAxis
                  dataKey="name"
                  tick={{ fill: "#cbd5e1", fontSize: 12 }}
                  interval={0}
                  angle={-15}
                  textAnchor="end"
                  height={60}
                />
                <YAxis
                  tick={{ fill: "#cbd5e1", fontSize: 12 }}
                  tickFormatter={(v) => `$${Math.round(v)}`}
                />
                <Tooltip
                  formatter={(v: number) => fmtCurrency(v)}
                  contentStyle={{
                    background: "#0f172a",
                    border: "1px solid #334155",
                    borderRadius: 8,
                  }}
                  labelStyle={{ color: "#cbd5e1" }}
                />
                <Bar dataKey="value" radius={[4, 4, 0, 0]}>
                  {chartData.map((_, i) => (
                    <Cell
                      key={i}
                      fill={
                        [
                          "#60a5fa",
                          "#34d399",
                          "#f59e0b",
                          "#f97316",
                          "#c084fc",
                          "#f472b6",
                          "#22d3ee",
                          "#a3e635",
                        ][i % 8]
                      }
                    />
                  ))}
                </Bar>
              </BarChart>
            </ResponsiveContainer>
          </div>
        </div>
      )}

      <div className="overflow-auto border border-slate-700 rounded mt-4">
        <table className="min-w-full text-sm">
          <thead className="bg-slate-800/60">
            <tr className="text-left">
              <th className="px-3 py-2">Merchant</th>
              <th className="px-3 py-2">Avg Amount</th>
              <th className="px-3 py-2">Cadence</th>
              <th className="px-3 py-2">Last Seen</th>
              <th className="px-3 py-2">Status</th>
              <th className="px-3 py-2">Trial</th>
              <th className="px-3 py-2">Price Change %</th>
            </tr>
          </thead>
          <tbody>
            {rows.map((r) => (
              <tr
                key={`${r.merchant}-${r.cadence}`}
                className="border-t border-slate-700/60"
              >
                <td className="px-3 py-2">{r.merchant}</td>
                <td className="px-3 py-2 text-amber-200">
                  -{fmtCurrency(r.avg_amount)}
                </td>
                <td className="px-3 py-2">
                  <Badge variant="info">{r.cadence}</Badge>
                </td>
                <td className="px-3 py-2">{r.last_seen}</td>
                <td className="px-3 py-2">
                  <Badge variant={r.status === "active" ? "success" : r.status === 'canceled' ? 'danger' : 'warning'}>
                    {r.status}
                  </Badge>
                  <div className="inline-flex gap-1 ml-2">
                    <button disabled={updating===r.merchant} onClick={()=>setStatus(r.merchant,'active')} className="px-2 py-0.5 rounded bg-slate-700">Active</button>
                    <button disabled={updating===r.merchant} onClick={()=>setStatus(r.merchant,'paused')} className="px-2 py-0.5 rounded bg-slate-700">Pause</button>
                    <button disabled={updating===r.merchant} onClick={()=>setStatus(r.merchant,'canceled')} className="px-2 py-0.5 rounded bg-red-700">Cancel</button>
                  </div>
                </td>
                <td className="px-3 py-2">
                  {r.trial_converted ? (
                    <Badge variant="warning">Trial converted</Badge>
                  ) : (
                    <span className="text-slate-400">-</span>
                  )}
                </td>
                <td
                  className={`px-3 py-2 ${
                    r.price_change_pct && r.price_change_pct > 0
                      ? "text-amber-300"
                      : "text-slate-300"
                  }`}
                >
                  {r.price_change_pct != null
                    ? fmtPct(r.price_change_pct)
                    : "-"}
                </td>
              </tr>
            ))}
            {rows.length === 0 && (
              <tr>
                <td
                  colSpan={7}
                  className="px-3 py-6 text-center text-slate-400"
                >
                  No subscriptions detected
                </td>
              </tr>
            )}
          </tbody>
        </table>
      </div>
    </div>
  );
}
