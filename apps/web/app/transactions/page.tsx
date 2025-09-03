"use client";

import { useEffect, useMemo, useState } from "react";
import { useUser } from "../../components/Providers";
import { Badge } from "../../components/Badge";
import { fmtCurrency } from "../../components/format";
import { categoryVariant } from "../../components/category";
import {
  ResponsiveContainer,
  BarChart,
  XAxis,
  YAxis,
  Tooltip,
  Bar,
  Cell,
} from "recharts";

const API = process.env.NEXT_PUBLIC_API_URL || "http://127.0.0.1:8000";

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
  const ctx = useUser();
  const [userId, setUserId] = useState(ctx.userId || "u_demo");
  const [limit, setLimit] = useState(50);
  const [rows, setRows] = useState<Tx[]>([]);
  const [busy, setBusy] = useState(false);

  const categoryData = useMemo(() => {
    const map: Record<string, number> = {};
    for (const r of rows) {
      const cat = r.category || "uncategorized";
      // Sum only expenses (negative amounts)
      if (r.amount < 0) {
        map[cat] = (map[cat] || 0) + Math.abs(r.amount);
      }
    }
    const entries = Object.entries(map).map(([name, value]) => ({
      name,
      value,
    }));
    // sort desc and take top 8
    return entries.sort((a, b) => b.value - a.value).slice(0, 8);
  }, [rows]);

  const merchantData = useMemo(() => {
    const map: Record<string, number> = {};
    for (const r of rows) {
      if (!r.merchant) continue;
      if (r.amount < 0) {
        const name = r.merchant;
        map[name] = (map[name] || 0) + Math.abs(r.amount);
      }
    }
    const entries = Object.entries(map).map(([name, value]) => ({
      name,
      value,
    }));
    return entries.sort((a, b) => b.value - a.value).slice(0, 10);
  }, [rows]);

  const load = async () => {
    setBusy(true);
    try {
      const res = await fetch(
        `${API}/users/${encodeURIComponent(userId)}/transactions?limit=${limit}`
      );
      const json = await res.json();
      setRows(Array.isArray(json) ? json : []);
    } catch (err) {
      ctx.showToast(String(err), "error");
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
          <input
            className="mt-1 rounded border border-slate-600 bg-slate-100 px-2 py-1"
            value={userId}
            onChange={(e) => {
              setUserId(e.target.value);
              ctx.setUserId(e.target.value);
            }}
          />
        </label>
        <label className="text-sm">
          <div className="text-slate-300">Limit</div>
          <input
            type="number"
            className="mt-1 w-24 rounded border border-slate-600 bg-slate-100 px-2 py-1"
            value={limit}
            onChange={(e) => setLimit(parseInt(e.target.value || "50", 10))}
          />
        </label>
        <button
          onClick={load}
          disabled={busy}
          className="rounded bg-blue-500 text-white px-3 py-1 disabled:opacity-50"
        >
          {busy ? "Loading…" : "Refresh"}
        </button>
      </div>

      {!!categoryData.length && (
        <div className="border border-slate-700 rounded p-3">
          <div className="flex items-center justify-between mb-2">
            <div className="font-semibold">Top Spend by Category</div>
            <div className="text-xs text-slate-400">
              MTD sample (last fetch)
            </div>
          </div>
          <div className="h-64">
            <ResponsiveContainer width="100%" height="100%">
              <BarChart data={categoryData}>
                <XAxis
                  dataKey="name"
                  tick={{ fill: "#cbd5e1", fontSize: 12 }}
                  interval={0}
                  angle={-15}
                  textAnchor="end"
                  height={50}
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
                  {categoryData.map((_, i) => (
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

      {!!merchantData.length && (
        <div className="border border-slate-700 rounded p-3 mt-4">
          <div className="flex items-center justify-between mb-2">
            <div className="font-semibold">Spend by Merchant</div>
            <div className="text-xs text-slate-400">Top 10</div>
          </div>
          <div className="h-64">
            <ResponsiveContainer width="100%" height="100%">
              <BarChart data={merchantData}>
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
                  {merchantData.map((_, i) => (
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
                <td className="px-3 py-2">{r.merchant || "-"}</td>
                <td className="px-3 py-2 text-slate-300">
                  {r.description || "-"}
                </td>
                <td
                  className={`px-3 py-2 whitespace-nowrap ${
                    r.amount < 0 ? "text-red-300" : "text-green-300"
                  }`}
                >
                  {fmtCurrency(r.amount)}
                </td>
                <td className="px-3 py-2">
                  {r.category ? (
                    <Badge variant={categoryVariant(r.category)}>
                      {r.category}
                    </Badge>
                  ) : (
                    <span className="text-slate-500">-</span>
                  )}
                </td>
                <td className="px-3 py-2">
                  {r.category_source ? (
                    <Badge
                      variant="info"
                      title={r.category_provenance || undefined}
                    >
                      {r.category_source}
                    </Badge>
                  ) : (
                    <span className="text-slate-500">-</span>
                  )}
                </td>
                <td className="px-3 py-2 text-slate-400">
                  {r.category_provenance || "-"}
                </td>
              </tr>
            ))}
            {rows.length === 0 && (
              <tr>
                <td
                  colSpan={7}
                  className="px-3 py-6 text-center text-slate-400"
                >
                  No transactions
                </td>
              </tr>
            )}
          </tbody>
        </table>
      </div>
    </div>
  );
}
