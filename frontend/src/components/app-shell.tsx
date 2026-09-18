"use client";

import Link from "next/link";
import { usePathname } from "next/navigation";
import { useState } from "react";

import { Logo } from "@/components/landing";
import { useAuth } from "@/lib/auth-context";
import { classNames } from "@/lib/format";

const NAVIGATION = [
  { href: "/tableau-de-bord", label: "Tableau de bord", icon: "grid" },
  { href: "/projets", label: "Mes projets", icon: "folder" },
  { href: "/financements", label: "Financements", icon: "target" },
  { href: "/profil", label: "Profil", icon: "user" },
] as const;

//: Visible uniquement pour le rôle ADMIN ; l'API le vérifie de son côté.
const ADMIN_NAVIGATION = [
  { href: "/admin/financements", label: "Administration", icon: "shield" },
] as const;

function NavIcon({ name }: { name: string }) {
  const paths: Record<string, string> = {
    grid: "M4 4h6v6H4zM14 4h6v6h-6zM4 14h6v6H4zM14 14h6v6h-6z",
    folder: "M3 7a2 2 0 0 1 2-2h4l2 2h8a2 2 0 0 1 2 2v8a2 2 0 0 1-2 2H5a2 2 0 0 1-2-2z",
    target: "M12 3v3m0 12v3M3 12h3m12 0h3M12 8a4 4 0 1 0 0 8 4 4 0 0 0 0-8z",
    user: "M12 12a4 4 0 1 0 0-8 4 4 0 0 0 0 8zM5 20a7 7 0 0 1 14 0",
    shield: "M12 3l7 3v6c0 4-3 7.5-7 9-4-1.5-7-5-7-9V6l7-3z",
  };
  return (
    <svg viewBox="0 0 24 24" className="h-4 w-4 shrink-0" fill="none" stroke="currentColor" strokeWidth="1.6" aria-hidden>
      <path d={paths[name]} strokeLinecap="round" strokeLinejoin="round" />
    </svg>
  );
}

export function AppShell({ children }: { children: React.ReactNode }) {
  const pathname = usePathname();
  const { user, logout } = useAuth();
  const [menuOpen, setMenuOpen] = useState(false);

  const displayName = user?.profile
    ? `${user.profile.first_name} ${user.profile.last_name}`.trim()
    : user?.email;

  return (
    <div className="flex min-h-screen">
      {/* Barre latérale */}
      <aside
        className={classNames(
          "fixed inset-y-0 left-0 z-40 w-64 border-r border-ink-800 bg-ink-900 transition-transform lg:static lg:translate-x-0",
          menuOpen ? "translate-x-0" : "-translate-x-full",
        )}
      >
        <div className="flex h-16 items-center gap-2.5 border-b border-ink-800 px-5">
          <Logo className="h-6 w-6" />
          <span className="font-display text-base text-slatey-100">FilmFund Africa</span>
        </div>

        <nav className="space-y-1 p-3">
          {[
            ...NAVIGATION,
            ...(user?.user_type === "ADMIN" ? ADMIN_NAVIGATION : []),
          ].map((item) => {
            const active = pathname === item.href || pathname.startsWith(`${item.href}/`);
            return (
              <Link
                key={item.href}
                href={item.href}
                onClick={() => setMenuOpen(false)}
                className={classNames(
                  "flex items-center gap-3 rounded-lg px-3 py-2 text-sm transition-colors",
                  active
                    ? "bg-brass-500/10 font-medium text-brass-200"
                    : "text-slatey-300 hover:bg-ink-800 hover:text-slatey-100",
                )}
              >
                <NavIcon name={item.icon} />
                {item.label}
              </Link>
            );
          })}
        </nav>

        <div className="absolute inset-x-0 bottom-0 border-t border-ink-800 p-3">
          <div className="rounded-lg bg-ink-800 p-3">
            <p className="text-xs text-slatey-400">Crédits IA restants</p>
            <p className="mt-0.5 font-display text-xl tabular-nums text-brass-200">
              {user?.ai_credits_remaining ?? "—"}
            </p>
          </div>
          <button type="button" onClick={logout} className="btn-ghost mt-2 w-full justify-start text-sm">
            Se déconnecter
          </button>
        </div>
      </aside>

      {menuOpen ? (
        <div
          className="fixed inset-0 z-30 bg-ink-950/70 lg:hidden"
          onClick={() => setMenuOpen(false)}
          aria-hidden
        />
      ) : null}

      {/* Contenu */}
      <div className="flex min-w-0 flex-1 flex-col">
        <header className="sticky top-0 z-20 flex h-16 items-center justify-between border-b border-ink-800 bg-ink-950/90 px-4 backdrop-blur sm:px-6">
          <button
            type="button"
            className="btn-ghost px-2 lg:hidden"
            onClick={() => setMenuOpen((open) => !open)}
            aria-label="Ouvrir le menu"
          >
            <svg viewBox="0 0 24 24" className="h-5 w-5" fill="none" stroke="currentColor" strokeWidth="1.8">
              <path d="M4 7h16M4 12h16M4 17h16" strokeLinecap="round" />
            </svg>
          </button>

          <div className="ml-auto flex items-center gap-3">
            <Link href="/projets/nouveau" className="btn-primary hidden sm:inline-flex">
              Nouveau projet
            </Link>
            <div className="flex items-center gap-2.5">
              <div className="flex h-8 w-8 items-center justify-center rounded-full bg-brass-500/15 text-xs font-semibold text-brass-200">
                {displayName?.slice(0, 1).toUpperCase() ?? "?"}
              </div>
              <span className="hidden text-sm text-slatey-300 sm:inline">{displayName}</span>
            </div>
          </div>
        </header>

        <main className="flex-1 px-4 py-7 sm:px-6 lg:px-8">
          <div className="mx-auto w-full max-w-5xl">{children}</div>
        </main>
      </div>
    </div>
  );
}
