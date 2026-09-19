# État du projet — rapport de livraison

Dernière mise à jour : 18 septembre 2026 · Périmètre livré : **Phase 1 (Foundation), Phase 2
(AI Writer), Phase 3 (Funding Intelligence), Phase 4 (Budget), Phase 5 (Abonnements) et Phase 6 (Automatisation)**, plus l'export qui figure
parmi les fonctionnalités indispensables du MVP.

Ce document dit ce qui fonctionne réellement, ce qui est partiel et ce qui n'est pas commencé.
Aucune fonctionnalité n'y est annoncée comme terminée si elle ne l'est pas.

---

## FEATURES IMPLEMENTED

### Fondations

- Monorepo `backend/` + `frontend/`, `docker-compose.yml` à six services (frontend, backend,
  worker, postgres, redis, n8n), `.env.example` complet, `Dockerfile` pour chaque service.
- Schéma PostgreSQL complet : **25 tables**, contraintes d'intégrité, index, migration Alembic
  initiale. Les tables des phases 3 à 5 existent déjà, pour éviter une migration structurante
  plus tard.
- Configuration centralisée et typée (`pydantic-settings`), aucun secret en dur.
- Journalisation structurée (JSON en production), identifiant de requête propagé via
  l'en-tête `X-Request-ID`, mesure de la latence de chaque requête.
- Gestion d'erreurs uniforme : chaque réponse d'erreur porte un `detail` lisible et un `code`
  exploitable par le frontend.

### Authentification et sécurité

- Inscription, connexion, déconnexion, jetons d'accès et de rafraîchissement (JWT), profil.
- **Inscription en deux temps, sans énumération de comptes** : l'API répond exactement la même
  chose que l'adresse soit libre ou déjà prise, et le compte n'est actif qu'une fois ouvert le
  lien reçu par e-mail. Le mot de passe est haché dans les deux cas, sans quoi l'écart de temps
  de réponse (mesuré : 298 ms contre 306 ms) rétablirait l'oracle supprimé. Le titulaire d'une
  adresse déjà inscrite est prévenu de la tentative, et lui seul. Le lien ne sert qu'une fois,
  expire en 24 heures, n'est stocké que haché, et n'est jamais renvoyé par l'API hors
  environnement `development`. Un compte non confirmé ne peut pas se connecter — message
  atteignable seulement avec le bon mot de passe, donc sans rien révéler à un tiers.
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
- **Limite partagée entre répliques** : avec `REDIS_URL`, les compteurs vivent dans Redis
  (fenêtre glissante par ensemble ordonné, comptage en transaction `MULTI`/`EXEC`) et la limite
  vaut pour le déploiement entier. Sans lui, chaque réplique compte de son côté et la limite
  réelle est multipliée par leur nombre — mesuré : 10 connexions acceptées pour une limite
  annoncée à 5, avec deux répliques. Si Redis devient injoignable, l'API continue de répondre
  en comptant en mémoire (un coupe-circuit évite d'attendre un serveur muet à chaque appel) et
  `GET /health` passe en `degraded` avec `"rate_limit": "redis-unreachable"`.
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
- **Génération hors requête HTTP** : une demande est acceptée en quelques millisecondes et
  exécutée par un worker. Mesuré sur un scénario de 110 pages (8 passes, fournisseur à 1,5 s
  par appel) : réponse en **10 ms** pour une génération de **12,2 s**, avec l'avancement
  visible passe après passe. Les crédits sont **réservés à la mise en file** — sans quoi on
  pourrait empiler des générations au-delà de son quota — et **rendus si la tâche échoue**. La
  base est la source de vérité : une file Redis perdue ne perd aucune tâche, un balayage les
  reprend, et une tâche dont le worker a disparu échoue proprement plutôt que de rester en
  cours — le délai se comptant depuis le **dernier signe de vie** et non depuis le démarrage,
  une génération longue mais vivante n'est jamais prise pour une tâche morte. Sans `REDIS_URL` ou sans worker, l'API génère elle-même : `GET /health` dit lequel
  des deux modes est actif.
- **Continuité tenue sur toute la longueur** : chaque passe reçoit non seulement la fin de la
  précédente, mais les faits établis par **toutes** celles d'avant — personnages apparus (avec
  leur nombre de répliques), lieux utilisés, segments déjà écrits. Ces faits sont extraits du
  texte produit par lecture du format standard (en-têtes de séquence, noms en majuscules) :
  aucun appel supplémentaire au fournisseur, donc aucun crédit. Un texte hors format ne produit
  simplement rien plutôt qu'un fait faux. Le rappel est borné (~900 caractères à la 40ᵉ passe,
  quelle que soit la longueur) : il ne prend pas la place du texte à écrire.
- **Scénarios longs en plusieurs passes** : un scénario dépassant ce qu'un appel unique peut
  produire est découpé selon la structure en trois actes ; chaque passe reçoit la fin de la
  précédente pour la continuité des personnages, des lieux et de la numérotation des séquences.
  Le coût en crédits est annoncé avant lancement.
- **Durée cible libre**, appliquant la règle « 1 page ≈ 1 minute » : le nombre de passes suit
  la durée demandée, il n'est plus plafonné à dix. `AI_MAX_OUTPUT_TOKENS` fixe ce qu'une passe
  produit, plus la longueur totale du scénario. Avec les valeurs par défaut, la durée maximale
  réalisable passe de **138 à 681 minutes** ; surtout, avec un `AI_MAX_OUTPUT_TOKENS` modeste
  (4000), un long métrage de 120 minutes était refusé et ne l'est plus. Un plafond de sécurité
  (`SCREENPLAY_MAX_PASSES`, 40 par défaut) refuse toujours explicitement une durée aberrante,
  en indiquant ce qui est réalisable.
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

### Budget et plan de financement

- **Trame de budget par type de projet** (documentaire, long métrage, court métrage, série TV,
  série web, animation) : 22 à 27 postes répartis sur les cinq phases de production, dans
  l'ordre où un comité de lecture les attend. La trame propose **la structure, jamais les
  montants** : un tarif plausible inventé serait un chiffre faux dans un dossier de
  financement. Régénérer complète sans écraser les lignes déjà chiffrées.
- **Tous les totaux sont calculés, jamais saisis** : le montant d'une ligne vaut quantité ×
  prix unitaire, le total du budget la somme des lignes, et le plan de financement suit le
  budget. Sous-totaux et part relative par phase.
- **Plan de financement où « acquis » veut dire acquis** : une source seulement espérée compte
  dans l'identifié et dans le recherché, pas dans le financé. Quatre chiffres distincts — budget
  total, acquis, identifié, non couvert même par l'espéré — plutôt qu'un pourcentage unique qui
  flatterait le dossier.
- **Calendrier de production** : une ligne par phase, dates de début et de fin.
- **Export XLSX** à trois feuilles (budget, plan de financement, calendrier), réservé aux offres
  qui incluent l'export. Les montants y sont des **formules** et non des valeurs figées : un
  financeur qui corrige un prix voit le total suivre.
- Le critère « Budget » du score de maturité lit ces tables : chiffrer le dossier fait monter le
  score immédiatement (mesuré sur un parcours réel : 4/100 → 19/100).

### Abonnements et paiements

- **Cycle d'abonnement complet** : souscription, activation sur paiement abouti, résiliation,
  échéance. Trois règles le portent. *Un paiement donne des droits, il ne les suppose pas* :
  rien n'est accordé tant qu'il n'est pas abouti — en mobile money, la personne doit encore
  valider sur son téléphone. *Les notifications sont idempotentes* : la référence porte une
  contrainte d'unicité, et une notification rejouée — ce que font tous les prestataires — ne
  prolonge pas l'abonnement une seconde fois. *Résilier n'est pas couper* : la période déjà
  payée va à son terme, c'est l'échéance qui fait redescendre à l'offre gratuite.
- **Notifications authentifiées** : signature HMAC-SHA256 vérifiée en temps constant avant
  toute lecture du contenu. Sans secret configuré, aucune notification n'est acceptée — une
  vérification qui s'ouvre quand la configuration est incomplète ne protège rien.
- **Couche prestataire interchangeable**, sur le modèle de `AIProvider` : `manual`
  (encaissement hors ligne validé depuis l'administration, et tracé au nom de qui valide) et
  `mock` (simulé, refusé en production). Chaque paiement est une ligne conservée, jamais
  écrasée, avec la charge utile reçue du prestataire.
- Renouveler avant l'échéance **prolonge** la période au lieu de la raccourcir.
- Écran d'abonnement : offres et prix venant du serveur, solde de crédits, historique des
  paiements, résiliation.

### Tableau de bord et administration

- Statistiques (projets, documents générés, opportunités compatibles, échéances), cartes projet
  avec score de maturité, notifications.
- Administration : liste et modification des utilisateurs, suspension de compte, statistiques
  projets **anonymisées**, consommation IA (appels, jetons, crédits, latence, échecs), gestion
  des offres et de leurs prix, **CRUD complet des dispositifs de financement et de leurs pièces
  exigées**.

### Veille automatisée et tâches planifiées

- **Le pipeline n8n n'écrit jamais dans la base vivante.** Il dépose des *candidats* dans une
  file de validation ; un administrateur les relit depuis `/admin/veille`, corrige ce qui doit
  l'être, puis publie ou écarte. Une opportunité proposée à un auteur engage son dossier de
  financement : elle ne peut pas venir d'une classification automatique non relue. Vérifié de
  bout en bout : deux candidats déposés, **zéro dispositif visible** avant relecture.
- **Deux garde-fous à l'entrée** : pas d'URL source, pas de candidat ; et déduplication par
  empreinte de la source — un second passage de la veille sur les mêmes pages produit
  0 nouveau candidat et 2 doublons, au lieu de remplir la file. Une décision humaine tient :
  un candidat écarté ne revient pas dans la file au passage suivant.
- **Aucune valeur devinée** : une date illisible est écartée avec une trace dans les journaux,
  jamais complétée. Les corrections du relecteur l'emportent sur l'extraction — c'est lui qui a
  lu la source. La traçabilité (`source_url`, `source_name`, `last_verified_at`) suit le
  candidat jusqu'au dispositif publié.
- **Routes d'automatisation authentifiées** par clé partagée comparée en temps constant. Sans
  clé configurée, elles sont fermées : une automatisation ouverte par défaut serait une porte
  d'entrée sur la base de financements.
- **Tâches planifiées déclenchables par liste fermée** (`notify_upcoming_deadlines`,
  `notify_incomplete_projects`, `send_pending_notification_emails`, `reset_monthly_credits`,
  `expire_due_subscriptions`) : une route acceptant un nom libre exposerait tout le module.
  Toutes sont idempotentes.
- **Envoi effectif des notifications par e-mail** : le drapeau `email_sent` existait sans que
  rien ne l'écrive. Une notification n'est marquée envoyée que si l'envoi a réussi — sans SMTP,
  elle reste en attente et repartira, au lieu d'être perdue.
- Les deux workflows n8n appellent désormais ces routes, au lieu d'exécuter des commandes shell
  dans le conteneur backend.

### Interface

- Next.js 14 (App Router), TypeScript strict, Tailwind. 19 routes, build de production
  vérifié, `tsc --noEmit` sans erreur.
- **Produit bilingue français / anglais, interface et API.** Catalogues typés dans
  `frontend/src/lib/i18n/` : le français définit les clés, l'anglais est typé d'après lui,
  si bien qu'une clé oubliée fait échouer `tsc`. L'API suit la même langue — messages
  d'erreur, messages de succès, et les libellés qu'elle calcule (critères de compatibilité,
  critères de maturité) ; le `code` d'erreur, lui, ne change jamais, c'est sur lui que le
  client se branche. Côté serveur, ce que le compilateur garantit à l'interface est tenu
  par `tests/test_i18n.py`, qui compare les jeux de clés, vérifie les variables des deux
  côtés, et relit le code source pour refuser une clé qui n'existe pas. Les **notifications**
  stockent leur clé et leurs paramètres plutôt que leur phrase : écrites une fois, elles sont
  relues dans la langue de qui les ouvre. Celles écrites avant cette mécanique gardent leur
  texte — mieux vaut une phrase dans la mauvaise langue qu'une notification vide. La langue vient du profil
  (`preferred_locale`), puis d'un cookie relu par le rendu serveur — `<html lang>` est donc
  juste dès le premier octet, et l'interface ne s'affiche jamais brièvement dans la mauvaise
  langue. Accords, dates, nombres et durées relatives viennent d'`Intl`, pas du catalogue.
  Sélecteur de langue dans l'en-tête, sur les pages d'authentification, sur la page publique
  et dans le profil.
- **20 tests de bout en bout (Playwright)** sur un vrai navigateur, une vraie API et une base
  neuve : inscription → confirmation d'adresse → connexion, non-énumération visible à l'écran,
  création de projet, génération d'un document puis ouverture dans l'éditeur, limites d'offre
  (projets, crédits, export), trame de budget et couverture du plan de financement, bascule de
  langue (rendu serveur, persistance, accord du singulier anglais, et message d'erreur
  de l'API dans la langue choisie). Ils démarrent eux-mêmes
  les deux serveurs : `npm run test:e2e`.
- Landing page complète en dix sections (problème, solution, AI Writer, Funding Intelligence,
  matching, budget, pour qui, tarifs, FAQ, CTA final).
- Direction artistique sobre : encre profonde, accent laiton, typographie display pour les
  titres. Aucun cliché caméra/clap/pellicule.
- États de chargement, états vides et messages d'erreur traités sur chaque écran.

### Qualité

- **Intégration continue** (`.github/workflows/ci.yml`) sur chaque pull request et sur `main` :
  lint, tests, migrations appliquées sur PostgreSQL et contrôle de dérive entre modèles et
  migrations, typage strict, build, puis parcours Playwright. Les tests tournent sur SQLite ;
  vérifier les migrations sur leur vraie cible évite de découvrir l'écart au déploiement.
- **Suivi des erreurs (Sentry), désactivé par défaut.** Sans `SENTRY_DSN`, rien n'est
  initialisé et aucune requête ne part vers un tiers ; avec un DSN, les exceptions de l'API
  **et du worker** sont remontées, et `GET /health` publie l'état sous `error_tracking`
  (`disabled`, `active`, ou `unavailable` si le paquet manque alors qu'un DSN est configuré).
  Un rapport d'erreur partant chez un tiers, il n'emporte ni identifiants, ni adresses
  e-mail, ni numéros de téléphone, ni jetons d'URL, ni contenu de dossier (synopsis,
  scénarios, budgets) : l'expurgation est testée, et trois réglages ferment ce qu'elle ne
  peut pas nommer — corps de requête, données d'identification et variables locales des
  piles d'appels. Le navigateur suit la même règle, y compris sur les fils d'Ariane, qui
  portent les jetons de confirmation dans l'URL.
- **551 tests** au vert (`pytest`), `ruff` sans avertissement. Une revue de sécurité dédiée a
  été menée sur le code livré ; les neuf défauts qu'elle a confirmés (contournement de la
  limitation de débit, secret JWT par défaut accepté en production, fuite du jeton de
  réinitialisation hors production, oracle de temps à la connexion, absence de révocation de
  session, export non soumis à l'offre, découpage des scénarios longs non monotone,
  champs projet jamais rafraîchis, sous-comptage des appels IA) sont corrigés et couverts par
  des tests de non-régression. Les cinq limites connues les plus lourdes — limitation de débit
  non partagée entre répliques, génération tenue dans la requête HTTP, durée de scénario
  plafonnée par le budget de sortie du fournisseur, énumération de comptes à l'inscription,
  et perte de continuité d'une passe à l'autre — sont corrigées. Le test d'intégration sur un vrai serveur
  Redis est ignoré si aucun n'est joignable — les autres tournent sans dépendance externe.
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
| **Funding Intelligence** | Module complet : recherche, filtres, matching, explication IA, administration, et pipeline de veille avec file de validation | La base est vide au démarrage : la veille doit être branchée sur des sources réelles, et chaque candidat relu |
| **Internationalisation** | Champ `preferred_locale`, paramètre de langue accepté par les prompts (français / anglais) | Traduction de l'interface : elle est en français |

---

## KNOWN ISSUES

1. **`AI_PROVIDER=mock` par défaut** — l'application démarre sans clé d'IA et produit alors des
   documents structurés mais non rédigés, explicitement marqués comme tels. C'est un choix
   assumé pour que l'installation fonctionne immédiatement, pas un oubli.
2. **Annulation impossible sans worker** — une génération peut être arrêtée
   (`POST /jobs/{id}/cancel`) : immédiatement si elle est en file, entre deux passes si elle
   est en cours, en ne rendant que les passes qui n'ont pas tourné. Mais sans `REDIS_URL` ni
   worker, l'API exécute la génération **dans la requête HTTP** : elle est terminée avant
   qu'on puisse l'arrêter. Il reste aussi un cas irréductible — une génération en un seul
   appel n'a pas de frontière avant sa fin : la demande est enregistrée, la tâche ira à son
   terme.
3. **Inscription inutilisable sans SMTP hors développement** — l'activation d'un compte passe
   désormais par un e-mail. En `staging` ou en production sans `SMTP_HOST`, le message est
   seulement journalisé : personne ne peut activer son compte. Configurer SMTP devient donc
   obligatoire dès qu'on quitte le poste de développement, où le jeton reste renvoyé par l'API.
4. **Budget : aucun repère de prix** — la trame donne les postes, l'auteur cherche les tarifs
   ailleurs. Une base de coûts indicative par pays rendrait le chiffrage plus rapide, mais
   suppose des données vérifiées que le produit n'a pas : proposer des montants inventés serait
   pire que ne rien proposer. Les drapeaux `allows_advanced_budget` et `allows_collaboration`
   restent **inappliqués**, faute de fonctionnalité correspondante : le module budget est
   ouvert à tous (seul l'export XLSX suit la règle d'offre commune), et la collaboration
   d'équipe n'existe pas. Ils sont conservés en base pour le jour où ces fonctionnalités
   seront écrites, mais **aucune description d'offre ne les annonce plus** — un test le
   vérifie. Les quatre contraintes réellement appliquées sont `max_projects`,
   `monthly_ai_credits`, `allows_export` et `allows_matching`.
5. **Continuité de style sur un très long scénario** — les noms, lieux et segments écrits sont
   désormais rappelés à chaque passe, ce qui écarte la dérive la plus visible. Restent le
   registre de langue et les détails secondaires, qu'aucun rappel factuel ne fixe : un scénario
   de dix heures demandera toujours une relecture d'ensemble.
6. **Souscription fermée pendant la bêta privée** — avec `PLATFORM_MODE=internal`
   (le défaut), `POST /billing/checkout` et la simulation de paiement répondent
   `403 subscription_closed`, pour tout le monde y compris les administrateurs : il n'y a
   rien à vendre tant que le produit n'est pas commercialisé. Résiliation et webhook du
   prestataire restent ouverts. Rien n'est supprimé — offres, abonnements, paiements et
   historiques sont conservés, et `PLATFORM_MODE=public` rouvre tout. L'**inscription
   publique** est fermée par le même interrupteur : `POST /auth/register` répond
   `403 registration_closed` et l'écran `/inscription` l'annonce, ce qui lève la
   conséquence qu'il fallait auparavant connaître — plus de compte non administrateur
   créé pendant la bêta pour rester coincé sur une offre gratuite en sommeil. Confirmer
   une adresse et redemander le lien restent ouverts, sans quoi un compte créé avant la
   bascule ne pourrait plus jamais s'activer. Les comptes de la bêta se créent avec
   `python -m scripts.create_admin`.
7. **Aucun prestataire de paiement réel** — le cycle d'abonnement fonctionne de bout en bout,
   mais avec `manual` (encaissement hors ligne) ou `mock` (simulé). Brancher CinetPay, PayDunya,
   Wave ou Flutterwave revient à écrire une classe implémentant `PaymentProvider` : trois
   méthodes, documentées dans `app/services/payments/base.py`.
8. **La veille n'a aucune source branchée** — le pipeline, la file de validation et les
   garde-fous sont en place, mais le nœud « source » des workflows pointe sur une URL d'exemple.
   Brancher un portail réel demande de choisir les sources et d'en lire la structure ; aucune
   n'est proposée par défaut, faute de pouvoir en vérifier la fiabilité ici.
9. **Couverture navigateur limitée à Chromium** — les parcours sont joués sur un seul moteur,
   dans une seule taille de fenêtre. Firefox, WebKit et l'affichage mobile ne sont pas testés ;
   les ajouter ne demande qu'une ligne de configuration, mais allonge d'autant chaque exécution.
10. **Polices chargées au runtime** — `next/font` télécharge les polices au moment du build, ce
   qui casse la construction d'image dans un environnement sans accès à Google Fonts. Elles sont
   donc chargées par feuille de style, avec des piles système en repli.

---

## ENVIRONMENT VARIABLES

Voir [`.env.example`](../.env.example) et la section 4 du [README](../README.md).

Indispensables en production : `DATABASE_URL`, `JWT_SECRET` (fort et unique), `CORS_ORIGINS`
(domaine réel), `AI_PROVIDER` + `AI_API_KEY`, `ENVIRONMENT=production`, `DEBUG=false`. Avec
plusieurs répliques, `REDIS_URL` s'ajoute à cette liste : sans lui, la limitation de débit
annoncée est multipliée par le nombre de répliques, et les générations s'exécutent dans la
requête HTTP. Le worker (`python -m app.workers.runner`) se déploie à côté de l'API. `SMTP_*` devient
indispensable dès `staging` : sans lui, aucun compte ne peut être activé.

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

1. **Déployer l'application.** Le schéma est en place sur le PostgreSQL managé
   (Supabase, projet `FilmFundAfrica`, migrations jusqu'à `0006`), mais **rien ne s'y
   connecte encore** : il n'existe aucun déploiement. Il manque un hôte pour l'API et le
   worker, et `DATABASE_URL` dans son environnement. Vercel Services héberge le frontend
   **et** l'API (voir `deploy/VERCEL.md`) ; ce qu'il n'héberge pas, c'est le worker, un
   processus long qui ne sert aucune requête. Voir la section 15 du README.
2. **Alimenter la base de financements** : le module fonctionne, mais il est vide. C'est
   désormais un travail éditorial — collecter des dispositifs réellement ouverts aux projets
   d'Afrique francophone, vérifier chaque source, les saisir depuis `/admin/financements`.
3. **Brancher un prestataire de paiement réel** : le cycle d'abonnement est complet et la
   couche prestataire est en place, mais aucun prestataire réel n'y est branché — cela demande
   un compte, des clés et la documentation exacte de son API. Écrire cette intégration « de
   mémoire » produirait un code qui compile et qui échoue en production.
4. **Brancher la veille sur des sources réelles** : le pipeline et la file de validation
   fonctionnent, mais le nœud « source » des workflows pointe encore sur une URL d'exemple.
   C'est un travail éditorial : choisir les portails à suivre, puis relire ce qu'ils remontent.
5. **Créer le projet Sentry et renseigner les DSN.** Le branchement est fait des deux côtés,
   mais il ne s'active qu'avec un DSN : il faut un compte et un projet Sentry, que personne
   ici ne peut inventer. Sans DSN, rien ne part — c'est le comportement par défaut, et il est
   testé.
6. **Produit analytics** : le point d'extension est le même que celui de Sentry
   (`app/core/logging.py` et `app/core/observability.py`), mais aucun outil n'y est branché.
7. **Faire relire les prompts de génération dans chaque langue.** La plomberie est en
   place : l'AI Writer propose une langue de document, le serveur la transmet au modèle et
   la retient sur le document, si bien que le retravail repart dans la bonne — « corriger »
   n'applique plus la typographie française à un texte anglais. Ce qui reste est éditorial
   et non technique : les onze prompts sont rédigés en français et visent les attentes d'un
   comité de lecture francophone. Le modèle produit bien de l'anglais, mais un portage
   sérieux demande de les réécrire et de les faire relire par un professionnel du secteur
   pour chaque langue — les attentes d'un comité ne se traduisent pas mot à mot.
