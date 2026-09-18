"use client";

import { useRouter, useSearchParams } from "next/navigation";
import { Suspense, useState } from "react";

import { Alert, SectionHeading, Spinner } from "@/components/ui";
import { ApiError, billingApi } from "@/lib/api";

/**
 * Page de paiement du prestataire simulé.
 *
 * Elle tient la place de la page d'un vrai prestataire, pour que le parcours
 * complet soit cliquable sans compte marchand. La route serveur qu'elle
 * appelle n'existe qu'en développement.
 */
function Simulation() {
  const params = useSearchParams();
  const router = useRouter();
  const reference = params.get("reference");
  const [error, setError] = useState<string | null>(null);
  const [busy, setBusy] = useState(false);

  async function settle(succeed: boolean) {
    if (!reference) return;
    setError(null);
    setBusy(true);
    try {
      await billingApi.simulate(reference, succeed);
      router.push("/abonnement");
    } catch (err) {
      setError(err instanceof ApiError ? err.message : "Simulation impossible.");
      setBusy(false);
    }
  }

  return (
    <div className="card mx-auto max-w-lg p-8">
      <SectionHeading
        title="Paiement simulé"
        description="Aucun montant réel n'est encaissé : ce prestataire n'existe que pour le développement."
      />

      {!reference ? (
        <Alert tone="warning">Référence de paiement absente de l&apos;adresse.</Alert>
      ) : (
        <>
          <p className="text-sm text-slatey-400">
            Référence <span className="text-slatey-200">{reference}</span>
          </p>
          {error ? (
            <div className="mt-4">
              <Alert tone="danger">{error}</Alert>
            </div>
          ) : null}
          <div className="mt-6 flex flex-wrap gap-3">
            <button
              type="button"
              className="btn-primary"
              onClick={() => settle(true)}
              disabled={busy}
            >
              {busy ? <Spinner /> : null}
              Confirmer le paiement
            </button>
            <button
              type="button"
              className="btn-secondary"
              onClick={() => settle(false)}
              disabled={busy}
            >
              Simuler un échec
            </button>
          </div>
        </>
      )}
    </div>
  );
}

export default function SimulationPage() {
  return (
    <Suspense fallback={<div className="card p-8 text-sm text-slatey-400">Chargement…</div>}>
      <Simulation />
    </Suspense>
  );
}
