import "./globals.css";
import type { Metadata } from "next";
import AppProviders from "../components/Providers";
import SignGate from "../components/SignGate";
import Header from "../components/Header";

export const metadata: Metadata = {
  title: "Smart Financial Coach",
  description: "Hackathon demo UI",
};

export default function RootLayout({
  children,
}: {
  children: React.ReactNode;
}) {
  return (
    <html lang="en">
      <body className="min-h-screen">
        <AppProviders>
          <Header />
          <main className="max-w-5xl mx-auto px-4 py-6">
            <SignGate>{children}</SignGate>
          </main>
        </AppProviders>
      </body>
    </html>
  );
}
