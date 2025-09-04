"use client";
import Link from "next/link";
import { useUser } from "./Providers";

export default function Header() {
  const { userId, setUserId } = useUser();

  return (
    <header className="border-b border-slate-700/50">
      <div className="max-w-5xl mx-auto px-4 py-4 flex items-center gap-6">
        <h1 className="text-xl font-semibold">Smart Financial Coach</h1>
        <nav className="flex gap-4 text-sm">
          <Link href="/" className="hover:underline">
            Home
          </Link>
          <Link href="/connect" className="hover:underline">
            Connect
          </Link>
          <Link href="/ingest" className="hover:underline">
            CSV Ingest
          </Link>
          <Link href="/transactions" className="hover:underline">
            Transactions
          </Link>
          <Link href="/subscriptions" className="hover:underline">
            Subscriptions
          </Link>
          <Link href="/plaid" className="hover:underline">
            Plaid
          </Link>
          <Link href="/insights" className="hover:underline">
            Insights
          </Link>
          <Link href="/goals" className="hover:underline">
            Goals
          </Link>
        </nav>
        <div className="ml-auto text-xs text-slate-400 flex items-center gap-3">
          <div>
            {process.env.NEXT_PUBLIC_API_URL || "http://localhost:8000"}
          </div>
          {userId ? (
            <>
              <div className="text-sm">
                Signed in: <strong>{userId}</strong>
              </div>
              <button
                className="text-sm underline"
                onClick={async () => {
                  try {
                    await fetch((process.env.NEXT_PUBLIC_API_URL||'http://localhost:8000')+"/auth/logout", { method: 'POST', credentials: 'include' });
                  } catch {}
                  setUserId("");
                }}
              >
                Sign out
              </button>
            </>
          ) : (
            <Link href="/auth" className="text-sm underline">
              Sign in
            </Link>
          )}
        </div>
      </div>
    </header>
  );
}
