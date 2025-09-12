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
  LineChart,
  Line,
  PieChart,
  Pie,
  Legend,
} from "recharts";

const API = process.env.NEXT_PUBLIC_API_URL || "http://localhost:8000";

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
  balance?: number;
};

type Analytics = {
  total_income: number;
  total_expenses: number;
  net_cash_flow: number;
  transaction_count: number;
  recurring_count: number;
  avg_transaction_size: number;
  top_merchants: Array<{
    name: string;
    amount: number;
    value: number;
    count: number;
    avgAmount: number;
  }>;
  category_breakdown: Array<{
    category: string;
    amount: number;
    value: number;
  }>;
  account_breakdown: Array<{
    account: string;
    income: number;
    expenses: number;
    net: number;
    count: number;
  }>;
  daily_trend: Array<{
    date: string;
    income: number;
    expenses: number;
    net: number;
  }>;
};

type TimeFilter = "week" | "month" | "quarter" | "year" | "all";
type TransactionFilter = "all" | "expenses" | "income" | "recurring";

export default function TransactionsPage() {
  const ctx = useUser();
  const [limit, setLimit] = useState(100);
  const [rows, setRows] = useState<Tx[]>([]);
  const [analytics, setAnalytics] = useState<Analytics | null>(null);
  const [busy, setBusy] = useState(false);
  const [searchTerm, setSearchTerm] = useState("");
  const [timeFilter, setTimeFilter] = useState<TimeFilter>("month");
  const [transactionFilter, setTransactionFilter] =
    useState<TransactionFilter>("all");
  const [selectedCategory, setSelectedCategory] = useState<string>("all");

  // Filter transactions based on current filters
  const filteredRows = useMemo(() => {
    let filtered = rows;

    // Search filter
    if (searchTerm) {
      const term = searchTerm.toLowerCase();
      filtered = filtered.filter(
        (r) =>
          r.merchant?.toLowerCase().includes(term) ||
          r.description?.toLowerCase().includes(term) ||
          r.category?.toLowerCase().includes(term)
      );
    }

    // Time filter
    const now = new Date();
    const filterDate = new Date();

    switch (timeFilter) {
      case "week":
        filterDate.setDate(now.getDate() - 7);
        break;
      case "month":
        filterDate.setMonth(now.getMonth() - 1);
        break;
      case "quarter":
        filterDate.setMonth(now.getMonth() - 3);
        break;
      case "year":
        filterDate.setFullYear(now.getFullYear() - 1);
        break;
      case "all":
        filterDate.setFullYear(1900);
        break;
    }

    filtered = filtered.filter((r) => new Date(r.date) >= filterDate);

    // Transaction type filter
    switch (transactionFilter) {
      case "expenses":
        filtered = filtered.filter((r) => r.amount < 0);
        break;
      case "income":
        filtered = filtered.filter((r) => r.amount > 0);
        break;
      case "recurring":
        filtered = filtered.filter((r) => r.is_recurring);
        break;
    }

    // Category filter
    if (selectedCategory !== "all") {
      filtered = filtered.filter(
        (r) => (r.category || "uncategorized") === selectedCategory
      );
    }

    return filtered;
  }, [rows, searchTerm, timeFilter, transactionFilter, selectedCategory]);

  // Available categories for filter dropdown
  const categories = useMemo(() => {
    const cats = new Set<string>();
    rows.forEach((r) => cats.add(r.category || "uncategorized"));
    return Array.from(cats).sort();
  }, [rows]);

  // Load analytics from backend API
  const loadAnalytics = async () => {
    if (!ctx.userId) return;

    try {
      const timeFilterDays =
        timeFilter === "week"
          ? 7
          : timeFilter === "month"
          ? 30
          : timeFilter === "quarter"
          ? 90
          : timeFilter === "year"
          ? 365
          : undefined;

      const params = new URLSearchParams({ user_id: ctx.userId });
      if (timeFilterDays) {
        params.append("days", timeFilterDays.toString());
      }

      const res = await fetch(`${API}/transactions/analytics?${params}`);
      if (!res.ok) throw new Error("Failed to load analytics");

      const analyticsData: Analytics = await res.json();
      setAnalytics(analyticsData);
    } catch (error) {
      console.error("Failed to load analytics:", error);
    }
  };

  // Load analytics when component mounts or time filter changes
  useEffect(() => {
    loadAnalytics();
  }, [ctx.userId, timeFilter]);

  // Daily spending trend
  const dailyTrend = useMemo(() => {
    // Use analytics data if available
    if (analytics?.daily_trend) {
      return analytics.daily_trend.map((d) => ({
        date: d.date,
        amount: d.expenses, // Use expenses for spending trend
        income: d.income,
        net: d.net,
      }));
    }

    // Fallback: calculate from filtered rows
    const dailyMap: Record<string, number> = {};
    filteredRows
      .filter((r) => r.amount < 0)
      .forEach((r) => {
        const date = r.date;
        dailyMap[date] = (dailyMap[date] || 0) + Math.abs(r.amount);
      });

    return Object.entries(dailyMap)
      .map(([date, amount]) => ({ date, amount }))
      .sort((a, b) => a.date.localeCompare(b.date))
      .slice(-30); // Last 30 days
  }, [analytics, filteredRows]);

  // Category spending analysis
  const categoryData = useMemo(() => {
    // Use analytics data if available
    if (analytics?.category_breakdown) {
      return analytics.category_breakdown
        .map((c) => ({
          name: c.category,
          value: c.value,
          percentage:
            analytics.total_expenses > 0
              ? (c.value / analytics.total_expenses) * 100
              : 0,
        }))
        .slice(0, 8);
    }

    // Fallback: calculate from filtered rows
    const map: Record<string, number> = {};
    for (const r of filteredRows) {
      const cat = r.category || "uncategorized";
      // Sum only expenses (negative amounts)
      if (r.amount < 0) {
        map[cat] = (map[cat] || 0) + Math.abs(r.amount);
      }
    }
    const totalExpenses = Object.values(map).reduce((sum, val) => sum + val, 0);
    const entries = Object.entries(map).map(([name, value]) => ({
      name,
      value,
      percentage:
        value > 0 && totalExpenses > 0 ? (value / totalExpenses) * 100 : 0,
    }));
    // sort desc and take top 8
    return entries.sort((a, b) => b.value - a.value).slice(0, 8);
  }, [analytics, filteredRows]);

  // Account breakdown
  const accountData = useMemo(() => {
    // Use analytics data if available
    if (analytics?.account_breakdown) {
      return analytics.account_breakdown.map((a) => ({
        account: a.account,
        income: a.income,
        expenses: a.expenses,
        net: a.net,
        balance: undefined, // API doesn't include balance yet
      }));
    }

    // Fallback: calculate from filtered rows
    const map: Record<
      string,
      { income: number; expenses: number; balance?: number }
    > = {};
    for (const r of filteredRows) {
      const account = r.account_id || "Unknown Account";
      if (!map[account]) {
        map[account] = { income: 0, expenses: 0, balance: r.balance };
      }

      if (r.amount > 0) {
        map[account].income += r.amount;
      } else {
        map[account].expenses += Math.abs(r.amount);
      }

      // Update balance if we have it
      if (r.balance !== undefined) {
        map[account].balance = r.balance;
      }
    }

    return Object.entries(map).map(([account, data]) => ({
      account,
      ...data,
      net: data.income - data.expenses,
    }));
  }, [analytics, filteredRows]);

  // Top merchants analysis
  // Merchant data - use analytics API data when available, fallback to filtered calculation
  const merchantData = useMemo(() => {
    // If we have analytics data, use it (this represents ALL data, not filtered)
    if (analytics?.top_merchants) {
      console.log(
        "Using analytics API merchant data:",
        analytics.top_merchants
      );
      return analytics.top_merchants.map((m) => ({
        name: m.name,
        value: m.value,
        amount: m.amount,
        count: m.count,
        avgAmount: m.avgAmount,
      }));
    }

    // Fallback: calculate from filtered rows for display purposes
    const map: Record<
      string,
      { amount: number; count: number; avgAmount: number }
    > = {};
    for (const r of filteredRows) {
      if (!r.merchant || r.amount >= 0) continue;
      const name = r.merchant;
      const amount = Math.abs(r.amount);

      if (!map[name]) {
        map[name] = { amount: 0, count: 0, avgAmount: 0 };
      }

      map[name].amount += amount;
      map[name].count += 1;
      map[name].avgAmount = map[name].amount / map[name].count;
    }

    const entries = Object.entries(map).map(([name, data]) => ({
      name,
      value: data.amount, // Chart expects 'value' field
      amount: data.amount,
      count: data.count,
      avgAmount: data.avgAmount,
    }));
    const result = entries.sort((a, b) => b.amount - a.amount).slice(0, 10);

    // Debug logging
    console.log("Merchant data calculation (fallback from filtered):");
    console.log("Filtered rows:", filteredRows.length);
    console.log(
      "Expense rows:",
      filteredRows.filter((r) => r.amount < 0).length
    );
    console.log("Merchant entries:", result);

    return result;
  }, [analytics, filteredRows]);

  const load = async () => {
    setBusy(true);
    try {
      if (!ctx.userId) return;
      const res = await fetch(
        `${API}/users/${encodeURIComponent(
          ctx.userId
        )}/transactions?limit=${limit}`
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
    if (ctx.userId) load();
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [ctx.userId, limit]);

  return (
    <div className="space-y-6">
      <div className="flex items-center justify-between">
        <h2 className="text-2xl font-semibold">Transaction Analysis</h2>
        <AddTransactionButton
          onAdded={() => load()}
          userId={ctx.userId || ""}
        />
      </div>

      {/* Analytics Summary Cards - All Transactions */}
      <div className="grid grid-cols-2 md:grid-cols-3 lg:grid-cols-6 gap-4">
        <div className="bg-slate-800/40 border border-slate-700 rounded-lg p-3">
          <div className="text-xs text-slate-400 uppercase tracking-wide">
            Total Income (All)
          </div>
          <div className="text-xl font-semibold text-green-400">
            {analytics ? fmtCurrency(analytics.total_income) : "$0.00"}
          </div>
          <div className="text-xs text-slate-500">
            Showing:{" "}
            {filteredRows
              .filter((r) => r.amount > 0)
              .reduce((sum, r) => sum + r.amount, 0)
              ? fmtCurrency(
                  filteredRows
                    .filter((r) => r.amount > 0)
                    .reduce((sum, r) => sum + r.amount, 0)
                )
              : "$0.00"}
          </div>
        </div>
        <div className="bg-slate-800/40 border border-slate-700 rounded-lg p-3">
          <div className="text-xs text-slate-400 uppercase tracking-wide">
            Total Expenses (All)
          </div>
          <div className="text-xl font-semibold text-red-400">
            {analytics ? fmtCurrency(analytics.total_expenses) : "$0.00"}
          </div>
          <div className="text-xs text-slate-500">
            Showing:{" "}
            {Math.abs(
              filteredRows
                .filter((r) => r.amount < 0)
                .reduce((sum, r) => sum + r.amount, 0)
            )
              ? fmtCurrency(
                  Math.abs(
                    filteredRows
                      .filter((r) => r.amount < 0)
                      .reduce((sum, r) => sum + r.amount, 0)
                  )
                )
              : "$0.00"}
          </div>
        </div>
        <div className="bg-slate-800/40 border border-slate-700 rounded-lg p-3">
          <div className="text-xs text-slate-400 uppercase tracking-wide">
            Net Cash Flow (All)
          </div>
          <div
            className={`text-xl font-semibold ${
              (analytics?.net_cash_flow || 0) >= 0
                ? "text-green-400"
                : "text-red-400"
            }`}
          >
            {analytics ? fmtCurrency(analytics.net_cash_flow) : "$0.00"}
          </div>
        </div>
        <div className="bg-slate-800/40 border border-slate-700 rounded-lg p-3">
          <div className="text-xs text-slate-400 uppercase tracking-wide">
            All Transactions
          </div>
          <div className="text-xl font-semibold text-slate-200">
            {analytics ? analytics.transaction_count : "0"}
          </div>
          <div className="text-xs text-slate-500">
            Showing: {filteredRows.length}
          </div>
        </div>
        <div className="bg-slate-800/40 border border-slate-700 rounded-lg p-3">
          <div className="text-xs text-slate-400 uppercase tracking-wide">
            Recurring (All)
          </div>
          <div className="text-xl font-semibold text-blue-400">
            {analytics ? analytics.recurring_count : "0"}
          </div>
        </div>
        <div className="bg-slate-800/40 border border-slate-700 rounded-lg p-3">
          <div className="text-xs text-slate-400 uppercase tracking-wide">
            Avg Amount (All)
          </div>
          <div className="text-xl font-semibold text-slate-200">
            {analytics ? fmtCurrency(analytics.avg_transaction_size) : "$0.00"}
          </div>
        </div>
      </div>

      {/* Filters */}
      <div className="bg-slate-800/40 border border-slate-700 rounded-lg p-4">
        <h3 className="font-semibold mb-3">Filters & Search</h3>
        <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-5 gap-3">
          <div>
            <label className="text-xs text-slate-400 uppercase tracking-wide block mb-1">
              Search
            </label>
            <input
              type="text"
              className="w-full rounded border border-slate-600 bg-slate-100 px-3 py-2 text-sm"
              placeholder="Search merchant, description, category..."
              value={searchTerm}
              onChange={(e) => setSearchTerm(e.target.value)}
            />
          </div>
          <div>
            <label className="text-xs text-slate-400 uppercase tracking-wide block mb-1">
              Time Period
            </label>
            <select
              className="w-full rounded border border-slate-600 bg-slate-100 px-3 py-2 text-sm"
              value={timeFilter}
              onChange={(e) => setTimeFilter(e.target.value as TimeFilter)}
            >
              <option value="week">Last Week</option>
              <option value="month">Last Month</option>
              <option value="quarter">Last Quarter</option>
              <option value="year">Last Year</option>
              <option value="all">All Time</option>
            </select>
          </div>
          <div>
            <label className="text-xs text-slate-400 uppercase tracking-wide block mb-1">
              Type
            </label>
            <select
              className="w-full rounded border border-slate-600 bg-slate-100 px-3 py-2 text-sm"
              value={transactionFilter}
              onChange={(e) =>
                setTransactionFilter(e.target.value as TransactionFilter)
              }
            >
              <option value="all">All Transactions</option>
              <option value="expenses">Expenses Only</option>
              <option value="income">Income Only</option>
              <option value="recurring">Recurring Only</option>
            </select>
          </div>
          <div>
            <label className="text-xs text-slate-400 uppercase tracking-wide block mb-1">
              Category
            </label>
            <select
              className="w-full rounded border border-slate-600 bg-slate-100 px-3 py-2 text-sm"
              value={selectedCategory}
              onChange={(e) => setSelectedCategory(e.target.value)}
            >
              <option value="all">All Categories</option>
              {categories.map((cat) => (
                <option key={cat} value={cat}>
                  {cat}
                </option>
              ))}
            </select>
          </div>
          <div>
            <label className="text-xs text-slate-400 uppercase tracking-wide block mb-1">
              Limit
            </label>
            <div className="flex gap-2">
              <input
                type="number"
                className="w-full rounded border border-slate-600 bg-slate-100 px-3 py-2 text-sm"
                value={limit}
                onChange={(e) =>
                  setLimit(parseInt(e.target.value || "100", 10))
                }
              />
              <button
                onClick={load}
                disabled={busy}
                className="rounded bg-blue-500 text-white px-3 py-2 disabled:opacity-50 text-sm whitespace-nowrap"
              >
                {busy ? "Loading…" : "Refresh"}
              </button>
            </div>
          </div>
        </div>
      </div>

      {/* Visualizations Grid */}
      <div className="grid grid-cols-1 lg:grid-cols-2 gap-6">
        {/* Daily Spending Trend */}
        {dailyTrend.length > 0 && (
          <div className="bg-slate-800/40 border border-slate-700 rounded-lg p-4">
            <h3 className="font-semibold mb-3">Daily Spending Trend</h3>
            <div className="h-64">
              <ResponsiveContainer width="100%" height="100%">
                <LineChart data={dailyTrend}>
                  <XAxis
                    dataKey="date"
                    tick={{ fill: "#cbd5e1", fontSize: 12 }}
                    tickFormatter={(date) =>
                      new Date(date).toLocaleDateString("en-US", {
                        month: "short",
                        day: "numeric",
                      })
                    }
                  />
                  <YAxis
                    tick={{ fill: "#cbd5e1", fontSize: 12 }}
                    tickFormatter={(v) => `$${Math.round(v)}`}
                  />
                  <Tooltip
                    formatter={(v: number) => [fmtCurrency(v), "Spent"]}
                    labelFormatter={(date) =>
                      new Date(date).toLocaleDateString()
                    }
                    contentStyle={{
                      background: "#0f172a",
                      border: "1px solid #334155",
                      borderRadius: 8,
                    }}
                  />
                  <Line
                    type="monotone"
                    dataKey="amount"
                    stroke="#60a5fa"
                    strokeWidth={2}
                    dot={{ r: 3 }}
                  />
                </LineChart>
              </ResponsiveContainer>
            </div>
          </div>
        )}

        {/* Category Breakdown */}
        {!!categoryData.length && (
          <div className="bg-slate-800/40 border border-slate-700 rounded-lg p-4">
            <div className="flex items-center justify-between mb-3">
              <h3 className="font-semibold">Spending by Category</h3>
              <div className="text-xs text-slate-400">
                {filteredRows.length} transactions
              </div>
            </div>
            <div className="h-64">
              <ResponsiveContainer width="100%" height="100%">
                <PieChart>
                  <Pie
                    data={categoryData}
                    cx="50%"
                    cy="50%"
                    outerRadius={80}
                    fill="#8884d8"
                    dataKey="value"
                    label={({ name, percentage }) =>
                      `${name} (${percentage.toFixed(1)}%)`
                    }
                    labelLine={false}
                  >
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
                  </Pie>
                  <Tooltip formatter={(v: number) => fmtCurrency(v)} />
                </PieChart>
              </ResponsiveContainer>
            </div>
          </div>
        )}

        {/* Top Merchants */}
        {!!merchantData.length && (
          <div className="bg-slate-800/40 border border-slate-700 rounded-lg p-4">
            <div className="flex items-center justify-between mb-3">
              <h3 className="font-semibold">Top Merchants</h3>
              <div className="text-xs text-slate-400">
                By total spend ({merchantData.length} merchants)
              </div>
            </div>
            <div className="h-64">
              <ResponsiveContainer width="100%" height="100%">
                <BarChart data={merchantData} layout="horizontal">
                  <XAxis
                    type="number"
                    tick={{ fill: "#cbd5e1", fontSize: 12 }}
                    tickFormatter={(v) => {
                      console.log("XAxis tick value:", v, "type:", typeof v);
                      if (v < 0.01) return "$0";
                      if (v < 1) return `$${v.toFixed(2)}`;
                      if (v < 10) return `$${v.toFixed(1)}`;
                      return `$${Math.round(v)}`;
                    }}
                  />
                  <YAxis
                    type="category"
                    dataKey="name"
                    tick={{ fill: "#cbd5e1", fontSize: 12 }}
                    width={120}
                  />
                  <Tooltip
                    formatter={(v: number, name: string) => {
                      if (name === "value")
                        return [fmtCurrency(v), "Total Spent"];
                      if (name === "amount")
                        return [fmtCurrency(v), "Total Spent"];
                      if (name === "count") return [v, "Transactions"];
                      if (name === "avgAmount")
                        return [fmtCurrency(v), "Avg per Transaction"];
                      return [fmtCurrency(v), "Total Spent"];
                    }}
                    contentStyle={{
                      background: "#0f172a",
                      border: "1px solid #334155",
                      borderRadius: 8,
                    }}
                  />
                  <Bar dataKey="value" fill="#60a5fa" radius={[0, 4, 4, 0]} />
                </BarChart>
              </ResponsiveContainer>
            </div>
          </div>
        )}

        {/* Account Breakdown */}
        {accountData.length > 1 && (
          <div className="bg-slate-800/40 border border-slate-700 rounded-lg p-4">
            <h3 className="font-semibold mb-3">Account Activity</h3>
            <div className="space-y-3">
              {accountData.map((acc) => (
                <div
                  key={acc.account}
                  className="flex items-center justify-between p-3 bg-slate-700/40 rounded"
                >
                  <div>
                    <div className="font-medium">{acc.account}</div>
                    <div className="text-sm text-slate-400">
                      {acc.balance !== undefined &&
                        `Balance: ${fmtCurrency(acc.balance)}`}
                    </div>
                  </div>
                  <div className="text-right">
                    <div className="flex gap-4 text-sm">
                      <span className="text-green-400">
                        +{fmtCurrency(acc.income)}
                      </span>
                      <span className="text-red-400">
                        -{fmtCurrency(acc.expenses)}
                      </span>
                    </div>
                    <div
                      className={`font-semibold ${
                        acc.net >= 0 ? "text-green-400" : "text-red-400"
                      }`}
                    >
                      Net: {fmtCurrency(acc.net)}
                    </div>
                  </div>
                </div>
              ))}
            </div>
          </div>
        )}
      </div>

      {/* Enhanced Transaction Table */}
      <div className="bg-slate-800/40 border border-slate-700 rounded-lg">
        <div className="p-4 border-b border-slate-700">
          <h3 className="font-semibold">Transaction Details</h3>
          <p className="text-sm text-slate-400 mt-1">
            Showing {filteredRows.length} of {rows.length} transactions
            {searchTerm && ` matching "${searchTerm}"`}
          </p>
        </div>

        <div className="overflow-x-auto">
          <table className="min-w-full text-sm">
            <thead className="bg-slate-800/60">
              <tr className="text-left">
                <th className="px-4 py-3">Date</th>
                <th className="px-4 py-3">Merchant</th>
                <th className="px-4 py-3">Description</th>
                <th className="px-4 py-3">Amount</th>
                <th className="px-4 py-3">Category</th>
                <th className="px-4 py-3">Account</th>
                <th className="px-4 py-3">Type</th>
                <th className="px-4 py-3">Balance</th>
              </tr>
            </thead>
            <tbody>
              {filteredRows.map((r, index) => (
                <tr
                  key={r.id}
                  className={`border-t border-slate-700/60 hover:bg-slate-700/30 transition-colors ${
                    index % 2 === 0 ? "bg-slate-800/20" : ""
                  }`}
                >
                  <td className="px-4 py-3 whitespace-nowrap font-mono text-xs">
                    {new Date(r.date).toLocaleDateString("en-US", {
                      month: "short",
                      day: "numeric",
                      year: "numeric",
                    })}
                  </td>
                  <td className="px-4 py-3 max-w-xs">
                    <div className="truncate font-medium">
                      {r.merchant || "-"}
                    </div>
                  </td>
                  <td className="px-4 py-3 text-slate-300 max-w-xs">
                    <div className="truncate text-sm">
                      {r.description || "-"}
                    </div>
                  </td>
                  <td className="px-4 py-3 whitespace-nowrap">
                    <div
                      className={`font-semibold ${
                        r.amount < 0 ? "text-red-300" : "text-green-300"
                      }`}
                    >
                      {r.amount < 0 ? "-" : "+"}
                      {fmtCurrency(Math.abs(r.amount))}
                    </div>
                  </td>
                  <td className="px-4 py-3">
                    {r.category ? (
                      <Badge variant={categoryVariant(r.category)}>
                        {r.category}
                      </Badge>
                    ) : (
                      <span className="text-slate-500 text-sm">
                        Uncategorized
                      </span>
                    )}
                  </td>
                  <td className="px-4 py-3">
                    <div className="text-xs text-slate-400">
                      {r.account_id || "Unknown"}
                    </div>
                  </td>
                  <td className="px-4 py-3">
                    <div className="flex flex-col gap-1">
                      {r.is_recurring && (
                        <Badge variant="info" title="Recurring transaction">
                          Recurring
                        </Badge>
                      )}
                      {r.category_source && (
                        <Badge
                          variant="neutral"
                          title={`Categorized by: ${r.category_source} ${
                            r.category_provenance
                              ? `(${r.category_provenance})`
                              : ""
                          }`}
                        >
                          {r.category_source}
                        </Badge>
                      )}
                    </div>
                  </td>
                  <td className="px-4 py-3 whitespace-nowrap text-xs text-slate-400 font-mono">
                    {r.balance !== undefined ? fmtCurrency(r.balance) : "-"}
                  </td>
                </tr>
              ))}
              {filteredRows.length === 0 && (
                <tr>
                  <td
                    colSpan={8}
                    className="px-4 py-12 text-center text-slate-400"
                  >
                    {searchTerm ||
                    timeFilter !== "all" ||
                    transactionFilter !== "all" ||
                    selectedCategory !== "all"
                      ? "No transactions match your current filters"
                      : "No transactions found"}
                  </td>
                </tr>
              )}
            </tbody>
          </table>
        </div>

        {filteredRows.length > 0 && (
          <div className="p-4 bg-slate-800/20 text-xs text-slate-400 border-t border-slate-700">
            <div className="flex flex-wrap gap-4">
              <span>Total: {filteredRows.length} transactions</span>
              <span>
                Income: {filteredRows.filter((r) => r.amount > 0).length}
              </span>
              <span>
                Expenses: {filteredRows.filter((r) => r.amount < 0).length}
              </span>
              <span>
                Recurring: {filteredRows.filter((r) => r.is_recurring).length}
              </span>
            </div>
          </div>
        )}
      </div>
    </div>
  );
}

function AddTransactionButton({
  userId,
  onAdded,
}: {
  userId: string;
  onAdded?: () => void;
}) {
  const ctx = useUser();
  const [open, setOpen] = useState(false);
  const [date, setDate] = useState(new Date().toISOString().split("T")[0]);
  const [amount, setAmount] = useState("");
  const [merchant, setMerchant] = useState("");
  const [desc, setDesc] = useState("");
  const [category, setCategory] = useState("");
  const [account, setAccount] = useState("");
  const [useAI, setUseAI] = useState(true);
  const [accounts, setAccounts] = useState<{ id: string; name: string }[]>([]);
  const [busy, setBusy] = useState(false);
  const [loadingAI, setLoadingAI] = useState(false);

  // Load user accounts when modal opens
  useEffect(() => {
    if (open) {
      loadAccounts();
    }
  }, [open]);

  const loadAccounts = async () => {
    try {
      // Get accounts from database directly via transactions table for now
      // In a real app, we'd have a dedicated accounts endpoint
      const res = await fetch(
        `${API}/users/${encodeURIComponent(
          ctx.userId || userId
        )}/transactions?limit=500`,
        { credentials: "include" }
      );
      if (res.ok) {
        const transactions = await res.json();
        console.log("Loaded transactions for accounts:", transactions.length);

        const accountSet = new Set<string>();
        transactions.forEach((tx: any) => {
          if (tx.account_id) {
            accountSet.add(tx.account_id);
          }
        });

        console.log("Found account IDs:", Array.from(accountSet));

        const accountList = Array.from(accountSet).map((id) => ({
          id,
          name:
            id === "a_checking"
              ? "Checking Account"
              : id === "a_credit"
              ? "Credit Card"
              : id === "user1_default"
              ? "Default Account"
              : id
                  .replace("a_", "")
                  .replace("_", " ")
                  .replace(/\b\w/g, (l) => l.toUpperCase()),
        }));

        console.log("Account list created:", accountList);
        setAccounts(accountList);

        if (accountList.length > 0 && !account) {
          setAccount(accountList[0].id); // Default to first account
        }
      } else {
        console.error(
          "Failed to fetch transactions:",
          res.status,
          res.statusText
        );
      }
    } catch (error) {
      console.error("Failed to load accounts:", error);
    }
  };

  // AI Category Suggestion
  const suggestCategory = async () => {
    if (!merchant.trim() && !desc.trim()) {
      ctx.showToast("Please enter a merchant or description first", "info");
      return;
    }

    setLoadingAI(true);
    try {
      const payload = {
        user_id: ctx.userId || userId,
        merchant: merchant.trim(),
        description: desc.trim(),
        top_k: 1,
      };

      const res = await fetch(`${API}/ai/categorizer/predict`, {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        credentials: "include",
        body: JSON.stringify(payload),
      });

      if (res.ok) {
        const result = await res.json();
        if (result.predictions && result.predictions.length > 0) {
          const topCategory = result.predictions[0].label; // API returns "label" not "category"
          setCategory(topCategory);
          ctx.showToast(`AI suggested: ${topCategory}`, "success");
        }
      }
    } catch (error) {
      console.error("AI categorization failed:", error);
      ctx.showToast("AI categorization failed", "error");
    } finally {
      setLoadingAI(false);
    }
  };

  const submit = async () => {
    if (!date || !amount) {
      ctx.showToast("Date and amount are required", "error");
      return;
    }

    const amountNum = parseFloat(amount);
    if (isNaN(amountNum)) {
      ctx.showToast("Please enter a valid amount", "error");
      return;
    }

    setBusy(true);
    try {
      let finalCategory = category.trim();

      // Auto-suggest category with AI if enabled and no category provided
      if (useAI && !finalCategory && (merchant.trim() || desc.trim())) {
        setLoadingAI(true);
        try {
          const aiPayload = {
            user_id: ctx.userId || userId,
            merchant: merchant.trim(),
            description: desc.trim(),
            top_k: 1,
          };

          const aiRes = await fetch(`${API}/ai/categorizer/predict`, {
            method: "POST",
            headers: { "Content-Type": "application/json" },
            credentials: "include",
            body: JSON.stringify(aiPayload),
          });

          if (aiRes.ok) {
            const aiResult = await aiRes.json();
            if (aiResult.predictions && aiResult.predictions.length > 0) {
              finalCategory = aiResult.predictions[0].label; // API returns "label" not "category"
              setCategory(aiResult.predictions[0].label);
              ctx.showToast(
                `AI suggested category: ${aiResult.predictions[0].label}`,
                "info"
              );
            }
          }
        } catch (aiError) {
          console.warn(
            "AI categorization failed, proceeding without:",
            aiError
          );
        } finally {
          setLoadingAI(false);
        }
      }

      const payload = {
        date,
        amount: amountNum,
        merchant: merchant.trim() || undefined,
        description: desc.trim() || undefined,
        category: finalCategory || undefined,
        account_id: account.trim() || undefined,
      };

      const res = await fetch(
        `${API}/users/${encodeURIComponent(ctx.userId || userId)}/transactions`,
        {
          method: "POST",
          headers: { "Content-Type": "application/json" },
          credentials: "include",
          body: JSON.stringify(payload),
        }
      );

      if (!res.ok) {
        throw new Error(`Failed to add transaction: ${res.statusText}`);
      }

      const json = await res.json();

      // Show insights and subscription notifications if any were generated
      const insightsCount = json.insights_generated || 0;
      const subUpdate = json.subscription_update;

      let message = "Transaction added successfully";
      if (insightsCount > 0) {
        message += ` • Generated ${insightsCount} insight${
          insightsCount > 1 ? "s" : ""
        }`;
      }

      if (subUpdate && subUpdate.action !== "none") {
        const subAction = subUpdate.action;
        if (subAction === "detected") {
          message += ` • New subscription detected: ${subUpdate.merchant}`;
        } else if (subAction === "amount_updated") {
          message += ` • Subscription price change: ${subUpdate.merchant}`;
        } else if (subAction === "updated") {
          message += ` • Subscription updated: ${subUpdate.merchant}`;
        }
      }

      ctx.showToast(message, "success");

      // Reset form
      setAmount("");
      setMerchant("");
      setDesc("");
      setCategory("");
      setAccount("");
      setOpen(false);

      if (onAdded) onAdded();
    } catch (e: any) {
      ctx.showToast(e.message || String(e), "error");
    } finally {
      setBusy(false);
    }
  };

  return (
    <div>
      <button
        onClick={() => setOpen(true)}
        className="rounded bg-emerald-500 hover:bg-emerald-600 text-white px-4 py-2 font-medium transition-colors"
      >
        Add Transaction
      </button>
      {open && (
        <div className="fixed inset-0 flex items-center justify-center bg-black/50 z-50">
          <div className="bg-slate-900 border border-slate-700 p-6 rounded-lg w-full max-w-md mx-4">
            <h3 className="font-semibold text-lg mb-4">Add New Transaction</h3>
            <div className="space-y-4">
              <div>
                <label className="block text-sm font-medium text-slate-300 mb-1">
                  Date *
                </label>
                <input
                  type="date"
                  className="w-full px-3 py-2 rounded border border-slate-600 bg-slate-100 text-slate-900"
                  value={date}
                  onChange={(e) => setDate(e.target.value)}
                />
              </div>

              <div>
                <label className="block text-sm font-medium text-slate-300 mb-1">
                  Amount *{" "}
                  <span className="text-xs text-slate-400">
                    (negative for expenses)
                  </span>
                </label>
                <input
                  type="number"
                  step="0.01"
                  className="w-full px-3 py-2 rounded border border-slate-600 bg-slate-100 text-slate-900"
                  placeholder="-25.50 (expense) or 1000.00 (income)"
                  value={amount}
                  onChange={(e) => setAmount(e.target.value)}
                />
              </div>

              <div>
                <label className="block text-sm font-medium text-slate-300 mb-1">
                  Merchant
                </label>
                <input
                  type="text"
                  className="w-full px-3 py-2 rounded border border-slate-600 bg-slate-100 text-slate-900"
                  placeholder="Starbucks, Amazon, etc."
                  value={merchant}
                  onChange={(e) => setMerchant(e.target.value)}
                />
              </div>

              <div>
                <label className="block text-sm font-medium text-slate-300 mb-1">
                  Description
                </label>
                <input
                  type="text"
                  className="w-full px-3 py-2 rounded border border-slate-600 bg-slate-100 text-slate-900"
                  placeholder="Coffee, groceries, salary, etc."
                  value={desc}
                  onChange={(e) => setDesc(e.target.value)}
                />
              </div>

              {/* AI Category Toggle */}
              <div className="flex items-center justify-between p-3 bg-slate-800/40 rounded-lg border border-slate-600">
                <div>
                  <label className="text-sm font-medium text-slate-300">
                    Let AI guess category
                  </label>
                  <p className="text-xs text-slate-400 mt-1">
                    AI will suggest a category based on merchant and description
                  </p>
                </div>
                <label className="relative inline-flex items-center cursor-pointer">
                  <input
                    type="checkbox"
                    className="sr-only peer"
                    checked={useAI}
                    onChange={(e) => setUseAI(e.target.checked)}
                  />
                  <div className="w-11 h-6 bg-slate-600 peer-focus:outline-none peer-focus:ring-4 peer-focus:ring-blue-300 rounded-full peer peer-checked:after:translate-x-full peer-checked:after:border-white after:content-[''] after:absolute after:top-[2px] after:left-[2px] after:bg-white after:border-slate-300 after:border after:rounded-full after:h-5 after:w-5 after:transition-all peer-checked:bg-blue-500"></div>
                </label>
              </div>

              <div className="grid grid-cols-2 gap-3">
                <div>
                  <div className="flex items-center justify-between mb-1">
                    <label className="block text-sm font-medium text-slate-300">
                      Category
                    </label>
                    {useAI && (
                      <button
                        type="button"
                        onClick={suggestCategory}
                        disabled={
                          loadingAI || (!merchant.trim() && !desc.trim())
                        }
                        className="text-xs px-2 py-1 bg-blue-500 hover:bg-blue-600 disabled:opacity-50 disabled:cursor-not-allowed rounded text-white transition-colors"
                      >
                        {loadingAI ? "..." : "AI Suggest"}
                      </button>
                    )}
                  </div>
                  <input
                    type="text"
                    className="w-full px-3 py-2 rounded border border-slate-600 bg-slate-100 text-slate-900"
                    placeholder="food, groceries, income"
                    value={category}
                    onChange={(e) => setCategory(e.target.value)}
                  />
                </div>

                <div>
                  <label className="block text-sm font-medium text-slate-300 mb-1">
                    Account *
                  </label>
                  <select
                    className="w-full px-3 py-2 rounded border border-slate-600 bg-slate-100 text-slate-900"
                    value={account}
                    onChange={(e) => setAccount(e.target.value)}
                    required
                  >
                    <option value="">Select Account</option>
                    {accounts.map((acc) => (
                      <option key={acc.id} value={acc.id}>
                        {acc.name}
                      </option>
                    ))}
                  </select>
                </div>
              </div>
            </div>

            <div className="flex gap-3 mt-6">
              <button
                onClick={submit}
                disabled={busy || loadingAI || !date || !amount || !account}
                className="flex-1 rounded bg-blue-500 hover:bg-blue-600 text-white px-4 py-2 font-medium transition-colors disabled:opacity-50 disabled:cursor-not-allowed"
              >
                {busy
                  ? "Adding..."
                  : loadingAI
                  ? "Getting AI suggestion..."
                  : "Add Transaction"}
              </button>
              <button
                onClick={() => setOpen(false)}
                disabled={busy}
                className="px-4 py-2 rounded bg-slate-600 hover:bg-slate-700 text-white font-medium transition-colors disabled:opacity-50"
              >
                Cancel
              </button>
            </div>
          </div>
        </div>
      )}
    </div>
  );
}
