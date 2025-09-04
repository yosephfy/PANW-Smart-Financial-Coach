"use client";

import AuthForm from "../../components/AuthForm";

export default function AuthPage() {
  return (
    <div className="max-w-md mx-auto py-12">
      <h1 className="text-2xl font-bold mb-4">Sign in or create an account</h1>
      <p className="text-slate-300 mb-6">Use a username and password to access your dashboard. After signing in, you'll connect your data via Plaid or CSV upload.</p>
      <AuthForm />
    </div>
  );
}

