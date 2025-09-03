"use client";

import { useEffect, useState } from "react";
import { Badge } from "../../components/Badge";
import React from "react";

const API = process.env.NEXT_PUBLIC_API_URL || "http://127.0.0.1:8000";

type Insight = {
  id: string;
  type: string;
  title: string;
  body: string;
  severity: "info" | "warn" | "critical" | string;
  data_json?: string;
  created_at?: string;
  rewritten_title?: string | null;
  rewritten_body?: string | null;
  rewritten_at?: string | null;
};

function severityVariant(sev?: string) {
  switch (sev) {
    case "critical":
      return "danger";
    case "warn":
      return "warning";
    case "info":
      return "info";
    default:
      return "neutral";
  }
}

export default function InsightsPage() {
  const [userId, setUserId] = useState("u_demo");
  const [rows, setRows] = useState<Insight[]>([]);
  const [filter, setFilter] = useState<string>("all");
  const [busy, setBusy] = useState(false);
  const [genBusy, setGenBusy] = useState(false);
  const [mlBusy, setMlBusy] = useState(false);
  const [rewriteBusy, setRewriteBusy] = useState<string | null>(null);

  const load = async () => {
    setBusy(true);
    try {
      const res = await fetch(
        `${API}/users/${encodeURIComponent(userId)}/insights`
      );
      const json = await res.json();
      setRows(Array.isArray(json) ? json : []);
    } finally {
      setBusy(false);
    }
  };

  const generate = async () => {
    setGenBusy(true);
    try {
      await fetch(`${API}/insights/generate`, {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({ user_id: userId }),
      });
      await load();
    } finally {
      setGenBusy(false);
    }
  };

  const runML = async () => {
    setMlBusy(true);
    try {
      await fetch(`${API}/anomaly/iforest/detect`, {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({ user_id: userId, contamination: 0.08 }),
      });
      await load();
    } finally {
      setMlBusy(false);
    }
  };

  const rewrite = async (id: string) => {
    setRewriteBusy(id);
    try {
      await fetch(`${API}/insights/rewrite`, {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({
          user_id: userId,
          insight_id: id,
          tone: "friendly",
        }),
      });
      await load();
    } finally {
      setRewriteBusy(null);
    }
  };

  useEffect(() => {
    load();
  }, []);

  return (
    <div className="space-y-4">
      <h2 className="text-lg font-semibold">Insights</h2>
      <div className="flex gap-3 items-end">
        <label className="text-sm">
          <div className="text-slate-300">User ID</div>
          <input
            className="mt-1 rounded border border-slate-600 bg-slate-100 px-2 py-1"
            value={userId}
            onChange={(e) => setUserId(e.target.value)}
          />
        </label>
        <button
          onClick={load}
          disabled={busy}
          className="rounded bg-blue-500 text-white px-3 py-1 disabled:opacity-50"
        >
          {busy ? "Loading…" : "Refresh"}
        </button>
        <button
          onClick={generate}
          disabled={genBusy}
          className="rounded bg-emerald-500 text-white px-3 py-1 disabled:opacity-50"
        >
          {genBusy ? "Generating…" : "Generate"}
        </button>
        <button
          onClick={runML}
          disabled={mlBusy}
          className="rounded bg-purple-500 text-white px-3 py-1 disabled:opacity-50"
        >
          {mlBusy ? "Detecting…" : "Run ML Outliers"}
        </button>
      </div>

      <div className="flex gap-2 items-center">
        <div className="text-sm text-slate-300">Filter</div>
        <div className="flex gap-2">
          {["all", "overspend", "trending", "ml_outlier"].map((t) => (
            <button
              key={t}
              onClick={() => setFilter(t)}
              className={`text-xs px-2 py-0.5 rounded ${
                filter === t
                  ? "bg-slate-700 text-white"
                  : "bg-transparent text-slate-300 border border-slate-700"
              }`}
            >
              {t === "all" ? "All" : t.replace("_", " ")}
            </button>
          ))}
        </div>
      </div>

      <div className="grid gap-3">
        {rows
          .filter((r) => (filter === "all" ? true : r.type === filter))
          .map((r) => (
            <div key={r.id} className="border border-slate-700 rounded p-3">
              <div className="flex items-start gap-2">
                <Badge variant={severityVariant(r.severity)}>
                  {r.severity}
                </Badge>
                {r.type === "ml_outlier" && <Badge variant="info">ML</Badge>}
                {r.type === "overspend" && (
                  <Badge variant="warning">Overspend</Badge>
                )}
                {r.type === "trending" && (
                  <Badge variant="success">Trending</Badge>
                )}
                <div className="font-semibold">
                  {r.rewritten_title || r.title}
                </div>
                <div className="ml-auto text-xs text-slate-400">
                  {r.created_at}
                </div>
              </div>
              <div className="text-slate-300 mt-1 text-sm">
                {r.rewritten_body || r.body}
              </div>
              <div className="mt-2 flex items-center gap-2">
                <button
                  onClick={() => rewrite(r.id)}
                  disabled={rewriteBusy === r.id}
                  className="rounded bg-slate-600 text-white px-2 py-0.5 text-xs disabled:opacity-50"
                >
                  {rewriteBusy === r.id ? "Rewriting…" : "Rewrite"}
                </button>
                {r.rewritten_at && (
                  <span className="text-xs text-slate-400">
                    rewritten at {r.rewritten_at}
                  </span>
                )}
              </div>
              {r.data_json && (
                <details className="mt-2">
                  <summary className="cursor-pointer text-xs text-slate-400">
                    Details
                  </summary>
                  <pre className="text-xs bg-slate-900/70 p-3 rounded overflow-auto mt-1">
                    {JSON.stringify(JSON.parse(r.data_json), null, 2)}
                  </pre>
                </details>
              )}
            </div>
          ))}
        {rows.length === 0 && (
          <div className="text-center text-slate-400 border border-slate-700 rounded py-10">
            No insights yet
          </div>
        )}
      </div>
    </div>
  );
}
