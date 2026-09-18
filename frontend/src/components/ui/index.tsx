"use client";

import Link from "next/link";
import type { ReactNode } from "react";

import { classNames } from "@/lib/format";
import { useI18n } from "@/lib/i18n";

/* ------------------------------------------------------------------ */
/* Retours d'état                                                      */
/* ------------------------------------------------------------------ */
export function Spinner({ className = "h-4 w-4" }: { className?: string }) {
  return (
    <svg className={classNames("animate-spin", className)} viewBox="0 0 24 24" fill="none" aria-hidden>
      <circle className="opacity-20" cx="12" cy="12" r="10" stroke="currentColor" strokeWidth="3" />
      <path
        className="opacity-90"
        fill="currentColor"
        d="M12 2a10 10 0 0 1 10 10h-3a7 7 0 0 0-7-7V2z"
      />
    </svg>
  );
}

export function Alert({
  tone = "info",
  title,
  children,
  onDismiss,
}: {
  tone?: "info" | "success" | "warning" | "danger";
  title?: string;
  children: ReactNode;
  onDismiss?: () => void;
}) {
  const { t } = useI18n();
  const tones = {
    info: "border-signal-info/40 bg-signal-info/10 text-slatey-100",
    success: "border-signal-success/40 bg-signal-success/10 text-slatey-100",
    warning: "border-signal-warning/40 bg-signal-warning/10 text-slatey-100",
    danger: "border-signal-danger/40 bg-signal-danger/10 text-slatey-100",
  } as const;

  return (
    <div className={classNames("rounded-lg border px-4 py-3 text-sm", tones[tone])} role="alert">
      <div className="flex items-start gap-3">
        <div className="flex-1">
          {title ? <p className="mb-0.5 font-semibold">{title}</p> : null}
          <div className="text-slatey-200">{children}</div>
        </div>
        {onDismiss ? (
          <button
            type="button"
            onClick={onDismiss}
            className="text-slatey-400 hover:text-slatey-100"
            aria-label={t("common.close")}
          >
            ✕
          </button>
        ) : null}
      </div>
    </div>
  );
}

export function EmptyState({
  title,
  description,
  action,
}: {
  title: string;
  description: string;
  action?: ReactNode;
}) {
  return (
    <div className="card flex flex-col items-center gap-3 px-6 py-14 text-center">
      <div className="flex h-11 w-11 items-center justify-center rounded-full border border-ink-600 bg-ink-800 text-brass-300">
        <svg viewBox="0 0 24 24" className="h-5 w-5" fill="none" stroke="currentColor" strokeWidth="1.6">
          <path d="M12 5v14M5 12h14" strokeLinecap="round" />
        </svg>
      </div>
      <h3 className="font-display text-lg text-slatey-100">{title}</h3>
      <p className="max-w-md text-sm text-slatey-400">{description}</p>
      {action ? <div className="mt-2">{action}</div> : null}
    </div>
  );
}

export function SkeletonCard({ lines = 3 }: { lines?: number }) {
  return (
    <div className="card space-y-3 p-5">
      <div className="skeleton h-4 w-1/3 rounded" />
      {Array.from({ length: lines }).map((_, index) => (
        <div key={index} className="skeleton h-3 w-full rounded" />
      ))}
    </div>
  );
}

/* ------------------------------------------------------------------ */
/* Présentation                                                        */
/* ------------------------------------------------------------------ */
export function Badge({
  tone = "neutral",
  children,
}: {
  tone?: "neutral" | "brass" | "success" | "warning" | "danger";
  children: ReactNode;
}) {
  const tones = {
    neutral: "border-ink-600 bg-ink-800 text-slatey-300",
    brass: "border-brass-500/40 bg-brass-500/10 text-brass-200",
    success: "border-signal-success/40 bg-signal-success/10 text-signal-success",
    warning: "border-signal-warning/40 bg-signal-warning/10 text-signal-warning",
    danger: "border-signal-danger/40 bg-signal-danger/10 text-signal-danger",
  } as const;
  return <span className={classNames("badge", tones[tone])}>{children}</span>;
}

/** Jauge du Project Readiness Score. */
export function ScoreRing({ value, size = 56 }: { value: number | null | undefined; size?: number }) {
  const { t } = useI18n();
  const score = value ?? 0;
  const radius = (size - 6) / 2;
  const circumference = 2 * Math.PI * radius;
  const offset = circumference * (1 - score / 100);
  const stroke = score >= 70 ? "#4C9A6A" : score >= 40 ? "#CBA04A" : "#B4564C";

  return (
    <div className="relative inline-flex" style={{ width: size, height: size }}>
      <svg width={size} height={size} className="-rotate-90">
        <circle cx={size / 2} cy={size / 2} r={radius} stroke="#1F2531" strokeWidth="4" fill="none" />
        <circle
          cx={size / 2}
          cy={size / 2}
          r={radius}
          stroke={stroke}
          strokeWidth="4"
          fill="none"
          strokeLinecap="round"
          strokeDasharray={circumference}
          strokeDashoffset={offset}
          style={{ transition: "stroke-dashoffset .6s ease" }}
        />
      </svg>
      <span
        className="absolute inset-0 flex items-center justify-center text-xs font-semibold tabular-nums text-slatey-100"
        title={t("ui.scoreTitle", { value: value ?? t("ui.scoreNotComputed") })}
      >
        {value ?? "—"}
      </span>
    </div>
  );
}

export function StatTile({
  label,
  value,
  hint,
  href,
}: {
  label: string;
  value: string | number;
  hint?: string;
  href?: string;
}) {
  const content = (
    <div className="card h-full p-5 transition-colors hover:border-ink-600">
      <p className="text-xs uppercase tracking-wide text-slatey-400">{label}</p>
      <p className="mt-2 font-display text-3xl tabular-nums text-slatey-100">{value}</p>
      {hint ? <p className="mt-1 text-xs text-slatey-400">{hint}</p> : null}
    </div>
  );
  return href ? <Link href={href}>{content}</Link> : content;
}

export function SectionHeading({
  eyebrow,
  title,
  description,
  action,
}: {
  eyebrow?: string;
  title: string;
  description?: string;
  action?: ReactNode;
}) {
  return (
    <div className="mb-5 flex flex-wrap items-end justify-between gap-3">
      <div>
        {eyebrow ? <p className="eyebrow mb-1.5">{eyebrow}</p> : null}
        <h2 className="font-display text-xl text-slatey-100">{title}</h2>
        {description ? <p className="mt-1 text-sm text-slatey-400">{description}</p> : null}
      </div>
      {action}
    </div>
  );
}
