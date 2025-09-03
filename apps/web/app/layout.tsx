import "./globals.css";
import type { Metadata } from "next";
import AppProviders from "../components/Providers";

export const metadata: Metadata = {
  title: "Smart Financial Coach",
  description: "Hackathon demo UI",
};

export default function RootLayout({
  children,
}: {
  children: React.ReactNode;
}) {
  return (
    <html lang="en">
      <body className="min-h-screen">
        <AppProviders>
          <header className="border-b border-slate-700/50">
            <div className="max-w-5xl mx-auto px-4 py-4 flex items-center gap-6">
              <h1 className="text-xl font-semibold">Smart Financial Coach</h1>
              <nav className="flex gap-4 text-sm">
                <a href="/" className="hover:underline">
                  Home
                </a>
                <a href="/ingest" className="hover:underline">
                  CSV Ingest
                </a>
                <a href="/transactions" className="hover:underline">
                  Transactions
                </a>
                <a href="/subscriptions" className="hover:underline">
                  Subscriptions
                </a>
                <a href="/plaid" className="hover:underline">
                  Plaid
                </a>
                <a href="/insights" className="hover:underline">
                  Insights
                </a>
              </nav>
              <span className="ml-auto text-xs text-slate-400">
                API:{" "}
                {process.env.NEXT_PUBLIC_API_URL || "http://127.0.0.1:8000"}
              </span>
            </div>
          </header>
          <main className="max-w-5xl mx-auto px-4 py-6">{children}</main>
        </AppProviders>
      </body>
    </html>
  );
}
