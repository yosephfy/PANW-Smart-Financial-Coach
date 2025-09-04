"use client";

import { useState } from "react";
import { useUser } from "../../components/Providers";

const API = process.env.NEXT_PUBLIC_API_URL || "http://localhost:8000";

export default function IngestPage() {
  const ctx = useUser();
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
      form.append("file", file);
      if (ctx.userId) form.append("user_id", ctx.userId);
      const res = await fetch(`${API}/ingest/csv/insights`, {
        method: "POST",
        body: form,
        // no cookies; send user_id in form
      });
      const json = await res.json();
      setResult(json);
      ctx.showToast("CSV ingested", "success");
    } catch (err) {
      setResult({ error: String(err) });
      ctx.showToast(String(err), "error");
    } finally {
      setBusy(false);
    }
  };

  return (
    <div className="space-y-4">
      <h2 className="text-lg font-semibold">CSV Ingestion</h2>
      <form
        onSubmit={submit}
        className="space-y-3 border border-slate-700 p-4 rounded"
      >
        <div className="grid md:grid-cols-1 gap-4">
          <label className="block text-sm">
            <span className="text-slate-300">CSV File</span>
            <input
              className="mt-1 w-full text-slate-200"
              type="file"
              accept=".csv"
              onChange={(e) => setFile(e.target.files?.[0] || null)}
            />
          </label>
        </div>
        <button
          disabled={busy || !file}
          className="rounded bg-blue-500 text-white px-3 py-1 disabled:opacity-50"
        >
          {busy ? "Uploading…" : "Upload & Ingest"}
        </button>
      </form>

      {result && (
        <div className="space-y-3">
          <pre className="text-xs bg-slate-900/70 p-3 rounded overflow-auto">
            {JSON.stringify(result.ingest || result, null, 2)}
          </pre>
          {result.subscriptions && (
            <div className="border border-slate-700 p-3 rounded">
              <div className="text-sm font-semibold">
                Detected Subscriptions ({result.subscriptions.detected})
              </div>
              <div className="text-xs text-slate-400">
                Inserted: {result.subscriptions.inserted} Updated:{" "}
                {result.subscriptions.updated}
              </div>
              {result.subscriptions.items &&
                result.subscriptions.items.length > 0 && (
                  <table className="w-full text-xs mt-2">
                    <thead>
                      <tr className="text-left text-slate-400">
                        <th>Merchant</th>
                        <th>Cadence</th>
                        <th>Avg</th>
                        <th>Last seen</th>
                        <th>Status</th>
                      </tr>
                    </thead>
                    <tbody>
                      {result.subscriptions.items.map((s: any) => (
                        <tr
                          key={s.merchant}
                          className="border-t border-slate-800"
                        >
                          <td className="py-1">{s.merchant}</td>
                          <td>{s.cadence}</td>
                          <td>${s.avg_amount}</td>
                          <td>{s.last_seen}</td>
                          <td>{s.status}</td>
                        </tr>
                      ))}
                    </tbody>
                  </table>
                )}
            </div>
          )}
        </div>
      )}
    </div>
  );
}
