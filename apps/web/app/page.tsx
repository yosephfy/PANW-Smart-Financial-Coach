"use client";

import { useEffect, useState } from "react";
import React from "react";
import { useUser } from "../components/Providers";
import Link from "next/link";

const API = process.env.NEXT_PUBLIC_API_URL || "http://localhost:3000/backend";

type ForecastItem = { category: string; forecast_next_month: number };

type AccountInfo = {
  id: string;
  name: string;
  balance: number;
  threshold: number;
  is_low: boolean;
  type: string;
};

type AccountTypeData = {
  accounts: AccountInfo[];
  total: number;
  count: number;
};

type SafeToSpendData = {
  user_id: string;
  days: number;
  checking: AccountTypeData & {
    safe_to_spend: number;
    buffer: number;
  };
  credit: AccountTypeData & {
    available_credit: number;
    buffer: number;
  };
  combined: {
    net_worth: number;
    safe_to_spend: number;
    avg_daily_spend: number;
    per_day_recurring: number;
    expected_spend: number;
    expected_recurring: number;
  };
  next_pay_date: string | null;
  days_to_pay: number;
};

function sparklineSvg(
  values: number[],
  width = 120,
  height = 36,
  stroke = "#34d399"
) {
  if (!values || values.length === 0) return null;
  const min = Math.min(...values);
  const max = Math.max(...values);
  const range = max - min || 1;
  const step = width / Math.max(1, values.length - 1);
  const points = values
    .map(
      (v, i) =>
        `${(i * step).toFixed(2)},${(
          height -
          ((v - min) / range) * height
        ).toFixed(2)}`
    )
    .join(" ");
  return (
    <svg
      width={width}
      height={height}
      viewBox={`0 0 ${width} ${height}`}
      preserveAspectRatio="none"
    >
      <polyline
        fill="none"
        stroke={stroke}
        strokeWidth={2}
        points={points}
        strokeLinecap="round"
        strokeLinejoin="round"
      />
    </svg>
  );
}

export default function Home() {
  const { userId } = useUser();
  const [busy, setBusy] = useState(false);
  const [items, setItems] = useState<ForecastItem[]>([]);
  const [historyMap, setHistoryMap] = useState<Record<string, number[]>>({});
  const [accountData, setAccountData] = useState<SafeToSpendData | null>(null);

  const load = async () => {
    setBusy(true);
    try {
      // Account type-aware safe-to-spend
      if (userId) {
        try {
          const r = await fetch(`${API}/cash/safe_to_spend_by_account_type`, {
            method: "POST",
            headers: { "Content-Type": "application/json" },
            body: JSON.stringify({ user_id: userId, days: 14 }),
          });

          if (r.ok) {
            const accountJson = await r.json();
            console.log("Account data received from API:", accountJson);
            console.log("API response structure check:", {
              hasCombined: !!accountJson?.combined,
              hasChecking: !!accountJson?.checking,
              hasCredit: !!accountJson?.credit,
              checkingAccounts: accountJson?.checking?.accounts?.length || 0,
              creditAccounts: accountJson?.credit?.accounts?.length || 0,
              checkingTotal: accountJson?.checking?.total,
              creditTotal: accountJson?.credit?.total,
            });
            if (accountJson && accountJson.combined) {
              setAccountData(accountJson);
            } else {
              console.warn("Invalid account data structure:", accountJson);
              setAccountData(null);
            }
          } else {
            console.error("API error:", r.status, r.statusText);
            // Fallback to old API if new one fails
            const fallbackR = await fetch(`${API}/cash/safe_to_spend`, {
              method: "POST",
              headers: { "Content-Type": "application/json" },
              body: JSON.stringify({ user_id: userId, days: 14, buffer: 100 }),
            });

            if (fallbackR.ok) {
              const fallbackData = await fallbackR.json();
              console.log("Fallback data:", fallbackData);

              // Try to get actual account data from transactions endpoint
              try {
                const txnR = await fetch(
                  `${API}/users/${userId}/transactions?limit=50`
                );
                if (txnR.ok) {
                  const txnData = await txnR.json();
                  console.log("Transaction data sample:", txnData?.slice(0, 3));

                  // Group transactions by account to get real account balances
                  const accountBalances: Record<
                    string,
                    { balance: number; name: string; latestDate: string }
                  > = {};

                  for (const txn of txnData) {
                    const accountId = txn.account_id || "unknown";
                    console.log(
                      `Transaction - accountId: ${accountId}, balance: ${txn.balance}, amount: ${txn.amount}, merchant: ${txn.merchant}, date: ${txn.date}`
                    );

                    if (txn.balance !== null && txn.balance !== undefined) {
                      // Only keep the latest balance per account (assuming sorted by date desc)
                      if (
                        !accountBalances[accountId] ||
                        txn.date > accountBalances[accountId].latestDate
                      ) {
                        accountBalances[accountId] = {
                          balance: parseFloat(txn.balance),
                          name: txn.account_name || accountId,
                          latestDate: txn.date,
                        };
                      }
                    }
                  }

                  console.log(
                    "Account balances from transactions:",
                    accountBalances
                  );

                  // Separate checking vs credit accounts
                  const checkingAccounts: AccountInfo[] = [];
                  const creditAccounts: AccountInfo[] = [];
                  let checkingTotal = 0;
                  let creditTotal = 0;

                  Object.entries(accountBalances).forEach(
                    ([accountId, data]) => {
                      // Credit detection based on your pattern: x_credit, or _credit suffix, or large debt
                      const hasCredit =
                        accountId.toLowerCase().includes("_credit") ||
                        accountId.toLowerCase().includes("credit");
                      const hasLargeDebt = data.balance < -1000; // Likely credit card debt
                      const isCredit = hasCredit || hasLargeDebt;

                      const balance = data.balance;

                      console.log(
                        `Processing account: ${accountId}, balance: ${balance}, hasCredit: ${hasCredit}, hasLargeDebt: ${hasLargeDebt}, isCredit: ${isCredit}`
                      );

                      const accountInfo: AccountInfo = {
                        id: accountId,
                        name: data.name,
                        balance: balance,
                        threshold: isCredit ? -1000 : -100,
                        is_low: balance < (isCredit ? -1000 : -100),
                        type: isCredit ? "credit" : "checking",
                      };

                      if (isCredit) {
                        creditAccounts.push(accountInfo);
                        creditTotal += balance;
                        console.log(
                          `Added to credit: ${balance}, creditTotal now: ${creditTotal}`
                        );
                      } else {
                        checkingAccounts.push(accountInfo);
                        checkingTotal += balance;
                        console.log(
                          `Added to checking: ${balance}, checkingTotal now: ${checkingTotal}`
                        );
                      }
                    }
                  );

                  console.log(
                    `Final totals - Checking: ${checkingTotal}, Credit: ${creditTotal}`
                  );

                  // If we didn't find any accounts, something is wrong with the data
                  if (Object.keys(accountBalances).length === 0) {
                    console.error("No accounts found in transaction data!");
                    throw new Error("No account data found");
                  }

                  const convertedData: SafeToSpendData = {
                    user_id: userId,
                    days: 14,
                    checking: {
                      accounts: checkingAccounts,
                      total: checkingTotal,
                      count: checkingAccounts.length,
                      safe_to_spend: fallbackData.safe_to_spend || 0,
                      buffer: 100,
                    },
                    credit: {
                      accounts: creditAccounts,
                      total: creditTotal,
                      count: creditAccounts.length,
                      available_credit: 0,
                      buffer: 200,
                    },
                    combined: {
                      net_worth: checkingTotal + creditTotal,
                      safe_to_spend: fallbackData.safe_to_spend || 0,
                      avg_daily_spend: fallbackData.avg_daily_spend || 0,
                      per_day_recurring: fallbackData.per_day_recurring || 0,
                      expected_spend: fallbackData.expected_spend || 0,
                      expected_recurring: fallbackData.expected_recurring || 0,
                    },
                    next_pay_date: fallbackData.next_pay_date || null,
                    days_to_pay: fallbackData.days_to_pay || 14,
                  };

                  console.log(
                    "Converted data with real accounts:",
                    convertedData
                  );
                  setAccountData(convertedData);
                } else {
                  throw new Error("Failed to get transactions");
                }
              } catch (txnError) {
                console.error("Failed to get transaction data:", txnError);
                // Ultimate fallback - use the old simple conversion
                const currentBalance = fallbackData.current_balance || 0;
                const safeToSpend = fallbackData.safe_to_spend || 0;

                const convertedData: SafeToSpendData = {
                  user_id: userId,
                  days: 14,
                  checking: {
                    accounts: [
                      {
                        id: "main_account",
                        name: "Main Account",
                        balance: currentBalance > 0 ? currentBalance : 0,
                        threshold: -100,
                        is_low: false,
                        type: "checking",
                      },
                    ],
                    total: currentBalance > 0 ? currentBalance : 0,
                    count: currentBalance > 0 ? 1 : 0,
                    safe_to_spend: safeToSpend,
                    buffer: 100,
                  },
                  credit: {
                    accounts:
                      currentBalance < 0
                        ? [
                            {
                              id: "main_credit",
                              name: "Credit Card",
                              balance: currentBalance,
                              threshold: -1000,
                              is_low: currentBalance < -1000,
                              type: "credit",
                            },
                          ]
                        : [],
                    total: currentBalance < 0 ? currentBalance : 0,
                    count: currentBalance < 0 ? 1 : 0,
                    available_credit: 0,
                    buffer: 200,
                  },
                  combined: {
                    net_worth: currentBalance,
                    safe_to_spend: safeToSpend,
                    avg_daily_spend: fallbackData.avg_daily_spend || 0,
                    per_day_recurring: fallbackData.per_day_recurring || 0,
                    expected_spend: fallbackData.expected_spend || 0,
                    expected_recurring: fallbackData.expected_recurring || 0,
                  },
                  next_pay_date: fallbackData.next_pay_date || null,
                  days_to_pay: fallbackData.days_to_pay || 14,
                };
                setAccountData(convertedData);
              }
            } else {
              setAccountData(null);
            }
          }
        } catch (err) {
          console.error("Failed to fetch account data:", err);
          setAccountData(null);
        }
      } else {
        setAccountData(null);
      }

      const res = await fetch(`${API}/forecast/categories`, {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({ user_id: userId, months_history: 6, top_k: 3 }),
      });
      const json = await res.json();
      const forecasts = json?.forecasts || [];
      setItems(forecasts);
      // pull small history per category if included or available
      const map: Record<string, number[]> = {};
      for (const f of forecasts) {
        // back-compat: some APIs include `history` array on the forecast
        if ((f as any).history) map[f.category] = (f as any).history;
      }
      setHistoryMap(map);
    } finally {
      setBusy(false);
    }
  };

  useEffect(() => {
    if (userId) load();
  }, [userId]);

  return (
    <div className="space-y-4">
      <h2 className="text-lg font-semibold">Welcome</h2>
      <p className="text-slate-300">
        Use the links above to upload a CSV, view transactions, subscriptions,
        and insights. Below is a quick forecast preview for next month.
      </p>

      {userId && !accountData && !busy && (
        <div className="border border-slate-700 rounded p-3">
          <div className="text-slate-400">
            Unable to load account data. Try refreshing.
          </div>
        </div>
      )}

      {userId && busy && !accountData && (
        <div className="border border-slate-700 rounded p-3">
          <div className="text-slate-400">Loading account information...</div>
        </div>
      )}

      {userId && accountData && (
        <div className="space-y-4">
          {/* Safe to spend overview */}
          <div className="border border-slate-700 rounded p-3">
            <div className="flex items-center justify-between mb-3">
              <div>
                <div className="text-sm text-slate-400">
                  Safe to spend (next 14 days)
                </div>
                <div
                  className={`text-2xl font-semibold ${
                    (accountData?.combined?.safe_to_spend ?? 0) >= 0
                      ? "text-emerald-300"
                      : "text-red-300"
                  }`}
                >
                  ${(accountData?.combined?.safe_to_spend ?? 0).toFixed(0)}
                </div>
              </div>
              <div className="text-sm text-slate-400">
                Net worth: ${(accountData?.combined?.net_worth ?? 0).toFixed(0)}
              </div>
              <button
                onClick={load}
                disabled={busy}
                className="rounded bg-blue-500 text-white px-3 py-1 disabled:opacity-50"
              >
                {busy ? "Recalc…" : "Recalculate"}
              </button>
            </div>
          </div>

          {/* Account breakdown */}
          <div className="grid md:grid-cols-2 gap-4">
            {/* Checking accounts */}
            <div className="border border-slate-700 rounded p-3">
              <div className="flex items-center justify-between mb-2">
                <h3 className="text-lg font-semibold text-blue-300">
                  Checking Accounts
                </h3>
                <span className="text-sm text-slate-400">
                  ({accountData?.checking?.count ?? 0})
                </span>
              </div>
              <div className="text-2xl font-semibold mb-2">
                ${(accountData?.checking?.total ?? 0).toFixed(2)}
              </div>
              {(accountData?.checking?.accounts?.length ?? 0) > 0 && (
                <div className="space-y-1">
                  {accountData?.checking?.accounts?.map((acc) => (
                    <div
                      key={acc.id}
                      className={`text-xs p-2 rounded ${
                        acc.is_low
                          ? "bg-red-900/20 border border-red-500/30"
                          : "bg-slate-800"
                      }`}
                    >
                      <div className="flex justify-between">
                        <span>{acc.name}</span>
                        <span className={acc.is_low ? "text-red-300" : ""}>
                          ${acc.balance.toFixed(2)}
                        </span>
                      </div>
                      {acc.is_low && (
                        <div className="text-red-400 text-xs mt-1">
                          Below threshold (${acc.threshold.toFixed(0)})
                        </div>
                      )}
                    </div>
                  ))}
                </div>
              )}
              {(accountData?.checking?.accounts?.length ?? 0) === 0 && (
                <div className="text-slate-500 text-sm">
                  No checking accounts found
                </div>
              )}
            </div>

            {/* Credit accounts */}
            <div className="border border-slate-700 rounded p-3">
              <div className="flex items-center justify-between mb-2">
                <h3 className="text-lg font-semibold text-purple-300">
                  Credit Cards
                </h3>
                <span className="text-sm text-slate-400">
                  ({accountData?.credit?.count ?? 0})
                </span>
              </div>
              <div className="text-2xl font-semibold mb-2">
                ${(accountData?.credit?.total ?? 0).toFixed(2)}
              </div>
              {(accountData?.credit?.accounts?.length ?? 0) > 0 && (
                <div className="space-y-1">
                  {accountData?.credit?.accounts?.map((acc) => (
                    <div
                      key={acc.id}
                      className={`text-xs p-2 rounded ${
                        acc.is_low
                          ? "bg-red-900/20 border border-red-500/30"
                          : "bg-slate-800"
                      }`}
                    >
                      <div className="flex justify-between">
                        <span>{acc.name}</span>
                        <span className={acc.is_low ? "text-red-300" : ""}>
                          ${acc.balance.toFixed(2)}
                        </span>
                      </div>
                      {acc.is_low && (
                        <div className="text-red-400 text-xs mt-1">
                          Over limit threshold (${acc.threshold.toFixed(0)})
                        </div>
                      )}
                    </div>
                  ))}
                </div>
              )}
              {(accountData?.credit?.accounts?.length ?? 0) === 0 && (
                <div className="text-slate-500 text-sm">
                  No credit cards found
                </div>
              )}
            </div>
          </div>
        </div>
      )}

      <div className="border border-slate-700 rounded p-4">
        <div className="flex items-end gap-3 mb-3">
          {!userId ? (
            <div>
              <Link href="/connect" className="btn">
                Sign in / Connect data
              </Link>
            </div>
          ) : (
            <button
              onClick={load}
              disabled={busy}
              className="rounded bg-blue-500 text-white px-3 py-1 disabled:opacity-50"
            >
              {busy ? "Loading…" : "Refresh Forecast"}
            </button>
          )}
        </div>
        <div className="grid md:grid-cols-3 gap-3">
          {items.map((it) => (
            <div
              key={it.category}
              className="rounded border border-slate-600 p-3"
            >
              <div className="text-sm text-slate-400">Category</div>
              <div className="font-semibold">{it.category}</div>
              <div className="mt-2 text-sm flex items-center gap-3">
                <div className="flex-1">
                  Forecast next month:{" "}
                  <span className="text-emerald-300">
                    ${it.forecast_next_month.toFixed(0)}
                  </span>
                </div>
                <div className="w-32 h-8">
                  {sparklineSvg(historyMap[it.category] || [])}
                </div>
              </div>
              <div className="text-xs text-slate-400">
                Suggestion: aim to trim ~20% if discretionary → save ~$
                {Math.round(it.forecast_next_month * 0.2)}
              </div>
            </div>
          ))}
          {items.length === 0 && (
            <div className="text-slate-400 text-sm">
              No forecast yet. Ingest some transactions first.
            </div>
          )}
        </div>
      </div>

      <div className="grid md:grid-cols-3 gap-4 mt-2">
        <a
          href="/ingest"
          className="block rounded border border-slate-700 p-4 hover:bg-slate-800/40"
        >
          <h3 className="font-semibold mb-1">CSV Ingest</h3>
          <p className="text-sm text-slate-400">
            Upload CSV for a user and import transactions.
          </p>
        </a>
        <a
          href="/transactions"
          className="block rounded border border-slate-700 p-4 hover:bg-slate-800/40"
        >
          <h3 className="font-semibold mb-1">Transactions</h3>
          <p className="text-sm text-slate-400">
            View the latest transactions by user.
          </p>
        </a>
        <a
          href="/subscriptions"
          className="block rounded border border-slate-700 p-4 hover:bg-slate-800/40"
        >
          <h3 className="font-semibold mb-1">Subscriptions</h3>
          <p className="text-sm text-slate-400">
            Detect and list recurring subscriptions.
          </p>
        </a>
      </div>
    </div>
  );
}
