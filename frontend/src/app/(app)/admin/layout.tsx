"use client";

import Link from "next/link";
import { usePathname } from "next/navigation";
import { useEffect, useState } from "react";

import { Alert } from "@/components/ui";
import { platformApi } from "@/lib/api";
import { useAuth } from "@/lib/auth-context";
import { classNames } from "@/lib/format";
import { useI18n, type MessageKey } from "@/lib/i18n";
import type { PlatformStatus } from "@/lib/types";

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
  const [platform, setPlatform] = useState<PlatformStatus | null>(null);

  // Pendant la bêta interne, aucun quota n'est opposé aux administrateurs.
  // C'est voulu — et c'est précisément pourquoi il faut le dire : sans ce
  // rappel, on croirait les règles d'offre éprouvées alors qu'elles ne
  // s'appliquent à personne dans l'équipe. Un échec est sans conséquence :
  // l'information est un repère, pas une garde.
  useEffect(() => {
    if (user?.user_type !== "ADMIN") return;
    platformApi
      .get()
      .then(setPlatform)
      .catch(() => setPlatform(null));
  }, [user?.user_type]);

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

      {platform ? (
        <Alert
          tone={platform.internal ? "warning" : "info"}
          title={t(platform.internal ? "platform.internal.title" : "platform.public.title")}
        >
          {platform.internal
            ? t("platform.internal.body", {
                start: platform.start_date,
                end: platform.target_end_date,
              })
            : t("platform.public.body")}
        </Alert>
      ) : null}

      {children}
    </div>
  );
}
