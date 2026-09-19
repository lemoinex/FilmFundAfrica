"use client";

import { useCallback, useEffect, useState } from "react";

import { Alert, Badge, SectionHeading, SkeletonCard, Spinner } from "@/components/ui";
import { ApiError, aiConfigApi } from "@/lib/api";
import { useI18n, type MessageKey } from "@/lib/i18n";
import type { AIConfig, AIConfigTestResult, AIProviderName, AIProviderState } from "@/lib/types";

/**
 * Configuration du fournisseur d'IA.
 *
 * Deux principes tiennent tout cet écran. **Une clé par fournisseur** : ce
 * sont deux comptes chez deux sociétés, changer de fournisseur ne doit pas
 * faire perdre l'autre clé. **Une clé saisie ne se relit jamais** : le
 * serveur ne renvoie que ses quatre derniers caractères, et le champ reste
 * donc toujours vide — ce n'est pas un oubli, c'est la seule façon qu'un
 * accès à cette page ne vaille pas le secret lui-même.
 */
export default function AdminIAPage() {
  const { t } = useI18n();
  const [config, setConfig] = useState<AIConfig | null>(null);
  const [model, setModel] = useState("");
  const [keys, setKeys] = useState<Record<string, string>>({});
  const [loading, setLoading] = useState(true);
  const [saving, setSaving] = useState(false);
  const [testing, setTesting] = useState(false);
  const [result, setResult] = useState<AIConfigTestResult | null>(null);
  const [error, setError] = useState<string | null>(null);
  const [notice, setNotice] = useState<string | null>(null);

  const load = useCallback(async () => {
    setLoading(true);
    try {
      const fresh = await aiConfigApi.get();
      setConfig(fresh);
      setModel(fresh.configured_model);
    } catch (err) {
      setError(err instanceof ApiError ? err.message : t("load.failed"));
    } finally {
      setLoading(false);
    }
  }, [t]);

  useEffect(() => {
    void load();
  }, [load]);

  async function apply(payload: Parameters<typeof aiConfigApi.update>[0]) {
    setError(null);
    setNotice(null);
    setResult(null);
    setSaving(true);
    try {
      const fresh = await aiConfigApi.update(payload);
      setConfig(fresh);
      setModel(fresh.configured_model);
      // Le champ se vide après enregistrement : la clé est partie, et rien
      // ne doit laisser croire qu'on peut encore la relire ici.
      setKeys({});
      setNotice(t("aiConfig.saved"));
    } catch (err) {
      setError(err instanceof ApiError ? err.message : t("load.failed"));
    } finally {
      setSaving(false);
    }
  }

  async function runTest() {
    setError(null);
    setNotice(null);
    setTesting(true);
    try {
      setResult(await aiConfigApi.test());
    } catch (err) {
      setError(err instanceof ApiError ? err.message : t("load.failed"));
    } finally {
      setTesting(false);
    }
  }

  if (loading) return <SkeletonCard lines={6} />;
  if (!config) return null;

  const active = config.providers.find((p) => p.name === config.active_provider);
  const missingModel =
    active !== undefined && !active.default_model && !model.trim() && active.requires_key;

  return (
    <div className="space-y-7">
      <div>
        <h1 className="font-display text-3xl text-slatey-100">{t("aiConfig.title")}</h1>
        <p className="mt-1.5 text-sm text-slatey-400">{t("aiConfig.subtitle")}</p>
      </div>

      {error ? (
        <Alert tone="danger" onDismiss={() => setError(null)}>
          {error}
        </Alert>
      ) : null}
      {notice ? (
        <Alert tone="info" onDismiss={() => setNotice(null)}>
          {notice}
        </Alert>
      ) : null}
      {config.active_provider === "mock" ? (
        <Alert tone="warning">{t("aiConfig.mockWarning")}</Alert>
      ) : null}

      {/* Fournisseur actif */}
      <div className="card p-6">
        <SectionHeading
          title={t("aiConfig.activeProvider")}
          description={t("aiConfig.providerHint")}
        />
        <div className="flex flex-wrap gap-2">
          {config.providers.map((provider) => (
            <button
              key={provider.name}
              type="button"
              disabled={saving}
              onClick={() => void apply({ provider: provider.name })}
              className={
                provider.name === config.active_provider
                  ? "btn-primary px-3 py-1.5 text-xs"
                  : "btn-secondary px-3 py-1.5 text-xs"
              }
            >
              {t(`aiConfig.provider.${provider.name}` as MessageKey)}
            </button>
          ))}
        </div>

        <div className="mt-5">
          <label className="mb-1.5 block text-xs uppercase tracking-wide text-slatey-500">
            {t("aiConfig.model")}
          </label>
          <div className="flex flex-wrap gap-2">
            <input
              className="input flex-1"
              value={model}
              placeholder={t("aiConfig.modelPlaceholder")}
              onChange={(event) => setModel(event.target.value)}
            />
            <button
              type="button"
              className="btn-secondary px-4 py-2 text-sm"
              disabled={saving}
              onClick={() => void apply({ model })}
            >
              {t("aiConfig.save")}
            </button>
          </div>
          <p className="mt-1.5 text-xs text-slatey-500">
            {t("aiConfig.modelEffective", { model: config.effective_model || "—" })} (
            {t(`aiConfig.source.${config.model_source}` as MessageKey)})
          </p>
          {missingModel ? (
            <div className="mt-3">
              <Alert tone="warning">{t("aiConfig.modelRequired")}</Alert>
            </div>
          ) : null}
        </div>
      </div>

      {/* Une clé par fournisseur */}
      {config.providers
        .filter((provider) => provider.requires_key)
        .map((provider) => (
          <ProviderKeyCard
            key={provider.name}
            provider={provider}
            value={keys[provider.name] ?? ""}
            saving={saving}
            onChange={(value) =>
              setKeys((current) => ({ ...current, [provider.name]: value }))
            }
            onSave={() =>
              void apply({
                key_provider: provider.name,
                api_key: keys[provider.name] ?? "",
              })
            }
            onRemove={() => {
              const label = t(`aiConfig.provider.${provider.name}` as MessageKey);
              if (window.confirm(t("aiConfig.removeKeyConfirm", { provider: label }))) {
                void apply({ key_provider: provider.name, api_key: "" });
              }
            }}
          />
        ))}

      {/* L'épreuve */}
      <div className="card p-6">
        <SectionHeading title={t("aiConfig.test")} description={t("aiConfig.testWarning")} />
        <button
          type="button"
          className="btn-primary px-4 py-2 text-sm"
          disabled={testing}
          onClick={() => void runTest()}
        >
          {testing ? (
            <span className="flex items-center gap-2">
              <Spinner /> {t("aiConfig.testRunning")}
            </span>
          ) : (
            t("aiConfig.test")
          )}
        </button>

        {result ? (
          <div className="mt-4">
            <Alert tone={result.ok ? "success" : "danger"}>
              {result.ok
                ? t("aiConfig.testOk", {
                    provider: result.provider,
                    model: result.model,
                    input: result.input_tokens,
                    output: result.output_tokens,
                    latency: result.latency_ms,
                  })
                : t("aiConfig.testFailed", { detail: result.detail })}
            </Alert>
          </div>
        ) : null}
      </div>
    </div>
  );
}

function ProviderKeyCard({
  provider,
  value,
  saving,
  onChange,
  onSave,
  onRemove,
}: {
  provider: AIProviderState;
  value: string;
  saving: boolean;
  onChange: (value: string) => void;
  onSave: () => void;
  onRemove: () => void;
}) {
  const { t } = useI18n();
  const name: AIProviderName = provider.name;

  return (
    <div className="card p-6">
      <SectionHeading
        title={t("aiConfig.keyLabel", {
          provider: t(`aiConfig.provider.${name}` as MessageKey),
        })}
        action={
          provider.key_source === "unreadable" ? (
            <Badge tone="danger">{t("aiConfig.source.unreadable")}</Badge>
          ) : provider.key_hint ? (
            <Badge tone="success">{provider.key_hint}</Badge>
          ) : (
            <Badge tone="neutral">{t("aiConfig.source.none")}</Badge>
          )
        }
      />

      {provider.key_source === "unreadable" ? (
        <Alert tone="danger">{t("aiConfig.keyUnreadable")}</Alert>
      ) : (
        <p className="text-sm text-slatey-400">
          {provider.key_hint
            ? t("aiConfig.keyInPlace", {
                hint: provider.key_hint,
                source: t(`aiConfig.source.${provider.key_source}` as MessageKey),
              })
            : t("aiConfig.keyAbsent")}
        </p>
      )}

      <div className="mt-4 flex flex-wrap gap-2">
        <input
          type="password"
          autoComplete="off"
          className="input flex-1"
          value={value}
          placeholder={t("aiConfig.keyPlaceholder")}
          onChange={(event) => onChange(event.target.value)}
        />
        <button
          type="button"
          className="btn-primary px-4 py-2 text-sm"
          disabled={saving || !value.trim()}
          onClick={onSave}
        >
          {provider.key_hint ? t("aiConfig.replaceKey") : t("aiConfig.save")}
        </button>
        {provider.key_source === "database" ? (
          <button
            type="button"
            className="btn-secondary px-4 py-2 text-sm"
            disabled={saving}
            onClick={onRemove}
          >
            {t("aiConfig.removeKey")}
          </button>
        ) : null}
      </div>

      <p className="mt-2 text-xs text-slatey-500">{t("aiConfig.keyNeverShown")}</p>
    </div>
  );
}
