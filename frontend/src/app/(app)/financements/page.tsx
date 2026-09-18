import Link from "next/link";

import { SectionHeading } from "@/components/ui";

export const metadata = { title: "Financements" };

/**
 * Le module Funding Intelligence (base d'opportunités, recherche, filtres,
 * matching) est planifié en Phase 3. Les tables et l'API de matching existent
 * déjà en base ; cette page annonce honnêtement ce qui n'est pas encore livré
 * plutôt que d'afficher des données fictives comme si elles étaient réelles.
 */
export default function FundingPage() {
  return (
    <>
      <SectionHeading
        eyebrow="Funding Intelligence"
        title="Financements"
        description="Fonds, bourses, résidences, laboratoires, festivals et forums de coproduction."
      />

      <div className="card p-8">
        <p className="text-sm leading-relaxed text-slatey-300">
          Ce module arrive en <strong className="text-slatey-100">Phase 3</strong>. Le schéma de
          base de données, les catégories de dispositifs, les exigences par dossier et la table
          de matching sont déjà en place : la recherche, les filtres et le score de
          compatibilité s&apos;y brancheront sans migration.
        </p>
        <p className="mt-4 text-sm leading-relaxed text-slatey-400">
          Règle tenue dès maintenant : aucune opportunité ne sera affichée sans sa source et sa
          date de dernière vérification, et le score de compatibilité restera un indicateur
          d&apos;aide à la décision — jamais une garantie de financement.
        </p>

        <div className="mt-6 flex flex-wrap gap-3">
          <Link href="/projets" className="btn-secondary">Revenir à mes projets</Link>
        </div>
      </div>
    </>
  );
}
