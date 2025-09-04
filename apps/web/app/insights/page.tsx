"use client";

import { useEffect, useState } from "react";
import { Badge } from "../../components/Badge";
import { useUser } from "../../components/Providers";
import React from "react";
import {
  PieChart,
  Pie,
  Cell,
  ResponsiveContainer,
  BarChart,
  Bar,
  XAxis,
  YAxis,
  CartesianGrid,
  Tooltip,
  Legend,
  LineChart,
  Line,
  Area,
  AreaChart,
} from "recharts";

const API = process.env.NEXT_PUBLIC_API_URL || "http://localhost:3000/backend";

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
  read_at?: string | null;
};

type InsightAnalytics = {
  total_insights: number;
  critical_count: number;
  warning_count: number;
  info_count: number;
  unread_count: number;
  by_type: Record<string, number>;
  by_severity: Record<string, number>;
  recent_trends: Array<{
    date: string;
    count: number;
    critical: number;
    warning: number;
    info: number;
  }>;
  top_categories: Array<{
    type: string;
    count: number;
    severity_distribution: Record<string, number>;
  }>;
};

const SEVERITY_COLORS = {
  critical: "#ef4444", // red
  warn: "#f59e0b", // amber
  warning: "#f59e0b", // amber (alternate)
  info: "#3b82f6", // blue
  neutral: "#6b7280", // gray
};

const TYPE_COLORS = [
  "#8b5cf6", // violet
  "#06b6d4", // cyan
  "#10b981", // emerald
  "#f59e0b", // amber
  "#ef4444", // red
  "#ec4899", // pink
  "#84cc16", // lime
  "#f97316", // orange
];

function severityVariant(sev?: string) {
  switch (sev) {
    case "critical":
      return "danger";
    case "warn":
    case "warning":
      return "warning";
    case "info":
      return "info";
    default:
      return "neutral";
  }
}

function getInsightIcon(type: string) {
  switch (type) {
    case "overspend_category":
    case "overspend":
      return "💰";
    case "trending_category":
    case "trending":
      return "📈";
    case "ml_outlier":
      return "🔍";
    case "expense_spike":
      return "⚡";
    case "merchant_spike":
      return "🏪";
    case "daily_spend_high":
      return "📊";
    case "budget":
    case "budget_alert":
      return "🚨";
    case "budget_progress":
      return "📋";
    case "budget_suggestion":
      return "💡";
    case "save_suggestion":
      return "💰";
    case "subscription_detected":
      return "🔄";
    case "subscription_price_change":
      return "💲";
    case "trial_converted":
      return "🔚";
    default:
      return "ℹ️";
  }
}

function formatInsightType(type: string) {
  return type.replace(/_/g, " ").replace(/\b\w/g, (l) => l.toUpperCase());
}

// MetricCard component for summary statistics
function MetricCard({
  title,
  value,
  subtitle,
  color = "blue",
  icon,
}: {
  title: string;
  value: string | number;
  subtitle?: string;
  color?: string;
  icon?: string;
}) {
  const colorClasses = {
    blue: "bg-blue-900/20 border-blue-500/30",
    green: "bg-emerald-900/20 border-emerald-500/30",
    yellow: "bg-yellow-900/20 border-yellow-500/30",
    red: "bg-red-900/20 border-red-500/30",
    purple: "bg-purple-900/20 border-purple-500/30",
  };

  return (
    <div
      className={`border rounded-lg p-4 ${
        colorClasses[color as keyof typeof colorClasses] || colorClasses.blue
      }`}
    >
      <div className="flex items-center gap-2 mb-2">
        {icon && <span className="text-lg">{icon}</span>}
        <h3 className="text-sm font-medium text-slate-400">{title}</h3>
      </div>
      <div className="text-2xl font-bold mb-1">{value}</div>
      {subtitle && <p className="text-xs text-slate-400">{subtitle}</p>}
    </div>
  );
}

// FilterButton component
function FilterButton({
  active,
  onClick,
  children,
  count,
}: {
  active: boolean;
  onClick: () => void;
  children: React.ReactNode;
  count?: number;
}) {
  return (
    <button
      onClick={onClick}
      className={`text-xs px-3 py-1.5 rounded-full whitespace-nowrap transition-colors ${
        active
          ? "bg-blue-500 text-white"
          : "bg-slate-800 text-slate-300 hover:bg-slate-700 border border-slate-600"
      }`}
    >
      {children}
      {count !== undefined && (
        <span className="ml-1 opacity-75">({count})</span>
      )}
    </button>
  );
}

export default function InsightsPage() {
  const ctx = useUser();
  const [rows, setRows] = useState<Insight[]>([]);
  const [analytics, setAnalytics] = useState<InsightAnalytics | null>(null);
  const [filter, setFilter] = useState<string>("all");
  const [severityFilter, setSeverityFilter] = useState<string>("all");
  const [viewMode, setViewMode] = useState<"dashboard" | "list">("dashboard");
  const [busy, setBusy] = useState(false);
  const [genBusy, setGenBusy] = useState(false);
  const [mlBusy, setMlBusy] = useState(false);

  // Use "user1" if no context user ID is available (consistent with subscriptions page)
  const userId = ctx.userId || "user1";

  const load = async () => {
    setBusy(true);
    try {
      const res = await fetch(
        `${API}/users/${encodeURIComponent(userId)}/insights`
      );
      const json = await res.json();
      const insights = Array.isArray(json) ? json : [];
      setRows(insights);

      // Calculate analytics
      const analytics = calculateAnalytics(insights);
      setAnalytics(analytics);
    } finally {
      setBusy(false);
    }
  };

  const calculateAnalytics = (insights: Insight[]): InsightAnalytics => {
    const total_insights = insights.length;
    const critical_count = insights.filter(
      (i) => i.severity === "critical"
    ).length;
    const warning_count = insights.filter(
      (i) => i.severity === "warn" || i.severity === "warning"
    ).length;
    const info_count = insights.filter((i) => i.severity === "info").length;
    const unread_count = insights.filter((i) => !i.read_at).length;

    const by_type: Record<string, number> = {};
    const by_severity: Record<string, number> = {};

    insights.forEach((insight) => {
      by_type[insight.type] = (by_type[insight.type] || 0) + 1;
      by_severity[insight.severity] = (by_severity[insight.severity] || 0) + 1;
    });

    // Calculate recent trends (group by date)
    const dateGroups: Record<
      string,
      { total: number; critical: number; warning: number; info: number }
    > = {};
    insights.forEach((insight) => {
      if (insight.created_at) {
        const date =
          insight.created_at.split("T")[0] || insight.created_at.split(" ")[0];
        if (!dateGroups[date]) {
          dateGroups[date] = { total: 0, critical: 0, warning: 0, info: 0 };
        }
        dateGroups[date].total++;
        if (insight.severity === "critical") dateGroups[date].critical++;
        else if (insight.severity === "warn" || insight.severity === "warning")
          dateGroups[date].warning++;
        else dateGroups[date].info++;
      }
    });

    const recent_trends = Object.entries(dateGroups)
      .map(([date, counts]) => ({
        date,
        count: counts.total,
        critical: counts.critical,
        warning: counts.warning,
        info: counts.info,
      }))
      .sort((a, b) => a.date.localeCompare(b.date))
      .slice(-7); // Last 7 days

    // Top categories with severity distribution
    const top_categories = Object.entries(by_type)
      .map(([type, count]) => {
        const severity_distribution: Record<string, number> = {};
        insights
          .filter((i) => i.type === type)
          .forEach((insight) => {
            severity_distribution[insight.severity] =
              (severity_distribution[insight.severity] || 0) + 1;
          });
        return { type, count, severity_distribution };
      })
      .sort((a, b) => b.count - a.count)
      .slice(0, 8);

    return {
      total_insights,
      critical_count,
      warning_count,
      info_count,
      unread_count,
      by_type,
      by_severity,
      recent_trends,
      top_categories,
    };
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
      ctx.showToast("Insights generated successfully", "success");
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
      ctx.showToast("ML anomaly detection completed", "success");
    } finally {
      setMlBusy(false);
    }
  };

  const markAsRead = async (insightId: string) => {
    try {
      // This would need a backend endpoint to mark as read
      // For now, just update locally
      setRows((prev) =>
        prev.map((row) =>
          row.id === insightId
            ? { ...row, read_at: new Date().toISOString() }
            : row
        )
      );
    } catch (error) {
      console.error("Failed to mark insight as read:", error);
    }
  };

  useEffect(() => {
    if (userId) load();
  }, [userId]);

  // Filter insights based on current filters
  const filteredInsights = rows.filter((insight) => {
    const typeMatch = filter === "all" || insight.type === filter;
    const severityMatch =
      severityFilter === "all" || insight.severity === severityFilter;
    return typeMatch && severityMatch;
  });

  // Prepare chart data
  const severityChartData = analytics
    ? Object.entries(analytics.by_severity).map(([severity, count]) => ({
        name: severity.charAt(0).toUpperCase() + severity.slice(1),
        value: count,
        color:
          SEVERITY_COLORS[severity as keyof typeof SEVERITY_COLORS] ||
          SEVERITY_COLORS.neutral,
      }))
    : [];

  const typeChartData = analytics
    ? analytics.top_categories.slice(0, 6).map((cat, index) => ({
        name: formatInsightType(cat.type),
        count: cat.count,
        color: TYPE_COLORS[index % TYPE_COLORS.length],
      }))
    : [];

  return (
    <div className="space-y-6">
      {/* Header */}
      <div className="flex items-center justify-between">
        <div>
          <h1 className="text-2xl font-bold text-white">Financial Insights</h1>
          <p className="text-slate-400">
            AI-powered analysis of your spending patterns
          </p>
        </div>
        <div className="flex items-center gap-3">
          <div className="flex rounded-lg border border-slate-600 overflow-hidden">
            <button
              onClick={() => setViewMode("dashboard")}
              className={`px-4 py-2 text-sm font-medium transition-colors ${
                viewMode === "dashboard"
                  ? "bg-blue-500 text-white"
                  : "text-slate-300 hover:text-white hover:bg-slate-700"
              }`}
            >
              📊 Dashboard
            </button>
            <button
              onClick={() => setViewMode("list")}
              className={`px-4 py-2 text-sm font-medium transition-colors ${
                viewMode === "list"
                  ? "bg-blue-500 text-white"
                  : "text-slate-300 hover:text-white hover:bg-slate-700"
              }`}
            >
              📋 List View
            </button>
          </div>
        </div>
      </div>

      {/* Action Buttons */}
      <div className="flex gap-3 items-center">
        <button
          onClick={load}
          disabled={busy}
          className="rounded-lg bg-blue-500 hover:bg-blue-600 text-white px-4 py-2 disabled:opacity-50 disabled:cursor-not-allowed transition-colors"
        >
          {busy ? "🔄 Loading..." : "🔄 Refresh"}
        </button>
        <button
          onClick={generate}
          disabled={genBusy}
          className="rounded-lg bg-emerald-500 hover:bg-emerald-600 text-white px-4 py-2 disabled:opacity-50 disabled:cursor-not-allowed transition-colors"
        >
          {genBusy ? "✨ Generating..." : "✨ Generate New Insights"}
        </button>
        <button
          onClick={runML}
          disabled={mlBusy}
          className="rounded-lg bg-purple-500 hover:bg-purple-600 text-white px-4 py-2 disabled:opacity-50 disabled:cursor-not-allowed transition-colors"
        >
          {mlBusy ? "🔍 Analyzing..." : "🤖 Run ML Analysis"}
        </button>
      </div>

      {analytics && viewMode === "dashboard" && (
        <>
          {/* Summary Cards */}
          <div className="grid grid-cols-2 md:grid-cols-5 gap-4">
            <MetricCard
              title="Total Insights"
              value={analytics.total_insights}
              subtitle="All insights generated"
              color="blue"
              icon="📊"
            />
            <MetricCard
              title="Critical Issues"
              value={analytics.critical_count}
              subtitle="Require immediate attention"
              color="red"
              icon="🚨"
            />
            <MetricCard
              title="Warnings"
              value={analytics.warning_count}
              subtitle="Need monitoring"
              color="yellow"
              icon="⚠️"
            />
            <MetricCard
              title="Informational"
              value={analytics.info_count}
              subtitle="General insights"
              color="green"
              icon="ℹ️"
            />
            <MetricCard
              title="Unread"
              value={analytics.unread_count}
              subtitle="New insights"
              color="purple"
              icon="🔔"
            />
          </div>

          {/* Charts Row */}
          <div className="grid md:grid-cols-2 gap-6">
            {/* Severity Distribution */}
            <div className="border border-slate-700 rounded-lg p-4">
              <h3 className="text-lg font-semibold mb-4 flex items-center gap-2">
                <span>📈</span> Severity Distribution
              </h3>
              <ResponsiveContainer width="100%" height={250}>
                <PieChart>
                  <Pie
                    data={severityChartData}
                    cx="50%"
                    cy="50%"
                    innerRadius={40}
                    outerRadius={100}
                    paddingAngle={2}
                    dataKey="value"
                  >
                    {severityChartData.map((entry, index) => (
                      <Cell key={`cell-${index}`} fill={entry.color} />
                    ))}
                  </Pie>
                  <Tooltip
                    contentStyle={{
                      backgroundColor: "#1e293b",
                      border: "1px solid #475569",
                      borderRadius: "8px",
                      color: "#f1f5f9",
                    }}
                  />
                  <Legend />
                </PieChart>
              </ResponsiveContainer>
            </div>

            {/* Top Categories */}
            <div className="border border-slate-700 rounded-lg p-4">
              <h3 className="text-lg font-semibold mb-4 flex items-center gap-2">
                <span>🏷️</span> Top Insight Categories
              </h3>
              <ResponsiveContainer width="100%" height={250}>
                <BarChart
                  data={typeChartData}
                  margin={{ top: 20, right: 30, left: 20, bottom: 5 }}
                >
                  <CartesianGrid strokeDasharray="3 3" stroke="#374151" />
                  <XAxis
                    dataKey="name"
                    stroke="#9ca3af"
                    angle={-45}
                    textAnchor="end"
                    height={60}
                    fontSize={10}
                  />
                  <YAxis stroke="#9ca3af" />
                  <Tooltip
                    contentStyle={{
                      backgroundColor: "#1e293b",
                      border: "1px solid #475569",
                      borderRadius: "8px",
                      color: "#f1f5f9",
                    }}
                  />
                  <Bar dataKey="count" fill="#3b82f6" radius={[4, 4, 0, 0]} />
                </BarChart>
              </ResponsiveContainer>
            </div>
          </div>

          {/* Recent Trends */}
          {analytics.recent_trends.length > 0 && (
            <div className="border border-slate-700 rounded-lg p-4">
              <h3 className="text-lg font-semibold mb-4 flex items-center gap-2">
                <span>📅</span> Recent Trends (Last 7 Days)
              </h3>
              <ResponsiveContainer width="100%" height={200}>
                <AreaChart data={analytics.recent_trends}>
                  <CartesianGrid strokeDasharray="3 3" stroke="#374151" />
                  <XAxis dataKey="date" stroke="#9ca3af" />
                  <YAxis stroke="#9ca3af" />
                  <Tooltip
                    contentStyle={{
                      backgroundColor: "#1e293b",
                      border: "1px solid #475569",
                      borderRadius: "8px",
                      color: "#f1f5f9",
                    }}
                  />
                  <Area
                    type="monotone"
                    dataKey="critical"
                    stackId="1"
                    stroke="#ef4444"
                    fill="#ef4444"
                    fillOpacity={0.8}
                  />
                  <Area
                    type="monotone"
                    dataKey="warning"
                    stackId="1"
                    stroke="#f59e0b"
                    fill="#f59e0b"
                    fillOpacity={0.8}
                  />
                  <Area
                    type="monotone"
                    dataKey="info"
                    stackId="1"
                    stroke="#3b82f6"
                    fill="#3b82f6"
                    fillOpacity={0.8}
                  />
                </AreaChart>
              </ResponsiveContainer>
            </div>
          )}
        </>
      )}

      {/* Filters */}
      <div className="space-y-4">
        <div>
          <h4 className="text-sm font-medium text-slate-300 mb-2">
            Filter by Category
          </h4>
          <div className="flex gap-2 flex-wrap">
            <FilterButton
              active={filter === "all"}
              onClick={() => setFilter("all")}
              count={rows.length}
            >
              All Insights
            </FilterButton>
            {analytics &&
              Object.entries(analytics.by_type)
                .sort(([, a], [, b]) => b - a)
                .slice(0, 8)
                .map(([type, count]) => (
                  <FilterButton
                    key={type}
                    active={filter === type}
                    onClick={() => setFilter(type)}
                    count={count}
                  >
                    {getInsightIcon(type)} {formatInsightType(type)}
                  </FilterButton>
                ))}
          </div>
        </div>

        <div>
          <h4 className="text-sm font-medium text-slate-300 mb-2">
            Filter by Severity
          </h4>
          <div className="flex gap-2 flex-wrap">
            <FilterButton
              active={severityFilter === "all"}
              onClick={() => setSeverityFilter("all")}
              count={rows.length}
            >
              All Severities
            </FilterButton>
            {analytics &&
              Object.entries(analytics.by_severity).map(([severity, count]) => (
                <FilterButton
                  key={severity}
                  active={severityFilter === severity}
                  onClick={() => setSeverityFilter(severity)}
                  count={count}
                >
                  {severity === "critical" && "🚨"}
                  {(severity === "warn" || severity === "warning") && "⚠️"}
                  {severity === "info" && "ℹ️"}{" "}
                  {severity.charAt(0).toUpperCase() + severity.slice(1)}
                </FilterButton>
              ))}
          </div>
        </div>
      </div>

      {/* Insights List/Grid */}
      <div className={viewMode === "dashboard" ? "grid gap-4" : "space-y-3"}>
        {filteredInsights.length > 0 ? (
          filteredInsights.map((insight) => (
            <div
              key={insight.id}
              className={`border border-slate-700 rounded-lg p-4 transition-all hover:border-slate-600 ${
                !insight.read_at ? "bg-slate-900/50" : "bg-transparent"
              }`}
            >
              <div className="flex items-start justify-between gap-3">
                <div className="flex items-start gap-3 flex-1">
                  <div className="text-2xl">{getInsightIcon(insight.type)}</div>
                  <div className="flex-1 min-w-0">
                    <div className="flex items-center gap-2 mb-2 flex-wrap">
                      <Badge variant={severityVariant(insight.severity)}>
                        {insight.severity}
                      </Badge>
                      <Badge variant="neutral">
                        {formatInsightType(insight.type)}
                      </Badge>
                      {insight.rewritten_title && (
                        <Badge variant="info">✨ AI Enhanced</Badge>
                      )}
                      {!insight.read_at && (
                        <Badge variant="warning">🔔 New</Badge>
                      )}
                    </div>
                    <h4 className="font-semibold text-white text-lg mb-2">
                      {insight.rewritten_title || insight.title}
                    </h4>
                    <p className="text-slate-300 text-sm leading-relaxed">
                      {insight.rewritten_body || insight.body}
                    </p>
                    <div className="flex items-center justify-between mt-3">
                      <div className="text-xs text-slate-500">
                        {insight.created_at &&
                          new Date(insight.created_at).toLocaleString()}
                      </div>
                      {!insight.read_at && (
                        <button
                          onClick={() => markAsRead(insight.id)}
                          className="text-xs text-blue-400 hover:text-blue-300 transition-colors"
                        >
                          Mark as read
                        </button>
                      )}
                    </div>
                  </div>
                </div>
              </div>

              {insight.data_json && (
                <details className="mt-4">
                  <summary className="cursor-pointer text-xs text-slate-400 hover:text-slate-300 transition-colors">
                    📋 View Technical Details
                  </summary>
                  <pre className="text-xs bg-slate-900/70 p-3 rounded-lg overflow-auto mt-2 border border-slate-700">
                    {JSON.stringify(JSON.parse(insight.data_json), null, 2)}
                  </pre>
                </details>
              )}
            </div>
          ))
        ) : (
          <div className="text-center py-12 border border-slate-700 rounded-lg">
            <div className="text-4xl mb-4">🔍</div>
            <h3 className="text-lg font-semibold text-slate-300 mb-2">
              No insights found
            </h3>
            <p className="text-slate-400 mb-4">
              {rows.length === 0
                ? "Generate your first insights to get started"
                : "No insights match your current filters"}
            </p>
            {rows.length === 0 && (
              <button
                onClick={generate}
                disabled={genBusy}
                className="bg-emerald-500 hover:bg-emerald-600 text-white px-6 py-2 rounded-lg disabled:opacity-50 transition-colors"
              >
                {genBusy ? "Generating..." : "Generate Insights"}
              </button>
            )}
          </div>
        )}
      </div>

      {/* Footer Stats */}
      {analytics && (
        <div className="border-t border-slate-700 pt-4">
          <div className="flex items-center justify-between text-sm text-slate-400">
            <span>
              Showing {filteredInsights.length} of {analytics.total_insights}{" "}
              insights
            </span>
            <span>
              Last updated:{" "}
              {rows.length > 0 && rows[0].created_at
                ? new Date(rows[0].created_at).toLocaleString()
                : "Never"}
            </span>
          </div>
        </div>
      )}
    </div>
  );
}
