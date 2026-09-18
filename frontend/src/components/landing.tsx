import Link from "next/link";

import { Badge } from "@/components/ui";

/* ------------------------------------------------------------------ */
/* Navigation                                                          */
/* ------------------------------------------------------------------ */
export function LandingNav() {
  return (
    <header className="sticky top-0 z-40 border-b border-ink-800/80 bg-ink-950/85 backdrop-blur">
      <nav className="container-page flex h-16 items-center justify-between">
        <Link href="/" className="flex items-center gap-2.5">
          <Logo />
          <span className="font-display text-lg text-slatey-100">FilmFund Africa</span>
        </Link>

        <div className="hidden items-center gap-7 text-sm text-slatey-300 md:flex">
          <a href="#solution" className="hover:text-slatey-100">Plateforme</a>
          <a href="#financements" className="hover:text-slatey-100">Financements</a>
          <a href="#tarifs" className="hover:text-slatey-100">Tarifs</a>
          <a href="#faq" className="hover:text-slatey-100">FAQ</a>
        </div>

        <div className="flex items-center gap-2">
          <Link href="/connexion" className="btn-ghost">Connexion</Link>
          <Link href="/inscription" className="btn-primary">Créer mon projet</Link>
        </div>
      </nav>
    </header>
  );
}

export function Logo({ className = "h-7 w-7" }: { className?: string }) {
  return (
    <svg viewBox="0 0 32 32" className={className} aria-hidden>
      <rect x="2" y="6" width="28" height="20" rx="3" fill="none" stroke="#CBA04A" strokeWidth="1.8" />
      <path d="M8 26V6M24 26V6" stroke="#CBA04A" strokeWidth="1.2" opacity=".45" />
      <path d="M12 12.5l7 3.5-7 3.5v-7z" fill="#CBA04A" />
    </svg>
  );
}

/* ------------------------------------------------------------------ */
/* 0 — Hero                                                            */
/* ------------------------------------------------------------------ */
export function Hero() {
  return (
    <section className="relative overflow-hidden bg-grain-fade">
      <div className="container-page py-20 sm:py-28">
        <div className="max-w-3xl animate-fade-up">
          <p className="eyebrow mb-5">De l&apos;idée au financement de votre projet audiovisuel</p>
          <h1 className="font-display text-4xl leading-[1.12] text-slatey-100 sm:text-5xl lg:text-6xl">
            Transformez votre idée en projet audiovisuel finançable.
          </h1>
          <p className="mt-6 max-w-2xl text-lg leading-relaxed text-slatey-300">
            Développez votre projet, créez votre dossier et découvrez les financements adaptés
            à votre film — avec un assistant conçu pour les réalités du cinéma africain
            francophone.
          </p>

          <div className="mt-9 flex flex-wrap gap-3">
            <Link href="/inscription" className="btn-primary px-6 py-3 text-base">
              Créer mon projet
            </Link>
            <a href="#solution" className="btn-secondary px-6 py-3 text-base">
              Découvrir la plateforme
            </a>
          </div>

          <p className="mt-6 text-sm text-slatey-400">
            Offre gratuite · Aucune carte bancaire requise
          </p>
        </div>
      </div>
      <div className="pointer-events-none absolute inset-x-0 bottom-0 h-px bg-gradient-to-r from-transparent via-brass-500/30 to-transparent" />
    </section>
  );
}

/* ------------------------------------------------------------------ */
/* 1 — Problème                                                        */
/* ------------------------------------------------------------------ */
const PROBLEMS = [
  "Structurer un projet encore flou",
  "Rédiger un dossier au niveau attendu",
  "Comprendre ce que veulent vraiment les financeurs",
  "Trouver les fonds adaptés à son film",
  "Suivre les appels à projets et leurs échéances",
  "Construire un budget crédible",
  "Préparer un pitch qui tient en trois minutes",
  "Travailler sans outil pensé pour l'Afrique",
];

export function Problem() {
  return (
    <section className="border-t border-ink-800 py-20">
      <div className="container-page">
        <div className="mb-10 max-w-2xl">
          <p className="eyebrow mb-3">Le problème</p>
          <h2 className="font-display text-3xl text-slatey-100">
            Le film existe. Le dossier, rarement.
          </h2>
          <p className="mt-4 text-slatey-300">
            Chaque année, des projets solides sont écartés non pas pour leur qualité
            artistique, mais parce que le dossier ne répond pas aux attentes des comités.
          </p>
        </div>

        <ul className="grid gap-3 sm:grid-cols-2 lg:grid-cols-4">
          {PROBLEMS.map((problem) => (
            <li key={problem} className="card p-4 text-sm text-slatey-300">
              <span className="mr-2 text-signal-danger">✕</span>
              {problem}
            </li>
          ))}
        </ul>
      </div>
    </section>
  );
}

/* ------------------------------------------------------------------ */
/* 2 — Solution                                                        */
/* ------------------------------------------------------------------ */
const PILLARS = [
  {
    title: "Project Development",
    description:
      "Structurez votre projet étape par étape : concept, personnages, enjeux, vision, public.",
  },
  {
    title: "Funding Intelligence",
    description:
      "Une base d'opportunités qui conserve sa source et sa date de dernière vérification.",
  },
  {
    title: "AI Assistant",
    description:
      "Un assistant spécialisé dans les documents du cinéma, pas un générateur de texte générique.",
  },
  {
    title: "Project Management",
    description: "Vos documents, leurs versions et vos échéances au même endroit.",
  },
];

export function Solution() {
  return (
    <section id="solution" className="border-t border-ink-800 py-20">
      <div className="container-page">
        <div className="mb-10 max-w-2xl">
          <p className="eyebrow mb-3">La solution</p>
          <h2 className="font-display text-3xl text-slatey-100">
            Une chaîne continue : idée → projet → dossier → financement.
          </h2>
          <p className="mt-4 text-slatey-300">
            FilmFund Africa n&apos;est pas un ERP audiovisuel. Chaque fonctionnalité renforce
            cette seule chaîne.
          </p>
        </div>

        <div className="grid gap-4 sm:grid-cols-2 lg:grid-cols-4">
          {PILLARS.map((pillar, index) => (
            <div key={pillar.title} className="card p-6">
              <span className="font-display text-sm text-brass-400">0{index + 1}</span>
              <h3 className="mt-3 font-display text-lg text-slatey-100">{pillar.title}</h3>
              <p className="mt-2 text-sm leading-relaxed text-slatey-400">{pillar.description}</p>
            </div>
          ))}
        </div>
      </div>
    </section>
  );
}

/* ------------------------------------------------------------------ */
/* 3 — AI Writer                                                       */
/* ------------------------------------------------------------------ */
const DOCUMENTS = [
  "Logline",
  "Synopsis court",
  "Synopsis long",
  "Note d'intention",
  "Note de réalisation",
  "Traitement",
  "Présentation des personnages",
  "Pitch oral",
  "Pitch écrit",
  "Bible du projet",
  "Scénario dialogué",
];

export function AiWriter() {
  return (
    <section className="border-t border-ink-800 py-20">
      <div className="container-page grid items-center gap-12 lg:grid-cols-2">
        <div>
          <p className="eyebrow mb-3">AI Writer</p>
          <h2 className="font-display text-3xl text-slatey-100">
            Des documents cohérents entre eux, pas onze textes indépendants.
          </h2>
          <p className="mt-4 text-slatey-300">
            Chaque document est écrit à partir du contexte complet du projet et des documents
            déjà validés : la note de réalisation prolonge la note d&apos;intention, le
            traitement suit le synopsis, le scénario respecte le traitement.
          </p>

          <ul className="mt-6 space-y-3 text-sm text-slatey-300">
            <li className="flex gap-3">
              <span className="text-brass-400">→</span>
              Structure professionnelle imposée et longueur cible — jamais de remplissage.
            </li>
            <li className="flex gap-3">
              <span className="text-brass-400">→</span>
              Durée de scénario au choix (10, 26, 52, 90, 120 min) : 1 page ≈ 1 minute.
            </li>
            <li className="flex gap-3">
              <span className="text-brass-400">→</span>
              Versions sauvegardées, comparables et restaurables à tout moment.
            </li>
            <li className="flex gap-3">
              <span className="text-brass-400">→</span>
              Information absente ? Le document écrit « Information non fournie. » plutôt que
              d&apos;inventer.
            </li>
          </ul>
        </div>

        <div className="card p-6">
          <p className="mb-4 text-xs uppercase tracking-wide text-slatey-400">
            Documents générables
          </p>
          <div className="flex flex-wrap gap-2">
            {DOCUMENTS.map((document) => (
              <Badge key={document} tone="brass">{document}</Badge>
            ))}
          </div>
          <div className="mt-6 border-t border-ink-700 pt-5">
            <p className="mb-3 text-xs uppercase tracking-wide text-slatey-400">
              Retravailler en un clic
            </p>
            <div className="flex flex-wrap gap-2">
              {["Régénérer", "Améliorer", "Raccourcir", "Développer", "Corriger"].map((action) => (
                <span key={action} className="btn-secondary pointer-events-none px-3 py-1.5 text-xs">
                  {action}
                </span>
              ))}
            </div>
          </div>
        </div>
      </div>
    </section>
  );
}

/* ------------------------------------------------------------------ */
/* 4 — Funding Intelligence · 5 — Matching                             */
/* ------------------------------------------------------------------ */
export function Funding() {
  return (
    <section id="financements" className="border-t border-ink-800 py-20">
      <div className="container-page">
        <div className="mb-10 max-w-2xl">
          <p className="eyebrow mb-3">Funding Intelligence &amp; Matching</p>
          <h2 className="font-display text-3xl text-slatey-100">
            Les financements qui correspondent vraiment à votre projet.
          </h2>
          <p className="mt-4 text-slatey-300">
            Fonds, bourses, résidences, laboratoires, festivals et forums de coproduction,
            filtrés par pays, genre, type de projet, budget et langue.
          </p>
        </div>

        <div className="grid gap-4 lg:grid-cols-3">
          <div className="card p-6 lg:col-span-2">
            <p className="mb-4 text-xs uppercase tracking-wide text-slatey-400">
              Exemple d&apos;analyse de compatibilité
            </p>
            <div className="space-y-3">
              {[
                { name: "Fonds A", score: 92 },
                { name: "Fonds B", score: 87 },
                { name: "Fonds C", score: 81 },
              ].map((fund) => (
                <div key={fund.name} className="flex items-center gap-4">
                  <span className="w-20 text-sm text-slatey-200">{fund.name}</span>
                  <div className="h-1.5 flex-1 overflow-hidden rounded-full bg-ink-700">
                    <div
                      className="h-full rounded-full bg-brass-400"
                      style={{ width: `${fund.score}%` }}
                    />
                  </div>
                  <span className="w-12 text-right text-sm tabular-nums text-brass-200">
                    {fund.score}%
                  </span>
                </div>
              ))}
            </div>
            <p className="mt-5 border-t border-ink-700 pt-4 text-xs leading-relaxed text-slatey-400">
              Pour chaque résultat : pourquoi ce fonds correspond, conditions remplies,
              conditions manquantes, documents requis, date limite, montant potentiel et lien
              de candidature.
            </p>
          </div>

          <div className="card border-brass-500/25 bg-brass-500/[0.04] p-6">
            <h3 className="font-display text-base text-brass-100">Ce que le score n&apos;est pas</h3>
            <p className="mt-3 text-sm leading-relaxed text-slatey-300">
              Le score de compatibilité est un indicateur d&apos;aide à la décision. Il ne
              constitue en aucun cas une garantie de financement : les conditions officielles
              de chaque organisme font foi.
            </p>
            <p className="mt-4 text-sm leading-relaxed text-slatey-400">
              Aucune opportunité n&apos;est affichée sans sa source et sa date de dernière
              vérification.
            </p>
          </div>
        </div>
      </div>
    </section>
  );
}

/* ------------------------------------------------------------------ */
/* 6 — Budget                                                          */
/* ------------------------------------------------------------------ */
export function BudgetSection() {
  return (
    <section className="border-t border-ink-800 py-20">
      <div className="container-page grid items-center gap-12 lg:grid-cols-2">
        <div className="card p-6">
          <p className="mb-4 text-xs uppercase tracking-wide text-slatey-400">
            Postes budgétaires
          </p>
          <div className="space-y-2.5">
            {[
              ["Développement", "recherche, écriture, repérages"],
              ["Préproduction", "casting, préparation, autorisations"],
              ["Production", "équipe, matériel, transport, décors"],
              ["Postproduction", "montage, étalonnage, mixage, sous-titrage"],
              ["Distribution", "festivals, communication, marketing"],
            ].map(([phase, detail]) => (
              <div key={phase} className="flex items-baseline justify-between gap-4 border-b border-ink-800 pb-2.5 last:border-0">
                <span className="text-sm font-medium text-slatey-200">{phase}</span>
                <span className="text-right text-xs text-slatey-400">{detail}</span>
              </div>
            ))}
          </div>
        </div>

        <div>
          <p className="eyebrow mb-3">Budget &amp; plan de financement</p>
          <h2 className="font-display text-3xl text-slatey-100">
            Un budget que le comité peut lire sans vous.
          </h2>
          <p className="mt-4 text-slatey-300">
            Budget par phase, plan de financement par source, calcul automatique du financement
            acquis, du financement recherché et du pourcentage couvert. Calendrier de production
            du développement à la distribution.
          </p>
          <Badge tone="neutral">Module à venir — Phase 4</Badge>
        </div>
      </div>
    </section>
  );
}

/* ------------------------------------------------------------------ */
/* 7 — Pour qui ?                                                      */
/* ------------------------------------------------------------------ */
const AUDIENCES = [
  {
    title: "Auteur · Réalisateur",
    items: ["Créer ses projets", "Générer ses documents", "Chercher des financements", "Suivre ses échéances"],
  },
  {
    title: "Producteur",
    items: ["Plusieurs projets", "Budgets", "Équipes et collaborateurs", "Suivi des candidatures"],
  },
  {
    title: "Institution",
    items: ["École de cinéma", "Incubateur, fonds culturel", "ONG, organisme de formation", "Gestion de cohortes"],
  },
];

export function Audiences() {
  return (
    <section className="border-t border-ink-800 py-20">
      <div className="container-page">
        <div className="mb-10 max-w-2xl">
          <p className="eyebrow mb-3">Pour qui ?</p>
          <h2 className="font-display text-3xl text-slatey-100">
            Des auteurs isolés aux structures qui accompagnent.
          </h2>
        </div>

        <div className="grid gap-4 md:grid-cols-3">
          {AUDIENCES.map((audience) => (
            <div key={audience.title} className="card p-6">
              <h3 className="font-display text-lg text-slatey-100">{audience.title}</h3>
              <ul className="mt-4 space-y-2 text-sm text-slatey-400">
                {audience.items.map((item) => (
                  <li key={item} className="flex gap-2.5">
                    <span className="text-brass-400">·</span>
                    {item}
                  </li>
                ))}
              </ul>
            </div>
          ))}
        </div>
      </div>
    </section>
  );
}

/* ------------------------------------------------------------------ */
/* 8 — Tarifs                                                          */
/* ------------------------------------------------------------------ */
const PLANS = [
  {
    name: "Gratuit",
    price: "0",
    period: "",
    description: "Pour tester la plateforme sur un projet.",
    features: ["1 projet", "1 génération IA", "Veille limitée"],
    cta: "Commencer",
    highlighted: false,
  },
  {
    name: "Pro Auteur",
    price: "20 000",
    period: "FCFA / mois",
    description: "Pour un auteur qui porte ses projets jusqu'au dépôt.",
    features: [
      "Projets illimités",
      "Génération IA complète",
      "Veille personnalisée",
      "Matching des financements",
      "Export PDF et Word",
    ],
    cta: "Choisir Pro Auteur",
    highlighted: true,
  },
  {
    name: "Producteur",
    price: "100 000",
    period: "FCFA / mois",
    description: "Pour une structure qui gère un portefeuille de projets.",
    features: [
      "Gestion multi-projets",
      "Budget avancé",
      "Collaboration d'équipe",
      "Export complet du dossier",
      "Suivi des candidatures",
    ],
    cta: "Choisir Producteur",
    highlighted: false,
  },
];

export function Pricing() {
  return (
    <section id="tarifs" className="border-t border-ink-800 py-20">
      <div className="container-page">
        <div className="mb-10 max-w-2xl">
          <p className="eyebrow mb-3">Tarifs</p>
          <h2 className="font-display text-3xl text-slatey-100">Trois offres, une seule promesse.</h2>
          <p className="mt-4 text-slatey-300">
            L&apos;usage de l&apos;IA fonctionne au crédit : chaque génération en consomme,
            afin que le service reste soutenable et prévisible.
          </p>
        </div>

        <div className="grid gap-4 lg:grid-cols-3">
          {PLANS.map((plan) => (
            <div
              key={plan.name}
              className={
                plan.highlighted
                  ? "card relative border-brass-500/50 bg-brass-500/[0.04] p-6 shadow-lift"
                  : "card p-6"
              }
            >
              {plan.highlighted ? (
                <span className="absolute -top-2.5 left-6 rounded-full bg-brass-400 px-2.5 py-0.5 text-[11px] font-semibold text-ink-950">
                  Le plus choisi
                </span>
              ) : null}

              <h3 className="font-display text-lg text-slatey-100">{plan.name}</h3>
              <p className="mt-1 text-sm text-slatey-400">{plan.description}</p>

              <p className="mt-5 flex items-baseline gap-2">
                <span className="font-display text-3xl text-slatey-100">{plan.price}</span>
                <span className="text-sm text-slatey-400">{plan.period}</span>
              </p>

              <ul className="mt-5 space-y-2.5 text-sm text-slatey-300">
                {plan.features.map((feature) => (
                  <li key={feature} className="flex gap-2.5">
                    <span className="text-brass-400">✓</span>
                    {feature}
                  </li>
                ))}
              </ul>

              <Link
                href="/inscription"
                className={plan.highlighted ? "btn-primary mt-6 w-full" : "btn-secondary mt-6 w-full"}
              >
                {plan.cta}
              </Link>
            </div>
          ))}
        </div>
      </div>
    </section>
  );
}

/* ------------------------------------------------------------------ */
/* 9 — FAQ                                                             */
/* ------------------------------------------------------------------ */
const FAQ_ITEMS = [
  {
    question: "L'IA écrit-elle mon film à ma place ?",
    answer:
      "Non. Elle met en forme ce que vous lui donnez, selon la structure attendue par les comités de lecture. Si une information manque, elle l'indique au lieu de l'inventer — jamais de personnage, d'événement ou de financement fabriqué.",
  },
  {
    question: "À qui appartiennent les documents générés ?",
    answer:
      "À vous. Vous les modifiez, les exportez en PDF ou en Word, et vous les emportez quand vous le souhaitez.",
  },
  {
    question: "Le score de compatibilité garantit-il un financement ?",
    answer:
      "Non, en aucun cas. C'est un indicateur d'aide à la décision qui compare votre projet aux critères publiés d'un dispositif. Les conditions officielles de l'organisme font foi.",
  },
  {
    question: "Les opportunités affichées sont-elles à jour ?",
    answer:
      "Chaque opportunité conserve sa source et sa date de dernière vérification, affichées avec elle. Les données de démonstration sont explicitement marquées comme fictives.",
  },
  {
    question: "Puis-je générer un scénario de long métrage complet ?",
    answer:
      "Oui. Vous choisissez la durée cible (10 à 120 minutes) ; un scénario long est écrit en plusieurs passes successives, chacune reprenant la continuité de la précédente. La longueur vient du nombre de séquences, jamais d'un étirement artificiel.",
  },
  {
    question: "Mes projets sont-ils visibles par d'autres utilisateurs ?",
    answer:
      "Non. Chaque projet est strictement cloisonné à son compte. Un utilisateur ne peut jamais accéder aux projets d'un autre.",
  },
];

export function Faq() {
  return (
    <section id="faq" className="border-t border-ink-800 py-20">
      <div className="container-page max-w-3xl">
        <p className="eyebrow mb-3">FAQ</p>
        <h2 className="mb-9 font-display text-3xl text-slatey-100">Questions fréquentes</h2>

        <div className="space-y-2.5">
          {FAQ_ITEMS.map((item) => (
            <details key={item.question} className="card group p-5 [&_summary::-webkit-details-marker]:hidden">
              <summary className="flex cursor-pointer items-center justify-between gap-4 text-sm font-medium text-slatey-100">
                {item.question}
                <span className="text-brass-400 transition-transform group-open:rotate-45">+</span>
              </summary>
              <p className="mt-3 text-sm leading-relaxed text-slatey-400">{item.answer}</p>
            </details>
          ))}
        </div>
      </div>
    </section>
  );
}

/* ------------------------------------------------------------------ */
/* 10 — CTA final + pied de page                                       */
/* ------------------------------------------------------------------ */
export function FinalCta() {
  return (
    <section className="border-t border-ink-800 bg-grain-fade py-20">
      <div className="container-page text-center">
        <h2 className="mx-auto max-w-2xl font-display text-3xl text-slatey-100 sm:text-4xl">
          Votre prochain dossier peut être prêt cette semaine.
        </h2>
        <p className="mx-auto mt-4 max-w-xl text-slatey-300">
          Créez votre compte, renseignez votre concept, et repartez avec un dossier structuré
          et une liste de financements à viser.
        </p>
        <div className="mt-8 flex flex-wrap justify-center gap-3">
          <Link href="/inscription" className="btn-primary px-6 py-3 text-base">
            Créer mon projet
          </Link>
          <Link href="/connexion" className="btn-secondary px-6 py-3 text-base">
            J&apos;ai déjà un compte
          </Link>
        </div>
      </div>
    </section>
  );
}

export function LandingFooter() {
  return (
    <footer className="border-t border-ink-800 py-10">
      <div className="container-page flex flex-col items-center justify-between gap-4 text-sm text-slatey-400 sm:flex-row">
        <div className="flex items-center gap-2.5">
          <Logo className="h-5 w-5" />
          <span>FilmFund Africa</span>
        </div>
        <p>De l&apos;idée au financement de votre projet audiovisuel.</p>
        <p>© {new Date().getFullYear()}</p>
      </div>
    </footer>
  );
}
