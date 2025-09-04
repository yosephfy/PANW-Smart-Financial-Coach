"use client";

import { useEffect, useState } from "react";
import { useUser } from "../../components/Providers";
import { Badge } from "../../components/Badge";
import React from "react";

const API = process.env.NEXT_PUBLIC_API_URL || "http://localhost:3000/backend";

type Plan = {
  target_date: string;
  months_left: number;
  current_surplus_monthly: number;
  required_monthly: number;
  gap: number;
  on_track: boolean;
  suggested_plan: {
    category: string;
    forecast_spend: number;
    suggested_cut: number;
    cut_pct: number;
    forecast_model?: string;
    max_cut_pct?: number;
  }[];
  total_potential?: number;
  feasible?: boolean;
  shortfall?: number;
};

type Goal = {
  id: string;
  name: string;
  target_amount: number;
  target_date: string;
  status: string;
  plan?: Plan;
  created_at?: string;
  achieved_at?: string;
};

type Contribution = {
  id: string;
  date: string;
  amount: number;
};

type GoalAnalytics = {
  total_goals: number;
  active_goals: number;
  achieved_goals: number;
  total_target_amount: number;
  total_progress: number;
  on_track_count: number;
  needs_adjustment_count: number;
  avg_months_left: number;
  total_monthly_required: number;
  total_monthly_surplus: number;
  feasible_goals: number;
};

const STATUS_COLORS = {
  active: "#3b82f6", // blue
  achieved: "#10b981", // emerald
  paused: "#f59e0b", // amber
  canceled: "#ef4444", // red
  off_track: "#f97316", // orange
};

const PRIORITY_COLORS = ["#10b981", "#3b82f6", "#f59e0b", "#ef4444", "#8b5cf6"];

function getGoalIcon(status: string) {
  switch (status) {
    case "achieved":
      return "🏆";
    case "active":
      return "🎯";
    case "paused":
      return "⏸️";
    case "canceled":
      return "❌";
    default:
      return "💰";
  }
}

function getStatusVariant(status: string) {
  switch (status) {
    case "achieved":
      return "success";
    case "active":
      return "info";
    case "paused":
      return "warning";
    case "canceled":
      return "danger";
    default:
      return "neutral";
  }
}

function formatCurrency(amount: number) {
  return new Intl.NumberFormat("en-US", {
    style: "currency",
    currency: "USD",
    minimumFractionDigits: 0,
    maximumFractionDigits: 0,
  }).format(amount);
}

function formatDate(dateString: string) {
  return new Date(dateString).toLocaleDateString("en-US", {
    year: "numeric",
    month: "short",
    day: "numeric",
  });
}

// MetricCard component for summary statistics
function MetricCard({
  title,
  value,
  subtitle,
  color = "blue",
  icon,
  trend,
}: {
  title: string;
  value: string | number;
  subtitle?: string;
  color?: string;
  icon?: string;
  trend?: "up" | "down" | "neutral";
}) {
  const colorClasses = {
    blue: "bg-blue-900/20 border-blue-500/30",
    green: "bg-emerald-900/20 border-emerald-500/30",
    yellow: "bg-yellow-900/20 border-yellow-500/30",
    red: "bg-red-900/20 border-red-500/30",
    purple: "bg-purple-900/20 border-purple-500/30",
  };

  const trendIcons = {
    up: "📈",
    down: "📉",
    neutral: "➡️",
  };

  return (
    <div
      className={`border rounded-lg p-4 ${
        colorClasses[color as keyof typeof colorClasses] || colorClasses.blue
      }`}
    >
      <div className="flex items-center justify-between mb-2">
        <div className="flex items-center gap-2">
          {icon && <span className="text-lg">{icon}</span>}
          <h3 className="text-sm font-medium text-slate-400">{title}</h3>
        </div>
        {trend && <span className="text-xs">{trendIcons[trend]}</span>}
      </div>
      <div className="text-2xl font-bold mb-1">{value}</div>
      {subtitle && <p className="text-xs text-slate-400">{subtitle}</p>}
    </div>
  );
}

// Progress bar component
function ProgressBar({
  progress,
  color = "#3b82f6",
  height = 8,
}: {
  progress: number;
  color?: string;
  height?: number;
}) {
  return (
    <div
      className={`w-full bg-slate-700 rounded-full`}
      style={{ height: `${height}px` }}
    >
      <div
        className="h-full rounded-full transition-all duration-300"
        style={{
          width: `${Math.min(Math.max(progress, 0), 100)}%`,
          backgroundColor: color,
        }}
      />
    </div>
  );
}

// Goal Card component
function GoalCard({
  goal,
  onUpdate,
  onContribute,
}: {
  goal: Goal;
  onUpdate: (goalId: string, updates: Partial<Goal>) => void;
  onContribute: (goalId: string, amount: number) => void;
}) {
  const [contributions, setContributions] = useState<Contribution[]>([]);
  const [showContributeModal, setShowContributeModal] = useState(false);
  const [contributionAmount, setContributionAmount] = useState(100);

  useEffect(() => {
    loadContributions();
  }, [goal.id]);

  const loadContributions = async () => {
    try {
      const res = await fetch(
        `${API}/goals/${encodeURIComponent(goal.id)}/contributions`
      );
      if (res.ok) {
        const data = await res.json();
        setContributions(Array.isArray(data) ? data : []);
      }
    } catch (error) {
      console.error("Failed to load contributions:", error);
    }
  };

  const totalContributed = contributions.reduce((sum, c) => sum + c.amount, 0);
  const progress = (totalContributed / goal.target_amount) * 100;
  const remaining = Math.max(goal.target_amount - totalContributed, 0);

  const handleContribute = async () => {
    try {
      await onContribute(goal.id, contributionAmount);
      setShowContributeModal(false);
      loadContributions();
    } catch (error) {
      console.error("Failed to contribute:", error);
    }
  };

  const statusActions = [
    {
      status: "active",
      label: "Activate",
      color: "bg-blue-600 hover:bg-blue-700",
    },
    {
      status: "paused",
      label: "Pause",
      color: "bg-yellow-600 hover:bg-yellow-700",
    },
    {
      status: "achieved",
      label: "Mark Complete",
      color: "bg-emerald-600 hover:bg-emerald-700",
    },
    {
      status: "canceled",
      label: "Cancel",
      color: "bg-red-600 hover:bg-red-700",
    },
  ].filter((action) => action.status !== goal.status);

  return (
    <div className="border border-slate-700 rounded-lg p-6 space-y-4">
      {/* Header */}
      <div className="flex items-start justify-between">
        <div className="flex items-center gap-3">
          <span className="text-2xl">{getGoalIcon(goal.status)}</span>
          <div>
            <h3 className="text-lg font-semibold text-white">{goal.name}</h3>
            <p className="text-sm text-slate-400">
              Target: {formatCurrency(goal.target_amount)} by{" "}
              {formatDate(goal.target_date)}
            </p>
          </div>
        </div>
        <div className="flex items-center gap-2">
          <Badge variant={getStatusVariant(goal.status)}>
            {goal.status || "active"}
          </Badge>
          {goal.plan && (
            <Badge variant={goal.plan.on_track ? "success" : "warning"}>
              {goal.plan.on_track ? "On Track" : "Needs Adjustment"}
            </Badge>
          )}
        </div>
      </div>

      {/* Progress Section */}
      <div className="space-y-3">
        <div className="flex items-center justify-between text-sm">
          <span className="text-slate-400">Progress</span>
          <span className="font-medium">
            {formatCurrency(totalContributed)} /{" "}
            {formatCurrency(goal.target_amount)} ({progress.toFixed(1)}%)
          </span>
        </div>
        <ProgressBar
          progress={progress}
          color={
            progress >= 100
              ? "#10b981"
              : progress >= 75
              ? "#3b82f6"
              : progress >= 50
              ? "#f59e0b"
              : "#ef4444"
          }
        />
        <div className="flex justify-between text-xs text-slate-500">
          <span>Contributed: {formatCurrency(totalContributed)}</span>
          <span>Remaining: {formatCurrency(remaining)}</span>
        </div>
      </div>

      {/* Plan Details */}
      {goal.plan && (
        <div className="grid grid-cols-2 md:grid-cols-4 gap-3">
          <div className="bg-slate-800/50 rounded-lg p-3">
            <div className="text-xs text-slate-400">Months Left</div>
            <div className="text-lg font-semibold">{goal.plan.months_left}</div>
          </div>
          <div className="bg-slate-800/50 rounded-lg p-3">
            <div className="text-xs text-slate-400">Required Monthly</div>
            <div className="text-lg font-semibold">
              {formatCurrency(goal.plan.required_monthly)}
            </div>
          </div>
          <div className="bg-slate-800/50 rounded-lg p-3">
            <div className="text-xs text-slate-400">Current Surplus</div>
            <div
              className={`text-lg font-semibold ${
                goal.plan.current_surplus_monthly >= 0
                  ? "text-emerald-400"
                  : "text-red-400"
              }`}
            >
              {formatCurrency(goal.plan.current_surplus_monthly)}
            </div>
          </div>
          <div className="bg-slate-800/50 rounded-lg p-3">
            <div className="text-xs text-slate-400">Funding Gap</div>
            <div
              className={`text-lg font-semibold ${
                goal.plan.gap <= 0 ? "text-emerald-400" : "text-red-400"
              }`}
            >
              {formatCurrency(goal.plan.gap)}
            </div>
          </div>
        </div>
      )}

      {/* Feasibility Warning */}
      {goal.plan && goal.plan.feasible === false && (
        <div className="bg-amber-900/20 border border-amber-500/30 rounded-lg p-3">
          <div className="flex items-center gap-2 mb-2">
            <span>⚠️</span>
            <span className="font-semibold text-amber-300">
              Plan may be unrealistic
            </span>
          </div>
          <p className="text-sm text-amber-200">
            Even with aggressive spending cuts, there's a shortfall of{" "}
            {formatCurrency(goal.plan.shortfall || 0)} per month. Consider
            extending the target date or increasing income.
          </p>
        </div>
      )}

      {/* Suggested Spending Cuts */}
      {goal.plan?.suggested_plan?.length ? (
        <div className="space-y-3">
          <h4 className="text-sm font-medium text-slate-300">
            💡 Suggested Spending Adjustments
          </h4>
          <div className="grid md:grid-cols-2 gap-3">
            {goal.plan.suggested_plan.map((sp) => (
              <div
                key={sp.category}
                className="bg-slate-800/30 rounded-lg p-3 border border-slate-600"
              >
                <div className="flex items-center justify-between mb-2">
                  <div className="font-medium capitalize">{sp.category}</div>
                  <Badge variant="warning">
                    -{(sp.cut_pct * 100).toFixed(0)}%
                  </Badge>
                </div>
                <div className="space-y-1 text-xs text-slate-400">
                  <div>Forecast: {formatCurrency(sp.forecast_spend)}</div>
                  <div>Suggested cut: {formatCurrency(sp.suggested_cut)}</div>
                  {sp.max_cut_pct && (
                    <div>
                      Max realistic: {(sp.max_cut_pct * 100).toFixed(0)}%
                    </div>
                  )}
                </div>
              </div>
            ))}
          </div>
        </div>
      ) : (
        goal.plan?.on_track && (
          <div className="bg-emerald-900/20 border border-emerald-500/30 rounded-lg p-3">
            <div className="flex items-center gap-2 text-emerald-300">
              <span>✅</span>
              <span className="font-medium">You're on track!</span>
            </div>
            <p className="text-sm text-emerald-200 mt-1">
              No spending adjustments needed. Keep up the great work!
            </p>
          </div>
        )
      )}

      {/* Action Buttons */}
      <div className="flex items-center gap-2 pt-2 border-t border-slate-700">
        <button
          onClick={() => setShowContributeModal(true)}
          disabled={goal.status === "achieved" || goal.status === "canceled"}
          className="bg-emerald-600 hover:bg-emerald-700 text-white px-4 py-2 rounded-lg text-sm font-medium disabled:opacity-50 disabled:cursor-not-allowed transition-colors"
        >
          💰 Contribute
        </button>

        {statusActions.map((action) => (
          <button
            key={action.status}
            onClick={() => onUpdate(goal.id, { status: action.status })}
            className={`${action.color} text-white px-3 py-2 rounded-lg text-xs font-medium transition-colors`}
          >
            {action.label}
          </button>
        ))}
      </div>

      {/* Milestones */}
      <Milestones goalId={goal.id} />

      {/* Contribute Modal */}
      {showContributeModal && (
        <div className="fixed inset-0 bg-black/50 flex items-center justify-center z-50">
          <div className="bg-slate-800 rounded-lg p-6 w-full max-w-md">
            <h3 className="text-lg font-semibold mb-4">Contribute to Goal</h3>
            <div className="space-y-4">
              <div>
                <label className="block text-sm font-medium text-slate-300 mb-2">
                  Contribution Amount
                </label>
                <input
                  type="number"
                  value={contributionAmount}
                  onChange={(e) =>
                    setContributionAmount(parseFloat(e.target.value) || 0)
                  }
                  className="w-full bg-slate-700 border border-slate-600 rounded-lg px-3 py-2 text-white"
                  min="0"
                  step="0.01"
                />
              </div>
              <div className="flex gap-3">
                <button
                  onClick={handleContribute}
                  className="flex-1 bg-emerald-600 hover:bg-emerald-700 text-white py-2 rounded-lg font-medium transition-colors"
                >
                  Contribute
                </button>
                <button
                  onClick={() => setShowContributeModal(false)}
                  className="flex-1 bg-slate-600 hover:bg-slate-700 text-white py-2 rounded-lg font-medium transition-colors"
                >
                  Cancel
                </button>
              </div>
            </div>
          </div>
        </div>
      )}
    </div>
  );
}

export default function GoalsPage() {
  const ctx = useUser();
  const [goals, setGoals] = useState<Goal[]>([]);
  const [analytics, setAnalytics] = useState<GoalAnalytics | null>(null);
  const [viewMode, setViewMode] = useState<"dashboard" | "list">("dashboard");
  const [busy, setBusy] = useState(false);
  const [showCreateModal, setShowCreateModal] = useState(false);

  // Form state for creating goals
  const [name, setName] = useState("Emergency Fund");
  const [amount, setAmount] = useState(5000);
  const [date, setDate] = useState("2025-12-31");

  // Use "user1" if no context user ID is available (consistent with other pages)
  const userId = ctx.userId || "user1";

  const load = async () => {
    setBusy(true);
    try {
      const res = await fetch(
        `${API}/users/${encodeURIComponent(userId)}/goals`
      );
      const json = await res.json();
      const goalsData = Array.isArray(json) ? json : [];
      setGoals(goalsData);

      // Calculate analytics
      const analytics = calculateAnalytics(goalsData);
      setAnalytics(analytics);
    } finally {
      setBusy(false);
    }
  };

  const calculateAnalytics = (goals: Goal[]): GoalAnalytics => {
    const total_goals = goals.length;
    const active_goals = goals.filter((g) => g.status === "active").length;
    const achieved_goals = goals.filter((g) => g.status === "achieved").length;
    const total_target_amount = goals.reduce(
      (sum, g) => sum + g.target_amount,
      0
    );
    const on_track_count = goals.filter((g) => g.plan?.on_track).length;
    const needs_adjustment_count = goals.filter(
      (g) => g.plan && !g.plan.on_track
    ).length;
    const feasible_goals = goals.filter((g) => g.plan?.feasible).length;

    const activeGoals = goals.filter((g) => g.status === "active" && g.plan);
    const avg_months_left =
      activeGoals.length > 0
        ? activeGoals.reduce((sum, g) => sum + (g.plan?.months_left || 0), 0) /
          activeGoals.length
        : 0;
    const total_monthly_required = activeGoals.reduce(
      (sum, g) => sum + (g.plan?.required_monthly || 0),
      0
    );
    const total_monthly_surplus = activeGoals.reduce(
      (sum, g) => sum + (g.plan?.current_surplus_monthly || 0),
      0
    );

    return {
      total_goals,
      active_goals,
      achieved_goals,
      total_target_amount,
      total_progress: 0, // Would need to calculate from contributions
      on_track_count,
      needs_adjustment_count,
      avg_months_left,
      total_monthly_required,
      total_monthly_surplus,
      feasible_goals,
    };
  };

  const createGoal = async (e: React.FormEvent) => {
    e.preventDefault();
    setBusy(true);
    try {
      const res = await fetch(`${API}/goals`, {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({
          user_id: userId,
          name,
          target_amount: amount,
          target_date: date,
        }),
      });

      if (!res.ok) {
        const j = await res.json().catch(() => null);
        throw new Error(j?.detail || "Failed to create goal");
      }

      ctx.showToast("Goal created successfully!", "success");
      setShowCreateModal(false);
      await load();
    } catch (error: any) {
      ctx.showToast(error.message || "Failed to create goal", "error");
    } finally {
      setBusy(false);
    }
  };

  const updateGoal = async (goalId: string, updates: any) => {
    try {
      await fetch(`${API}/goals/${encodeURIComponent(goalId)}`, {
        method: "PATCH",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify(updates),
      });
      await load();
      ctx.showToast("Goal updated successfully", "success");
    } catch (error: any) {
      ctx.showToast(error.message || "Failed to update goal", "error");
    }
  };

  const contributeToGoal = async (goalId: string, amount: number) => {
    try {
      await fetch(`${API}/goals/${encodeURIComponent(goalId)}/contributions`, {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({ amount }),
      });
      await load();
      ctx.showToast(
        `Contributed ${formatCurrency(amount)} successfully!`,
        "success"
      );
    } catch (error: any) {
      ctx.showToast(error.message || "Failed to contribute", "error");
    }
  };

  const fundWithSTS = async () => {
    try {
      await fetch(`${API}/goals/fund/auto`, {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({ user_id: userId }),
      });
      await load();
      ctx.showToast("Auto-funded goals with safe-to-spend amount", "success");
    } catch (error: any) {
      ctx.showToast(error.message || "Failed to auto-fund goals", "error");
    }
  };

  useEffect(() => {
    if (userId) load();
  }, [userId]);

  return (
    <div className="space-y-6">
      {/* Header */}
      <div className="space-y-4">
        <div className="flex items-center justify-between">
          <div>
            <h1 className="text-3xl font-bold text-white">Financial Goals</h1>
            <p className="text-slate-400 mt-1">
              Plan, track, and achieve your financial objectives
            </p>
          </div>
          <div className="flex items-center gap-3">
            {/* View Toggle */}
            <div className="flex rounded-lg border border-slate-600 bg-slate-800 overflow-hidden">
              <button
                onClick={() => setViewMode("dashboard")}
                className={`px-3 py-2 text-sm font-medium transition-all duration-200 ${
                  viewMode === "dashboard"
                    ? "bg-blue-600 text-white shadow-sm"
                    : "text-slate-300 hover:text-white hover:bg-slate-700"
                }`}
              >
                📊 Dashboard
              </button>
              <button
                onClick={() => setViewMode("list")}
                className={`px-3 py-2 text-sm font-medium transition-all duration-200 ${
                  viewMode === "list"
                    ? "bg-blue-600 text-white shadow-sm"
                    : "text-slate-300 hover:text-white hover:bg-slate-700"
                }`}
              >
                📋 List
              </button>
            </div>
            {/* Refresh Button */}
            <button
              onClick={load}
              disabled={busy}
              className="p-2 rounded-lg bg-slate-700 hover:bg-slate-600 text-slate-300 hover:text-white disabled:opacity-50 transition-all duration-200"
              title="Refresh goals"
            >
              {busy ? "🔄" : "↻"}
            </button>
          </div>
        </div>

        {/* Action Buttons */}
        <div className="flex items-center gap-3 flex-wrap">
          <button
            onClick={() => setShowCreateModal(true)}
            className="flex items-center gap-2 bg-emerald-600 hover:bg-emerald-700 text-white px-4 py-2 rounded-lg font-medium transition-colors shadow-sm"
          >
            <span>🎯</span>
            Create Goal
          </button>
          <button
            onClick={fundWithSTS}
            disabled={busy}
            className="flex items-center gap-2 bg-blue-600 hover:bg-blue-700 text-white px-4 py-2 rounded-lg font-medium disabled:opacity-50 transition-colors shadow-sm"
          >
            <span>💰</span>
            Auto-Fund
          </button>
          {analytics && (
            <div className="flex items-center gap-4 ml-auto text-sm text-slate-400">
              <span>{analytics.total_goals} goals</span>
              <span>•</span>
              <span>{analytics.active_goals} active</span>
              <span>•</span>
              <span>
                {formatCurrency(analytics.total_target_amount)} target
              </span>
            </div>
          )}
        </div>
      </div>

      {analytics && viewMode === "dashboard" && (
        <>
          {/* Summary Cards */}
          <div className="grid grid-cols-2 md:grid-cols-4 gap-4">
            <MetricCard
              title="Total Goals"
              value={analytics.total_goals}
              subtitle="All time goals created"
              color="blue"
              icon="🎯"
            />
            <MetricCard
              title="Active Goals"
              value={analytics.active_goals}
              subtitle="Currently working towards"
              color="green"
              icon="⚡"
            />
            <MetricCard
              title="Achieved"
              value={analytics.achieved_goals}
              subtitle="Successfully completed"
              color="purple"
              icon="🏆"
            />
            <MetricCard
              title="Total Target"
              value={formatCurrency(analytics.total_target_amount)}
              subtitle="Combined goal amounts"
              color="yellow"
              icon="💰"
            />
          </div>

          {/* Planning Metrics */}
          <div className="grid grid-cols-1 md:grid-cols-3 gap-4">
            <MetricCard
              title="On Track"
              value={`${analytics.on_track_count} of ${analytics.active_goals}`}
              subtitle="Goals progressing well"
              color="green"
              icon="✅"
            />
            <MetricCard
              title="Average Timeline"
              value={`${analytics.avg_months_left.toFixed(1)} months`}
              subtitle="Remaining time to goals"
              color="blue"
              icon="📅"
            />
            <MetricCard
              title="Monthly Required"
              value={formatCurrency(analytics.total_monthly_required)}
              subtitle="Total needed per month"
              color="red"
              icon="📈"
            />
          </div>
        </>
      )}

      {/* Goals List */}
      <div className="space-y-4">
        {goals.length > 0 ? (
          goals.map((goal) => (
            <GoalCard
              key={goal.id}
              goal={goal}
              onUpdate={updateGoal}
              onContribute={contributeToGoal}
            />
          ))
        ) : (
          <div className="text-center py-12 border border-slate-700 rounded-lg">
            <div className="text-4xl mb-4">🎯</div>
            <h3 className="text-lg font-semibold text-slate-300 mb-2">
              No goals yet
            </h3>
            <p className="text-slate-400 mb-4">
              Create your first financial goal to get started on your journey
            </p>
            <button
              onClick={() => setShowCreateModal(true)}
              className="bg-emerald-600 hover:bg-emerald-700 text-white px-6 py-2 rounded-lg font-medium transition-colors"
            >
              Create Your First Goal
            </button>
          </div>
        )}
      </div>

      {/* Create Goal Modal */}
      {showCreateModal && (
        <div className="fixed inset-0 bg-black/50 flex items-center justify-center z-50">
          <div className="bg-slate-800 rounded-lg p-6 w-full max-w-lg">
            <h3 className="text-lg font-semibold mb-4">Create New Goal</h3>
            <form onSubmit={createGoal} className="space-y-4">
              <div>
                <label className="block text-sm font-medium text-slate-300 mb-2">
                  Goal Name
                </label>
                <input
                  type="text"
                  value={name}
                  onChange={(e) => setName(e.target.value)}
                  className="w-full bg-slate-700 border border-slate-600 rounded-lg px-3 py-2 text-white"
                  placeholder="e.g., Emergency Fund, Vacation, Down Payment"
                  required
                />
              </div>
              <div className="grid grid-cols-2 gap-4">
                <div>
                  <label className="block text-sm font-medium text-slate-300 mb-2">
                    Target Amount
                  </label>
                  <input
                    type="number"
                    value={amount}
                    onChange={(e) => setAmount(parseFloat(e.target.value) || 0)}
                    className="w-full bg-slate-700 border border-slate-600 rounded-lg px-3 py-2 text-white"
                    min="0"
                    step="0.01"
                    required
                  />
                </div>
                <div>
                  <label className="block text-sm font-medium text-slate-300 mb-2">
                    Target Date
                  </label>
                  <input
                    type="date"
                    value={date}
                    onChange={(e) => setDate(e.target.value)}
                    className="w-full bg-slate-700 border border-slate-600 rounded-lg px-3 py-2 text-white"
                    required
                  />
                </div>
              </div>
              <div className="flex gap-3 pt-4">
                <button
                  type="submit"
                  disabled={busy}
                  className="flex-1 bg-emerald-600 hover:bg-emerald-700 text-white py-2 rounded-lg font-medium disabled:opacity-50 transition-colors"
                >
                  {busy ? "Creating..." : "Create Goal"}
                </button>
                <button
                  type="button"
                  onClick={() => setShowCreateModal(false)}
                  className="flex-1 bg-slate-600 hover:bg-slate-700 text-white py-2 rounded-lg font-medium transition-colors"
                >
                  Cancel
                </button>
              </div>
            </form>
          </div>
        </div>
      )}

      {/* Footer Stats */}
      {analytics && (
        <div className="border-t border-slate-700 pt-4">
          <div className="flex items-center justify-between text-sm text-slate-400">
            <span>
              Showing {goals.length} goals • {analytics.active_goals} active •{" "}
              {analytics.achieved_goals} achieved
            </span>
            <span>
              Total target amount:{" "}
              {formatCurrency(analytics.total_target_amount)}
            </span>
          </div>
        </div>
      )}
    </div>
  );
}

function Milestones({ goalId }: { goalId: string }) {
  const [rows, setRows] = useState<
    {
      id: string;
      name: string;
      target_amount: number;
      hit_at?: string | null;
    }[]
  >([]);

  useEffect(() => {
    (async () => {
      try {
        const r = await fetch(
          `${API}/goals/${encodeURIComponent(goalId)}/milestones`
        );
        const j = await r.json();
        if (Array.isArray(j)) setRows(j);
      } catch {}
    })();
  }, [goalId]);

  if (!rows.length) return null;

  return (
    <div className="space-y-2">
      <div className="text-sm font-medium text-slate-300">🎯 Milestones</div>
      <div className="flex gap-2 flex-wrap">
        {rows.map((m) => (
          <div
            key={m.id}
            className={`px-3 py-1 rounded-full border text-xs font-medium ${
              m.hit_at
                ? "border-emerald-600 text-emerald-300 bg-emerald-900/20"
                : "border-slate-600 text-slate-300 bg-slate-800/50"
            }`}
          >
            {m.name || formatCurrency(m.target_amount)} {m.hit_at ? "✓" : ""}
          </div>
        ))}
      </div>
    </div>
  );
}
