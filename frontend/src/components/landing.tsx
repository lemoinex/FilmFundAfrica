"use client";

import Link from "next/link";

import { LanguageSwitcher } from "@/components/language-switcher";
import { Badge } from "@/components/ui";
import { useI18n, type MessageKey } from "@/lib/i18n";
import { DOCUMENT_TYPES } from "@/lib/labels";

/* ------------------------------------------------------------------ */
/* Navigation                                                          */
/* ------------------------------------------------------------------ */
const NAV_LINKS: { href: string; label: MessageKey }[] = [
  { href: "#solution", label: "landing.nav.platform" },
  { href: "#financements", label: "landing.nav.funding" },
  { href: "#tarifs", label: "landing.nav.pricing" },
  { href: "#faq", label: "landing.nav.faq" },
];

export function LandingNav() {
  const { t } = useI18n();

  return (
    <header className="sticky top-0 z-40 border-b border-ink-800/80 bg-ink-950/85 backdrop-blur">
      <nav className="container-page flex h-16 items-center justify-between">
        <Link href="/" className="flex items-center gap-2.5">
          <Logo />
          <span className="font-display text-lg text-slatey-100">{t("common.appName")}</span>
        </Link>

        <div className="hidden items-center gap-7 text-sm text-slatey-300 md:flex">
          {NAV_LINKS.map((link) => (
            <a key={link.href} href={link.href} className="hover:text-slatey-100">
              {t(link.label)}
            </a>
          ))}
        </div>

        <div className="flex items-center gap-2">
          <LanguageSwitcher />
          <Link href="/connexion" className="btn-ghost">{t("landing.nav.login")}</Link>
          <Link href="/inscription" className="btn-primary">{t("landing.cta")}</Link>
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
  const { t } = useI18n();

  return (
    <section className="relative overflow-hidden bg-grain-fade">
      <div className="container-page py-20 sm:py-28">
        <div className="max-w-3xl animate-fade-up">
          <p className="eyebrow mb-5">{t("landing.hero.eyebrow")}</p>
          <h1 className="font-display text-4xl leading-[1.12] text-slatey-100 sm:text-5xl lg:text-6xl">
            {t("landing.hero.title")}
          </h1>
          <p className="mt-6 max-w-2xl text-lg leading-relaxed text-slatey-300">
            {t("landing.hero.body")}
          </p>

          <div className="mt-9 flex flex-wrap gap-3">
            <Link href="/inscription" className="btn-primary px-6 py-3 text-base">
              {t("landing.cta")}
            </Link>
            <a href="#solution" className="btn-secondary px-6 py-3 text-base">
              {t("landing.hero.discover")}
            </a>
          </div>

          <p className="mt-6 text-sm text-slatey-400">{t("landing.hero.noCard")}</p>
        </div>
      </div>
      <div className="pointer-events-none absolute inset-x-0 bottom-0 h-px bg-gradient-to-r from-transparent via-brass-500/30 to-transparent" />
    </section>
  );
}

/* ------------------------------------------------------------------ */
/* 1 — Problème                                                        */
/* ------------------------------------------------------------------ */
const PROBLEMS: MessageKey[] = [
  "landing.problem.1",
  "landing.problem.2",
  "landing.problem.3",
  "landing.problem.4",
  "landing.problem.5",
  "landing.problem.6",
  "landing.problem.7",
  "landing.problem.8",
];

export function Problem() {
  const { t } = useI18n();

  return (
    <section className="border-t border-ink-800 py-20">
      <div className="container-page">
        <div className="mb-10 max-w-2xl">
          <p className="eyebrow mb-3">{t("landing.problem.eyebrow")}</p>
          <h2 className="font-display text-3xl text-slatey-100">{t("landing.problem.title")}</h2>
          <p className="mt-4 text-slatey-300">{t("landing.problem.body")}</p>
        </div>

        <ul className="grid gap-3 sm:grid-cols-2 lg:grid-cols-4">
          {PROBLEMS.map((problem) => (
            <li key={problem} className="card p-4 text-sm text-slatey-300">
              <span className="mr-2 text-signal-danger">✕</span>
              {t(problem)}
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
const PILLARS: { title: MessageKey; description: MessageKey }[] = [
  { title: "landing.pillar.development", description: "landing.pillar.developmentBody" },
  { title: "landing.pillar.funding", description: "landing.pillar.fundingBody" },
  { title: "landing.pillar.ai", description: "landing.pillar.aiBody" },
  { title: "landing.pillar.management", description: "landing.pillar.managementBody" },
];

export function Solution() {
  const { t } = useI18n();

  return (
    <section id="solution" className="border-t border-ink-800 py-20">
      <div className="container-page">
        <div className="mb-10 max-w-2xl">
          <p className="eyebrow mb-3">{t("landing.solution.eyebrow")}</p>
          <h2 className="font-display text-3xl text-slatey-100">{t("landing.solution.title")}</h2>
          <p className="mt-4 text-slatey-300">{t("landing.solution.body")}</p>
        </div>

        <div className="grid gap-4 sm:grid-cols-2 lg:grid-cols-4">
          {PILLARS.map((pillar, index) => (
            <div key={pillar.title} className="card p-6">
              <span className="font-display text-sm text-brass-400">0{index + 1}</span>
              <h3 className="mt-3 font-display text-lg text-slatey-100">{t(pillar.title)}</h3>
              <p className="mt-2 text-sm leading-relaxed text-slatey-400">
                {t(pillar.description)}
              </p>
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
const WRITER_POINTS: MessageKey[] = [
  "landing.writer.point1",
  "landing.writer.point2",
  "landing.writer.point3",
  "landing.writer.point4",
];

/** Les mêmes actions que dans l'éditeur, plus la régénération complète. */
const REWORK_ACTIONS: MessageKey[] = [
  "landing.writer.regenerate",
  "editor.refine.IMPROVE",
  "editor.refine.SHORTEN",
  "editor.refine.EXPAND",
  "editor.refine.CORRECT",
];

export function AiWriter() {
  const { t } = useI18n();

  return (
    <section className="border-t border-ink-800 py-20">
      <div className="container-page grid items-center gap-12 lg:grid-cols-2">
        <div>
          <p className="eyebrow mb-3">{t("writer.title")}</p>
          <h2 className="font-display text-3xl text-slatey-100">{t("landing.writer.title")}</h2>
          <p className="mt-4 text-slatey-300">{t("landing.writer.body")}</p>

          <ul className="mt-6 space-y-3 text-sm text-slatey-300">
            {WRITER_POINTS.map((point) => (
              <li key={point} className="flex gap-3">
                <span className="text-brass-400">→</span>
                {t(point)}
              </li>
            ))}
          </ul>
        </div>

        <div className="card p-6">
          <p className="mb-4 text-xs uppercase tracking-wide text-slatey-400">
            {t("landing.writer.documents")}
          </p>
          {/* La liste vient du catalogue de documents : la page d'accueil ne
              peut pas annoncer un document que l'AI Writer ne produit pas. */}
          <div className="flex flex-wrap gap-2">
            {DOCUMENT_TYPES.map((type) => (
              <Badge key={type} tone="brass">
                {t(`documentType.${type}`)}
              </Badge>
            ))}
          </div>
          <div className="mt-6 border-t border-ink-700 pt-5">
            <p className="mb-3 text-xs uppercase tracking-wide text-slatey-400">
              {t("landing.writer.rework")}
            </p>
            <div className="flex flex-wrap gap-2">
              {REWORK_ACTIONS.map((action) => (
                <span key={action} className="btn-secondary pointer-events-none px-3 py-1.5 text-xs">
                  {t(action)}
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
const EXAMPLE_FUNDS = [
  { letter: "A", score: 92 },
  { letter: "B", score: 87 },
  { letter: "C", score: 81 },
];

export function Funding() {
  const { t } = useI18n();

  return (
    <section id="financements" className="border-t border-ink-800 py-20">
      <div className="container-page">
        <div className="mb-10 max-w-2xl">
          <p className="eyebrow mb-3">{t("landing.funding.eyebrow")}</p>
          <h2 className="font-display text-3xl text-slatey-100">{t("landing.funding.title")}</h2>
          <p className="mt-4 text-slatey-300">{t("landing.funding.body")}</p>
        </div>

        <div className="grid gap-4 lg:grid-cols-3">
          <div className="card p-6 lg:col-span-2">
            <p className="mb-4 text-xs uppercase tracking-wide text-slatey-400">
              {t("landing.funding.example")}
            </p>
            <div className="space-y-3">
              {EXAMPLE_FUNDS.map((fund) => (
                <div key={fund.letter} className="flex items-center gap-4">
                  <span className="w-20 text-sm text-slatey-200">
                    {t("landing.funding.exampleFund", { letter: fund.letter })}
                  </span>
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
              {t("landing.funding.exampleNote")}
            </p>
          </div>

          <div className="card border-brass-500/25 bg-brass-500/[0.04] p-6">
            <h3 className="font-display text-base text-brass-100">
              {t("landing.funding.notTitle")}
            </h3>
            <p className="mt-3 text-sm leading-relaxed text-slatey-300">
              {t("landing.funding.notBody")}
            </p>
            <p className="mt-4 text-sm leading-relaxed text-slatey-400">
              {t("landing.funding.sourceNote")}
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
const BUDGET_ROWS: { phase: MessageKey; detail: MessageKey }[] = [
  { phase: "budgetCategory.DEVELOPMENT", detail: "landing.budget.development" },
  { phase: "budgetCategory.PRE_PRODUCTION", detail: "landing.budget.preProduction" },
  { phase: "budgetCategory.PRODUCTION", detail: "landing.budget.production" },
  { phase: "budgetCategory.POST_PRODUCTION", detail: "landing.budget.postProduction" },
  { phase: "budgetCategory.DISTRIBUTION", detail: "landing.budget.distribution" },
];

export function BudgetSection() {
  const { t } = useI18n();

  return (
    <section className="border-t border-ink-800 py-20">
      <div className="container-page grid items-center gap-12 lg:grid-cols-2">
        <div className="card p-6">
          <p className="mb-4 text-xs uppercase tracking-wide text-slatey-400">
            {t("landing.budget.lines")}
          </p>
          <div className="space-y-2.5">
            {BUDGET_ROWS.map((row) => (
              <div
                key={row.phase}
                className="flex items-baseline justify-between gap-4 border-b border-ink-800 pb-2.5 last:border-0"
              >
                <span className="text-sm font-medium text-slatey-200">{t(row.phase)}</span>
                <span className="text-right text-xs text-slatey-400">{t(row.detail)}</span>
              </div>
            ))}
          </div>
        </div>

        <div>
          <p className="eyebrow mb-3">{t("landing.budget.eyebrow")}</p>
          <h2 className="font-display text-3xl text-slatey-100">{t("landing.budget.title")}</h2>
          <p className="mt-4 text-slatey-300">{t("landing.budget.body")}</p>
        </div>
      </div>
    </section>
  );
}

/* ------------------------------------------------------------------ */
/* 7 — Pour qui ?                                                      */
/* ------------------------------------------------------------------ */
const AUDIENCES: { title: MessageKey; items: MessageKey[] }[] = [
  {
    title: "landing.audience.author",
    items: [
      "landing.audience.author1",
      "landing.audience.author2",
      "landing.audience.author3",
      "landing.audience.author4",
    ],
  },
  {
    title: "landing.audience.producer",
    items: [
      "landing.audience.producer1",
      "landing.audience.producer2",
      "landing.audience.producer3",
      "landing.audience.producer4",
    ],
  },
  {
    title: "landing.audience.institution",
    items: [
      "landing.audience.institution1",
      "landing.audience.institution2",
      "landing.audience.institution3",
      "landing.audience.institution4",
    ],
  },
];

export function Audiences() {
  const { t } = useI18n();

  return (
    <section className="border-t border-ink-800 py-20">
      <div className="container-page">
        <div className="mb-10 max-w-2xl">
          <p className="eyebrow mb-3">{t("landing.audiences.eyebrow")}</p>
          <h2 className="font-display text-3xl text-slatey-100">{t("landing.audiences.title")}</h2>
        </div>

        <div className="grid gap-4 md:grid-cols-3">
          {AUDIENCES.map((audience) => (
            <div key={audience.title} className="card p-6">
              <h3 className="font-display text-lg text-slatey-100">{t(audience.title)}</h3>
              <ul className="mt-4 space-y-2 text-sm text-slatey-400">
                {audience.items.map((item) => (
                  <li key={item} className="flex gap-2.5">
                    <span className="text-brass-400">·</span>
                    {t(item)}
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
const PLANS: {
  name: MessageKey;
  price: string;
  period: MessageKey | null;
  description: MessageKey;
  features: MessageKey[];
  cta: MessageKey;
  highlighted: boolean;
}[] = [
  {
    name: "plan.FREE",
    price: "0",
    period: null,
    description: "landing.pricing.freeBody",
    features: ["landing.pricing.free1", "landing.pricing.free2", "landing.pricing.free3"],
    cta: "landing.pricing.freeCta",
    highlighted: false,
  },
  {
    name: "plan.PRO_AUTHOR",
    price: "20 000",
    period: "landing.pricing.perMonth",
    description: "landing.pricing.proBody",
    features: [
      "landing.pricing.pro1",
      "landing.pricing.pro2",
      "landing.pricing.pro3",
      "landing.pricing.pro4",
      "landing.pricing.pro5",
    ],
    cta: "landing.pricing.proCta",
    highlighted: true,
  },
  {
    name: "plan.PRODUCER",
    price: "100 000",
    period: "landing.pricing.perMonth",
    description: "landing.pricing.producerBody",
    features: [
      "landing.pricing.producer1",
      "landing.pricing.producer2",
      "landing.pricing.producer3",
      "landing.pricing.producer4",
      "landing.pricing.producer5",
    ],
    cta: "landing.pricing.producerCta",
    highlighted: false,
  },
];

export function Pricing() {
  const { t } = useI18n();

  return (
    <section id="tarifs" className="border-t border-ink-800 py-20">
      <div className="container-page">
        <div className="mb-10 max-w-2xl">
          <p className="eyebrow mb-3">{t("landing.pricing.eyebrow")}</p>
          <h2 className="font-display text-3xl text-slatey-100">{t("landing.pricing.title")}</h2>
          <p className="mt-4 text-slatey-300">{t("landing.pricing.body")}</p>
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
                  {t("landing.pricing.mostChosen")}
                </span>
              ) : null}

              <h3 className="font-display text-lg text-slatey-100">{t(plan.name)}</h3>
              <p className="mt-1 text-sm text-slatey-400">{t(plan.description)}</p>

              <p className="mt-5 flex items-baseline gap-2">
                <span className="font-display text-3xl text-slatey-100">{plan.price}</span>
                <span className="text-sm text-slatey-400">{plan.period ? t(plan.period) : ""}</span>
              </p>

              <ul className="mt-5 space-y-2.5 text-sm text-slatey-300">
                {plan.features.map((feature) => (
                  <li key={feature} className="flex gap-2.5">
                    <span className="text-brass-400">✓</span>
                    {t(feature)}
                  </li>
                ))}
              </ul>

              <Link
                href="/inscription"
                className={plan.highlighted ? "btn-primary mt-6 w-full" : "btn-secondary mt-6 w-full"}
              >
                {t(plan.cta)}
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
const FAQ_ITEMS: { question: MessageKey; answer: MessageKey }[] = [
  { question: "landing.faq.q1", answer: "landing.faq.a1" },
  { question: "landing.faq.q2", answer: "landing.faq.a2" },
  { question: "landing.faq.q3", answer: "landing.faq.a3" },
  { question: "landing.faq.q4", answer: "landing.faq.a4" },
  { question: "landing.faq.q5", answer: "landing.faq.a5" },
  { question: "landing.faq.q6", answer: "landing.faq.a6" },
];

export function Faq() {
  const { t } = useI18n();

  return (
    <section id="faq" className="border-t border-ink-800 py-20">
      <div className="container-page max-w-3xl">
        <p className="eyebrow mb-3">{t("landing.nav.faq")}</p>
        <h2 className="mb-9 font-display text-3xl text-slatey-100">{t("landing.faq.title")}</h2>

        <div className="space-y-2.5">
          {FAQ_ITEMS.map((item) => (
            <details
              key={item.question}
              className="card group p-5 [&_summary::-webkit-details-marker]:hidden"
            >
              <summary className="flex cursor-pointer items-center justify-between gap-4 text-sm font-medium text-slatey-100">
                {t(item.question)}
                <span className="text-brass-400 transition-transform group-open:rotate-45">+</span>
              </summary>
              <p className="mt-3 text-sm leading-relaxed text-slatey-400">{t(item.answer)}</p>
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
  const { t } = useI18n();

  return (
    <section className="border-t border-ink-800 bg-grain-fade py-20">
      <div className="container-page text-center">
        <h2 className="mx-auto max-w-2xl font-display text-3xl text-slatey-100 sm:text-4xl">
          {t("landing.final.title")}
        </h2>
        <p className="mx-auto mt-4 max-w-xl text-slatey-300">{t("landing.final.body")}</p>
        <div className="mt-8 flex flex-wrap justify-center gap-3">
          <Link href="/inscription" className="btn-primary px-6 py-3 text-base">
            {t("landing.cta")}
          </Link>
          <Link href="/connexion" className="btn-secondary px-6 py-3 text-base">
            {t("landing.final.haveAccount")}
          </Link>
        </div>
      </div>
    </section>
  );
}

export function LandingFooter() {
  const { t } = useI18n();

  return (
    <footer className="border-t border-ink-800 py-10">
      <div className="container-page flex flex-col items-center justify-between gap-4 text-sm text-slatey-400 sm:flex-row">
        <div className="flex items-center gap-2.5">
          <Logo className="h-5 w-5" />
          <span>{t("common.appName")}</span>
        </div>
        <p>{t("common.tagline")}</p>
        <p>© {new Date().getFullYear()}</p>
      </div>
    </footer>
  );
}
