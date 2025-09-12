"use client";

import { useEffect, useState } from "react";
import { useUser } from "../../components/Providers";

const API = process.env.NEXT_PUBLIC_API_URL || "http://localhost:8000";

type Budget = { category: string; monthly_budget: number };

export default function BudgetsPage() {
  const { userId, showToast } = useUser();
  const [rows, setRows] = useState<Budget[]>([]);
  const [cat, setCat] = useState("");
  const [amt, setAmt] = useState("");
  const [busy, setBusy] = useState(false);

  const load = async () => {
    if (!userId) return;
    const res = await fetch(
      `${API}/users/${encodeURIComponent(userId)}/budgets`
    );
    const json = await res.json();
    setRows(Array.isArray(json) ? json : []);
  };

  const upsert = async (e: React.FormEvent) => {
    e.preventDefault();
    if (!userId || !cat || !amt) return;
    setBusy(true);
    try {
      const res = await fetch(
        `${API}/users/${encodeURIComponent(
          userId
        )}/budgets/${encodeURIComponent(cat)}`,
        {
          method: "PUT",
          headers: { "Content-Type": "application/json" },
          body: JSON.stringify({ monthly_budget: parseFloat(amt) }),
        }
      );
      if (!res.ok) throw new Error("Failed to save");
      showToast("Budget saved", "success");
      setCat("");
      setAmt("");
      await load();
    } catch (e: any) {
      showToast(e?.message || String(e), "error");
    } finally {
      setBusy(false);
    }
  };

  const del = async (category: string) => {
    if (!userId) return;
    await fetch(
      `${API}/users/${encodeURIComponent(userId)}/budgets/${encodeURIComponent(
        category
      )}`,
      { method: "DELETE" }
    );
    await load();
  };

  useEffect(() => {
    if (userId) load();
  }, [userId]);

  return (
    <div className="space-y-4">
      <h2 className="text-lg font-semibold">Budgets</h2>
      <form onSubmit={upsert} className="flex gap-2 items-end">
        <label className="text-sm">
          <div className="text-slate-300">Category</div>
          <input
            className="mt-1 w-48 rounded border border-slate-600 bg-slate-100 px-2 py-1"
            value={cat}
            onChange={(e) => setCat(e.target.value)}
            placeholder="groceries"
          />
        </label>
        <label className="text-sm">
          <div className="text-slate-300">Monthly Budget ($)</div>
          <input
            className="mt-1 w-32 rounded border border-slate-600 bg-slate-100 px-2 py-1"
            value={amt}
            onChange={(e) => setAmt(e.target.value)}
            placeholder="400"
          />
        </label>
        <button
          disabled={busy || !cat || !amt}
          className="rounded bg-emerald-500 text-white px-3 py-1 disabled:opacity-50"
        >
          {busy ? "Saving…" : "Save"}
        </button>
      </form>

      <div className="border border-slate-700 rounded overflow-auto">
        <table className="min-w-full text-sm">
          <thead className="bg-slate-800/60">
            <tr className="text-left">
              <th className="px-3 py-2">Category</th>
              <th className="px-3 py-2">Monthly Budget</th>
              <th className="px-3 py-2"></th>
            </tr>
          </thead>
          <tbody>
            {rows.map((r) => (
              <tr key={r.category} className="border-t border-slate-700/60">
                <td className="px-3 py-2">{r.category}</td>
                <td className="px-3 py-2">${r.monthly_budget}</td>
                <td className="px-3 py-2 text-right">
                  <button
                    onClick={() => del(r.category)}
                    className="rounded bg-red-700 text-white px-2 py-0.5 text-xs"
                  >
                    Delete
                  </button>
                </td>
              </tr>
            ))}
            {rows.length === 0 && (
              <tr>
                <td
                  colSpan={3}
                  className="px-3 py-6 text-center text-slate-400"
                >
                  No budgets set
                </td>
              </tr>
            )}
          </tbody>
        </table>
      </div>
    </div>
  );
}
