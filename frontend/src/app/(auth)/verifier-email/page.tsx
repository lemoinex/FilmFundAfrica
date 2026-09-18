"use client";

import Link from "next/link";
import { useSearchParams } from "next/navigation";
import { Suspense, useEffect, useRef, useState } from "react";

import { Alert, Spinner } from "@/components/ui";
import { ApiError } from "@/lib/api";
import { useAuth } from "@/lib/auth-context";
import { useI18n } from "@/lib/i18n";

function VerifyEmail() {
  const params = useSearchParams();
  const token = params.get("token");
  const { verifyEmail } = useAuth();
  const { t } = useI18n();
  const [error, setError] = useState<string | null>(null);
  // En développement, React monte deux fois : sans ce garde, le lien serait
  // consommé par le premier appel et le second afficherait une erreur.
  const started = useRef(false);

  useEffect(() => {
    if (!token || started.current) return;
    started.current = true;
    verifyEmail(token).catch((err) => {
      setError(err instanceof ApiError ? err.message : t("verify.failed"));
    });
  }, [token, verifyEmail, t]);

  if (!token) {
    return (
      <div className="card p-8">
        <h1 className="font-display text-2xl text-slatey-100">{t("verify.incompleteTitle")}</h1>
        <p className="mt-3 text-sm text-slatey-400">{t("verify.incompleteBody")}</p>
        <Link href="/connexion" className="btn-secondary mt-6 inline-flex">
          {t("forgot.backToLogin")}
        </Link>
      </div>
    );
  }

  if (error) {
    return (
      <div className="card p-8">
        <h1 className="font-display text-2xl text-slatey-100">{t("verify.failedTitle")}</h1>
        <div className="mt-4">
          <Alert tone="danger">{error}</Alert>
        </div>
        <p className="mt-4 text-sm text-slatey-400">{t("verify.failedHelp")}</p>
        <Link href="/connexion" className="btn-primary mt-6 inline-flex">
          {t("verify.goToLogin")}
        </Link>
      </div>
    );
  }

  return (
    <div className="card p-8">
      <h1 className="font-display text-2xl text-slatey-100">{t("verify.inProgressTitle")}</h1>
      <p className="mt-3 flex items-center gap-2 text-sm text-slatey-400">
        <Spinner /> {t("verify.inProgressBody")}
      </p>
    </div>
  );
}

function VerifyEmailFallback() {
  const { t } = useI18n();
  return <div className="card p-8 text-sm text-slatey-400">{t("common.loading")}</div>;
}

export default function VerifyEmailPage() {
  return (
    <Suspense fallback={<VerifyEmailFallback />}>
      <VerifyEmail />
    </Suspense>
  );
}
