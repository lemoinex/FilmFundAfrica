# Automatisations n8n

n8n tourne sur `http://localhost:5678` (Docker Compose) et atteint l'API sur
`http://backend:8000`.

## Workflows fournis

| Fichier | Rôle |
| --- | --- |
| `workflows/veille-financements.json` | Squelette du pipeline de veille (Phase 6) : source → extraction → nettoyage → classification → validation humaine → base |
| `workflows/alertes-echeances.json` | Appel quotidien des tâches de notification du backend |

Importez-les depuis l'interface n8n (*Workflows → Import from file*).

## Tâches exposées par le backend

`backend/app/workers/tasks.py` — fonctions synchrones et idempotentes :

- `notify_upcoming_deadlines(days=7)` : une notification par échéance proche sur un
  financement suivi ;
- `notify_incomplete_projects(threshold=50)` : signale les dossiers au score faible ;
- `reset_monthly_credits()` : recharge les crédits IA dont la période est écoulée.

## Règle de la veille

Le pipeline ne doit jamais écrire une opportunité sans `source_url`, `source_name` et
`last_verified_at`. Une opportunité classifiée automatiquement entre au statut `UNVERIFIED` et
demande une validation humaine avant de passer à `OPEN`.
