# Automatisations n8n

n8n tourne sur `http://localhost:5678` (Docker Compose) et atteint l'API sur
`http://backend:8000`.

## Workflows fournis

| Fichier | Rôle |
| --- | --- |
| `workflows/veille-financements.json` | Pipeline de veille : source → extraction → nettoyage → classification → **dépôt en file de validation** |
| `workflows/alertes-echeances.json` | Déclenchement quotidien des tâches planifiées du backend |

Importez-les depuis l'interface n8n (*Workflows → Import from file*).

## Authentification

Les deux workflows envoient l'en-tête `X-API-Key`, comparé en temps constant à
`N8N_API_KEY`. **Sans clé configurée côté backend, ces routes sont fermées** : une
automatisation ouverte par défaut serait une porte d'entrée sur la base de financements.

Dans n8n, la clé se lit depuis la variable d'environnement `FILMFUND_API_KEY` : ne la
recopiez pas en clair dans les nœuds.

## Routes exposées à l'automatisation

| Route | Rôle |
| --- | --- |
| `POST /api/v1/automation/opportunities` | Dépose des candidats en file de validation |
| `GET /api/v1/automation/tasks` | Liste fermée des tâches déclenchables |
| `POST /api/v1/automation/tasks/{nom}` | Déclenche une tâche |

Tâches disponibles : `notify_upcoming_deadlines`, `notify_incomplete_projects`,
`send_pending_notification_emails`, `reset_monthly_credits`, `expire_due_subscriptions`.
Toutes sont idempotentes : les rejouer ne produit pas de doublons.

## La règle de la veille

**Le pipeline n'écrit jamais dans la base vivante.** Il dépose des *candidats* ;
un administrateur les relit depuis `/admin/veille`, corrige ce qui doit l'être,
puis publie ou écarte. Une opportunité proposée à un auteur engage son dossier de
financement : elle ne peut pas venir d'une classification automatique non relue.

Deux garde-fous à l'entrée :

- **pas de `source_url`, pas de candidat** — un dispositif sans source vérifiable ne vaut
  rien ;
- **déduplication par empreinte de la source** — une veille hebdomadaire repasse sur les
  mêmes pages, et une file pleine de doublons ne serait jamais relue.

Un champ absent de la source reste absent : ne complétez jamais une date limite, un montant
ou une condition dans le nœud de classification. Une valeur illisible est écartée par l'API
plutôt que devinée, et la personne qui relit la source la renseigne si elle le juge utile.
