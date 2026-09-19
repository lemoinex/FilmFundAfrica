"use client";

import Link from "next/link";
import { usePathname } from "next/navigation";

import { Alert } from "@/components/ui";
import { useAuth } from "@/lib/auth-context";
import { classNames } from "@/lib/format";
import { useI18n, type MessageKey } from "@/lib/i18n";

const ADMIN_TABS: { href: string; label: MessageKey }[] = [
  { href: "/admin/financements", label: "admin.tabs.funding" },
  { href: "/admin/veille", label: "admin.tabs.watch" },
  { href: "/admin/ia", label: "admin.tabs.ai" },
];

/**
 * Garde côté interface. Elle évite d'afficher un écran inutilisable, mais
 * la sécurité réelle est côté API : chaque route `/admin/*` vérifie le rôle.
 */
export default function AdminLayout({ children }: { children: React.ReactNode }) {
  const { user } = useAuth();
  const pathname = usePathname();
  const { t } = useI18n();

  if (user && user.user_type !== "ADMIN") {
    return (
      <Alert tone="danger" title={t("admin.restricted.title")}>
        {t("admin.restricted.body")}
      </Alert>
    );
  }

  return (
    <div className="space-y-6">
      <div>
        <p className="eyebrow mb-1.5">{t("admin.title")}</p>
        <nav className="flex gap-1 border-b border-ink-800">
          {ADMIN_TABS.map((tab) => (
            <Link
              key={tab.href}
              href={tab.href}
              className={classNames(
                "-mb-px border-b-2 px-4 py-2.5 text-sm transition-colors",
                pathname.startsWith(tab.href)
                  ? "border-brass-400 text-brass-200"
                  : "border-transparent text-slatey-400 hover:text-slatey-200",
              )}
            >
              {t(tab.label)}
            </Link>
          ))}
        </nav>
      </div>

      {children}
    </div>
  );
}
