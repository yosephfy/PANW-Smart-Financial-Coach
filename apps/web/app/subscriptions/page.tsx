"use client";

import { useState, useEffect } from "react";
import { useUser } from "../../components/Providers";
import {
  BarChart,
  Bar,
  XAxis,
  YAxis,
  CartesianGrid,
  Tooltip,
  Legend,
  ResponsiveContainer,
  PieChart,
  Pie,
  Cell,
  LineChart,
  Line,
  Area,
  AreaChart,
} from "recharts";
import { Badge } from "../../components/Badge";

const API = process.env.NEXT_PUBLIC_API_URL || "http://localhost:8000";

// Currency formatter
const fmtCurrency = (x: number) => {
  return new Intl.NumberFormat("en-US", {
    style: "currency",
    currency: "USD",
  }).format(x);
};

// Percentage formatter
const fmtPct = (x: number) => {
  return new Intl.NumberFormat("en-US", {
    style: "percent",
    minimumFractionDigits: 1,
    maximumFractionDigits: 1,
  }).format(x / 100);
};

// Chart colors
const COLORS = [
  "#3b82f6",
  "#ef4444",
  "#f59e0b",
  "#10b981",
  "#8b5cf6",
  "#f97316",
];
const STATUS_COLORS = {
  active: "#10b981",
  paused: "#f59e0b",
  canceled: "#ef4444",
};

interface Subscription {
  merchant: string;
  avg_amount: number;
  cadence: string;
  last_seen: string;
  status: string;
  price_change_pct: number | null;
  trial_converted: boolean;
}

interface SubscriptionAnalytics {
  total_subscriptions: number;
  active_subscriptions: number;
  paused_subscriptions: number;
  canceled_subscriptions: number;
  monthly_total: number;
  yearly_projected: number;
  avg_subscription_cost: number;
  subscription_by_status: Array<{
    name: string;
    value: number;
    amount: number;
  }>;
  subscription_by_cadence: Array<{
    name: string;
    count: number;
    amount: number;
  }>;
  monthly_trends: Array<{ month: string; amount: number }>;
  top_subscriptions: Array<{
    merchant: string;
    amount: number;
    cadence: string;
    status: string;
  }>;
  cost_distribution: Array<{ range: string; count: number }>;
  trial_conversions: number;
  price_increases: number;
  recent_changes: Array<{
    merchant: string;
    status: string;
    days_ago: number;
    amount: number;
  }>;
}

const FilterButton = ({
  active,
  onClick,
  children,
}: {
  active: boolean;
  onClick: () => void;
  children: React.ReactNode;
}) => (
  <button
    onClick={onClick}
    className={`px-3 py-1.5 rounded-md text-sm font-medium transition-colors ${
      active
        ? "bg-blue-600 text-white"
        : "bg-slate-700 text-slate-300 hover:bg-slate-600"
    }`}
  >
    {children}
  </button>
);

const MetricCard = ({
  title,
  value,
  subtitle,
  trend,
}: {
  title: string;
  value: string | number;
  subtitle?: string;
  trend?: { value: number; isPositive: boolean };
}) => (
  <div className="bg-slate-800/60 backdrop-blur rounded-lg p-4 border border-slate-700/50">
    <div className="flex items-center justify-between mb-2">
      <h3 className="text-slate-400 text-sm font-medium">{title}</h3>
      {trend && (
        <span
          className={`text-xs px-2 py-1 rounded ${
            trend.isPositive
              ? "bg-red-500/20 text-red-400"
              : "bg-green-500/20 text-green-400"
          }`}
        >
          {trend.isPositive ? "↑" : "↓"} {Math.abs(trend.value)}%
        </span>
      )}
    </div>
    <div className="text-2xl font-bold text-white mb-1">{value}</div>
    {subtitle && <div className="text-slate-400 text-xs">{subtitle}</div>}
  </div>
);

export default function SubscriptionsPage() {
  const ctx = useUser();
  const [subscriptions, setSubscriptions] = useState<Subscription[]>([]);
  const [analytics, setAnalytics] = useState<SubscriptionAnalytics | null>(
    null
  );
  const [loading, setLoading] = useState(true);
  const [updating, setUpdating] = useState<string | null>(null);
  const [statusFilter, setStatusFilter] = useState<string>("all");
  const [cadenceFilter, setCadenceFilter] = useState<string>("all");
  const [viewMode, setViewMode] = useState<"list" | "analytics">("analytics");

  const userId = "user1"; // Use user1 to match database data

  const fetchSubscriptions = async () => {
    try {
      const response = await fetch(`${API}/users/${userId}/subscriptions`);
      if (response.ok) {
        const data = await response.json();
        setSubscriptions(data);
      }
    } catch (error) {
      console.error("Failed to fetch subscriptions:", error);
      ctx.showToast("Failed to load subscriptions", "error");
    }
  };

  const fetchAnalytics = async () => {
    try {
      const response = await fetch(`${API}/subscriptions/analytics/${userId}`);
      if (response.ok) {
        const data = await response.json();
        setAnalytics(data);
      }
    } catch (error) {
      console.error("Failed to fetch analytics:", error);
      ctx.showToast("Failed to load analytics", "error");
    }
  };

  const detectSubscriptions = async () => {
    setLoading(true);
    try {
      const response = await fetch(`${API}/subscriptions/detect`, {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({ user_id: userId }),
      });

      if (response.ok) {
        const result = await response.json();
        ctx.showToast(
          `Detected ${result.detected} subscriptions (${result.inserted} new, ${result.updated} updated)`,
          "success"
        );
        await Promise.all([fetchSubscriptions(), fetchAnalytics()]);
      } else {
        throw new Error("Detection failed");
      }
    } catch (error) {
      console.error("Subscription detection failed:", error);
      ctx.showToast("Failed to detect subscriptions", "error");
    } finally {
      setLoading(false);
    }
  };

  const updateStatus = async (merchant: string, status: string) => {
    setUpdating(merchant);
    try {
      const response = await fetch(
        `${API}/subscriptions/${encodeURIComponent(merchant)}`,
        {
          method: "PATCH",
          headers: { "Content-Type": "application/json" },
          body: JSON.stringify({ user_id: userId, status }),
        }
      );

      if (response.ok) {
        ctx.showToast(`Updated ${merchant} to ${status}`, "success");
        await Promise.all([fetchSubscriptions(), fetchAnalytics()]);
      } else {
        throw new Error("Update failed");
      }
    } catch (error) {
      console.error("Status update failed:", error);
      ctx.showToast("Failed to update subscription", "error");
    } finally {
      setUpdating(null);
    }
  };

  useEffect(() => {
    const loadData = async () => {
      setLoading(true);
      await Promise.all([fetchSubscriptions(), fetchAnalytics()]);
      setLoading(false);
    };
    loadData();
  }, []);

  // Filter subscriptions based on selected filters
  const filteredSubscriptions = subscriptions.filter((sub) => {
    const statusMatch = statusFilter === "all" || sub.status === statusFilter;
    const cadenceMatch =
      cadenceFilter === "all" || sub.cadence === cadenceFilter;
    return statusMatch && cadenceMatch;
  });

  if (loading && !analytics) {
    return (
      <div className="min-h-screen bg-slate-900 text-white p-4">
        <div className="max-w-6xl mx-auto">
          <div className="animate-pulse space-y-4">
            <div className="h-8 bg-slate-700 rounded w-1/3"></div>
            <div className="grid grid-cols-1 md:grid-cols-4 gap-4">
              {[1, 2, 3, 4].map((i) => (
                <div key={i} className="h-24 bg-slate-700 rounded"></div>
              ))}
            </div>
            <div className="h-64 bg-slate-700 rounded"></div>
          </div>
        </div>
      </div>
    );
  }

  return (
    <div className="min-h-screen bg-slate-900 text-white p-4">
      <div className="max-w-6xl mx-auto space-y-6">
        {/* Header */}
        <div className="flex flex-col sm:flex-row justify-between items-start sm:items-center gap-4">
          <div>
            <h1 className="text-3xl font-bold mb-2">Subscription Management</h1>
            <p className="text-slate-400">
              Track and manage your recurring subscriptions
            </p>
          </div>
          <div className="flex gap-2">
            <FilterButton
              active={viewMode === "analytics"}
              onClick={() => setViewMode("analytics")}
            >
              Analytics
            </FilterButton>
            <FilterButton
              active={viewMode === "list"}
              onClick={() => setViewMode("list")}
            >
              List View
            </FilterButton>
            <button
              onClick={detectSubscriptions}
              disabled={loading}
              className="px-4 py-2 bg-blue-600 hover:bg-blue-700 disabled:bg-blue-800 rounded-md text-sm font-medium transition-colors"
            >
              {loading ? "Detecting..." : "Detect Subscriptions"}
            </button>
          </div>
        </div>

        {/* Analytics View */}
        {viewMode === "analytics" && analytics && (
          <div className="space-y-6">
            {/* Key Metrics */}
            <div className="grid grid-cols-1 sm:grid-cols-2 lg:grid-cols-4 gap-4">
              <MetricCard
                title="Total Subscriptions"
                value={analytics.total_subscriptions}
                subtitle={`${analytics.active_subscriptions} active`}
              />
              <MetricCard
                title="Monthly Total"
                value={fmtCurrency(analytics.monthly_total)}
                subtitle="Active subscriptions only"
              />
              <MetricCard
                title="Yearly Projected"
                value={fmtCurrency(analytics.yearly_projected)}
                subtitle="Based on current active"
              />
              <MetricCard
                title="Average Cost"
                value={fmtCurrency(analytics.avg_subscription_cost)}
                subtitle="Per active subscription"
              />
            </div>

            {/* Status Overview */}
            <div className="grid grid-cols-1 lg:grid-cols-2 gap-6">
              <div className="bg-slate-800/60 backdrop-blur rounded-lg p-4 border border-slate-700/50">
                <h3 className="text-lg font-semibold mb-4">
                  Status Distribution
                </h3>
                <ResponsiveContainer width="100%" height={200}>
                  <PieChart>
                    <Pie
                      data={analytics.subscription_by_status}
                      cx="50%"
                      cy="50%"
                      labelLine={false}
                      label={({ name, value }) => `${name}: ${value}`}
                      outerRadius={80}
                      fill="#8884d8"
                      dataKey="value"
                    >
                      {analytics.subscription_by_status.map((entry, index) => (
                        <Cell
                          key={`cell-${index}`}
                          fill={
                            STATUS_COLORS[
                              entry.name.toLowerCase() as keyof typeof STATUS_COLORS
                            ] || COLORS[index % COLORS.length]
                          }
                        />
                      ))}
                    </Pie>
                    <Tooltip />
                  </PieChart>
                </ResponsiveContainer>
              </div>

              <div className="bg-slate-800/60 backdrop-blur rounded-lg p-4 border border-slate-700/50">
                <h3 className="text-lg font-semibold mb-4">
                  Cadence Breakdown
                </h3>
                <ResponsiveContainer width="100%" height={200}>
                  <BarChart data={analytics.subscription_by_cadence}>
                    <CartesianGrid strokeDasharray="3 3" stroke="#374151" />
                    <XAxis
                      dataKey="name"
                      tick={{ fill: "#9ca3af", fontSize: 12 }}
                    />
                    <YAxis tick={{ fill: "#9ca3af", fontSize: 12 }} />
                    <Tooltip
                      contentStyle={{
                        backgroundColor: "#1f2937",
                        border: "1px solid #374151",
                      }}
                      formatter={(value, name) => [
                        name === "count"
                          ? `${value} subscriptions`
                          : fmtCurrency(Number(value)),
                        name === "count" ? "Count" : "Total Amount",
                      ]}
                    />
                    <Bar dataKey="count" fill="#3b82f6" />
                  </BarChart>
                </ResponsiveContainer>
              </div>
            </div>

            {/* Monthly Trends */}
            {analytics.monthly_trends.length > 0 && (
              <div className="bg-slate-800/60 backdrop-blur rounded-lg p-4 border border-slate-700/50">
                <h3 className="text-lg font-semibold mb-4">
                  Monthly Subscription Spending
                </h3>
                <ResponsiveContainer width="100%" height={300}>
                  <AreaChart data={analytics.monthly_trends.reverse()}>
                    <CartesianGrid strokeDasharray="3 3" stroke="#374151" />
                    <XAxis
                      dataKey="month"
                      tick={{ fill: "#9ca3af", fontSize: 12 }}
                    />
                    <YAxis
                      tick={{ fill: "#9ca3af", fontSize: 12 }}
                      tickFormatter={(value) => fmtCurrency(value)}
                    />
                    <Tooltip
                      contentStyle={{
                        backgroundColor: "#1f2937",
                        border: "1px solid #374151",
                      }}
                      formatter={(value) => [
                        fmtCurrency(Number(value)),
                        "Spending",
                      ]}
                    />
                    <Area
                      type="monotone"
                      dataKey="amount"
                      stroke="#3b82f6"
                      fill="#3b82f6"
                      fillOpacity={0.3}
                    />
                  </AreaChart>
                </ResponsiveContainer>
              </div>
            )}

            {/* Cost Distribution & Insights */}
            <div className="grid grid-cols-1 lg:grid-cols-2 gap-6">
              <div className="bg-slate-800/60 backdrop-blur rounded-lg p-4 border border-slate-700/50">
                <h3 className="text-lg font-semibold mb-4">
                  Cost Distribution
                </h3>
                <ResponsiveContainer width="100%" height={200}>
                  <BarChart data={analytics.cost_distribution}>
                    <CartesianGrid strokeDasharray="3 3" stroke="#374151" />
                    <XAxis
                      dataKey="range"
                      tick={{ fill: "#9ca3af", fontSize: 12 }}
                    />
                    <YAxis tick={{ fill: "#9ca3af", fontSize: 12 }} />
                    <Tooltip
                      contentStyle={{
                        backgroundColor: "#1f2937",
                        border: "1px solid #374151",
                      }}
                      formatter={(value) => [`${value} subscriptions`, "Count"]}
                    />
                    <Bar dataKey="count" fill="#10b981" />
                  </BarChart>
                </ResponsiveContainer>
              </div>

              <div className="bg-slate-800/60 backdrop-blur rounded-lg p-4 border border-slate-700/50">
                <h3 className="text-lg font-semibold mb-4">Insights</h3>
                <div className="space-y-3">
                  <div className="flex justify-between items-center p-2 bg-slate-700/50 rounded">
                    <span className="text-slate-300">Trial Conversions</span>
                    <Badge variant="info">{analytics.trial_conversions}</Badge>
                  </div>
                  <div className="flex justify-between items-center p-2 bg-slate-700/50 rounded">
                    <span className="text-slate-300">Price Increases</span>
                    <Badge variant="warning">{analytics.price_increases}</Badge>
                  </div>
                  <div className="flex justify-between items-center p-2 bg-slate-700/50 rounded">
                    <span className="text-slate-300">Active vs Total</span>
                    <Badge variant="success">
                      {Math.round(
                        (analytics.active_subscriptions /
                          Math.max(analytics.total_subscriptions, 1)) *
                          100
                      )}
                      %
                    </Badge>
                  </div>
                </div>
              </div>
            </div>

            {/* Recent Changes */}
            {analytics.recent_changes.length > 0 && (
              <div className="bg-slate-800/60 backdrop-blur rounded-lg p-4 border border-slate-700/50">
                <h3 className="text-lg font-semibold mb-4">
                  Recent Activity (Last 30 Days)
                </h3>
                <div className="space-y-2">
                  {analytics.recent_changes.map((change, index) => (
                    <div
                      key={index}
                      className="flex justify-between items-center p-2 bg-slate-700/50 rounded"
                    >
                      <div className="flex items-center gap-3">
                        <span className="font-medium">{change.merchant}</span>
                        <Badge
                          variant={
                            change.status === "active"
                              ? "success"
                              : change.status === "paused"
                              ? "warning"
                              : "danger"
                          }
                        >
                          {change.status}
                        </Badge>
                      </div>
                      <div className="text-right">
                        <div className="text-amber-200">
                          {fmtCurrency(change.amount)}
                        </div>
                        <div className="text-xs text-slate-400">
                          {change.days_ago} days ago
                        </div>
                      </div>
                    </div>
                  ))}
                </div>
              </div>
            )}
          </div>
        )}

        {/* List View */}
        {viewMode === "list" && (
          <div className="space-y-4">
            {/* Filters */}
            <div className="flex flex-wrap gap-4 items-center">
              <div className="flex items-center gap-2">
                <span className="text-sm text-slate-400">Status:</span>
                <div className="flex gap-1">
                  {["all", "active", "paused", "canceled"].map((status) => (
                    <FilterButton
                      key={status}
                      active={statusFilter === status}
                      onClick={() => setStatusFilter(status)}
                    >
                      {status.charAt(0).toUpperCase() + status.slice(1)}
                    </FilterButton>
                  ))}
                </div>
              </div>
              <div className="flex items-center gap-2">
                <span className="text-sm text-slate-400">Cadence:</span>
                <div className="flex gap-1">
                  {["all", "monthly", "weekly", "yearly"].map((cadence) => (
                    <FilterButton
                      key={cadence}
                      active={cadenceFilter === cadence}
                      onClick={() => setCadenceFilter(cadence)}
                    >
                      {cadence.charAt(0).toUpperCase() + cadence.slice(1)}
                    </FilterButton>
                  ))}
                </div>
              </div>
            </div>

            {/* Subscription Chart */}
            {filteredSubscriptions.length > 0 && (
              <div className="bg-slate-800/60 backdrop-blur rounded-lg p-4 border border-slate-700/50">
                <h3 className="text-lg font-semibold mb-4">
                  Subscription Costs ({filteredSubscriptions.length}{" "}
                  subscriptions)
                </h3>
                <ResponsiveContainer width="100%" height={250}>
                  <BarChart data={filteredSubscriptions.slice(0, 15)}>
                    <CartesianGrid strokeDasharray="3 3" stroke="#374151" />
                    <XAxis
                      dataKey="merchant"
                      tick={{ fill: "#9ca3af", fontSize: 10 }}
                      angle={-45}
                      textAnchor="end"
                      height={60}
                    />
                    <YAxis
                      tick={{ fill: "#9ca3af", fontSize: 12 }}
                      tickFormatter={(value) => fmtCurrency(value)}
                    />
                    <Tooltip
                      contentStyle={{
                        backgroundColor: "#1f2937",
                        border: "1px solid #374151",
                      }}
                      formatter={(value) => [
                        fmtCurrency(Number(value)),
                        "Amount",
                      ]}
                    />
                    <Bar dataKey="avg_amount" fill="#3b82f6" />
                  </BarChart>
                </ResponsiveContainer>
              </div>
            )}

            {/* Subscription Table */}
            <div className="overflow-auto border border-slate-700 rounded">
              <table className="min-w-full text-sm">
                <thead className="bg-slate-800/60">
                  <tr className="text-left">
                    <th className="px-3 py-2">Merchant</th>
                    <th className="px-3 py-2">Avg Amount</th>
                    <th className="px-3 py-2">Cadence</th>
                    <th className="px-3 py-2">Last Seen</th>
                    <th className="px-3 py-2">Status</th>
                    <th className="px-3 py-2">Trial</th>
                    <th className="px-3 py-2">Price Change %</th>
                    <th className="px-3 py-2">Actions</th>
                  </tr>
                </thead>
                <tbody>
                  {filteredSubscriptions.map((sub) => (
                    <tr
                      key={`${sub.merchant}-${sub.cadence}`}
                      className="border-t border-slate-700/60"
                    >
                      <td className="px-3 py-2 font-medium">{sub.merchant}</td>
                      <td className="px-3 py-2 text-amber-200">
                        -{fmtCurrency(sub.avg_amount)}
                      </td>
                      <td className="px-3 py-2">
                        <Badge variant="info">{sub.cadence}</Badge>
                      </td>
                      <td className="px-3 py-2 text-slate-300">
                        {sub.last_seen}
                      </td>
                      <td className="px-3 py-2">
                        <Badge
                          variant={
                            sub.status === "active"
                              ? "success"
                              : sub.status === "canceled"
                              ? "danger"
                              : "warning"
                          }
                        >
                          {sub.status}
                        </Badge>
                      </td>
                      <td className="px-3 py-2">
                        {sub.trial_converted ? (
                          <Badge variant="warning">Trial converted</Badge>
                        ) : (
                          <span className="text-slate-400">-</span>
                        )}
                      </td>
                      <td
                        className={`px-3 py-2 ${
                          sub.price_change_pct && sub.price_change_pct > 0
                            ? "text-red-400"
                            : sub.price_change_pct && sub.price_change_pct < 0
                            ? "text-green-400"
                            : "text-slate-300"
                        }`}
                      >
                        {sub.price_change_pct != null
                          ? fmtPct(sub.price_change_pct)
                          : "-"}
                      </td>
                      <td className="px-3 py-2">
                        <div className="flex gap-1">
                          <button
                            disabled={updating === sub.merchant}
                            onClick={() => updateStatus(sub.merchant, "active")}
                            className="px-2 py-0.5 rounded bg-green-600 hover:bg-green-700 disabled:bg-green-800 text-xs transition-colors"
                          >
                            Active
                          </button>
                          <button
                            disabled={updating === sub.merchant}
                            onClick={() => updateStatus(sub.merchant, "paused")}
                            className="px-2 py-0.5 rounded bg-yellow-600 hover:bg-yellow-700 disabled:bg-yellow-800 text-xs transition-colors"
                          >
                            Pause
                          </button>
                          <button
                            disabled={updating === sub.merchant}
                            onClick={() =>
                              updateStatus(sub.merchant, "canceled")
                            }
                            className="px-2 py-0.5 rounded bg-red-600 hover:bg-red-700 disabled:bg-red-800 text-xs transition-colors"
                          >
                            Cancel
                          </button>
                        </div>
                      </td>
                    </tr>
                  ))}
                  {filteredSubscriptions.length === 0 && (
                    <tr>
                      <td
                        colSpan={8}
                        className="px-3 py-6 text-center text-slate-400"
                      >
                        {subscriptions.length === 0
                          ? "No subscriptions detected. Click 'Detect Subscriptions' to scan your transactions."
                          : "No subscriptions match the current filters."}
                      </td>
                    </tr>
                  )}
                </tbody>
              </table>
            </div>
          </div>
        )}
      </div>
    </div>
  );
}
