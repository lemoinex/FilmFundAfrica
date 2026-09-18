# FilmFund Africa

**De l'idée au financement de votre projet audiovisuel.**

Plateforme SaaS destinée aux réalisateurs, scénaristes, producteurs et professionnels de
l'audiovisuel, avec une priorité donnée à l'Afrique francophone. Elle permet de structurer un
projet, de générer les documents professionnels du dossier, d'en suivre la maturité et de
l'exporter dans un format exploitable par un comité de lecture.

> **État du dépôt : Phases 1, 2 et 3 livrées et exécutables** (fondations, authentification,
> projets, AI Writer, versioning, export, Funding Intelligence). Les phases 4 à 6 (budget,
> monétisation, automatisation n8n) disposent de leur schéma de base de données et de leurs
> points d'extension, mais pas encore de leur logique métier. Voir
> [`docs/ETAT_DU_PROJET.md`](docs/ETAT_DU_PROJET.md) pour le détail, poste par poste.

---

## Sommaire

1. [Architecture](#1-architecture)
2. [Installation](#2-installation)
3. [Configuration](#3-configuration)
4. [Variables d'environnement](#4-variables-denvironnement)
5. [Lancement avec Docker](#5-lancement-avec-docker)
6. [Lancement du backend](#6-lancement-du-backend)
7. [Lancement du frontend](#7-lancement-du-frontend)
8. [Migrations de base de données](#8-migrations-de-base-de-données)
9. [Données de démonstration](#9-données-de-démonstration)
10. [Configuration de l'IA](#10-configuration-de-lia)
11. [Configuration de n8n](#11-configuration-de-n8n)
12. [Langue de l'interface](#12-langue-de-linterface)
13. [Observabilité](#13-observabilité)
14. [Tests](#14-tests)
15. [Déploiement](#15-déploiement)
16. [Règles produit non négociables](#16-règles-produit-non-négociables)

---

## 1. Architecture

```text
                    FILMFUND AFRICA
                           │
             ┌─────────────┴─────────────┐
             │                           │
         FRONTEND                       API
      Next.js 14 / TS               FastAPI / Python
             │                           │
             └─────────────┬─────────────┘
                           │
                       PostgreSQL
                           │
          ┌────────────────┼────────────────┐
          │                │                │
      AI Service       Funding DB         Users
          │                │
   Anthropic / OpenAI     n8n
   / Mock                  │
          └────────────┬───┘
                       │
                 Notifications
```

```text
filmfund-africa/
├── backend/            API FastAPI, modèles, services, prompts versionnés
│   ├── app/
│   │   ├── api/v1/     Routes HTTP
│   │   ├── core/       Configuration, sécurité, base de données, erreurs, logs
│   │   ├── models/     Tables SQLAlchemy (22 tables)
│   │   ├── prompts/    Prompts versionnés, un module par document
│   │   ├── repositories/  Requêtes SQL isolées
│   │   ├── schemas/    Contrats d'entrée/sortie Pydantic
│   │   ├── services/   Logique métier + couche d'abstraction IA
│   │   └── workers/    Worker de génération + tâches planifiées (n8n)
│   ├── alembic/        Migrations
│   ├── scripts/seed.py Données de démonstration
│   └── tests/          230 tests (pytest)
├── frontend/           Next.js 14 (App Router), TypeScript, Tailwind
├── database/           Initialisation PostgreSQL
├── docs/               État du projet, décisions d'architecture
├── n8n/                Workflows d'automatisation
├── prompts/            → voir backend/app/prompts
├── .github/workflows/  Intégration continue (lint, tests, migrations, e2e)
├── docker-compose.yml
├── .env.example
└── LICENSE
```

**Séparation des responsabilités du backend** : une route ne contient jamais de SQL ni de
prompt. Elle valide, délègue à un service, qui passe par un repository pour la base et par
`AIService` pour l'IA.

---

## 2. Installation

Prérequis : **Docker + Docker Compose** (voie recommandée), ou **Python 3.11+**, **Node.js 20+**
et **PostgreSQL 14+** pour une installation manuelle.

```bash
git clone https://github.com/lemoinex/FilmFundAfrica.git
cd FilmFundAfrica
cp .env.example .env
```

Éditez ensuite `.env` (voir section 4). Au minimum, changez `JWT_SECRET` et
`POSTGRES_PASSWORD`.

---

## 3. Configuration

Générez un secret JWT solide :

```bash
openssl rand -hex 32
```

L'application démarre sans clé d'IA : `AI_PROVIDER=mock` produit des documents structurés à
partir de vos seules saisies, sans appel réseau. C'est le mode par défaut, utile pour tester
l'application de bout en bout et faire tourner la suite de tests.

---

## 4. Variables d'environnement

Toutes les variables sont documentées dans [`.env.example`](.env.example). Les principales :

| Variable | Rôle | Défaut |
| --- | --- | --- |
| `DATABASE_URL` | Connexion PostgreSQL (compatible Supabase / Neon) | local Docker |
| `JWT_SECRET` | Signature des jetons — **obligatoire en production** (≥ 32 caractères) | — |
| `ACCESS_TOKEN_EXPIRE_MINUTES` | Durée du jeton d'accès | `60` |
| `EMAIL_VERIFICATION_EXPIRE_MINUTES` | Durée du lien de confirmation d'adresse | `1440` |
| `PAYMENT_PROVIDER` | `manual` (encaissement hors ligne) ou `mock` (simulé, développement) | `manual` |
| `PAYMENT_WEBHOOK_SECRET` | Secret signant les notifications du prestataire | vide |
| `AI_PROVIDER` | `anthropic`, `openai` ou `mock` | `mock` |
| `AI_API_KEY` | Clé du fournisseur choisi | vide |
| `AI_MODEL` | Modèle utilisé | `claude-sonnet-4-5` |
| `AI_MAX_OUTPUT_TOKENS` | Plafond de sortie par appel — pilote la taille d'une passe | `8000` |
| `SCREENPLAY_MAX_PASSES` | Plafond de sécurité du nombre de passes d'un scénario | `40` |
| `AI_CREDITS_FREE/PRO/PRODUCER` | Quotas mensuels par offre | `1` / `300` / `500` |
| `RATE_LIMIT_AUTH_PER_MINUTE` | Limitation sur les routes d'authentification | `10` |
| `REDIS_URL` | Compteurs de limitation partagés entre répliques ; vide = compteurs en mémoire | vide |
| `REDIS_TIMEOUT_SECONDS` | Délai au-delà duquel l'appel à Redis est abandonné | `0.25` |
| `JOB_TIMEOUT_SECONDS` | Durée **sans signe de vie** au-delà de laquelle une génération est déclarée interrompue | `900` |
| `JOB_STALE_SECONDS` | Âge à partir duquel une tâche en attente est reprise par le balayage | `60` |
| `TRUSTED_PROXY_IPS` | Proxys autorisés à définir `X-Forwarded-For` ; vide = en-tête ignoré | vide |
| `SMTP_*` | Envoi des e-mails ; si vide, les messages sont journalisés | vide |
| `N8N_WEBHOOK_URL` | Point d'entrée des automatisations | — |
| `N8N_API_KEY` | Clé de l'automatisation (veille, tâches planifiées) ; vide = routes fermées | vide |
| `SENTRY_DSN` | Suivi des erreurs du backend et du worker ; vide = aucun envoi vers un tiers | vide |
| `SENTRY_TRACES_SAMPLE_RATE` | Part des requêtes tracées pour la performance | `0` |
| `DEFAULT_LOCALE` | Langue servie à qui n'a pas encore choisi (`fr` ou `en`) | `fr` |
| `NEXT_PUBLIC_API_URL` | URL de l'API vue par le navigateur | `http://localhost:8000` |
| `NEXT_PUBLIC_SENTRY_DSN` | Suivi des erreurs du navigateur, **lu au build** ; vide = greffon non chargé | vide |

**Aucune clé API réelle ne doit être commitée.** `.env` est ignoré par git.

---

## 5. Lancement avec Docker

```bash
docker compose up --build
```

| Service | URL |
| --- | --- |
| Frontend | http://localhost:3000 |
| API | http://localhost:8000 |
| Documentation OpenAPI | http://localhost:8000/docs |
| n8n | http://localhost:5678 |
| PostgreSQL | `localhost:5432` |

Le service `backend` applique les migrations Alembic au démarrage.

Pour créer les données de démonstration :

```bash
docker compose exec backend python -m scripts.seed
```

---

## 6. Lancement du backend

```bash
cd backend
python -m venv .venv && source .venv/bin/activate   # Windows : .venv\Scripts\activate
pip install -r requirements-dev.txt
cp ../.env.example .env        # puis ajustez DATABASE_URL
alembic upgrade head
uvicorn app.main:app --reload
```

Avec `REDIS_URL`, lancez le worker de génération dans un second terminal :

```bash
python -m app.workers.runner
```

Sans lui, l'API exécute les générations elle-même : c'est fonctionnel, mais un scénario long
tient alors la requête HTTP ouverte plusieurs minutes. `GET /health` indique lequel des deux
modes est actif (`"generation": "worker"` ou `"inline-no-worker"`).

L'API écoute sur `http://localhost:8000`. La documentation OpenAPI est générée
automatiquement sur `/docs` (Swagger) et `/redoc`.

Pour un essai sans PostgreSQL, `DATABASE_URL=sqlite:///./dev.db` fonctionne (usage local
uniquement).

---

## 7. Lancement du frontend

```bash
cd frontend
npm install
npm run dev
```

Interface sur `http://localhost:3000`. `NEXT_PUBLIC_API_URL` doit pointer vers l'API.

Commandes utiles : `npm run build`, `npm run typecheck`, `npm run lint`.

---

## 8. Migrations de base de données

```bash
cd backend
alembic upgrade head                                   # appliquer
alembic revision --autogenerate -m "description"       # créer après modification des modèles
alembic downgrade -1                                   # revenir d'une version
```

Les modèles SQLAlchemy sont la source de vérité du schéma ; Alembic en dérive les migrations.

---

## 9. Données de démonstration

```bash
cd backend
python -m scripts.seed           # crée les données si absentes
python -m scripts.seed --reset   # les supprime puis les recrée
```

| Compte | Identifiants | Offre |
| --- | --- | --- |
| Auteur | `auteur.demo@example.com` / `Demo2026!` | Pro Auteur |
| Producteur | `producteur.demo@example.com` / `Demo2026!` | Producteur |
| Admin | `admin.demo@example.com` / `Demo2026!` | Producteur |

### Créer un compte administrateur

L'espace d'administration (`/admin/financements`) est réservé au rôle `ADMIN`. Pour créer un
administrateur réel — ou promouvoir un compte existant :

```bash
cd backend
python -m scripts.create_admin --email vous@exemple.com            # création
python -m scripts.create_admin --email vous@exemple.com --promote  # promotion, mot de passe inchangé

# Avec Docker :
docker compose exec backend python -m scripts.create_admin --email vous@exemple.com
```

Le mot de passe est demandé à la saisie, masqué et confirmé : il n'est **jamais** passé en
argument (l'historique du shell et la liste des processus le rendraient visible) ni écrit dans
un fichier. Pour un déploiement automatisé, la variable `FILMFUND_ADMIN_PASSWORD` est acceptée,
à condition de ne pas la versionner. Il doit faire au moins 8 caractères et mêler lettres et
chiffres. Changer le mot de passe d'un compte révoque ses sessions ouvertes.

Les comptes de démonstration ci-dessus sont publics : ne les utilisez jamais en production.

Le seed crée 3 projets et 3 opportunités **fictives**, marquées `is_demo=true`, au statut
`UNVERIFIED`, et portant la mention `DEMO DATA — NOT REAL` dans leur description. L'interface
les affiche avec ce marquage. Elles ne doivent jamais être présentées comme de véritables
dispositifs de financement.

---

## 10. Configuration de l'IA

Le code métier n'appelle jamais un fournisseur directement :

```text
AIService
   └── AIProvider
        ├── AnthropicProvider   (API Messages)
        ├── OpenAIProvider      (Chat Completions)
        └── MockProvider        (déterministe, hors ligne)
```

Pour activer une génération réelle :

```bash
AI_PROVIDER=anthropic
AI_API_KEY=sk-...
AI_MODEL=claude-sonnet-4-5
```

**Prompts versionnés** — un module par document dans `backend/app/prompts/`, chacun portant un
numéro de version enregistré dans `document_versions` et `ai_usage`. Aucun prompt n'est écrit
dans une route API. Chaque prompt reçoit le contexte structuré du projet **et** les documents
dont il dépend : la note de réalisation voit la note d'intention et le synopsis, le scénario
voit le traitement.

**Scénarios longs** — un long métrage de 110 pages représente environ 21 000 mots, bien au-delà
de ce qu'un appel unique produit. `screenplay_service.py` découpe donc l'écriture en passes
successives suivant la structure en trois actes, chaque passe recevant la fin de la précédente
pour la continuité (personnages, lieux, numérotation des séquences). Chaque passe consomme un
crédit, et l'interface annonce le coût avant de lancer la génération.

La durée réalisable dépend de `AI_MAX_OUTPUT_TOKENS` : avec la valeur par défaut (8000), un
scénario va jusqu'à **138 minutes**. Au-delà, l'API refuse explicitement plutôt que de renvoyer
un scénario tronqué, et l'interface n'offre que les durées réellement productibles — elle
interroge `GET /api/v1/documents/screenplay-capacity` au lieu de dupliquer la règle.

---

## Funding Intelligence

**Score de compatibilité déterministe.** Le rapprochement projet / dispositif est calculé par
des règles, pas par l'IA : il est donc reproductible, explicable ligne à ligne, instantané et
**gratuit**. Sept critères pondérés, pour 100 points au total : pays éligible (25, bloquant),
type de projet (20, bloquant), genre (12), langue (8), format et durée (10), échéance (10,
bloquante si dépassée), documents exigés (15, à crédit partiel).

**Une information absente n'est jamais interprétée.** Un critère que les données du projet ne
permettent pas d'évaluer est marqué « à vérifier », retiré du dénominateur, et n'est compté ni
pour ni contre le projet. En contrepartie, la réponse expose `assessed_ratio` : la part de la
grille réellement évaluée. Un projet sans pays ni genre ni durée obtient donc « score calculé
sur 53 % de la grille », et non un score flatteur bâti sur des suppositions.

**Un critère bloquant non rempli rend la candidature inéligible**, mais le dispositif reste
affiché avec la raison, plutôt que d'être masqué silencieusement.

**L'IA n'intervient que sur demande.** Le bouton « Analyser avec l'IA » rédige l'explication
détaillée du rapprochement et consomme 1 crédit ; une explication déjà produite est réaffichée
sans nouveau débit. L'IA ne recalcule jamais le score et ne peut inventer aucune condition
d'éligibilité : elle ne reçoit que les faits présents en base.

**Traçabilité.** Un dispositif ne peut pas être créé sans `source_name` et `source_url`, ni
publié comme ouvert sans URL source. Chaque vérification humaine horodate `last_verified_at`,
affiché à l'utilisateur sous chaque opportunité.

**Alimentation de la base.** La saisie se fait depuis l'espace d'administration
(`/admin/financements`, réservé au rôle `ADMIN`) ou par l'API. Le pipeline de veille automatisée
reste à construire en Phase 6 ; son squelette n8n est dans `n8n/workflows/`.

---

## 10 bis. Crédits IA

**Crédits IA** — l'usage n'est jamais illimité. Les quotas, les prix et les fonctionnalités
incluses (dont l'export) sont stockés en base et modifiables depuis l'administration
(`PUT /api/v1/admin/plans/{code}`), jamais codés en dur.

---

## 11. Configuration de n8n

n8n est démarré par Docker Compose sur `http://localhost:5678` et atteint l'API sur
`http://backend:8000`. Les workflows d'exemple sont dans `n8n/workflows/`.

Les tâches planifiées exposées par le backend (`backend/app/workers/tasks.py`) sont
idempotentes et appelables en ligne de commande ou depuis n8n :

```bash
python -c "from app.workers.tasks import notify_upcoming_deadlines; print(notify_upcoming_deadlines())"
python -c "from app.workers.tasks import reset_monthly_credits; print(reset_monthly_credits())"
```

---

## 12. Langue de l'interface

L'interface est disponible en **français** et en **anglais**. Le sélecteur figure dans
l'en-tête de l'application, sur les pages d'authentification, sur la page publique, et
dans le profil.

**L'API répond dans la même langue.** Le frontend envoie la langue choisie en
`Accept-Language` à chaque appel, et le backend s'en sert pour ses messages d'erreur, ses
messages de succès et les libellés qu'il calcule (critères de compatibilité, critères de
maturité). Le `code` d'erreur, lui, ne change jamais : c'est sur lui que le client se
branche, pas sur la phrase.

La langue affichée est déterminée dans cet ordre :

1. la préférence enregistrée sur le profil (`preferred_locale`), qui suit le compte d'un
   appareil à l'autre — elle est posée **à l'inscription** d'après la langue alors utilisée,
   et non laissée sur la valeur par défaut de la colonne ;
2. le cookie `filmfund_locale`, propre au navigateur — c'est lui que lit le rendu serveur,
   pour que `<html lang>` soit juste dès le premier octet envoyé ; c'est aussi lui que le
   client HTTP envoie en `Accept-Language` ;
3. `Accept-Language` du navigateur, côté API, pour un appelant sans session ;
4. `DEFAULT_LOCALE`, à défaut.

### Ajouter une langue

Les catalogues sont dans `frontend/src/lib/i18n/` : `fr.ts` est la langue de référence et
définit les clés, `en.ts` est typé `Record<MessageKey, string>` d'après elle. **Une clé
ajoutée au français et oubliée ailleurs fait échouer `tsc`** — c'est la seule garantie qui
tienne dans la durée, une traduction manquante ne se voyant pas à la relecture.

Pour une troisième langue : ajouter `xx.ts` sur le modèle de `en.ts`, puis l'inscrire dans
`LOCALES`, `LOCALE_NAMES` (`locale.ts`) et `CATALOGS` (`index.tsx` et `translate.ts`).
Les accords et les formats de date, de nombre et de durée relative viennent d'`Intl` :
rien à traduire de ce côté.

Côté API, les catalogues sont dans `backend/app/core/i18n.py`, sur le même principe : le
français définit les clés. Python n'offrant pas la garantie du compilateur, c'est
`tests/test_i18n.py` qui la remplace — il compare les jeux de clés, vérifie que les
variables `{ainsi}` sont les mêmes des deux côtés, et **relit le code source pour vérifier
que toute clé citée existe**. Une clé mal orthographiée fait échouer les tests en nommant
son fichier.

### Ce qui reste en français, quelle que soit la langue choisie

* Les **documents générés** par l'AI Writer, ainsi que la structure annoncée par
  `GET /documents/types` : leur langue est celle des prompts, pas celle de l'interface.
* Les **messages de validation par champ** (`errors[].message` d'une réponse 422) : ils
  viennent de Pydantic et sont en anglais. Les retraduire supposerait de rejouer sa logique
  de validation.
* Les **noms des offres** et des dispositifs de financement, qui sont des données saisies,
  pas des libellés d'interface.

---

## 13. Observabilité

Sans `SENTRY_DSN`, rien n'est initialisé : l'application tourne exactement comme avant et
aucune requête ne part vers un tiers. C'est le même principe que `AI_PROVIDER=mock` ou
`PAYMENT_PROVIDER=manual` — l'installation par défaut ne dépend d'aucun service externe.

Avec un DSN, les exceptions de l'API **et du worker** sont remontées. `GET /health` publie
l'état sous `error_tracking` : `disabled`, `active`, ou `unavailable` quand un DSN est
configuré mais que le paquet `sentry-sdk` manque — un déploiement qui se croit suivi sans
l'être ne doit pas rester silencieux.

### Ce qui ne part jamais

Un rapport d'erreur part chez un tiers : il ne peut pas emporter ce que les gens nous ont
confié. `backend/app/core/observability.py` expurge, avant tout envoi :

* les **identifiants** — en-têtes `Authorization`, cookies, signatures de webhook, mots de
  passe, jetons de réinitialisation ou de confirmation traînant dans une URL ;
* les **données personnelles** — adresses e-mail, numéros de téléphone ;
* le **contenu des dossiers** — synopsis, scénarios, budgets : c'est le travail des
  auteurs.

Trois réglages ferment ce que l'expurgation par nom de clé ne peut pas reconnaître :
`send_default_pii=False`, `max_request_body_size="never"` et `include_local_variables=False`
— cette dernière parce que les variables locales portent les prompts et les segments de
scénario sous les noms de variables du code, qu'aucune liste ne peut énumérer. On perd en
confort de diagnostic ce qu'on gagne à ne pas exfiltrer le travail des auteurs.

Le navigateur suit la même règle (`frontend/src/lib/observability.ts`), avec un risque en
plus : les fils d'Ariane de navigation portent l'URL complète, donc les jetons de
`/verifier-email?token=…`. Ils sont expurgés au même titre. L'enrobage Sentry n'est
appliqué au build que si `NEXT_PUBLIC_SENTRY_DSN` est défini : sans DSN, le bundle est
identique à ce qu'il était (≈ 87 kB de JS partagé, contre ≈ 136 kB avec).

L'identifiant de requête (`X-Request-ID`) est posé en étiquette sur chaque événement :
une erreur remontée se relie aux journaux JSON sans avoir à joindre son contenu.

---

## 14. Tests

```bash
cd frontend
npm run typecheck
npm run build
npm run test:e2e           # 16 parcours de bout en bout (Playwright)
```

### Intégration continue

`.github/workflows/ci.yml` rejoue ces contrôles sur chaque pull request et sur `main` :

| Job | Contenu |
| --- | --- |
| `backend` | `ruff`, `pytest` (avec un service Redis, qui active le test d'intégration de la limitation de débit), migrations appliquées **sur PostgreSQL**, et `alembic check` |
| `frontend` | `tsc --noEmit`, `next lint`, build de production |
| `e2e` | Playwright sur Chromium, après le succès des deux autres |

Le point le moins évident est le plus utile : les tests tournent sur SQLite, mais la
production vise PostgreSQL. Les migrations sont donc appliquées sur leur vraie cible, et
`alembic check` échoue si un modèle a changé sans migration — une dérive qui se découvrirait
sinon au déploiement, sur la base réelle.

Les tests de bout en bout démarrent eux-mêmes une API jetable (SQLite neuve,
`AI_PROVIDER=mock`) et le frontend : il n'y a rien à lancer avant. Ils supposent seulement
que les dépendances Python du backend sont installées ; `E2E_PYTHON` permet de désigner
l'interpréteur à utiliser (`E2E_PYTHON=backend/.venv/bin/python npm run test:e2e`). Le
navigateur s'installe une fois avec `npx playwright install chromium`, ou `PLAYWRIGHT_CHROMIUM_PATH`
pointe un binaire déjà présent.

```bash
cd backend
pytest                    # 230 tests
ruff check .              # lint
```

Couverture, côté API : inscription en deux temps et **non-énumération des comptes à l'inscription**,
connexion, rafraîchissement et réinitialisation de mot de passe,
**révocation des sessions au changement de mot de passe**, non-énumération à la connexion,
refus de démarrage avec une configuration de production non sécurisée, **non-contournement de
la limitation de débit par `X-Forwarded-For`**, CRUD projets, **isolation stricte des données
entre utilisateurs**, quotas de projets et de crédits, **export réservé aux offres qui
l'incluent**, génération IA, cohérence inter-documents, découpage des scénarios longs,
versioning et restauration, **continuité entre les passes d'un scénario long**,
exports PDF/DOCX/ZIP/XLSX, **budget et plan de financement** (trame par type de projet,
totaux recalculés, couverture acquise contre espérée), contrôle d'accès administrateur,
**limitation de débit partagée entre répliques**, **génération asynchrone** (réserve des
crédits, remboursement en cas d'échec, avancement par passe, reprise des tâches perdues).

Couverture, côté navigateur : inscription → confirmation d'adresse → connexion, non-énumération
visible à l'écran, création de projet, génération d'un document et ouverture dans l'éditeur,
limites d'offre (projets, crédits, export), installation de la trame de budget, chiffrage d'un
poste et couverture du plan de financement.

---

## 15. Déploiement

### Base de données : Supabase

Supabase ne sert ici que de **PostgreSQL géré**. Ni le SDK, ni Supabase Auth, ni l'API REST
ne sont utilisés : le backend parle PostgreSQL directement, et l'authentification comme
l'isolation des données sont faites par l'API. Brancher une autre instance PostgreSQL ne
demanderait que de changer `DATABASE_URL`.

```bash
# Connexion applicative — mode « session pooler », port 5432
DATABASE_URL="postgresql://postgres.<ref>:<mot-de-passe>@<hôte-pooler>:5432/postgres"
```

Trois pièges, dans l'ordre où on les rencontre :

1. **L'hôte direct `db.<ref>.supabase.co` ne répond qu'en IPv6.** Un serveur ou un
   conteneur sans IPv6 n'a aucune route vers lui : le pooler, lui, a une adresse IPv4.
   Son nom d'hôte exact figure dans le tableau de bord, bouton *Connect*.
2. **Prenez le pooler en mode « session » (5432), pas « transaction » (6543).** psycopg
   utilise des requêtes préparées, que le mode transaction ne gère pas — il faudrait
   ajouter `?prepare_threshold=0`. Surtout, Alembic pose des verrous de session pendant une
   migration : les faire passer par le mode transaction expose à des migrations à moitié
   appliquées.
3. **Encodez les caractères spéciaux du mot de passe.** Dans une URL, `@` s'écrit `%40`,
   `#` s'écrit `%23`, `/` s'écrit `%2F`. Un mot de passe contenant un `@` non encodé coupe
   l'URL en deux et produit une erreur d'hôte introuvable, pas une erreur de mot de passe —
   l'origine du problème est alors peu lisible.

Le préfixe `postgresql://` est accepté tel quel : la configuration le convertit en
`postgresql+psycopg://`.

Ensuite :

```bash
alembic upgrade head     # applique ce qui manque, ne rejoue rien
```

Les **offres d'abonnement se créent d'elles-mêmes** au premier besoin
(`CreditService.ensure_plans`) : une base neuve n'a aucune donnée de référence à charger à
la main. `python -m scripts.seed` n'est utile que pour un jeu de démonstration.

> **L'API REST de Supabase expose le schéma `public`.** Elle n'est d'aucune utilité pour
> cette application, et tant qu'elle est ouverte sans RLS, la clé `anon` — publique par
> nature — donne accès en lecture et en écriture à toutes les tables, `users` et
> `payments` compris. Retirez `public` des schémas exposés (*Project Settings → API*), ou
> activez RLS sans politique sur chaque table : le rôle `postgres`, qu'utilise le backend,
> n'y est pas soumis.

### Hébergement

Quatre services : l'API, le worker de génération, le frontend et Redis. **Vercel ne
convient qu'au frontend** — l'API et le worker sont des processus longs, pas des fonctions.

Une configuration prête pour Railway est fournie dans
[`deploy/railway/`](deploy/railway/README.md) : un fichier par service, les variables
d'environnement à renseigner, l'ordre de mise en route et les pièges (migrations avec
plusieurs répliques, variables `NEXT_PUBLIC_*` figées au build, stockage éphémère).

L'application est conçue pour un hébergement conteneurisé :

1. Provisionner PostgreSQL (Supabase, Neon ou instance gérée) et renseigner `DATABASE_URL`.
2. Définir `ENVIRONMENT=production`, `DEBUG=false`, un `JWT_SECRET` fort et `CORS_ORIGINS`
   avec le domaine réel du frontend. **L'application refuse de démarrer** si le secret est
   absent, trop court ou resté à sa valeur de développement, si `DEBUG` est actif, ou si un
   fournisseur d'IA est configuré sans clé.
3. Construire et publier les images `backend/` et `frontend/`.
4. Appliquer les migrations : `alembic upgrade head`.
5. Servir le frontend derrière HTTPS, avec `NEXT_PUBLIC_API_URL` pointant sur l'API publique.

Derrière un proxy inverse, renseignez `TRUSTED_PROXY_IPS` avec son adresse : sans cela
l'en-tête `X-Forwarded-For` est ignoré (et la limitation de débit s'applique à l'IP du proxy).

**Avec plusieurs répliques, renseignez `REDIS_URL`.** Sans lui, chaque réplique compte les
appels de son côté : avec trois répliques, `RATE_LIMIT_AUTH_PER_MINUTE=10` autorise en
réalité trente tentatives de connexion par minute. Avec lui, la limite vaut pour le
déploiement entier. Si Redis devient injoignable, l'API continue de répondre en comptant en
mémoire (limite dégradée, jamais d'indisponibilité) et `GET /health` renvoie
`"rate_limit": "redis-unreachable"` avec un statut `degraded` — à surveiller.

**Configurez SMTP.** L'activation d'un compte passe par un lien envoyé par e-mail : sans
`SMTP_HOST`, le message est seulement journalisé et personne ne peut activer son compte. Seul
l'environnement `development` fait exception — l'API y renvoie le jeton dans sa réponse, ce
qu'elle ne fait jamais ailleurs.

**Déployez le worker de génération** (`python -m app.workers.runner`) à côté de l'API : c'est
lui qui écrit les documents. Sans worker, l'API s'en charge, et un scénario long tient la
requête ouverte jusqu'à l'expiration du proxy. Le worker est sans état : plusieurs instances
peuvent tourner en parallèle, chaque tâche n'étant exécutée que par une seule d'entre elles.

**À faire avant une mise en production réelle** : brancher Sentry et un stockage d'objets si
les utilisateurs téléversent des fichiers.

---

## 16. Règles produit non négociables

Ces règles sont implémentées, testées, et ne doivent pas être contournées :

- **L'IA n'invente rien.** Ni personnage, ni événement, ni lieu réel, ni financement, ni
  condition de candidature. Une information absente produit « Information non fournie. » et
  apparaît dans la section « Informations à compléter » du document.
- **Aucune opportunité n'est présentée comme active sans sa source** (`source_url`,
  `source_name`) et sa date de dernière vérification (`last_verified_at`). L'API refuse la
  création d'un dispositif sans source, et sa publication comme ouvert sans URL source.
- **Le score de compatibilité ne devine rien.** Un critère non évaluable est signalé comme tel
  et retiré du calcul ; il n'est jamais remplacé par une hypothèse.
- **Le score de compatibilité est un indicateur d'aide à la décision**, jamais une garantie de
  financement. Le score de maturité mesure l'avancement du dossier, pas sa qualité artistique.
- **Les données de démonstration sont marquées comme telles** et ne sont jamais présentées
  comme réelles.
- **Un utilisateur n'accède jamais aux projets d'un autre.** L'API renvoie 404 (et non 403) pour
  ne pas divulguer l'existence d'une ressource.
- **Changer ou réinitialiser son mot de passe révoque toutes les sessions ouvertes**, jetons de
  rafraîchissement compris : la réinitialisation remédie réellement à un compte compromis.
- **Le jeton de réinitialisation n'est jamais renvoyé par l'API** en dehors de l'environnement
  `development`.
- **Aucun secret dans le dépôt.** Toutes les clés passent par des variables d'environnement, et
  la configuration de production est validée au démarrage.

---

## Licence

MIT — voir [LICENSE](LICENSE).
