"use client";

import React, {
  createContext,
  useCallback,
  useContext,
  useEffect,
  useMemo,
  useState,
} from "react";

type ToastType = "info" | "success" | "error" | "warning";
type ToastItem = { id: string; message: string; type: ToastType };

type UserContextType = {
  userId: string;
  setUserId: (s: string) => void;
  showToast: (message: string, type?: ToastType) => void;
  ready: boolean;
};

const UserContext = createContext<UserContextType | null>(null);

export function useUser() {
  const ctx = useContext(UserContext);
  if (!ctx) throw new Error("useUser must be used within AppProviders");
  return ctx;
}

export function useToast() {
  const ctx = useContext(UserContext);
  if (!ctx) throw new Error("useToast must be used within AppProviders");
  return ctx.showToast;
}

export function AppProviders({ children }: { children: React.ReactNode }) {
  const [userId, setUserId] = useState("");
  const [ready, setReady] = useState(false);

  useEffect(() => {
    try {
      const stored = localStorage.getItem("sfc:userId");
      if (stored) setUserId(stored);
    } catch {}
    setReady(true);
  }, []);

  useEffect(() => {
    try {
      if (userId) localStorage.setItem("sfc:userId", userId);
      else localStorage.removeItem("sfc:userId");
    } catch {}
  }, [userId]);
  const [toasts, setToasts] = useState<ToastItem[]>([]);

  const showToast = useCallback((message: string, type: ToastType = "info") => {
    const id = Math.random().toString(36).slice(2, 9);
    const t = { id, message, type };
    setToasts((s) => [t, ...s]);
    setTimeout(() => setToasts((s) => s.filter((x) => x.id !== id)), 4000);
  }, []);

  const value = useMemo(
    () => ({ userId, setUserId, showToast, ready }),
    [userId, showToast, ready]
  );

  return (
    <UserContext.Provider value={value}>
      {children}
      <div aria-live="polite" className="fixed right-4 bottom-4 space-y-2 z-50">
        {toasts.map((t) => (
          <div
            key={t.id}
            className={`max-w-sm px-3 py-2 rounded shadow-md text-sm border ${
              t.type === "success"
                ? "bg-emerald-700/80 border-emerald-600 text-emerald-100"
                : t.type === "error"
                ? "bg-red-700/80 border-red-600 text-red-100"
                : t.type === "warning"
                ? "bg-amber-700/80 border-amber-600 text-amber-100"
                : "bg-slate-800/80 border-slate-700 text-slate-100"
            }`}
          >
            {t.message}
          </div>
        ))}
      </div>
    </UserContext.Provider>
  );
}

export default AppProviders;
