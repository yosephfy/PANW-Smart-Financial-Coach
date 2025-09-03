"use client";

import React, { useEffect, useState } from "react";
import { useUser } from "./Providers";
import { useRouter } from "next/navigation";

const API = process.env.NEXT_PUBLIC_API_URL || "http://127.0.0.1:8000";

export default function UserLogin() {
  const ctx = useUser();
  const [users, setUsers] = useState<string[]>([]);
  const [loading, setLoading] = useState(false);
  const [newId, setNewId] = useState("");

  const load = async () => {
    setLoading(true);
    try {
      const res = await fetch(`${API}/users`);
      const json = await res.json();
      setUsers(Array.isArray(json) ? json.map((u: any) => u.id) : []);
    } catch (e) {
      // ignore
    } finally {
      setLoading(false);
    }
  };

  useEffect(() => {
    load();
  }, []);

  const create = async () => {
    const id = newId.trim();
    if (!id) return;
    try {
      await fetch(`${API}/users`, {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({ user_id: id }),
      });
      ctx.setUserId(id);
      setNewId("");
      load();
      ctx.showToast(`Logged in as ${id}`, "success");
      router.push("/connect");
    } catch (e) {
      ctx.showToast(String(e), "error");
    }
  };

  const router = useRouter();

  return (
    <div className="flex items-center gap-3">
      <div>
        <select
          className="rounded border border-slate-600 bg-slate-100 px-2 py-1"
          value={ctx.userId}
          onChange={(e) => {
            ctx.setUserId(e.target.value);
            router.push("/connect");
          }}
        >
          <option value="">Select user</option>
          {users.map((u) => (
            <option key={u} value={u}>
              {u}
            </option>
          ))}
        </select>
      </div>
      <div className="text-xs text-slate-400">or create:</div>
      <input
        className="rounded border border-slate-600 bg-slate-100 px-2 py-1"
        value={newId}
        onChange={(e) => setNewId(e.target.value)}
        placeholder="new user id"
      />
      <button
        onClick={create}
        className="rounded bg-blue-500 text-white px-3 py-1"
      >
        Create / Login
      </button>
    </div>
  );
}
