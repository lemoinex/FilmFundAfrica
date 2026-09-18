# État du projet — rapport de livraison

Dernière mise à jour : 18 septembre 2026 · Périmètre livré : **Phase 1 (Foundation), Phase 2
(AI Writer) et Phase 3 (Funding Intelligence)**, plus l'export qui figure parmi les
fonctionnalités indispensables du MVP.

Ce document dit ce qui fonctionne réellement, ce qui est partiel et ce qui n'est pas commencé.
Aucune fonctionnalité n'y est annoncée comme terminée si elle ne l'est pas.

---

## FEATURES IMPLEMENTED

### Fondations

- Monorepo `backend/` + `frontend/`, `docker-compose.yml` à quatre services (frontend, backend,
  postgres, n8n), `.env.example` complet, `Dockerfile` pour chaque service.
- Schéma PostgreSQL complet : **21 tables**, contraintes d'intégrité, index, migration Alembic
  initiale. Les tables des phases 3 à 5 existent déjà, pour éviter une migration structurante
  plus tard.
- Configuration centralisée et typée (`pydantic-settings`), aucun secret en dur.
- Journalisation structurée (JSON en production), identifiant de requête propagé via
  l'en-tête `X-Request-ID`, mesure de la latence de chaque requête.
- Gestion d'erreurs uniforme : chaque réponse d'erreur porte un `detail` lisible et un `code`
  exploitable par le frontend.

### Authentification et sécurité

- Inscription, connexion, déconnexion, jetons d'accès et de rafraîchissement (JWT), profil.
- Réinitialisation de mot de passe par jeton à usage unique et à durée limitée ; seul le
  SHA-256 du jeton est stocké en base.
- Mots de passe hachés avec bcrypt ; politique de robustesse à l'inscription.
- Contrôle d'accès par rôle (`AUTHOR`, `DIRECTOR`, `PRODUCER`, `INSTITUTION`, `ADMIN`) ; le
  rôle `ADMIN` ne peut pas être obtenu par inscription publique.
- **Isolation stricte des données** : un utilisateur ne peut accéder à aucune ressource d'un
  autre compte. Les réponses renvoient 404 plutôt que 403, pour ne pas divulguer l'existence
  d'une ressource. Couvert par des tests dédiés sur les projets, les documents et les exports.
- Limitation de débit sur les routes d'authentification et de génération IA, **non contournable
  par un en-tête `X-Forwarded-For` forgé** : cet en-tête n'est lu que si la connexion provient
  d'un proxy déclaré dans `TRUSTED_PROXY_IPS`. Les compteurs inactifs sont purgés.
- **Révocation des sessions** : un changement ou une réinitialisation de mot de passe invalide
  immédiatement tous les jetons émis auparavant, jetons de rafraîchissement compris.
- **Le jeton de réinitialisation n'est jamais renvoyé par l'API** hors environnement
  `development` : le renvoyer permettrait de prendre le contrôle de n'importe quel compte connu.
- Connexion à temps constant : le hachage est vérifié même pour un compte inexistant, sans quoi
  l'écart de latence révélerait les adresses inscrites. Réponses identiques en cas d'e-mail
  inconnu ou de mot de passe erroné.
- **Refus de démarrer en production** avec une configuration dangereuse : secret JWT absent,
  trop court ou resté à sa valeur de développement, `DEBUG` actif, ou fournisseur d'IA sans clé.

### Projets

- CRUD complet, recherche par titre, pagination.
- Personnages : ajout, modification, suppression, ordonnancement.
- Assistant de création en sept étapes (informations générales, concept, personnages, enjeux,
  vision, objectifs, public cible) ; seul le titre est obligatoire.
- **Project Readiness Score** : calcul déterministe sur 100 points répartis selon les neuf
  critères du cahier des charges, avec le détail par critère et la liste des actions à mener.
  Recalculé à chaque modification du projet ou de ses documents.
- Quotas de projets par offre (l'offre gratuite est limitée à un projet).

### AI Writer

- Couche d'abstraction `AIService` → `AIProvider`, avec trois implémentations : Anthropic,
  OpenAI et un fournisseur `mock` déterministe et hors ligne. Le fournisseur se change par une
  seule variable d'environnement.
- **11 prompts versionnés**, un module par document : logline, synopsis court, synopsis long,
  note d'intention, note de réalisation, traitement, présentation des personnages, pitch oral,
  pitch écrit, bible du projet, scénario. Chaque prompt impose une structure professionnelle et
  une longueur cible.
- **Cohérence inter-documents** : chaque prompt reçoit le contexte structuré du projet et le
  contenu des documents dont il dépend. La note de réalisation voit la note d'intention et le
  synopsis ; le scénario voit le traitement et les personnages.
- **Scénarios longs en plusieurs passes** : un scénario dépassant ce qu'un appel unique peut
  produire est découpé selon la structure en trois actes ; chaque passe reçoit la fin de la
  précédente pour la continuité des personnages, des lieux et de la numérotation des séquences.
  Le coût en crédits est annoncé avant lancement.
- Durée cible du scénario au choix (10 à 120 minutes), appliquant la règle « 1 page ≈ 1 minute ».
- Actions de retravail : **Régénérer, Améliorer, Raccourcir, Développer, Corriger**.
- **Versioning complet** : chaque génération, sauvegarde manuelle ou restauration crée une
  version horodatée, avec son origine, le modèle et la version de prompt utilisés. Consultation
  et restauration de n'importe quelle version.
- Éditeur avec sauvegarde automatique, aperçu Markdown rendu sans `dangerouslySetInnerHTML`,
  avertissement avant de quitter une page non enregistrée.
- **Système de crédits IA** : chaque génération en consomme ; quotas et prix stockés en base et
  modifiables depuis l'administration.
- Extraction automatique de la section « Informations à compléter » produite par l'IA, affichée
  à l'utilisateur après chaque génération.

### Export

- Réservé aux offres qui l'incluent (`allows_export`, modifiable depuis l'administration) ;
  l'offre gratuite reçoit un 402 explicite plutôt qu'un export silencieusement offert.
- **PDF** : dossier complet avec page de garde, un document par section.
- **DOCX** : export document par document, avec conservation des titres et des listes.
- **ZIP** : archive du projet (fiche projet, chaque document en `.docx` et en `.md`, dossier
  complet en PDF).

### Funding Intelligence

- Base des dispositifs : fonds, subventions, résidences, festivals, laboratoires, ateliers,
  coproductions, bourses, forums de pitch.
- **Recherche filtrée** : plein texte, pays, type de projet, genre, langue, type de dispositif,
  montant, fenêtre d'échéance, tri. Un dispositif dont un critère n'est pas renseigné reste
  visible — l'absence d'information n'est pas une exclusion. Les échéances dépassées sont
  masquées par défaut, consultables à la demande. Les facettes sont calculées depuis la base.
- **Matching déterministe** : sept critères pondérés pour 100 points (pays 25, type 20, genre 12,
  langue 8, format et durée 10, échéance 10, documents exigés 15). Reproductible, explicable
  critère par critère, instantané et **gratuit**.
- **Critères bloquants** : pays non éligible, type de projet non accepté, échéance dépassée.
  Le dispositif reste affiché avec la raison plutôt que d'être masqué.
- **Crédit partiel sur les documents exigés** : le score progresse à mesure que l'auteur rédige
  les pièces demandées, ce qui en fait un signal d'avancement et pas seulement un verdict.
- **Aucune donnée devinée** : un critère non évaluable est marqué « à vérifier », retiré du
  dénominateur, et la réponse expose `assessed_ratio` — la part de la grille réellement évaluée.
- **Explication IA à la demande** : 1 crédit, réutilisée sans nouveau débit si déjà produite.
  L'IA ne recalcule pas le score et ne reçoit que les faits présents en base.
- **Traçabilité imposée par l'API** : création impossible sans `source_name` et `source_url`,
  publication comme ouvert impossible sans URL source, horodatage de chaque vérification.
- Écran de recherche avec filtres, fiche détaillée d'un dispositif, écran des financements
  compatibles d'un projet (conditions remplies / non remplies / à vérifier, documents manquants
  avec lien vers l'AI Writer), et **espace d'administration** réservé au rôle `ADMIN`.
- Notification automatique lorsqu'un projet dépasse 70 % de compatibilité avec un dispositif.

### Tableau de bord et administration

- Statistiques (projets, documents générés, opportunités compatibles, échéances), cartes projet
  avec score de maturité, notifications.
- Administration : liste et modification des utilisateurs, suspension de compte, statistiques
  projets **anonymisées**, consommation IA (appels, jetons, crédits, latence, échecs), gestion
  des offres et de leurs prix, **CRUD complet des dispositifs de financement et de leurs pièces
  exigées**.

### Interface

- Next.js 14 (App Router), TypeScript strict, Tailwind. 17 routes, build de production
  vérifié, `tsc --noEmit` sans erreur.
- Landing page complète en dix sections (problème, solution, AI Writer, Funding Intelligence,
  matching, budget, pour qui, tarifs, FAQ, CTA final).
- Direction artistique sobre : encre profonde, accent laiton, typographie display pour les
  titres. Aucun cliché caméra/clap/pellicule.
- États de chargement, états vides et messages d'erreur traités sur chaque écran.

### Qualité

- **96 tests** au vert (`pytest`), `ruff` sans avertissement. Une revue de sécurité dédiée a
  été menée sur le code livré ; les neuf défauts qu'elle a confirmés (contournement de la
  limitation de débit, secret JWT par défaut accepté en production, fuite du jeton de
  réinitialisation hors production, oracle de temps à la connexion, absence de révocation de
  session, export non soumis à l'offre, découpage des scénarios longs non monotone,
  champs projet jamais rafraîchis, sous-comptage des appels IA) sont corrigés et couverts par
  des tests de non-régression.
- Parcours de bout en bout vérifié sur une instance réelle : inscription → projet → génération →
  édition → restauration de version → score → export PDF et ZIP → tableau de bord → refus au
  dépassement de quota ; puis saisie admin d'un dispositif → recherche filtrée → matching
  gratuit → progression du score au fil des documents rédigés (85 % → 93 % → 100 %) →
  explication IA facturée une seule fois → inéligibilité motivée → projet incomplet évalué sur
  53 % de la grille sans rien deviner.

---

## FEATURES PARTIALLY IMPLEMENTED

| Fonctionnalité | Ce qui existe | Ce qui manque |
| --- | --- | --- |
| **Funding Intelligence** | Module complet : recherche, filtres, matching, explication IA, administration | La base est vide au démarrage : elle s'alimente par saisie administrateur. Le pipeline de veille automatisée (collecte, classification, validation) reste en Phase 6 |
| **Budget et plan de financement** | Tables `budgets`, `budget_items`, `funding_plans`, `funding_plan_lines`, `production_schedules` ; catégories de postes ; calculs de financement acquis/recherché/pourcentage sur le modèle ; le critère « Budget » du score les lit déjà | Générateur de budget, API, interface |
| **Notifications** | Table, API de lecture et de marquage, affichage au tableau de bord, tâches de détection d'échéances et de dossiers incomplets | Envoi effectif des e-mails (le service SMTP existe et journalise à défaut), déclenchement planifié |
| **Abonnements** | Trois offres en base avec prix et quotas configurables depuis l'administration, quotas appliqués | Aucun paiement : changer d'offre se fait aujourd'hui par l'administration |
| **Internationalisation** | Champ `preferred_locale`, paramètre de langue accepté par les prompts (français / anglais) | Traduction de l'interface : elle est en français |

---

## KNOWN ISSUES

1. **Limitation de débit en mémoire** — correcte sur une instance unique, sans effet réparti sur
   plusieurs répliques. À basculer sur Redis avant une montée en charge horizontale.
2. **Génération synchrone** — un scénario de 110 pages enchaîne plusieurs appels au fournisseur
   et peut dépasser plusieurs minutes, en tenant la requête HTTP ouverte. Une file de tâches
   (Redis + worker) est le prolongement naturel ; l'architecture y est préparée.
3. **`AI_PROVIDER=mock` par défaut** — l'application démarre sans clé d'IA et produit alors des
   documents structurés mais non rédigés, explicitement marqués comme tels. C'est un choix
   assumé pour que l'installation fonctionne immédiatement, pas un oubli.
4. **Durée maximale d'un scénario liée à `AI_MAX_OUTPUT_TOKENS`** — avec la valeur par défaut
   (8000), le découpage couvre jusqu'à 138 minutes. Au-delà, l'API refuse explicitement
   (`screenplay_too_long`) plutôt que de facturer un scénario tronqué, et l'interface n'affiche
   que les durées réellement productibles, obtenues auprès du serveur. Augmenter
   `AI_MAX_OUTPUT_TOKENS` relève la limite.
5. **Pas de tests frontend** — le typage strict et le build de production sont vérifiés, mais
   aucun test d'interaction n'est écrit. Playwright sur les parcours critiques est la première
   dette à combler.
6. **Inscription : 409 sur e-mail déjà pris** — c'est un compromis d'ergonomie assumé, qui
   permet à un tiers de tester si une adresse est inscrite. La connexion, elle, ne révèle rien
   (message et temps de réponse identiques). Le supprimer suppose de basculer sur une
   inscription en deux temps avec confirmation par e-mail.
7. **Polices chargées au runtime** — `next/font` télécharge les polices au moment du build, ce
   qui casse la construction d'image dans un environnement sans accès à Google Fonts. Elles sont
   donc chargées par feuille de style, avec des piles système en repli.

---

## ENVIRONMENT VARIABLES

Voir [`.env.example`](../.env.example) et la section 4 du [README](../README.md).

Indispensables en production : `DATABASE_URL`, `JWT_SECRET` (fort et unique), `CORS_ORIGINS`
(domaine réel), `AI_PROVIDER` + `AI_API_KEY`, `ENVIRONMENT=production`, `DEBUG=false`.

---

## HOW TO RUN

```bash
cp .env.example .env          # puis ajuster JWT_SECRET et POSTGRES_PASSWORD
docker compose up --build
docker compose exec backend python -m scripts.seed
```

Frontend : http://localhost:3000 · API : http://localhost:8000/docs

Comptes de démonstration : voir la section 9 du README.

Installation manuelle : sections 6 et 7 du README.

---

## NEXT STEPS

1. **Alimenter la base de financements** : le module fonctionne, mais il est vide. C'est
   désormais un travail éditorial — collecter des dispositifs réellement ouverts aux projets
   d'Afrique francophone, vérifier chaque source, les saisir depuis `/admin/financements`.
2. **Phase 4 — Budget** : générateur de budget par type de projet, plan de financement,
   calendrier de production, export XLSX.
3. **Passer la génération en asynchrone** : Redis + worker, avec suivi de progression par passe
   pour les scénarios longs.
4. **Tests frontend** : Playwright sur inscription → projet → génération → export.
5. **Phase 5 — Monétisation** : intégration d'un prestataire de paiement adapté à la zone FCFA
   (mobile money notamment), gestion du cycle d'abonnement.
6. **Phase 6 — Automatisation** : pipeline de veille n8n (source → extraction → nettoyage →
   classification → validation humaine → base), notifications par e-mail. Il alimentera la base
   de financements que l'administration remplit aujourd'hui à la main.
7. **Observabilité** : brancher Sentry et un outil de produit analytics sur les points
   d'extension déjà en place.
8. **Internationalisation** : extraire les chaînes de l'interface, ajouter l'anglais.
