"use client";
import Link from "next/link";
import { useUser } from "../../components/Providers";

export default function ConnectPage() {
  const { userId } = useUser();

  return (
    <div className="max-w-3xl mx-auto py-12">
      <h1 className="text-2xl font-bold mb-4">Connect your data</h1>
      <p className="mb-6">
        Choose how you'd like to connect transactions for your account.
      </p>

      {/* Requires sign-in; SignGate will redirect to /auth if not signed in */}

      <div className="grid gap-4 md:grid-cols-2">
        <div className="p-6 border rounded">
          <h2 className="font-semibold">Plaid (connect bank)</h2>
          <p className="text-sm mt-2 mb-4">
            Use Plaid to connect live bank accounts.
          </p>
          <Link href={userId ? "/plaid" : "/auth"} className="btn">
            {userId ? "Connect Plaid" : "Sign in to enable"}
          </Link>
        </div>

        <div className="p-6 border rounded">
          <h2 className="font-semibold">Upload CSV</h2>
          <p className="text-sm mt-2 mb-4">
            Upload a CSV file exported from your bank.
          </p>
          <Link href={userId ? "/ingest" : "/auth"} className="btn">
            {userId ? "Upload CSV" : "Sign in to enable"}
          </Link>
        </div>
      </div>
    </div>
  );
}
