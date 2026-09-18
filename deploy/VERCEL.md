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
la requête**. Ce mode existe et fonctionne — mais la requête reste alors ouverte le temps
de toute la génération.

Combien de temps, exactement ? Le découpage est déterministe : `plan_segments` répartit
les pages par acte, une page par minute, et `AI_MAX_OUTPUT_TOKENS` (8000) fixe ce qu'une
passe peut écrire — 17 pages. Chaque passe est bornée par `AI_TIMEOUT_SECONDS` (180 s).
Les nombres ci-dessous sortent de ce calcul, pas d'une estimation :

| Document | Passes | Pire cas |
| --- | --- | --- |
| Logline, synopsis, notes, pitch, bible | 1 | 180 s |
| Scénario jusqu'à 17 min | 1 | 180 s |
| Scénario 26 ou 30 min | 3 | 540 s |
| Scénario 52 min | 4 | 720 s |
| Scénario 90 min | 7 | 1 260 s — 21 min |
| Scénario 120 min | 8 | 1 440 s — 24 min |

C'est un pire cas : il suppose que chaque appel va au bout de son délai de garde. Le
plafond `maxDuration` de Vercel dépend du plan, et je n'ai pas pu le vérifier depuis ici —
la documentation en ligne n'est pas joignable dans cet environnement. Ses propres exemples
vont jusqu'à `1800`, ce qui logerait un long métrage ; **à confirmer sur le plan retenu
avant de s'y fier.**

Mais le plafond n'est pas le seul argument, ni le meilleur. Tenir une requête HTTP ouverte
vingt minutes est fragile quel qu'en soit le plafond : une coupure réseau, un onglet fermé,
un redéploiement, et le travail est perdu sans reprise possible — le client n'a aucun moyen
de suivre l'avancement ni de récupérer les passes déjà écrites. La file existe pour ça.

Le scénario long est l'argument principal du produit. Trois façons de s'en sortir :

1. **Tout sur Vercel, en assumant la génération pendant la requête.** Il faut alors relever
   `maxDuration` pour l'API et vérifier que le plan le permet. Tient pour une démonstration
   ou les documents courts ; sur un long métrage, l'utilisateur attend sans filet.
2. **Frontend et API sur Vercel, worker et Redis ailleurs** (voir `deploy/railway/`). Les
   deux partagent `DATABASE_URL` et `REDIS_URL` ; l'API dépose la tâche, le worker
   l'exécute, et la requête HTTP ne reste pas ouverte. C'est le découpage pour lequel
   l'application a été écrite.
3. **Tout sur Railway.** Un seul hébergeur, un seul endroit où regarder quand ça casse.

L'option 2 tire le meilleur des deux : le frontend profite du réseau de Vercel, et la
génération longue reste possible.
