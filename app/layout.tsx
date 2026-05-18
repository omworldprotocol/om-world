import type { Metadata } from "next";
import Link from "next/link";
import "./globals.css";

export const metadata: Metadata = {
  title: "OM World — One Mind, One World",
  description:
    "A self-growing intent realization network. Every realization should make the next realization easier.",
};

export default function RootLayout({ children }: { children: React.ReactNode }) {
  return (
    <html lang="en">
      <body className="min-h-screen font-sans antialiased">
        <header className="border-b border-black/10">
          <nav className="mx-auto flex max-w-6xl items-center justify-between px-6 py-4">
            <Link href="/" className="text-lg font-semibold tracking-tight">
              OM World
            </Link>
            <div className="flex gap-6 text-sm">
              <Link href="/intent" className="hover:underline">
                Submit an Intent
              </Link>
              <Link href="/capability" className="hover:underline">
                Contribute a Capability
              </Link>
              <Link href="/patterns" className="hover:underline">
                Patterns
              </Link>
              <Link href="/dashboard" className="hover:underline">
                Dashboard
              </Link>
            </div>
          </nav>
        </header>
        <main className="mx-auto max-w-6xl px-6 py-10">{children}</main>
        <footer className="mx-auto max-w-6xl border-t border-black/10 px-6 py-6 text-xs text-black/60">
          One Mind, One World. — Genesis MVP v0.1
        </footer>
      </body>
    </html>
  );
}
