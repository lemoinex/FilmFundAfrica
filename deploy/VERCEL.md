# Déploiement sur Vercel

`vercel.json`, à la racine, déclare les deux services et le routage. Il est requis par
Vercel pour un projet à plusieurs services.

## Routage

| Chemin | Service |
| --- | --- |
| `/api/*` | `backend` — toutes les routes de l'API sont sous `/api/v1` |
| `/health`, `/docs`, `/redoc`, `/openapi.json` | `backend` |
| tout le reste | `frontend` |

L'ordre compte : la règle attrape-tout arrive en dernier. `/` va donc au frontend — la page
d'accueil publique — et non à la route d'information de l'API, qui devient inaccessible de
l'extérieur. C'est sans conséquence : elle ne sert qu'au diagnostic, et `/health` la
remplace.

`/docs` expose Swagger publiquement, ce qui est déjà le comportement de l'application
partout ailleurs. Pour le fermer, retirez les trois lignes correspondantes de `vercel.json`
et l'API ne sera plus atteignable que sous `/api`.

## Variables d'environnement

Backend et frontend étant servis par le **même domaine**, il n'y a pas de requête
inter-origines : le frontend appelle l'API sur son propre domaine, et CORS ne se pose plus.

| Service | Variable | Valeur |
| --- | --- | --- |
| `frontend` | `NEXT_PUBLIC_API_URL` | le domaine public du projet — **lu au build** |
| `backend` | `DATABASE_URL` | pooler Supabase, mode session, port 5432 |
| `backend` | `ENVIRONMENT` | `production` |
| `backend` | `DEBUG` | `false` |
| `backend` | `JWT_SECRET` | `openssl rand -hex 32`, au moins 32 caractères |
| `backend` | `CORS_ORIGINS` | le même domaine, par sécurité |
| `backend` | `FRONTEND_URL` | idem, pour les liens des e-mails |
| `backend` | `AI_PROVIDER`, `AI_API_KEY` | sinon les documents ne sont pas rédigés |
| `backend` | `SMTP_*` | sinon aucun compte ne peut être activé |

## La limite à connaître avant de s'engager

**Vercel n'héberge pas le worker.** C'est un processus long qui ne sert aucune requête
HTTP ; rien dans le modèle de Vercel ne lui correspond. Sans lui et sans `REDIS_URL`,
l'application bascule sur son mode de repli documenté : **l'API génère elle-même, pendant
la requête**. Ce mode existe et fonctionne — mais il est alors borné par `maxDuration`.

Conséquence concrète, par type de document :

| Document | Passes | Tient dans une requête ? |
| --- | --- | --- |
| Logline, synopsis, notes, pitch, bible | 1 | oui |
| Scénario court (10 à 30 min) | 1 à 3 | oui |
| Scénario long (90 à 120 min) | 8 à 12, jusqu'à 180 s chacune | **non** — dépasse le plafond |

Le scénario long est l'argument principal du produit. Trois façons de s'en sortir :

1. **Tout sur Vercel, sans scénario long.** Acceptable pour une mise en ligne rapide ou une
   démonstration, pas pour la promesse commerciale.
2. **Frontend et API sur Vercel, worker et Redis ailleurs** (voir `deploy/railway/`). Les
   deux partagent `DATABASE_URL` et `REDIS_URL` ; l'API dépose la tâche, le worker
   l'exécute, et la requête HTTP ne reste pas ouverte. C'est le découpage pour lequel
   l'application a été écrite.
3. **Tout sur Railway.** Un seul hébergeur, un seul endroit où regarder quand ça casse.

L'option 2 tire le meilleur des deux : le frontend profite du réseau de Vercel, et la
génération longue reste possible.
