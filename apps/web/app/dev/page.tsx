"use client";

import { useEffect, useState } from "react";
import { useUser } from "../../components/Providers";
import React from "react";

const API = process.env.NEXT_PUBLIC_API_URL || "http://localhost:3000/backend";

type APIEndpoint = {
  category: string;
  name: string;
  method: string;
  url: string;
  description: string;
  payload?: any;
  sampleResponse?: string;
};

type TestResult = {
  endpoint: string;
  success: boolean;
  response?: any;
  error?: string;
  duration?: number;
};

const API_ENDPOINTS: APIEndpoint[] = [
  // Core API
  {
    category: "Core",
    name: "Health Check",
    method: "GET",
    url: "/health",
    description: "API health status",
  },
  {
    category: "Core",
    name: "Root Info",
    method: "GET",
    url: "/",
    description: "API information and available endpoints",
  },

  // AI & ML Endpoints
  {
    category: "AI & ML",
    name: "Train Categorizer",
    method: "POST",
    url: "/ai/categorizer/train",
    description: "Train AI categorizer model for specific user",
    payload: { user_id: "user1", min_per_class: 5 },
  },
  {
    category: "AI & ML",
    name: "Predict Category",
    method: "POST",
    url: "/ai/categorizer/predict",
    description: "Predict transaction category using AI",
    payload: {
      user_id: "user1",
      merchant: "Starbucks",
      description: "Coffee purchase",
      top_k: 3,
    },
  },
  {
    category: "AI & ML",
    name: "Train Global Categorizer",
    method: "POST",
    url: "/ai/categorizer/train/global",
    description: "Train global AI model from all training data",
    payload: { min_per_class: 5 },
  },
  {
    category: "AI & ML",
    name: "Anomaly Detection",
    method: "POST",
    url: "/anomaly/iforest/detect",
    description: "Detect transaction anomalies using Isolation Forest",
    payload: { user_id: "user1", contamination: 0.08 },
  },
  {
    category: "AI & ML",
    name: "Train Recurring Model",
    method: "POST",
    url: "/ai/is_recurring/train",
    description: "Train recurring transaction detection model",
    payload: { user_id: "user1" },
  },
  {
    category: "AI & ML",
    name: "Predict Recurring",
    method: "POST",
    url: "/ai/is_recurring/predict",
    description: "Predict if transaction is recurring",
    payload: {
      user_id: "user1",
      merchant: "Netflix",
      description: "Monthly subscription",
      amount: 15.99,
      date: "2025-01-15",
    },
  },

  // Categorization
  {
    category: "Categorization",
    name: "Explain Categorization",
    method: "POST",
    url: "/categorization/explain",
    description: "Explain how a transaction was categorized",
    payload: {
      merchant: "Amazon",
      description: "Online purchase",
      mcc: "5411",
    },
  },

  // Forecasting
  {
    category: "Forecasting",
    name: "Category Forecast",
    method: "POST",
    url: "/forecast/categories",
    description: "Forecast spending by category for next month",
    payload: { user_id: "user1", months_history: 6, top_k: 8 },
  },

  // Insights
  {
    category: "Insights",
    name: "Generate Insights",
    method: "POST",
    url: "/insights/generate",
    description: "Generate AI-powered financial insights",
    payload: { user_id: "user1" },
  },
  {
    category: "Insights",
    name: "Get User Insights",
    method: "GET",
    url: "/users/user1/insights",
    description: "Get all insights for a user",
  },
  {
    category: "Insights",
    name: "Rewrite Insight",
    method: "POST",
    url: "/insights/rewrite",
    description: "Rewrite insight using LLM",
    payload: {
      title: "High Spending Alert",
      body: "You spent more than usual",
      data_json: "{}",
      tone: "friendly",
    },
  },

  // Goals
  {
    category: "Goals",
    name: "Create Goal",
    method: "POST",
    url: "/goals",
    description: "Create a new financial goal",
    payload: {
      user_id: "user1",
      name: "Emergency Fund",
      target_amount: 5000,
      target_date: "2025-12-31",
    },
  },
  {
    category: "Goals",
    name: "Get User Goals",
    method: "GET",
    url: "/users/user1/goals",
    description: "Get all goals for a user",
  },
  {
    category: "Goals",
    name: "Auto-Fund Goals",
    method: "POST",
    url: "/goals/fund/auto",
    description: "Automatically fund goals with safe-to-spend amount",
    payload: { user_id: "user1" },
  },

  // Subscriptions
  {
    category: "Subscriptions",
    name: "Detect Subscriptions",
    method: "POST",
    url: "/subscriptions/detect",
    description: "Detect recurring subscriptions from transactions",
    payload: { user_id: "user1" },
  },
  {
    category: "Subscriptions",
    name: "Get User Subscriptions",
    method: "GET",
    url: "/users/user1/subscriptions",
    description: "Get all subscriptions for a user",
  },
  {
    category: "Subscriptions",
    name: "Subscription Analytics",
    method: "GET",
    url: "/subscriptions/analytics/user1",
    description: "Get comprehensive subscription analytics",
  },

  // Cash Flow
  {
    category: "Cash Flow",
    name: "Safe to Spend",
    method: "POST",
    url: "/cash/safe_to_spend",
    description: "Calculate safe-to-spend amount",
    payload: { user_id: "user1", days: 14, buffer: 100.0 },
  },
  {
    category: "Cash Flow",
    name: "Safe to Spend by Account Type",
    method: "POST",
    url: "/cash/safe_to_spend_by_account_type",
    description: "Account type aware safe-to-spend calculation",
    payload: { user_id: "user1", days: 14 },
  },
  {
    category: "Cash Flow",
    name: "Low Balance Check",
    method: "POST",
    url: "/cash/low_balance/check",
    description: "Check for accounts with low balances",
    payload: { user_id: "user1", lookback_days: 30 },
  },
  {
    category: "Cash Flow",
    name: "Upcoming Bills",
    method: "POST",
    url: "/cash/upcoming_bills",
    description: "Get upcoming recurring bills",
    payload: { user_id: "user1", days: 14 },
  },

  // Transactions
  {
    category: "Transactions",
    name: "Get User Transactions",
    method: "GET",
    url: "/users/user1/transactions?limit=10",
    description: "Get transactions for a user",
  },
  {
    category: "Transactions",
    name: "Transaction Analytics",
    method: "GET",
    url: "/users/user1/transactions/analytics",
    description: "Get comprehensive transaction analytics",
  },

  // Budgets
  {
    category: "Budgets",
    name: "Get User Budgets",
    method: "GET",
    url: "/users/user1/budgets",
    description: "Get budget information for a user",
  },

  // Data Ingestion
  {
    category: "Data Ingestion",
    name: "CSV Upload",
    method: "POST",
    url: "/ingest/csv",
    description: "Upload and parse CSV transactions (requires file upload)",
  },
  {
    category: "Data Ingestion",
    name: "CSV with Insights",
    method: "POST",
    url: "/ingest/csv/insights",
    description: "Upload CSV and generate insights (requires file upload)",
  },
];

export default function DevPage() {
  const ctx = useUser();
  const [selectedCategory, setSelectedCategory] = useState<string>("All");
  const [testResults, setTestResults] = useState<TestResult[]>([]);
  const [isRunning, setIsRunning] = useState(false);
  const [selectedEndpoint, setSelectedEndpoint] = useState<APIEndpoint | null>(
    null
  );
  const [customPayload, setCustomPayload] = useState("");
  const [response, setResponse] = useState("");

  const userId = ctx.userId || "user1";

  const categories = [
    "All",
    ...Array.from(new Set(API_ENDPOINTS.map((e) => e.category))),
  ];
  const filteredEndpoints =
    selectedCategory === "All"
      ? API_ENDPOINTS
      : API_ENDPOINTS.filter((e) => e.category === selectedCategory);

  const runTest = async (endpoint: APIEndpoint): Promise<TestResult> => {
    const startTime = Date.now();
    try {
      // Replace user1 with actual userId in URLs and payloads
      const url = endpoint.url.replace(/user1/g, userId);
      const payload = endpoint.payload
        ? JSON.parse(JSON.stringify(endpoint.payload).replace(/user1/g, userId))
        : undefined;

      const options: RequestInit = {
        method: endpoint.method,
        headers: { "Content-Type": "application/json" },
      };

      if (payload && endpoint.method !== "GET") {
        options.body = JSON.stringify(payload);
      }

      const res = await fetch(`${API}${url}`, options);
      const responseData = await res.json().catch(() => res.text());
      const duration = Date.now() - startTime;

      return {
        endpoint: endpoint.name,
        success: res.ok,
        response: responseData,
        duration,
        error: res.ok ? undefined : `${res.status}: ${res.statusText}`,
      };
    } catch (error: any) {
      return {
        endpoint: endpoint.name,
        success: false,
        error: error.message,
        duration: Date.now() - startTime,
      };
    }
  };

  const runAllTests = async () => {
    setIsRunning(true);
    setTestResults([]);

    const results: TestResult[] = [];
    for (const endpoint of filteredEndpoints) {
      // Skip file upload endpoints in bulk tests
      if (endpoint.url.includes("/ingest/csv")) continue;

      const result = await runTest(endpoint);
      results.push(result);
      setTestResults([...results]);
    }
    setIsRunning(false);
  };

  const runSingleTest = async (endpoint: APIEndpoint) => {
    const result = await runTest(endpoint);
    setTestResults((prev) => {
      const filtered = prev.filter((r) => r.endpoint !== endpoint.name);
      return [...filtered, result];
    });
  };

  const testEndpoint = async () => {
    if (!selectedEndpoint) return;

    setResponse("Running...");
    try {
      let payload;
      if (customPayload.trim()) {
        payload = JSON.parse(customPayload);
      } else if (selectedEndpoint.payload) {
        payload = JSON.parse(
          JSON.stringify(selectedEndpoint.payload).replace(/user1/g, userId)
        );
      }

      const url = selectedEndpoint.url.replace(/user1/g, userId);
      const options: RequestInit = {
        method: selectedEndpoint.method,
        headers: { "Content-Type": "application/json" },
      };

      if (payload && selectedEndpoint.method !== "GET") {
        options.body = JSON.stringify(payload);
      }

      const res = await fetch(`${API}${url}`, options);
      const responseData = await res.json().catch(() => res.text());

      setResponse(
        JSON.stringify(
          {
            status: res.status,
            statusText: res.statusText,
            success: res.ok,
            data: responseData,
          },
          null,
          2
        )
      );
    } catch (error: any) {
      setResponse(JSON.stringify({ error: error.message }, null, 2));
    }
  };

  const getResultForEndpoint = (endpointName: string) => {
    return testResults.find((r) => r.endpoint === endpointName);
  };

  return (
    <div className="space-y-6">
      {/* Header */}
      <div>
        <h1 className="text-3xl font-bold text-white flex items-center gap-3">
          <span>🛠️</span> Developer Mode
        </h1>
        <p className="text-slate-400 mt-1">
          Test and explore all API endpoints, AI models, and system capabilities
        </p>
      </div>

      {/* Quick Stats */}
      <div className="grid grid-cols-2 md:grid-cols-4 gap-4">
        <div className="bg-slate-800 rounded-lg p-4">
          <div className="text-2xl font-bold text-blue-400">
            {API_ENDPOINTS.length}
          </div>
          <div className="text-sm text-slate-400">Total Endpoints</div>
        </div>
        <div className="bg-slate-800 rounded-lg p-4">
          <div className="text-2xl font-bold text-emerald-400">
            {categories.length - 1}
          </div>
          <div className="text-sm text-slate-400">Categories</div>
        </div>
        <div className="bg-slate-800 rounded-lg p-4">
          <div className="text-2xl font-bold text-purple-400">
            {testResults.filter((r) => r.success).length}
          </div>
          <div className="text-sm text-slate-400">Passed Tests</div>
        </div>
        <div className="bg-slate-800 rounded-lg p-4">
          <div className="text-2xl font-bold text-red-400">
            {testResults.filter((r) => !r.success).length}
          </div>
          <div className="text-sm text-slate-400">Failed Tests</div>
        </div>
      </div>

      {/* Controls */}
      <div className="flex items-center gap-3 flex-wrap">
        <select
          value={selectedCategory}
          onChange={(e) => setSelectedCategory(e.target.value)}
          className="bg-slate-700 border border-slate-600 rounded-lg px-3 py-2 text-white"
        >
          {categories.map((cat) => (
            <option key={cat} value={cat}>
              {cat}
            </option>
          ))}
        </select>

        <button
          onClick={runAllTests}
          disabled={isRunning}
          className="flex items-center gap-2 bg-blue-600 hover:bg-blue-700 text-white px-4 py-2 rounded-lg font-medium disabled:opacity-50"
        >
          {isRunning ? "🔄 Testing..." : "🚀 Run All Tests"}
        </button>

        <button
          onClick={() => setTestResults([])}
          className="bg-slate-600 hover:bg-slate-700 text-white px-4 py-2 rounded-lg font-medium"
        >
          🗑️ Clear Results
        </button>

        <div className="text-sm text-slate-400 ml-auto">
          API: {API} | User:{" "}
          <span className="text-white font-medium">{userId}</span>
        </div>
      </div>

      {/* Main Content Grid */}
      <div className="grid lg:grid-cols-2 gap-6">
        {/* Endpoints List */}
        <div className="space-y-4">
          <h2 className="text-xl font-semibold text-white">API Endpoints</h2>
          <div className="space-y-2 max-h-96 overflow-y-auto">
            {filteredEndpoints.map((endpoint, idx) => {
              const result = getResultForEndpoint(endpoint.name);
              return (
                <div
                  key={idx}
                  className={`border rounded-lg p-3 cursor-pointer transition-colors ${
                    selectedEndpoint?.name === endpoint.name
                      ? "border-blue-500 bg-blue-500/10"
                      : "border-slate-700 hover:border-slate-600"
                  }`}
                  onClick={() => {
                    setSelectedEndpoint(endpoint);
                    setCustomPayload(
                      endpoint.payload
                        ? JSON.stringify(endpoint.payload, null, 2)
                        : ""
                    );
                  }}
                >
                  <div className="flex items-center justify-between">
                    <div className="flex items-center gap-3">
                      <span
                        className={`px-2 py-1 text-xs rounded font-medium ${
                          endpoint.method === "GET"
                            ? "bg-green-600"
                            : endpoint.method === "POST"
                            ? "bg-blue-600"
                            : endpoint.method === "PATCH"
                            ? "bg-yellow-600"
                            : "bg-red-600"
                        }`}
                      >
                        {endpoint.method}
                      </span>
                      <div>
                        <div className="font-medium text-white">
                          {endpoint.name}
                        </div>
                        <div className="text-xs text-slate-400">
                          {endpoint.description}
                        </div>
                      </div>
                    </div>
                    <div className="flex items-center gap-2">
                      {result && (
                        <div className="flex items-center gap-1">
                          <span
                            className={
                              result.success
                                ? "text-emerald-400"
                                : "text-red-400"
                            }
                          >
                            {result.success ? "✓" : "✗"}
                          </span>
                          {result.duration && (
                            <span className="text-xs text-slate-400">
                              {result.duration}ms
                            </span>
                          )}
                        </div>
                      )}
                      <button
                        onClick={(e) => {
                          e.stopPropagation();
                          runSingleTest(endpoint);
                        }}
                        className="text-blue-400 hover:text-blue-300 text-sm"
                      >
                        Test
                      </button>
                    </div>
                  </div>
                </div>
              );
            })}
          </div>
        </div>

        {/* Test Interface */}
        <div className="space-y-4">
          <h2 className="text-xl font-semibold text-white">Test Interface</h2>

          {selectedEndpoint ? (
            <div className="space-y-4">
              <div className="bg-slate-800 rounded-lg p-4">
                <div className="flex items-center gap-3 mb-2">
                  <span
                    className={`px-2 py-1 text-xs rounded font-medium ${
                      selectedEndpoint.method === "GET"
                        ? "bg-green-600"
                        : selectedEndpoint.method === "POST"
                        ? "bg-blue-600"
                        : "bg-yellow-600"
                    }`}
                  >
                    {selectedEndpoint.method}
                  </span>
                  <code className="text-blue-400">{selectedEndpoint.url}</code>
                </div>
                <p className="text-sm text-slate-300">
                  {selectedEndpoint.description}
                </p>
              </div>

              {selectedEndpoint.payload && (
                <div>
                  <label className="block text-sm font-medium text-slate-300 mb-2">
                    Request Payload (JSON)
                  </label>
                  <textarea
                    value={customPayload}
                    onChange={(e) => setCustomPayload(e.target.value)}
                    className="w-full h-32 bg-slate-700 border border-slate-600 rounded-lg px-3 py-2 text-white font-mono text-sm"
                    placeholder="Enter JSON payload..."
                  />
                </div>
              )}

              <button
                onClick={testEndpoint}
                className="w-full bg-emerald-600 hover:bg-emerald-700 text-white py-2 rounded-lg font-medium"
              >
                🧪 Test Endpoint
              </button>

              {response && (
                <div>
                  <label className="block text-sm font-medium text-slate-300 mb-2">
                    Response
                  </label>
                  <pre className="w-full h-64 bg-slate-900 border border-slate-600 rounded-lg p-3 text-green-400 font-mono text-xs overflow-auto">
                    {response}
                  </pre>
                </div>
              )}
            </div>
          ) : (
            <div className="bg-slate-800 rounded-lg p-8 text-center text-slate-400">
              <div className="text-4xl mb-2">🎯</div>
              <p>Select an endpoint from the list to test it</p>
            </div>
          )}
        </div>
      </div>

      {/* Recent Test Results */}
      {testResults.length > 0 && (
        <div className="space-y-4">
          <h2 className="text-xl font-semibold text-white">Test Results</h2>
          <div className="grid gap-2 max-h-64 overflow-y-auto">
            {testResults.map((result, idx) => (
              <div
                key={idx}
                className={`flex items-center justify-between p-3 rounded border ${
                  result.success
                    ? "border-emerald-700 bg-emerald-900/20"
                    : "border-red-700 bg-red-900/20"
                }`}
              >
                <div className="flex items-center gap-3">
                  <span
                    className={
                      result.success ? "text-emerald-400" : "text-red-400"
                    }
                  >
                    {result.success ? "✓" : "✗"}
                  </span>
                  <span className="font-medium">{result.endpoint}</span>
                  {result.error && (
                    <span className="text-red-400 text-sm">
                      ({result.error})
                    </span>
                  )}
                </div>
                <div className="text-xs text-slate-400">
                  {result.duration}ms
                </div>
              </div>
            ))}
          </div>
        </div>
      )}

      {/* API Documentation */}
      <div className="border-t border-slate-700 pt-6">
        <h2 className="text-xl font-semibold text-white mb-4">
          Quick Reference
        </h2>
        <div className="grid md:grid-cols-2 gap-6">
          <div>
            <h3 className="font-medium text-slate-300 mb-2">
              🤖 AI & ML Features
            </h3>
            <ul className="text-sm text-slate-400 space-y-1">
              <li>• Transaction categorization with provenance</li>
              <li>• Anomaly detection using Isolation Forest</li>
              <li>• Recurring subscription detection</li>
              <li>• Spending forecasting by category</li>
              <li>• LLM-powered insight rewriting</li>
            </ul>
          </div>
          <div>
            <h3 className="font-medium text-slate-300 mb-2">
              💰 Financial Features
            </h3>
            <ul className="text-sm text-slate-400 space-y-1">
              <li>• Safe-to-spend calculations</li>
              <li>• Goal setting and auto-funding</li>
              <li>• Subscription analytics and tracking</li>
              <li>• Budget monitoring and insights</li>
              <li>• Cash flow analysis</li>
            </ul>
          </div>
        </div>
      </div>
    </div>
  );
}
