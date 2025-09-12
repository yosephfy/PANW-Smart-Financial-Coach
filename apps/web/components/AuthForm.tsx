"use client";
import { useState } from "react";
import { useUser } from "./Providers";
import { useRouter } from "next/navigation";

const API = process.env.NEXT_PUBLIC_API_URL || "http://localhost:8000";

export default function AuthForm() {
  const { setUserId, showToast } = useUser();
  const [username, setUsername] = useState("");
  const [password, setPassword] = useState("");
  const [busy, setBusy] = useState<"login" | "register" | null>(null);
  const router = useRouter();

  const doAuth = async (kind: "login" | "register") => {
    setBusy(kind);
    try {
      if (!username) throw new Error("Enter a username");
      if (!password) throw new Error("Enter a password");
      const res = await fetch(`${API}/auth/${kind}`, {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({ username, password }),
      });
      const json = await res.json();
      if (!res.ok) throw new Error(json?.detail || `Failed to ${kind}`);
      if (!json?.id) throw new Error("Invalid response from server");
      setUserId(json.id);
      showToast(`Signed in as ${json.id}`, "success");
      router.replace("/");
    } catch (e: any) {
      showToast(e?.message || String(e), "error");
    } finally {
      setBusy(null);
    }
  };

  return (
    <form
      onSubmit={(e) => {
        e.preventDefault();
        doAuth("login");
      }}
      className="space-y-3"
    >
      <div className="grid md:grid-cols-2 gap-3">
        <label className="text-sm">
          <div className="text-slate-300">Username</div>
          <input
            className="mt-1 w-full rounded border border-slate-600 bg-slate-100 px-2 py-1"
            value={username}
            onChange={(e) => setUsername(e.target.value)}
          />
        </label>
        <label className="text-sm">
          <div className="text-slate-300">Password</div>
          <input
            type="password"
            className="mt-1 w-full rounded border border-slate-600 bg-slate-100 px-2 py-1"
            value={password}
            onChange={(e) => setPassword(e.target.value)}
          />
        </label>
      </div>
      <div className="flex items-center gap-3">
        <button
          className="rounded bg-blue-500 text-white px-3 py-1 disabled:opacity-50"
          disabled={busy !== null}
          type="submit"
        >
          {busy === "login" ? "Logging in…" : "Login"}
        </button>
        <button
          type="button"
          onClick={() => doAuth("register")}
          className="rounded bg-slate-600 text-white px-3 py-1 disabled:opacity-50"
          disabled={busy !== null}
        >
          {busy === "register" ? "Registering…" : "Create account"}
        </button>
      </div>
    </form>
  );
}
