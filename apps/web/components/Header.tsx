"use client";
import Link from "next/link";
import { useUser } from "./Providers";
import { usePathname } from "next/navigation";

const navigationLinks = [
  { href: "/", label: "Home", icon: "🏠" },
  { href: "/transactions", label: "Transactions", icon: "💳" },
  { href: "/budgets", label: "Budgets", icon: "📊" },
  { href: "/goals", label: "Goals", icon: "🎯" },
  { href: "/insights", label: "Insights", icon: "💡" },
  { href: "/subscriptions", label: "Subscriptions", icon: "🔄" },
  { href: "/connect", label: "Connect", icon: "🔗" },
  { href: "/ingest", label: "Import", icon: "📤" },
  { href: "/dev", label: "Developer", icon: "🛠️" },
];

export default function Header() {
  const { userId, setUserId } = useUser();
  const pathname = usePathname();

  const handleSignOut = () => {
    setUserId("");
  };

  return (
    <header className="sticky top-0 z-50 bg-slate-900/95 backdrop-blur-sm border-b border-slate-700/50">
      <div className="max-w-7xl mx-auto px-4 py-3">
        {/* Logo */}
        <div className="flex items-center gap-3">
          <Link
            href="/"
            className="flex items-center gap-2 hover:opacity-80 transition-opacity"
          >
            <span className="text-2xl">💰</span>
            <h1 className="text-xl font-bold text-white">
              Smart Financial Coach
            </h1>
          </Link>
        </div>
        <div className="flex items-center justify-between">
          {/* Navigation */}
          <nav className="hidden md:flex items-center gap-1">
            {navigationLinks.map((link) => {
              const isActive = pathname === link.href;
              return (
                <Link
                  key={link.href}
                  href={link.href}
                  className={`flex items-center gap-2 px-3 py-2 rounded-lg text-sm font-medium transition-all duration-200 ${
                    isActive
                      ? "bg-blue-600 text-white shadow-sm"
                      : "text-slate-300 hover:text-white hover:bg-slate-700"
                  }`}
                >
                  <span className="text-base">{link.icon}</span>
                  <span className="hidden lg:inline">{link.label}</span>
                </Link>
              );
            })}
          </nav>

          {/* User Section */}
          <div className="flex items-center gap-3">
            {/* API Status (Development Only) */}
            {process.env.NODE_ENV === "development" && (
              <div className="hidden xl:flex items-center gap-2 px-2 py-1 rounded bg-slate-800 text-xs text-slate-400">
                <span className="w-2 h-2 bg-green-400 rounded-full"></span>
                API:{" "}
                {process.env.NEXT_PUBLIC_API_URL || "localhost:3000/backend"}
              </div>
            )}

            {/* User Authentication */}
            {userId ? (
              <div className="flex items-center gap-3">
                <div className="hidden sm:flex items-center gap-2 px-3 py-1 bg-slate-800 rounded-lg">
                  <span className="text-emerald-400">●</span>
                  <span className="text-sm text-slate-300">
                    <span className="text-slate-400">Signed in as:</span>{" "}
                    <strong className="text-white">{userId}</strong>
                  </span>
                </div>
                <button
                  onClick={handleSignOut}
                  className="flex items-center gap-2 px-3 py-2 text-sm font-medium text-slate-300 hover:text-white hover:bg-slate-700 rounded-lg transition-all duration-200"
                >
                  <span>👋</span>
                  <span className="hidden sm:inline">Sign Out</span>
                </button>
              </div>
            ) : (
              <Link
                href="/auth"
                className="flex items-center gap-2 px-4 py-2 bg-blue-600 hover:bg-blue-700 text-white rounded-lg font-medium transition-colors shadow-sm"
              >
                <span>🔐</span>
                <span>Sign In</span>
              </Link>
            )}
          </div>
        </div>

        {/* Mobile Navigation */}
        <nav className="md:hidden mt-3 pt-3 border-t border-slate-700/50">
          <div className="grid grid-cols-4 gap-2">
            {navigationLinks.slice(0, 8).map((link) => {
              const isActive = pathname === link.href;
              return (
                <Link
                  key={link.href}
                  href={link.href}
                  className={`flex flex-col items-center gap-1 p-2 rounded-lg text-xs font-medium transition-all duration-200 ${
                    isActive
                      ? "bg-blue-600 text-white"
                      : "text-slate-300 hover:text-white hover:bg-slate-700"
                  }`}
                >
                  <span className="text-lg">{link.icon}</span>
                  <span className="truncate w-full text-center">
                    {link.label}
                  </span>
                </Link>
              );
            })}
          </div>
        </nav>
      </div>
    </header>
  );
}
