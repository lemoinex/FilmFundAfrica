"use client";

import Link from "next/link";
import { useSearchParams } from "next/navigation";
import { Suspense, useEffect, useRef, useState } from "react";

import { Alert, Spinner } from "@/components/ui";
import { ApiError } from "@/lib/api";
import { useAuth } from "@/lib/auth-context";

function VerifyEmail() {
  const params = useSearchParams();
  const token = params.get("token");
  const { verifyEmail } = useAuth();
  const [error, setError] = useState<string | null>(null);
  // En développement, React monte deux fois : sans ce garde, le lien serait
  // consommé par le premier appel et le second afficherait une erreur.
  const started = useRef(false);

  useEffect(() => {
    if (!token || started.current) return;
    started.current = true;
    verifyEmail(token).catch((err) => {
      setError(
        err instanceof ApiError ? err.message : "Confirmation impossible pour le moment.",
      );
    });
  }, [token, verifyEmail]);

  if (!token) {
    return (
      <div className="card p-8">
        <h1 className="font-display text-2xl text-slatey-100">Lien incomplet</h1>
        <p className="mt-3 text-sm text-slatey-400">
          Ce lien ne contient pas de jeton de confirmation. Ouvrez celui reçu par e-mail sans
          le modifier.
        </p>
        <Link href="/connexion" className="btn-secondary mt-6 inline-flex">
          Retour à la connexion
        </Link>
      </div>
    );
  }

  if (error) {
    return (
      <div className="card p-8">
        <h1 className="font-display text-2xl text-slatey-100">Confirmation impossible</h1>
        <div className="mt-4">
          <Alert tone="danger">{error}</Alert>
        </div>
        <p className="mt-4 text-sm text-slatey-400">
          Un lien de confirmation ne sert qu&apos;une fois et expire au bout de 24 heures. Depuis
          page de connexion, vous pouvez en demander un nouveau.
        </p>
        <Link href="/connexion" className="btn-primary mt-6 inline-flex">
          Aller à la connexion
        </Link>
      </div>
    );
  }

  return (
    <div className="card p-8">
      <h1 className="font-display text-2xl text-slatey-100">Confirmation en cours…</h1>
      <p className="mt-3 flex items-center gap-2 text-sm text-slatey-400">
        <Spinner /> Activation de votre compte.
      </p>
    </div>
  );
}

export default function VerifyEmailPage() {
  return (
    <Suspense fallback={<div className="card p-8 text-sm text-slatey-400">Chargement…</div>}>
      <VerifyEmail />
    </Suspense>
  );
}
