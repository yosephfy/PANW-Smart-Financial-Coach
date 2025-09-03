export default function Home() {
  return (
    <div className="space-y-4">
      <h2 className="text-lg font-semibold">Welcome</h2>
      <p className="text-slate-300">Use the links above to upload a CSV, view transactions, and see detected subscriptions.</p>

      <div className="grid md:grid-cols-3 gap-4 mt-6">
        <a href="/ingest" className="block rounded border border-slate-700 p-4 hover:bg-slate-800/40">
          <h3 className="font-semibold mb-1">CSV Ingest</h3>
          <p className="text-sm text-slate-400">Upload CSV for a user and import transactions.</p>
        </a>
        <a href="/transactions" className="block rounded border border-slate-700 p-4 hover:bg-slate-800/40">
          <h3 className="font-semibold mb-1">Transactions</h3>
          <p className="text-sm text-slate-400">View the latest transactions by user.</p>
        </a>
        <a href="/subscriptions" className="block rounded border border-slate-700 p-4 hover:bg-slate-800/40">
          <h3 className="font-semibold mb-1">Subscriptions</h3>
          <p className="text-sm text-slate-400">Detect and list recurring subscriptions.</p>
        </a>
      </div>
    </div>
  )
}

