/**
 * Catalogue français — langue de référence.
 *
 * C'est ce fichier qui définit les clés : `en.ts` est typé d'après lui, si
 * bien qu'une clé ajoutée ici et oubliée là-bas fait échouer la compilation.
 * Les clés sont plates et préfixées par écran (`projets.`, `budget.`) pour
 * qu'on retrouve d'un coup d'œil tout ce que porte une page.
 *
 * Les valeurs peuvent contenir des variables `{ainsi}`. Une clé pluralisée
 * s'écrit en autant de variantes que la langue en compte (`_one`, `_other`
 * en français et en anglais) ; c'est `Intl.PluralRules` qui choisit.
 */

export const fr = {
  // --- Formats ---
  "format.now": "à l'instant",
  "format.lessThanOnePage": "moins d'une page",
  "format.pages_one": "~{count} page",
  "format.pages_other": "~{count} pages",

  // --- Vocabulaire commun ---
  "common.appName": "FilmFund Africa",
  "common.tagline": "De l'idée au financement de votre projet audiovisuel.",
  "common.save": "Enregistrer",
  "common.saving": "Enregistrement…",
  "common.cancel": "Annuler",
  "common.close": "Fermer",
  "common.delete": "Supprimer",
  "common.edit": "Éditer",
  "common.back": "Retour",
  "common.loading": "Chargement…",
  "common.none": "—",
  "common.optional": "facultatif",
  "common.required": "obligatoire",
  "common.yes": "Oui",
  "common.no": "Non",
  "common.search": "Rechercher",
  "common.filter": "Filtrer",
  "common.reset": "Réinitialiser",
  "common.confirm": "Confirmer",
  "common.continue": "Continuer",
  "common.retry": "Réessayer",
  "common.unknownError": "Une erreur est survenue. Merci de réessayer.",
  "common.language": "Langue",
  "common.changeLanguage": "Changer de langue",

  // --- Navigation ---
  "nav.dashboard": "Tableau de bord",
  "nav.projects": "Mes projets",
  "nav.funding": "Financements",
  "nav.subscription": "Abonnement",
  "nav.profile": "Profil",
  "nav.admin": "Administration",
  "nav.openMenu": "Ouvrir le menu",
  "nav.newProject": "Nouveau projet",
  "nav.logout": "Se déconnecter",
  "nav.creditsRemaining": "Crédits IA restants",
  "nav.creditsUnlimited": "Illimité (bêta)",

  // --- Administration ---
  "admin.title": "Administration",
  "admin.tabs.funding": "Financements",
  "admin.tabs.watch": "Veille",
  "admin.tabs.ai": "Intelligence artificielle",
  "platform.internal.title": "Bêta interne",
  "platform.internal.body":
    "Les contraintes d'offre — quotas de projets, crédits IA, export — ne sont pas opposées aux administrateurs. Elles restent appliquées à tous les autres comptes. Depuis le {start}, cible du {end}.",
  "platform.public.title": "Phase commerciale",
  "platform.public.body":
    "Les règles d'abonnement s'appliquent à tous les comptes, administrateurs compris.",

  // --- Configuration de l'IA ---
  "aiConfig.title": "Fournisseur d'intelligence artificielle",
  "aiConfig.subtitle":
    "Choisissez le fournisseur, déposez sa clé, éprouvez-la. Chaque fournisseur garde la sienne.",
  "aiConfig.activeProvider": "Fournisseur actif",
  "aiConfig.providerHint":
    "Le changement s'applique à la prochaine génération, sans redéploiement.",
  "aiConfig.model": "Modèle",
  "aiConfig.modelPlaceholder": "Laisser vide pour le défaut du fournisseur",
  "aiConfig.modelEffective": "Modèle appliqué : {model}",
  "aiConfig.modelRequired":
    "Ce fournisseur n'a pas de modèle par défaut : indiquez-en un, sinon aucune génération ne partira.",
  "aiConfig.source.database": "saisi ici",
  "aiConfig.source.environment": "variable d'environnement",
  "aiConfig.source.provider_default": "défaut du fournisseur",
  "aiConfig.source.none": "aucune",
  "aiConfig.source.unreadable": "illisible",
  "aiConfig.provider.anthropic": "Anthropic (Claude)",
  "aiConfig.provider.openai": "OpenAI",
  "aiConfig.provider.mock": "Hors ligne (mock)",
  "aiConfig.keyLabel": "Clé API — {provider}",
  "aiConfig.keyPlaceholder": "Coller la clé, puis enregistrer",
  "aiConfig.keyInPlace": "Clé en place ({hint}), source : {source}",
  "aiConfig.keyAbsent": "Aucune clé enregistrée pour ce fournisseur.",
  "aiConfig.keyUnreadable":
    "Une clé est enregistrée mais ne peut plus être déchiffrée : la clé de chiffrement du serveur (SECRETS_KEY, ou JWT_SECRET à défaut) a changé depuis. Collez-en une nouvelle pour rétablir le service.",
  "aiConfig.keyNotNeeded": "Ce fournisseur n'appelle aucun service externe : il n'a pas de clé.",
  "aiConfig.keyNeverShown":
    "Une clé enregistrée ne peut plus être relue, ici ni ailleurs : elle est chiffrée en base et seuls ses quatre derniers caractères sont affichés. Pour la remplacer, collez-en une nouvelle.",
  "aiConfig.replaceKey": "Remplacer la clé",
  "aiConfig.removeKey": "Supprimer la clé",
  "aiConfig.removeKeyConfirm":
    "Supprimer la clé {provider} ? Les générations échoueront tant qu'aucune autre ne sera fournie.",
  "aiConfig.save": "Enregistrer",
  "aiConfig.saved": "Configuration enregistrée.",
  "aiConfig.test": "Éprouver la configuration",
  "aiConfig.testRunning": "Appel en cours…",
  "aiConfig.testWarning":
    "L'essai passe un appel réel, facturé par le fournisseur. C'est aussi la seule façon de distinguer une clé valide d'un solde épuisé.",
  "aiConfig.testOk":
    "Appel abouti — {provider} / {model}, {input} jetons en entrée, {output} en sortie, {latency} ms.",
  "aiConfig.testFailed": "Appel refusé : {detail}",
  "aiConfig.mockWarning":
    "Le mode « mock » ne rédige rien : il produit une structure vide et la chaîne d'agents rend un dossier non exportable. Utile hors ligne, jamais pour un dossier réel.",
  "admin.restricted.title": "Accès réservé",
  "admin.restricted.body": "Cet espace est réservé aux administrateurs de la plateforme.",

  // --- Composants partagés ---
  "ui.scoreTitle": "Score de maturité : {value}/100",
  "ui.scoreNotComputed": "non calculé",

  // --- Financements (composants partagés) ---
  "funding.source": "Source",
  "funding.sourceMissing": "Source non renseignée",
  "funding.verifiedOn": "Vérifié le {date}",
  "funding.neverVerified": "jamais vérifié",
  "funding.noDeadline": "Sans date limite",
  "funding.deadlinePassed": "Échéance dépassée",
  "funding.daysLeft_one": "J-{count}",
  "funding.daysLeft_other": "J-{count}",
  "funding.demoData": "DEMO DATA — NOT REAL",
  "funding.blocking": "bloquant",
  "funding.scoreDisclaimer":
    "Le score de compatibilité est un indicateur d'aide à la décision. Il ne garantit en aucun cas l'obtention d'un financement : les conditions officielles de l'organisme font foi et doivent être vérifiées sur son site.",

  // --- Types de projet ---
  "projectType.DOCUMENTARY": "Documentaire",
  "projectType.FEATURE_FILM": "Long métrage",
  "projectType.SHORT_FILM": "Court métrage",
  "projectType.TV_SERIES": "Série TV",
  "projectType.WEB_SERIES": "Web-série",
  "projectType.ANIMATION": "Animation",

  // --- Étapes de projet ---
  "projectStatus.IDEA": "Idée",
  "projectStatus.DEVELOPMENT": "Développement",
  "projectStatus.WRITING": "Écriture",
  "projectStatus.PRE_PRODUCTION": "Préproduction",
  "projectStatus.PRODUCTION": "Production",
  "projectStatus.POST_PRODUCTION": "Postproduction",
  "projectStatus.COMPLETED": "Terminé",

  // --- Profils d'utilisateur ---
  "userType.AUTHOR": "Auteur",
  "userType.DIRECTOR": "Réalisateur",
  "userType.PRODUCER": "Producteur",
  "userType.INSTITUTION": "Institution",
  "userType.ADMIN": "Administrateur",

  // --- Documents du dossier ---
  "documentType.LOGLINE": "Logline",
  "documentType.SHORT_SYNOPSIS": "Synopsis court",
  "documentType.LONG_SYNOPSIS": "Synopsis long",
  "documentType.INTENT_NOTE": "Note d'intention",
  "documentType.DIRECTING_NOTE": "Note de réalisation",
  "documentType.TREATMENT": "Traitement",
  "documentType.CHARACTER_SHEET": "Présentation des personnages",
  "documentType.ORAL_PITCH": "Pitch oral",
  "documentType.WRITTEN_PITCH": "Pitch écrit",
  "documentType.SERIES_BIBLE": "Bible du projet",
  "documentType.SCREENPLAY": "Scénario",

  "documentStatus.DRAFT": "Brouillon",
  "documentStatus.IN_REVIEW": "En relecture",
  "documentStatus.FINAL": "Finalisé",

  "origin.MANUAL": "Édition manuelle",
  "origin.AI_GENERATE": "Génération IA",
  "origin.AI_IMPROVE": "IA — amélioration",
  "origin.AI_SHORTEN": "IA — raccourcissement",
  "origin.AI_EXPAND": "IA — développement",
  "origin.AI_CORRECT": "IA — correction",
  "origin.RESTORE": "Restauration",

  // --- Catégories de financement ---
  "fundingCategory.FUND": "Fonds",
  "fundingCategory.GRANT": "Subvention",
  "fundingCategory.RESIDENCY": "Résidence",
  "fundingCategory.FESTIVAL": "Festival",
  "fundingCategory.LAB": "Laboratoire",
  "fundingCategory.WORKSHOP": "Atelier",
  "fundingCategory.COPRODUCTION": "Coproduction",
  "fundingCategory.BURSARY": "Bourse",
  "fundingCategory.PITCHING_FORUM": "Forum de pitch",

  "fundingStatus.OPEN": "Ouvert",
  "fundingStatus.CLOSED": "Clos",
  "fundingStatus.UPCOMING": "À venir",
  "fundingStatus.UNVERIFIED": "Non vérifié",

  // --- Budget ---
  "budgetCategory.DEVELOPMENT": "Développement",
  "budgetCategory.PRE_PRODUCTION": "Préparation",
  "budgetCategory.PRODUCTION": "Tournage",
  "budgetCategory.POST_PRODUCTION": "Post-production",
  "budgetCategory.DISTRIBUTION": "Diffusion et frais généraux",

  "fundingSource.PRODUCER": "Apport producteur",
  "fundingSource.PUBLIC_FUND": "Fonds public",
  "fundingSource.TELEVISION": "Préachat télévision",
  "fundingSource.COPRODUCER": "Coproducteur",
  "fundingSource.INVESTOR": "Investisseur",
  "fundingSource.SPONSOR": "Mécénat / parrainage",
  "fundingSource.OTHER": "Autre",

  // --- Connexion ---
  "login.title": "Connexion",
  "login.subtitle": "Retrouvez vos projets et vos dossiers.",
  "login.email": "Adresse e-mail",
  "login.password": "Mot de passe",
  "login.forgot": "Mot de passe oublié ?",
  "login.submit": "Se connecter",
  "login.failed": "Connexion impossible pour le moment.",
  "login.resend": "Renvoyer le lien de confirmation",
  "login.resent": "Si un lien était en attente, un nouveau vient de partir vers cette adresse.",
  "login.noAccount": "Pas encore de compte ?",
  "login.createAccount": "Créer un compte",

  // --- Mot de passe oublié ---
  "forgot.title": "Mot de passe oublié",
  "forgot.subtitle": "Nous vous envoyons un lien pour choisir un nouveau mot de passe.",
  "forgot.submit": "Envoyer le lien",
  "forgot.failed": "Demande impossible pour le moment.",
  "forgot.backToLogin": "Retour à la connexion",

  // --- Nouveau mot de passe ---
  "reset.title": "Nouveau mot de passe",
  "reset.token": "Jeton reçu par e-mail",
  "reset.newPassword": "Nouveau mot de passe",
  "reset.passwordHint": "Au moins 8 caractères, mêlant lettres et chiffres.",
  "reset.submit": "Définir le mot de passe",
  "reset.failed": "Réinitialisation impossible.",
  "reset.done": "Mot de passe mis à jour. Vous pouvez vous connecter avec le nouveau.",

  // --- Confirmation d'adresse ---
  "verify.incompleteTitle": "Lien incomplet",
  "verify.incompleteBody":
    "Ce lien ne contient pas de jeton de confirmation. Ouvrez celui reçu par e-mail sans le modifier.",
  "verify.failedTitle": "Confirmation impossible",
  "verify.failed": "Confirmation impossible pour le moment.",
  "verify.failedHelp":
    "Un lien de confirmation ne sert qu'une fois et expire au bout de 24 heures. Depuis la page de connexion, vous pouvez en demander un nouveau.",
  "verify.goToLogin": "Aller à la connexion",
  "verify.inProgressTitle": "Confirmation en cours…",
  "verify.inProgressBody": "Activation de votre compte.",

  // --- Inscription ---
  "register.title": "Créer un compte",
  "register.subtitle": "Gratuit — 1 projet et 1 génération IA pour commencer.",
  "register.firstName": "Prénom",
  "register.lastName": "Nom",
  "register.iAm": "Je suis",
  "register.country": "Pays",
  "register.city": "Ville",
  "register.submit": "Créer mon compte",
  "register.failed": "Inscription impossible pour le moment.",
  "register.alreadyRegistered": "Déjà inscrit ?",
  "register.checkInbox": "Vérifiez votre boîte mail",
  "register.linkSentTo":
    "Le lien a été envoyé à {email}. Il expire dans 24 heures. Pensez à regarder dans les indésirables.",
  "register.resend": "Renvoyer le lien",
  "register.resent": "Si un lien était en attente, un nouveau vient de partir.",

  // --- Chargement ---
  "load.failed": "Chargement impossible.",

  // --- Tableau de bord ---
  "dashboard.welcome": "Bienvenue, {name}",
  "dashboard.subtitle": "Voici l'état de vos projets et de vos échéances.",
  "dashboard.stat.projects": "Mes projets",
  "dashboard.stat.documents": "Documents générés",
  "dashboard.stat.opportunities": "Opportunités compatibles",
  "dashboard.stat.deadlines": "Échéances prochaines",
  "dashboard.stat.deadlinesHint": "45 prochains jours",
  "dashboard.recommended": "Opportunités recommandées",
  "dashboard.recommendedHint":
    "Chaque opportunité est affichée avec sa source et sa date de dernière vérification.",
  "dashboard.noRecommendation":
    "Aucune recommandation pour l'instant. Ouvrez un projet puis lancez l'analyse des financements compatibles — le calcul est gratuit.",
  "dashboard.amount": "Montant",
  "dashboard.deadline": "Date limite",
  "dashboard.verifiedOn": "Vérifié le",
  "dashboard.shortDisclaimer":
    "Le score de compatibilité est un indicateur d'aide à la décision et ne garantit en aucun cas l'obtention d'un financement.",

  // --- Projets ---
  "projects.title": "Mes projets",
  "projects.subtitle":
    "Chaque projet regroupe ses documents, ses versions et son score de maturité.",
  "projects.searchPlaceholder": "Rechercher un projet par titre…",
  "projects.empty": "Aucun projet pour l'instant",
  "projects.emptyDescription":
    "Créez votre premier projet : l'assistant vous guide en sept étapes, de l'idée au public visé.",
  "projects.emptyShort": "Créez votre premier projet : l'assistant vous guide en sept étapes.",
  "projects.create": "Créer mon projet",
  "projects.noResult": "Aucun résultat",
  "projects.noResultDescription": "Aucun projet ne correspond à cette recherche.",
  "projects.documentCount_one": "{count} document",
  "projects.documentCount_other": "{count} documents",
  "projects.updated": "Modifié {when}",

  // --- Profil ---
  "profile.title": "Profil",
  "profile.subtitle": "Ces informations n'apparaissent dans aucun document généré.",
  "profile.plan": "Offre {plan}",
  "profile.memberSince": "Membre depuis {date}",
  "profile.credits": "Crédits IA",
  "profile.profession": "Profession",
  "profile.bio": "Présentation",
  "profile.saved": "Profil enregistré.",
  "profile.saveFailed": "Enregistrement impossible.",
  "profile.languageHint":
    "La langue choisie suit votre compte d'un appareil à l'autre. Elle sert de langue proposée par défaut pour les documents générés, que vous pouvez changer à chaque génération.",

  // --- Offres ---
  "plan.FREE": "Gratuit",
  "plan.PRO_AUTHOR": "Pro Auteur",
  "plan.PRODUCER": "Producteur",

  // --- Paiement simulé ---
  "simulation.title": "Paiement simulé",
  "simulation.subtitle":
    "Aucun montant réel n'est encaissé : ce prestataire n'existe que pour le développement.",
  "simulation.missingReference": "Référence de paiement absente de l'adresse.",
  "simulation.reference": "Référence",
  "simulation.confirm": "Confirmer le paiement",
  "simulation.fail": "Simuler un échec",
  "simulation.failed": "Simulation impossible.",

  // --- Abonnement ---
  "billing.title": "Abonnement",
  "billing.subtitle":
    "Les prix et les quotas viennent du serveur : ils sont modifiables sans nouvelle version de l'application.",
  "billing.free": "Gratuit",
  "billing.pricePerMonth": "{amount} {currency} / mois",
  "billing.currentPlan": "Offre en cours : {plan}",
  "billing.renewsOn": "Reconduction le {date}.",
  "billing.cancelledUntil": "Résilié : actif jusqu'au {date}, sans reconduction.",
  "billing.noDeadline": "Offre gratuite, sans échéance.",
  "billing.cancel": "Résilier",
  "billing.cancelConfirm":
    "Résilier l'abonnement ? Il reste actif jusqu'à la fin de la période payée.",
  "billing.cancelFailed": "Résiliation impossible.",
  "billing.subscribe": "Souscrire",
  "billing.subscribeFailed": "Souscription impossible.",
  "billing.checkoutOpened":
    "Paiement ouvert sous la référence {reference}. Votre offre sera activée dès sa validation.",
  "billing.inUse": "en cours",
  "billing.creditsLeft_one": "{count} crédit IA restant",
  "billing.creditsLeft_other": "{count} crédits IA restants",
  "billing.unlimitedProjects": "Projets illimités",
  "billing.projectQuota_one": "{count} projet",
  "billing.projectQuota_other": "{count} projets",
  "billing.monthlyCredits_one": "{count} crédit IA par mois",
  "billing.monthlyCredits_other": "{count} crédits IA par mois",
  "billing.exportAllowed": "Export du dossier",
  "billing.exportDenied": "Sans export",
  "billing.matchingAllowed": "Matching financements",
  "billing.matchingDenied": "Matching limité",
  "billing.mobileMoney": "Paiement mobile money",
  "billing.mobileMoneyHint":
    "Renseignez le numéro à débiter avant de souscrire, si votre prestataire le demande.",
  "billing.phone": "Numéro de téléphone",
  "billing.payments": "Mes paiements",

  "paymentStatus.PENDING": "En attente",
  "paymentStatus.SUCCEEDED": "Réglé",
  "paymentStatus.FAILED": "Échoué",
  "paymentStatus.CANCELLED": "Annulé",
  "paymentStatus.REFUNDED": "Remboursé",

  // --- Recherche de financements ---
  "search.eyebrow": "Funding Intelligence",
  "search.title": "Financements",
  "search.subtitle":
    "Fonds, bourses, résidences, laboratoires, festivals et forums de coproduction.",
  "search.placeholder": "Rechercher un fonds, un organisme, un mot-clé…",
  "search.country": "Pays",
  "search.allCountries": "Tous les pays",
  "search.projectType": "Type de projet",
  "search.allTypes": "Tous les types",
  "search.category": "Type de financement",
  "search.allCategories": "Tous les dispositifs",
  "search.genre": "Genre",
  "search.allGenres": "Tous les genres",
  "search.language": "Langue",
  "search.allLanguages": "Toutes les langues",
  "search.minAmount": "Montant minimum",
  "search.noMinimum": "Aucun minimum",
  "search.sort": "Trier par",
  "search.sort.deadline": "Échéance la plus proche",
  "search.sort.recent": "Ajout le plus récent",
  "search.sort.amount": "Montant le plus élevé",
  "search.sort.name": "Ordre alphabétique",
  "search.includeClosed": "Inclure les dispositifs clos",
  "search.activeFilters_one": "{count} filtre actif",
  "search.activeFilters_other": "{count} filtres actifs",
  "search.failed": "Recherche impossible.",
  "search.empty": "Aucun dispositif ne correspond",
  "search.emptyFiltered":
    "Élargissez vos critères, ou incluez les dispositifs clos pour consulter les éditions passées.",
  "search.emptyBase":
    "La base des financements est encore vide. Un administrateur peut y ajouter des dispositifs depuis l'espace d'administration.",
  "search.results_one": "{count} dispositif trouvé",
  "search.results_other": "{count} dispositifs trouvés",
  "search.previous": "Précédent",
  "search.next": "Suivant",
  "search.pageOf": "Page {page} sur {total}",

  // --- Fiche d'un financement ---
  "opportunity.backToList": "← Financements",
  "opportunity.amountRange": "{min} – {max} {currency}",
  "opportunity.amountUpTo": "jusqu'à {max} {currency}",
  "opportunity.amountFrom": "à partir de {min} {currency}",
  "opportunity.demoTitle": "Donnée de démonstration",
  "opportunity.demoBody":
    "Ce dispositif est fictif. Il sert uniquement à illustrer le fonctionnement de la plateforme et ne correspond à aucun financement réel.",
  "opportunity.unverifiedTitle": "Fiche non vérifiée",
  "opportunity.unverifiedBody":
    "Les informations ci-dessous n'ont pas encore été contrôlées par l'équipe. Vérifiez-les sur le site de l'organisme avant de préparer votre candidature.",
  "opportunity.criteria": "Critères",
  "opportunity.amount": "Montant",
  "opportunity.deadline": "Date limite",
  "opportunity.opening": "Ouverture des candidatures",
  "opportunity.eligibleCountries": "Pays éligibles",
  "opportunity.allCountries": "Tous les pays",
  "opportunity.projectTypes": "Types de projet",
  "opportunity.allTypes": "Tous les types",
  "opportunity.genres": "Genres",
  "opportunity.allGenres": "Tous les genres",
  "opportunity.languages": "Langues",
  "opportunity.allLanguages": "Toutes les langues",
  "opportunity.requirements": "Pièces à fournir",
  "opportunity.requirementsHint": "Les documents marqués sont générables depuis l'AI Writer.",
  "opportunity.requirementsMissing":
    "Information non fournie. Consultez le règlement sur le site de l'organisme.",
  "opportunity.requirementOptional": "facultatif",
  "opportunity.sourceSection": "Source et candidature",
  "opportunity.sourceName": "Source de l'information",
  "opportunity.lastCheck": "Dernière vérification",
  "opportunity.apply": "Candidater sur le site de l'organisme",
  "opportunity.openSource": "Consulter la source",
  "opportunity.website": "Site de l'organisme",
  "opportunity.officialTerms":
    "Les conditions officielles publiées par l'organisme font foi. Vérifiez-les avant de déposer votre dossier : une fiche peut avoir été modifiée depuis sa dernière vérification.",
  "opportunity.notProvided": "Information non fournie.",

  // --- Assistant de création de projet ---
  "newProject.back": "← Mes projets",
  "newProject.title": "Nouveau projet",
  "newProject.subtitle":
    "Seul le titre est obligatoire. Tout le reste peut être complété plus tard — mais plus vous renseignez, meilleurs seront les documents générés.",
  "newProject.failed": "Création impossible pour le moment.",
  "newProject.stepAria": "Étape {number} : {title}",
  "newProject.stepCounter": "Étape {number} sur {total}",
  "newProject.step.general": "Informations générales",
  "newProject.step.generalHint": "Ce que le projet est, formellement.",
  "newProject.step.concept": "Concept",
  "newProject.step.conceptHint": "L'idée, en quelques phrases tenables.",
  "newProject.step.characters": "Personnages",
  "newProject.step.charactersHint": "Qui porte le récit — et contre qui.",
  "newProject.step.stakes": "Enjeux",
  "newProject.step.stakesHint": "Ce qui se perd si rien ne change.",
  "newProject.step.vision": "Vision du réalisateur",
  "newProject.step.visionHint": "Comment le film sera fait, et pourquoi ainsi.",
  "newProject.step.objectives": "Objectifs",
  "newProject.step.objectivesHint": "Ce que vous attendez du projet.",
  "newProject.step.audience": "Public cible",
  "newProject.step.audienceHint": "À qui le film s'adresse.",
  "newProject.titleField": "Titre du projet *",
  "newProject.genrePlaceholder": "Documentaire de création, drame…",
  "newProject.duration": "Durée cible (minutes)",
  "newProject.durationHint": "Détermine la longueur du scénario : 1 page ≈ 1 minute.",
  "newProject.logline": "Logline",
  "newProject.loglinePlaceholder": "Une à deux phrases : qui, ce qu'il veut, ce qui l'en empêche.",
  "newProject.concept": "Concept",
  "newProject.conceptPlaceholder": "De quoi parle le film, et par quel dispositif ?",
  "newProject.theme": "Thème",
  "newProject.character": "Personnage {number}",
  "newProject.removeCharacter": "Retirer",
  "newProject.characterName": "Nom",
  "newProject.characterRole": "Rôle (protagoniste…)",
  "newProject.characterAge": "Âge",
  "newProject.characterDescription": "Description : situation, désir, contradiction.",
  "newProject.characterArc": "Arc : ce qui change en lui du début à la fin.",
  "newProject.addCharacter": "Ajouter un personnage",
  "newProject.charactersHint":
    "L'IA n'invente jamais de personnage : elle n'utilise que ceux saisis ici.",
  "newProject.stakes": "Enjeux",
  "newProject.stakesPlaceholder":
    "Qu'est-ce qui est en jeu ? Que perd le protagoniste s'il échoue ?",
  "newProject.vision": "Vision du réalisateur",
  "newProject.visionPlaceholder":
    "Parti pris de mise en scène : image, son, montage, rapport aux personnes filmées.",
  "newProject.visionHint": "Ce champ nourrit directement la note de réalisation.",
  "newProject.objectives": "Objectifs",
  "newProject.objectivesPlaceholder":
    "Festivals visés, diffusion envisagée, partenaires recherchés…",
  "newProject.audience": "Public cible",
  "newProject.audiencePlaceholder": "Qui regarde ce film, où, et pourquoi ?",

  // --- Fiche projet ---
  "project.exportFailed": "Export impossible.",
  "project.deleteConfirm": "Supprimer définitivement ce projet et tous ses documents ?",
  "project.deleteFailed": "Suppression impossible.",
  "project.defaultExportName": "dossier",
  "project.readiness": "Maturité",
  "project.openWriter": "Ouvrir l'AI Writer",
  "project.matchingFunding": "Financements compatibles",
  "project.budget": "Budget et financement",
  "project.exportPdf": "Exporter le dossier (PDF)",
  "project.exportZip": "Tout exporter (ZIP)",
  "project.readinessTitle": "Maturité du projet : {score}/100",
  "project.readinessHint":
    "Indicateur interne d'avancement du dossier. Il ne préjuge d'aucune décision de financement.",
  "project.toImprove": "À améliorer",
  "project.nothingToImprove": "Le dossier est complet sur tous les critères suivis.",
  "project.documents": "Documents du dossier",
  "project.generateDocument": "Générer un document",
  "project.noDocument": "Aucun document",
  "project.noDocumentHint":
    "L'AI Writer produit vos documents à partir du contexte du projet, dans l'ordre qui garantit leur cohérence.",
  "project.documentMeta":
    "{words} mots · {pages} · version {version} · modifié {when}",
  "project.characters": "Personnages",
  "project.charactersHint": "L'IA ne s'appuie que sur les personnages saisis ici.",
  "project.noCharacter":
    "Aucun personnage saisi. Ajoutez-en depuis l'édition du projet pour améliorer la qualité des documents générés.",
  "project.arc": "Arc — ",

  // --- AI Writer ---
  // --- Dossier construit par la chaîne d'agents ---
  "project.openDossier": "Dossier de financement",
  "dossier.title": "Dossier de financement",
  "dossier.subtitle":
    "Huit experts se relaient sur votre projet, puis deux instances le contrôlent avant qu'il puisse partir.",
  "dossier.run": "Lancer la chaîne",
  "dossier.rerun": "Relancer la chaîne",
  "dossier.running": "Passage en cours…",
  "dossier.runFailed": "Le passage a échoué.",
  "dossier.cost_one": "{count} crédit",
  "dossier.cost_other": "{count} crédits",
  "dossier.costHint":
    "Un passage coûte un crédit par agent : les huit sont facturés, les reprises éventuelles aussi.",
  "dossier.progress": "Agent {done} sur {total}",
  "dossier.neverRun": "La chaîne n'a jamais tourné sur ce projet.",
  "dossier.neverRunHint":
    "Lancez-la pour obtenir une première version du dossier, puis les constats à corriger.",
  "dossier.lastRun": "Dernier passage {when}",
  "dossier.runsCount_one": "{count} passage",
  "dossier.runsCount_other": "{count} passages",

  // --- Verdict ---
  "dossier.exportable": "Le dossier peut partir",
  "dossier.notExportable": "Le dossier ne peut pas partir",
  "dossier.exportableHint": "Une relecture humaine reste due avant toute soumission.",
  "dossier.verdict.PASS": "Conforme",
  "dossier.verdict.PASS_WITH_WARNINGS": "Conforme, avec réserves",
  "dossier.verdict.REQUIRES_CORRECTION": "À corriger",
  "dossier.verdict.BLOCKED": "Bloqué",
  "dossier.stop": "Arrêter",
  "dossier.stopping": "Arrêt demandé…",
  "dossier.stopHint":
    "L'arrêt prend effet entre deux agents : les crédits des agents qui n'auront pas tourné vous sont rendus.",
  "dossier.stopPending":
    "L'agent en cours va au bout — son appel est déjà parti. La chaîne s'arrêtera juste après.",
  "dossier.stalled":
    "La reprise n'a rien changé : le problème demande une décision humaine, pas un tour de plus.",
  "dossier.exhausted":
    "La limite de reprises est atteinte. Le dossier reste non exportable.",

  // --- Constats ---
  "dossier.loadFailed": "Impossible de charger le dossier.",
  "dossier.noFindingHint": "Rien ne s'oppose au dossier pour l'instant.",
  "dossier.noHistoryHint": "Les modifications apparaîtront ici dès le premier passage.",
  "dossier.exportPdf": "Exporter le dossier (PDF)",
  "dossier.exportDraft": "Exporter le brouillon (PDF)",
  "dossier.exportDocx": "Exporter en Word",
  "dossier.exportFailed": "Export impossible.",
  "dossier.findings": "Constats",
  "dossier.noFinding": "Aucun constat ouvert.",
  "dossier.showResolved": "Voir aussi les constats levés",
  "dossier.hideResolved": "Masquer les constats levés",
  "dossier.resolved": "Levé",
  "dossier.openFindings_one": "{count} constat ouvert",
  "dossier.openFindings_other": "{count} constats ouverts",
  "dossier.blockingFindings_one": "dont {count} bloquant",
  "dossier.blockingFindings_other": "dont {count} bloquants",
  "dossier.toFix": "À corriger par",
  "dossier.suggestion": "Correction proposée",
  "severity.CRITICAL": "Bloquant",
  "severity.MAJOR": "Important",
  "severity.MINOR": "Mineur",
  "severity.PASS": "Conforme",

  // --- Sections ---
  "dossier.sections": "Le dossier",
  "dossier.emptySection": "Rien encore.",
  "dossier.section.concept": "Concept",
  "dossier.section.screenplay": "Scénario",
  "dossier.section.director_vision": "Vision de réalisation",
  "dossier.section.production_plan": "Plan de production",
  "dossier.section.financing_plan": "Plan de financement",
  "dossier.section.impact_analysis": "Impact",

  // --- Historique ---
  "dossier.history": "Modifications",
  "dossier.noHistory": "Aucune modification enregistrée.",
  "dossier.runs": "Passages",
  "dossier.runDetail": "Détail du passage",
  "dossier.rounds_one": "{count} reprise",
  "dossier.rounds_other": "{count} reprises",
  "dossier.noRound": "sans reprise",
  "dossier.step": "Étape {n}",

  // --- Agents ---
  "agent.DEVELOPMENT": "Développement",
  "agent.SCREENWRITER": "Scénario",
  "agent.DIRECTOR": "Réalisation",
  "agent.PRODUCER": "Production",
  "agent.FINANCING": "Financement",
  "agent.IMPACT": "Impact",
  "agent.CONSISTENCY_VALIDATOR": "Contrôle de cohérence",
  "agent.FUNDING_PACKAGE_VALIDATOR": "Contrôle du dossier",

  "writer.title": "AI Writer",
  "writer.subtitle":
    "Chaque document est écrit à partir du contexte du projet et des documents déjà rédigés, pour rester cohérent avec eux.",
  "writer.generationFailed": "Génération impossible.",
  "writer.notGenerated": "Non généré",
  "writer.versionWords": "v{version} · {words} mots",
  "writer.targetLength": "Longueur cible : {min} à {max} page(s).",
  "writer.screenplayLength": "Longueur pilotée par la durée cible : 1 page ≈ 1 minute.",
  "writer.promptVersion": "prompt v{version}",
  "writer.outline": "Structure imposée",
  "writer.missingDependencies": "Documents recommandés avant celui-ci",
  "writer.missingDependenciesBody":
    "{documents}. Vous pouvez générer quand même : les sections dépendantes indiqueront « Information non fournie. »",
  "writer.screenplayDuration": "Durée cible du scénario",
  "writer.minutes": "{count} min",
  "writer.passesHint_one":
    "Soit ~{pages} pages. Le scénario est écrit en une passe, coûtant 1 crédit.",
  "writer.passesHint_other":
    "Soit ~{pages} pages. Un scénario long est écrit en {count} passes successives, chacune reprenant la continuité de la précédente — et coûtant 1 crédit.",
  "writer.maxMinutes":
    " Durée maximale avec la configuration actuelle du serveur : {minutes} minutes.",
  "writer.documentLanguage": "Langue du document",
  "writer.documentLanguageHint":
    "Celle du dossier, pas celle du film : un long métrage en wolof se présente en français à un fonds francophone.",
  "writer.instructions": "Consignes complémentaires (facultatif)",
  "writer.instructionsPlaceholder": "Ton, angle à privilégier, contrainte d'un fonds précis…",
  "writer.generate": "Générer",
  "writer.regenerate": "Régénérer",
  "writer.openInEditor": "Ouvrir dans l'éditeur",
  "writer.cost_one": "Coût : {count} crédit · solde {balance}",
  "writer.cost_other": "Coût : {count} crédits · solde {balance}",
  "writer.queued": "En file d'attente…",
  "writer.writingPass": "Rédaction en cours — passe {current} sur {total}.",
  "writer.writing": "Rédaction en cours…",
  "writer.mayLeave": "Vous pouvez quitter cette page : la génération continue côté serveur.",
  "writer.underAMinute": "Cela prend généralement moins d'une minute.",
  "writer.resultTitle": "Document généré",
  "writer.resultMeta": "{words} mots · version {version} · {passes} passe(s) · {seconds} s",
  "writer.mockTitle": "Aucun fournisseur d'IA configuré",
  "writer.mockBody":
    "Le serveur tourne avec AI_PROVIDER=mock : le document reprend vos saisies et la structure attendue, sans rédaction. Renseignez AI_PROVIDER et AI_API_KEY pour une génération réelle.",
  "writer.missingInformation": "Informations à compléter",
  "writer.generatedWith": "Généré avec {provider} · {model} · prompt v{version}",
  "writer.projectDocuments": "Documents du projet",

  // --- Éditeur de document ---
  "editor.back": "← AI Writer",
  "editor.meta": "Version {version} · {words} mots · {pages}",
  "editor.statusLabel": "Statut du document",
  "editor.exportWord": "Exporter en Word",
  "editor.saveFailed": "Sauvegarde impossible.",
  "editor.actionFailed": "Action impossible.",
  "editor.restoreFailed": "Restauration impossible.",
  "editor.preview": "Aperçu",
  "editor.refine.IMPROVE": "Améliorer",
  "editor.refine.SHORTEN": "Raccourcir",
  "editor.refine.EXPAND": "Développer",
  "editor.refine.CORRECT": "Corriger",
  "editor.refineDone": "{action} — version {version} créée.",
  "editor.unsaved": "Modifications non enregistrées",
  "editor.saveError": "Échec de l'enregistrement",
  "editor.saved": "Enregistré",
  "editor.contentLabel": "Contenu du document",
  "editor.emptyDocument":
    "Ce document est vide. Passez en mode Édition ou régénérez-le depuis l'AI Writer.",
  "editor.history": "Historique des versions",
  "editor.historyHint":
    "Chaque génération, chaque sauvegarde manuelle et chaque restauration crée une version.",
  "editor.version": "Version {number}",
  "editor.currentVersion": "actuelle",
  "editor.versionMeta": "{date} · {words} mots",
  "editor.restore": "Restaurer",
  "editor.restoreConfirm":
    "Restaurer la version {number} ? Le texte actuel est conservé comme version précédente.",
  "editor.restored": "Version {number} restaurée.",

  // --- Financements compatibles d'un projet ---
  "match.title": "Financements compatibles",
  "match.subtitle": "Analyse calculée par règles — aucun crédit IA consommé. Dernier calcul {when}.",
  "match.rerun": "Relancer l'analyse",
  "match.failed": "Analyse impossible.",
  "match.explainFailed": "Explication impossible.",
  "match.emptyBase": "Aucun dispositif dans la base",
  "match.emptyBaseHint":
    "La base des financements est encore vide. Un administrateur peut y ajouter des dispositifs ; l'analyse se relancera ensuite automatiquement.",
  "match.seeFunding": "Voir les financements",
  "match.count_one": "{count} opportunité",
  "match.count_other": "{count} opportunités",
  "match.excluded_one": " · {count} écartée pour inéligibilité",
  "match.excluded_other": " · {count} écartées pour inéligibilité",
  "match.showIneligible": "Afficher les dispositifs inéligibles",
  "match.ineligible": "Inéligible",
  "match.conditionsMet_one": "condition remplie",
  "match.conditionsMet_other": "conditions remplies",
  "match.conditionsUnmet_one": "condition non remplie",
  "match.conditionsUnmet_other": "conditions non remplies",
  "match.conditionsUnknown_one": "condition à vérifier",
  "match.conditionsUnknown_other": "conditions à vérifier",
  "match.partialScore":
    "Score calculé sur {ratio} % de la grille : complétez votre projet pour l'affiner. Les critères non évaluables ne sont ni comptés pour, ni contre vous.",
  "match.hideDetail": "Masquer le détail",
  "match.showDetail": "Voir le détail du score",
  "match.noCredits": "Crédits IA épuisés",
  "match.alreadyExplained": "Explication déjà rédigée : aucun crédit ne sera débité",
  "match.costsOneCredit": "Consomme 1 crédit IA",
  "match.showExplanation": "Afficher l'analyse",
  "match.explainWithAi": "Analyser avec l'IA (1 crédit)",
  "match.fullEntry": "Fiche complète",
  "match.criteriaDetail": "Détail des critères",
  "match.requiredDocuments": "Documents exigés",
  "match.generateMissing": "Générer les documents manquants",
  "match.explanationTitle": "Analyse détaillée",
  "match.explanationFree": "Analyse déjà produite — aucun crédit débité",
  "match.explanationCost": "{credits} crédit · {provider}",

  // --- Budget et financement ---
  "budget.title": "Budget et financement",
  "budget.subtitle":
    "La trame propose les postes qu'un comité de lecture attend. Les montants, eux, ne sont jamais devinés : vous les renseignez.",
  "budget.actionFailed": "Action impossible.",
  "budget.saveFailed": "Enregistrement impossible.",
  "budget.forecast": "Budget prévisionnel",
  "budget.forecastMeta_one": "{count} poste · total {total}",
  "budget.forecastMeta_other": "{count} postes · total {total}",
  "budget.installTemplate": "Installer la trame",
  "budget.completeTemplate": "Compléter la trame",
  "budget.exportSpreadsheet": "Exporter en tableur",
  "budget.emptyTitle": "Budget vide",
  "budget.emptyBody":
    "Installez la trame : elle propose les postes attendus pour un projet de type {type}, à chiffrer ensuite ligne par ligne.",
  "budget.money": "{amount} {currency}",
  "budget.quantityOf": "Quantité — {label}",
  "budget.unitPriceOf": "Prix unitaire — {label}",
  "budget.deleteItem": "Supprimer {label}",
  "budget.total": "Total",
  "budget.addItem": "Ajouter un poste",
  "budget.addItemPlaceholder": "Ex. Location de caméra",
  "budget.itemPhase": "Phase du poste",
  "budget.add": "Ajouter",
  "budget.plan": "Plan de financement",
  "budget.planHint": "« Acquis » veut dire acquis : une source espérée reste dans le recherché.",
  "budget.totalBudget": "Budget total",
  "budget.secured": "Acquis",
  "budget.identified": "Identifié",
  "budget.sought": "Reste à financer",
  "budget.fundedShare": "{percentage} % du budget est acquis.",
  "budget.uncovered":
    " {amount} ne sont couverts par aucune source, même espérée.",
  "budget.removeSource": "Retirer",
  "budget.noSource": "Aucune source listée. Ajoutez les fonds, préachats et apports envisagés.",
  "budget.addSource": "Ajouter une source",
  "budget.addSourcePlaceholder": "Ex. Fonds de soutien national",
  "budget.sourceType": "Type de source",
  "budget.sourceAmount": "Montant",
  "budget.sourceAmountLabel": "Montant de la source",
  "budget.schedule": "Calendrier de production",
  "budget.scheduleHint": "Une ligne par phase : les dates que les financeurs demandent.",
  "budget.phaseStart": "Début — {phase}",
  "budget.phaseEnd": "Fin — {phase}",

  // --- Veille : file de validation ---
  "watch.title": "Veille — file de validation",
  "watch.subtitle":
    "La veille automatisée dépose ici ce qu'elle trouve. Rien n'est proposé aux auteurs avant votre relecture : un dispositif inexact engage leur dossier de financement.",
  "watch.actionFailed": "Action impossible.",
  "watch.rejected": "Candidat écarté.",
  "candidateStatus.PENDING": "À relire",
  "candidateStatus.APPROVED": "Publié",
  "candidateStatus.REJECTED": "Écarté",
  "watch.emptyPending":
    "Aucun candidat à relire. La veille n'a rien déposé depuis sa dernière exécution.",
  "watch.emptyOther": "Aucun candidat dans cet état.",
  "watch.candidateMeta": "Source : {source} · déposé le {date}",
  "watch.openSource": "Ouvrir la source ↗",
  "watch.extractedFields": "Champs extraits",
  "watch.noField": "Aucun champ extrait : tout est à saisir.",
  "watch.field.organization": "Organisme *",
  "watch.field.country": "Pays",
  "watch.field.deadline": "Date limite (AAAA-MM-JJ)",
  "watch.field.application_url": "Lien de candidature",
  "watch.editHint":
    "Ce que vous saisissez l'emporte sur l'extraction : c'est vous qui avez lu la source. Laissez vide un champ absent de la source plutôt que de le deviner.",
  "watch.publish": "Publier le dispositif",
  "watch.reject": "Écarter",
  "watch.reasonPlaceholder": "Motif (si écarté)",
  "watch.reasonLabel": "Motif — {name}",
  "watch.reason": "Motif : {note}",

  // --- Administration des financements ---
  "adminFunding.title": "Base des financements",
  "adminFunding.subtitle":
    "Chaque dispositif exige une source consultable : sans elle, il ne peut pas être publié comme ouvert.",
  "adminFunding.add": "Ajouter un dispositif",
  "adminFunding.verified": "Dispositif vérifié et publié.",
  "adminFunding.verifyFailed": "Vérification impossible.",
  "adminFunding.deleteConfirm": "Supprimer définitivement « {name} » ?",
  "adminFunding.deleted": "Dispositif supprimé.",
  "adminFunding.deleteFailed": "Suppression impossible.",
  "adminFunding.searchPlaceholder": "Rechercher un dispositif…",
  "adminFunding.empty": "Aucun dispositif",
  "adminFunding.emptyHint":
    "La base est vide. Ajoutez un premier dispositif : il apparaîtra ensuite dans la recherche et dans les analyses de compatibilité des projets.",
  "adminFunding.editEntry": "Modifier",
  "adminFunding.verifyAndPublish": "Vérifier et publier",
  "adminFunding.neverVerified": "Jamais vérifié",
  "adminFunding.formEdit": "Modifier le dispositif",
  "adminFunding.formNew": "Nouveau dispositif",
  "adminFunding.saved": "Dispositif mis à jour.",
  "adminFunding.created": "Dispositif ajouté.",
  "adminFunding.saveFailed": "Enregistrement impossible.",
  "adminFunding.name": "Nom du dispositif *",
  "adminFunding.organization": "Organisme *",
  "adminFunding.description": "Description",
  "adminFunding.traceability": "Traçabilité (obligatoire)",
  "adminFunding.sourceName": "Nom de la source *",
  "adminFunding.sourceNamePlaceholder": "Site officiel de l'organisme, appel à projets…",
  "adminFunding.sourceUrl": "URL de la source *",
  "adminFunding.traceabilityHint":
    "Un dispositif ne peut pas être publié comme ouvert sans son URL source. Elle est affichée aux utilisateurs avec la date de dernière vérification.",
  "adminFunding.organizationCountry": "Pays de l'organisme",
  "adminFunding.eligibleCountries": "Pays éligibles (séparés par des virgules)",
  "adminFunding.eligibleCountriesPlaceholder":
    "Sénégal, Cameroun, Côte d'Ivoire — laisser vide si ouvert à tous",
  "adminFunding.eligibleCountriesHint":
    "Vide = ouvert à tous les pays. Un projet dont le pays n'y figure pas est marqué inéligible, avec la raison.",
  "adminFunding.acceptedTypes": "Types de projet acceptés",
  "adminFunding.acceptedTypesHint": "Aucune sélection = ouvert à tous les types.",
  "adminFunding.genres": "Genres (virgules)",
  "adminFunding.languages": "Langues (virgules)",
  "adminFunding.minAmount": "Montant minimum",
  "adminFunding.maxAmount": "Montant maximum",
  "adminFunding.currency": "Devise",
  "adminFunding.applicationUrl": "Lien de candidature",
  "adminFunding.website": "Site de l'organisme",
  "adminFunding.requirementsText": "Pièces à fournir (texte libre)",
  "adminFunding.requiredDocuments": "Documents exigés",
  "adminFunding.requiredDocumentsHint":
    "Un document rattaché à un type permet au matching de dire à l'auteur ce qui manque à son dossier.",
  "adminFunding.requirementLabel": "Intitulé (Synopsis, Budget…)",
  "adminFunding.noDocumentType": "Aucun type rattaché",
  "adminFunding.removeRequirement": "Retirer",
  "adminFunding.addRequirement": "Ajouter une pièce",
  "adminFunding.status": "Statut",
  "adminFunding.statusUnverified": "Non vérifié — non présenté comme actif",
  "adminFunding.statusOpen": "Ouvert — vérifié et publié",
  "adminFunding.statusUpcoming": "À venir",
  "adminFunding.statusClosed": "Clos",
  "adminFunding.submitNew": "Ajouter le dispositif",

  // --- Page d'accueil publique ---
  "landing.nav.platform": "Plateforme",
  "landing.nav.funding": "Financements",
  "landing.nav.pricing": "Tarifs",
  "landing.nav.faq": "FAQ",
  "landing.nav.login": "Connexion",
  "landing.cta": "Créer mon projet",
  "landing.hero.eyebrow": "De l'idée au financement de votre projet audiovisuel",
  "landing.hero.title": "Transformez votre idée en projet audiovisuel finançable.",
  "landing.hero.body":
    "Développez votre projet, créez votre dossier et découvrez les financements adaptés à votre film — avec un assistant conçu pour les réalités du cinéma africain francophone.",
  "landing.hero.discover": "Découvrir la plateforme",
  "landing.hero.noCard": "Offre gratuite · Aucune carte bancaire requise",

  "landing.problem.eyebrow": "Le problème",
  "landing.problem.title": "Le film existe. Le dossier, rarement.",
  "landing.problem.body":
    "Chaque année, des projets solides sont écartés non pas pour leur qualité artistique, mais parce que le dossier ne répond pas aux attentes des comités.",
  "landing.problem.1": "Structurer un projet encore flou",
  "landing.problem.2": "Rédiger un dossier au niveau attendu",
  "landing.problem.3": "Comprendre ce que veulent vraiment les financeurs",
  "landing.problem.4": "Trouver les fonds adaptés à son film",
  "landing.problem.5": "Suivre les appels à projets et leurs échéances",
  "landing.problem.6": "Construire un budget crédible",
  "landing.problem.7": "Préparer un pitch qui tient en trois minutes",
  "landing.problem.8": "Travailler sans outil pensé pour l'Afrique",

  "landing.solution.eyebrow": "La solution",
  "landing.solution.title": "Une chaîne continue : idée → projet → dossier → financement.",
  "landing.solution.body":
    "FilmFund Africa n'est pas un ERP audiovisuel. Chaque fonctionnalité renforce cette seule chaîne.",
  "landing.pillar.development": "Project Development",
  "landing.pillar.developmentBody":
    "Structurez votre projet étape par étape : concept, personnages, enjeux, vision, public.",
  "landing.pillar.funding": "Funding Intelligence",
  "landing.pillar.fundingBody":
    "Une base d'opportunités qui conserve sa source et sa date de dernière vérification.",
  "landing.pillar.ai": "AI Assistant",
  "landing.pillar.aiBody":
    "Un assistant spécialisé dans les documents du cinéma, pas un générateur de texte générique.",
  "landing.pillar.management": "Project Management",
  "landing.pillar.managementBody":
    "Vos documents, leurs versions et vos échéances au même endroit.",

  "landing.writer.title": "Des documents cohérents entre eux, pas onze textes indépendants.",
  "landing.writer.body":
    "Chaque document est écrit à partir du contexte complet du projet et des documents déjà validés : la note de réalisation prolonge la note d'intention, le traitement suit le synopsis, le scénario respecte le traitement.",
  "landing.writer.point1":
    "Structure professionnelle imposée et longueur cible — jamais de remplissage.",
  "landing.writer.point2":
    "Durée de scénario au choix (10, 26, 52, 90, 120 min) : 1 page ≈ 1 minute.",
  "landing.writer.point3": "Versions sauvegardées, comparables et restaurables à tout moment.",
  "landing.writer.point4":
    "Information absente ? Le document écrit « Information non fournie. » plutôt que d'inventer.",
  "landing.writer.documents": "Documents générables",
  "landing.writer.rework": "Retravailler en un clic",
  "landing.writer.regenerate": "Régénérer",

  "landing.funding.eyebrow": "Funding Intelligence & Matching",
  "landing.funding.title": "Les financements qui correspondent vraiment à votre projet.",
  "landing.funding.body":
    "Fonds, bourses, résidences, laboratoires, festivals et forums de coproduction, filtrés par pays, genre, type de projet, budget et langue.",
  "landing.funding.example": "Exemple d'analyse de compatibilité",
  "landing.funding.exampleFund": "Fonds {letter}",
  "landing.funding.exampleNote":
    "Pour chaque résultat : pourquoi ce fonds correspond, conditions remplies, conditions manquantes, documents requis, date limite, montant potentiel et lien de candidature.",
  "landing.funding.notTitle": "Ce que le score n'est pas",
  "landing.funding.notBody":
    "Le score de compatibilité est un indicateur d'aide à la décision. Il ne constitue en aucun cas une garantie de financement : les conditions officielles de chaque organisme font foi.",
  "landing.funding.sourceNote":
    "Aucune opportunité n'est affichée sans sa source et sa date de dernière vérification.",

  "landing.budget.lines": "Postes budgétaires",
  "landing.budget.development": "recherche, écriture, repérages",
  "landing.budget.preProduction": "casting, préparation, autorisations",
  "landing.budget.production": "équipe, matériel, transport, décors",
  "landing.budget.postProduction": "montage, étalonnage, mixage, sous-titrage",
  "landing.budget.distribution": "festivals, communication, marketing",
  "landing.budget.eyebrow": "Budget & plan de financement",
  "landing.budget.title": "Un budget que le comité peut lire sans vous.",
  "landing.budget.body":
    "Budget par phase, plan de financement par source, calcul automatique du financement acquis, du financement recherché et du pourcentage couvert. Calendrier de production du développement à la distribution.",

  "landing.audiences.eyebrow": "Pour qui ?",
  "landing.audiences.title": "Des auteurs isolés aux structures qui accompagnent.",
  "landing.audience.author": "Auteur · Réalisateur",
  "landing.audience.author1": "Créer ses projets",
  "landing.audience.author2": "Générer ses documents",
  "landing.audience.author3": "Chercher des financements",
  "landing.audience.author4": "Suivre ses échéances",
  "landing.audience.producer": "Producteur",
  "landing.audience.producer1": "Plusieurs projets",
  "landing.audience.producer2": "Budgets",
  "landing.audience.producer3": "Équipes et collaborateurs",
  "landing.audience.producer4": "Suivi des candidatures",
  "landing.audience.institution": "Institution",
  "landing.audience.institution1": "École de cinéma",
  "landing.audience.institution2": "Incubateur, fonds culturel",
  "landing.audience.institution3": "ONG, organisme de formation",
  "landing.audience.institution4": "Gestion de cohortes",

  "landing.pricing.eyebrow": "Tarifs",
  "landing.pricing.title": "Trois offres, une seule promesse.",
  "landing.pricing.body":
    "L'usage de l'IA fonctionne au crédit : chaque génération en consomme, afin que le service reste soutenable et prévisible.",
  "landing.pricing.mostChosen": "Le plus choisi",
  "landing.pricing.perMonth": "FCFA / mois",
  "landing.pricing.freeBody": "Pour tester la plateforme sur un projet.",
  "landing.pricing.free1": "1 projet",
  "landing.pricing.free2": "1 génération IA",
  "landing.pricing.free3": "Veille limitée",
  "landing.pricing.freeCta": "Commencer",
  "landing.pricing.proBody": "Pour un auteur qui porte ses projets jusqu'au dépôt.",
  "landing.pricing.pro1": "Projets illimités",
  "landing.pricing.pro2": "Génération IA complète",
  "landing.pricing.pro3": "Veille personnalisée",
  "landing.pricing.pro4": "Matching des financements",
  "landing.pricing.pro5": "Export PDF et Word",
  "landing.pricing.proCta": "Choisir Pro Auteur",
  "landing.pricing.producerBody": "Pour une structure qui gère un portefeuille de projets.",
  "landing.pricing.producer1": "Gestion multi-projets",
  "landing.pricing.producer2": "Budget avancé",
  "landing.pricing.producer3": "Collaboration d'équipe",
  "landing.pricing.producer4": "Export complet du dossier",
  "landing.pricing.producer5": "Suivi des candidatures",
  "landing.pricing.producerCta": "Choisir Producteur",

  "landing.faq.title": "Questions fréquentes",
  "landing.faq.q1": "L'IA écrit-elle mon film à ma place ?",
  "landing.faq.a1":
    "Non. Elle met en forme ce que vous lui donnez, selon la structure attendue par les comités de lecture. Si une information manque, elle l'indique au lieu de l'inventer — jamais de personnage, d'événement ou de financement fabriqué.",
  "landing.faq.q2": "À qui appartiennent les documents générés ?",
  "landing.faq.a2":
    "À vous. Vous les modifiez, les exportez en PDF ou en Word, et vous les emportez quand vous le souhaitez.",
  "landing.faq.q3": "Le score de compatibilité garantit-il un financement ?",
  "landing.faq.a3":
    "Non, en aucun cas. C'est un indicateur d'aide à la décision qui compare votre projet aux critères publiés d'un dispositif. Les conditions officielles de l'organisme font foi.",
  "landing.faq.q4": "Les opportunités affichées sont-elles à jour ?",
  "landing.faq.a4":
    "Chaque opportunité conserve sa source et sa date de dernière vérification, affichées avec elle. Les données de démonstration sont explicitement marquées comme fictives.",
  "landing.faq.q5": "Puis-je générer un scénario de long métrage complet ?",
  "landing.faq.a5":
    "Oui. Vous choisissez la durée cible (10 à 120 minutes) ; un scénario long est écrit en plusieurs passes successives, chacune reprenant la continuité de la précédente. La longueur vient du nombre de séquences, jamais d'un étirement artificiel.",
  "landing.faq.q6": "Mes projets sont-ils visibles par d'autres utilisateurs ?",
  "landing.faq.a6":
    "Non. Chaque projet est strictement cloisonné à son compte. Un utilisateur ne peut jamais accéder aux projets d'un autre.",

  "landing.final.title": "Votre prochain dossier peut être prêt cette semaine.",
  "landing.final.body":
    "Créez votre compte, renseignez votre concept, et repartez avec un dossier structuré et une liste de financements à viser.",
  "landing.final.haveAccount": "J'ai déjà un compte",

  // --- Client HTTP ---
  "api.sessionExpired": "Session expirée. Reconnectez-vous.",
  "api.jobTrackingAborted": "Suivi de la génération interrompu.",
  "api.generationFailed": "La génération a échoué.",
  "api.generationCancelled": "Génération arrêtée. Les passes qui n'ont pas tourné vous sont rendues.",

  // --- Client HTTP (suite) ---
  "api.httpError": "Erreur {status}",
} as const;

export type MessageKey = keyof typeof fr;
