"use client";

import Link from "next/link";

import { Logo } from "@/components/landing";
import { LanguageSwitcher } from "@/components/language-switcher";
import { useI18n } from "@/lib/i18n";

export default function AuthLayout({ children }: { children: React.ReactNode }) {
  const { t } = useI18n();

  return (
    <div className="flex min-h-screen flex-col bg-grain-fade">
      <header className="container-page flex h-16 items-center">
        <Link href="/" className="flex items-center gap-2.5">
          <Logo />
          <span className="font-display text-lg text-slatey-100">{t("common.appName")}</span>
        </Link>
        {/* Le choix de la langue doit précéder la création du compte : c'est
            la première page que voit quelqu'un qui n'a pas encore de profil. */}
        <LanguageSwitcher className="ml-auto" />
      </header>

      <main className="container-page flex flex-1 items-center justify-center py-12">
        <div className="w-full max-w-md animate-fade-up">{children}</div>
      </main>

      <footer className="container-page py-6 text-center text-xs text-slatey-500">
        {t("common.tagline")}
      </footer>
    </div>
  );
}
