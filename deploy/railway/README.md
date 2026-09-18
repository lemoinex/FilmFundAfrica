# Déploiement sur Railway

Quatre services, tirés du même dépôt. Les trois premiers se construisent à partir des
`Dockerfile` déjà présents ; le quatrième est un module Railway.

| Service | Répertoire racine | Config | Rôle |
| --- | --- | --- | --- |
| `api` | `backend` | `deploy/railway/api.json` | API FastAPI, applique les migrations au démarrage |
| `worker` | `backend` | `deploy/railway/worker.json` | Génération des documents hors requête HTTP |
| `frontend` | `frontend` | `deploy/railway/frontend.json` | Next.js |
| `redis` | — | — | Module Redis de Railway |

`api` et `worker` partagent le même répertoire racine et la même image : ils ne diffèrent
que par leur commande de démarrage. C'est pour cela qu'ils ont deux fichiers de
configuration distincts, à désigner dans les réglages de chaque service — un unique
`railway.json` à la racine de `backend/` serait lu par les deux et ne pourrait pas les
distinguer.

## Variables d'environnement

### `api` et `worker` — les mêmes

| Variable | Valeur |
| --- | --- |
| `DATABASE_URL` | URL du pooler Supabase, **mode session, port 5432** (voir section 15 du README) |
| `REDIS_URL` | `${{Redis.REDIS_URL}}` — référence au service Redis |
| `ENVIRONMENT` | `production` |
| `DEBUG` | `false` |
| `JWT_SECRET` | `openssl rand -hex 32` — **au moins 32 caractères** |
| `CORS_ORIGINS` | le domaine public du service `frontend` |
| `FRONTEND_URL` | idem, pour les liens des e-mails |
| `TRUSTED_PROXY_IPS` | l'adresse du proxy de Railway, sinon `X-Forwarded-For` est ignoré |
| `AI_PROVIDER`, `AI_API_KEY` | le fournisseur réel, sinon les documents ne sont pas rédigés |
| `SMTP_*` | sans quoi les liens de confirmation ne partent pas et les comptes restent inactifs |
| `PAYMENT_PROVIDER` | `manual` tant qu'aucun prestataire réel n'est branché |
| `SENTRY_DSN` | facultatif ; vide, aucune requête ne part vers un tiers |

**L'application refuse de démarrer** si `JWT_SECRET` est absent, trop court ou resté à sa
valeur de développement, si `DEBUG` est actif, ou si un fournisseur d'IA est configuré sans
clé. C'est voulu : mieux vaut un déploiement qui échoue franchement qu'un déploiement en
production avec un secret de développement.

### `frontend`

| Variable | Valeur | Quand |
| --- | --- | --- |
| `NEXT_PUBLIC_API_URL` | domaine public du service `api` | **au build** |
| `NEXT_PUBLIC_SENTRY_DSN` | facultatif | **au build** |

Ces deux valeurs sont figées dans le bundle par Next.js. Les changer impose de
**reconstruire** le service : les redéfinir au démarrage n'a aucun effet.

## Ordre de mise en route

1. Créer le service `redis` (module Railway).
2. Créer `api`, lui donner ses variables, le déployer. Il applique les migrations au
   démarrage ; sur la base Supabase déjà migrée jusqu'à `0006`, c'est un no-op.
3. Créer `worker` avec les mêmes variables.
4. Créer `frontend` avec `NEXT_PUBLIC_API_URL` pointant sur le domaine de `api`.
5. Revenir sur `api` et `worker` pour renseigner `CORS_ORIGINS` et `FRONTEND_URL` avec le
   domaine de `frontend`, puis redéployer les deux.

L'aller-retour de l'étape 5 est inévitable : chacun a besoin de l'adresse de l'autre.

## Points de vigilance

* **Migrations et répliques.** `api` applique les migrations au démarrage. Avec plusieurs
  répliques, plusieurs conteneurs les lanceraient en même temps ; Alembic pose un verrou,
  mais le plus sûr reste de garder une seule réplique le temps d'un déploiement portant une
  migration.
* **`REDIS_URL` n'est pas optionnel au-delà d'une réplique.** Sans lui, chaque réplique
  compte les appels de son côté : avec trois répliques, une limite de 10 connexions par
  minute en autorise trente. Il conditionne aussi la file de génération — sans Redis, l'API
  génère elle-même, ce qui tient la requête ouverte sur un scénario long.
* **Le worker n'a pas de sonde HTTP.** Il ne sert aucune requête : lui en attacher une le
  déclarerait malade à tort. D'où l'absence de `healthcheckPath` dans sa configuration.
* **Le stockage des fichiers est local au conteneur** (`STORAGE_URL=./storage`). Sur un
  hébergeur au système de fichiers éphémère, les exports générés disparaissent au
  redéploiement. Ils sont régénérables à la demande, donc ce n'est pas une perte de données
  — mais il faut le savoir avant de promettre un lien durable.
