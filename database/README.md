# Base de données

PostgreSQL 16. Le schéma est défini par les modèles SQLAlchemy de
`backend/app/models/` ; Alembic en dérive les migrations.

## Tables (21)

| Domaine | Tables |
| --- | --- |
| Utilisateurs | `users`, `profiles`, `password_reset_tokens` |
| Projets | `projects`, `characters` |
| Documents | `documents`, `document_versions` |
| Financements | `funding_opportunities`, `funding_requirements`, `project_funding_matches` |
| Budget | `budgets`, `budget_items`, `funding_plans`, `funding_plan_lines`, `production_schedules` |
| Facturation | `subscription_plans`, `subscriptions`, `ai_usage` |
| Système | `notifications`, `audit_logs`, `app_settings` |

Les tables des phases 3 à 5 sont créées dès la première migration : leur logique métier
viendra s'y brancher sans migration structurante.

## Règles

- Chaque projet est rattaché à un `user_id` ; toutes les requêtes du domaine filtrent dessus.
- `documents` porte une contrainte d'unicité `(project_id, document_type)` : un document par
  type et par projet, son historique vivant dans `document_versions`.
- `funding_opportunities` conserve `source_url`, `source_name` et `last_verified_at`. Une
  opportunité sans ces informations ne doit jamais être présentée comme active.
- `is_demo = true` marque les données de démonstration, qui ne doivent jamais être présentées
  comme réelles.

## Commandes

```bash
cd backend
alembic upgrade head
alembic revision --autogenerate -m "description"
python -m scripts.seed
```
