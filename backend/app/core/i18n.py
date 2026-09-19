"""Messages de l'API, en francais et en anglais.

L'interface a ses propres catalogues (`frontend/src/lib/i18n/`) ; ceux-ci
couvrent ce que l'interface ne peut pas traduire parce qu'elle ne fait que le
reafficher : le `detail` des reponses HTTP, et les libelles que le serveur
calcule — criteres de compatibilite et criteres de maturite.

La langue de l'appelant vient, dans l'ordre : de la preference enregistree sur
son profil, posee des que la dependance d'authentification l'a identifie ; de
l'en-tete `Accept-Language`, que le frontend renseigne avec la langue choisie
dans l'interface plutot qu'avec celle du navigateur ; puis de
`DEFAULT_LOCALE`. Le `code` d'une erreur ne depend d'aucune langue : c'est sur
lui que le client se branche, jamais sur la phrase.

**Le francais est la langue de reference** : c'est lui qui definit les cles.
En TypeScript, le compilateur refuse une cle manquante ; Python n'offre pas
cette garantie, alors `tests/test_i18n.py` la remplace — il compare les deux
jeux de cles et echoue a la moindre divergence. Une traduction oubliee ne se
voit pas a la relecture ; elle doit faire echouer quelque chose.

Les valeurs portent des variables `{ainsi}`, remplies au moment du rendu. Un
message qui doit s'accorder s'ecrit en deux cles, `_one` et `_other`, et c'est
`plural()` qui choisit — 0 est singulier en francais, pluriel en anglais.
"""

from __future__ import annotations

from typing import Any, Literal

from fastapi import Request

from app.core.config import settings

Locale = Literal["fr", "en"]
LOCALES: tuple[Locale, ...] = ("fr", "en")

FR: dict[str, str] = {
    # --- Erreurs generiques ---
    "error.validation": "Données invalides.",
    "error.database": "Erreur interne côté base de données.",
    # --- Authentification et compte ---
    "auth.required": "Authentification requise.",
    "auth.tokenInvalidOrExpired": "Jeton invalide ou expiré.",
    "auth.tokenInvalid": "Jeton invalide.",
    "auth.userNotFound": "Utilisateur introuvable.",
    "auth.accountSuspended": "Ce compte est suspendu.",
    "auth.adminOnly": "Accès réservé aux administrateurs.",
    "auth.accountNotFound": "Compte introuvable.",
    "auth.accountNotFoundOrSuspended": "Compte introuvable ou suspendu.",
    "auth.refreshInvalidOrExpired": "Jeton de rafraîchissement invalide ou expiré.",
    "auth.verificationLinkInvalid": "Lien de confirmation invalide ou expiré.",
    "auth.resetLinkInvalid": "Lien de réinitialisation invalide ou expiré.",
    "auth.currentPasswordWrong": "Mot de passe actuel incorrect.",
    "auth.logout": "Déconnexion effectuée.",
    "auth.passwordUpdatedSignIn": "Mot de passe mis à jour. Vous pouvez vous connecter.",
    "auth.passwordUpdated": "Mot de passe mis à jour.",
    # --- Projets et documents ---
    "project.notFound": "Projet introuvable.",
    "project.deleted": "Projet supprimé.",
    "character.notFound": "Personnage introuvable.",
    "character.deleted": "Personnage supprimé.",
    "document.notFound": "Document introuvable.",
    "document.deleted": "Document supprimé.",
    "document.versionNotFound": "Version introuvable.",
    # --- Financements ---
    "funding.opportunityNotFound": "Dispositif de financement introuvable.",
    "funding.requirementNotFound": "Exigence introuvable.",
    "funding.opportunityDeleted": "Dispositif supprimé.",
    "funding.opportunityPublished": "Dispositif publié : {name}.",
    "funding.candidateNotFound": "Candidat introuvable.",
    # --- Budget ---
    "budget.itemNotFound": "Poste budgétaire introuvable.",
    "budget.itemDeleted": "Poste supprimé.",
    "budget.sourceNotFound": "Source de financement introuvable.",
    "budget.sourceDeleted": "Source supprimée.",
    "budget.phaseRemoved": "Phase retirée du calendrier.",
    # --- Abonnements et paiements ---
    "billing.paymentNotFound": "Paiement introuvable.",
    "billing.planNotFound": "Offre introuvable.",
    "billing.planUpdated": "Offre mise à jour.",
    "billing.subscriptionAlreadyCancelled": "Cet abonnement est déjà résilié.",
    "billing.planUnavailable": "Cette offre n'est plus proposée.",
    "billing.subscriptionClosed": (
        "FilmFund Africa est en bêta privée : la souscription est fermée. Les "
        "offres et les abonnements existants sont conservés, et la souscription "
        "rouvrira à l'ouverture commerciale."
    ),
    # --- Administration ---
    "admin.userNotFound": "Utilisateur introuvable.",
    "admin.cannotSuspendSelf": "Vous ne pouvez pas suspendre votre propre compte.",
    "admin.accountSuspended": "Compte suspendu.",
    # --- Tableau de bord ---
    "notification.notFound": "Notification introuvable.",
    "notification.markedRead": "Notification marquée comme lue.",
    # --- Taches de generation ---
    "job.notFound": "Tâche introuvable.",
    "job.alreadyFinished": (
        "Cette génération est déjà terminée ({status}) : il n'y a plus rien à arrêter."
    ),
    # --- Fournisseur d'IA ---
    "ai.unreachable": "Fournisseur IA injoignable : {reason}",
    "ai.emptyResponse": "Le fournisseur IA a renvoyé une réponse vide.",
    "ai.refused": (
        "Le modèle a refusé de traiter cette demande ({reason}). Reformulez, ou "
        "signalez-le si le refus vous paraît infondé."
    ),
    # --- Session et quotas ---
    "auth.sessionPasswordChanged": (
        "Session expirée : le mot de passe a été modifié. Reconnectez-vous."
    ),
    "auth.registrationClosed": (
        "FilmFund Africa est en bêta privée : la création de compte est fermée. "
        "L'inscription rouvrira à l'ouverture commerciale ; si vous avez déjà un "
        "compte, vous pouvez vous connecter."
    ),
    "quota.exportNotIncluded": (
        "L'export n'est pas inclus dans l'offre « {plan} ». Passez à une offre "
        "supérieure pour exporter votre dossier."
    ),
    "quota.matchingNotIncluded": (
        "Le rapprochement avec les financements n'est pas inclus dans l'offre "
        "« {plan} ». La recherche reste ouverte — vous pouvez consulter tous les "
        "dispositifs — mais l'analyse de compatibilité de votre projet demande une "
        "offre supérieure."
    ),
    # --- Quotas ---
    "auth.emailNotVerified": (
        "Adresse non confirmée. Ouvrez le lien reçu par e-mail, ou demandez-en un "
        "nouveau."
    ),
    "quota.projectLimit": (
        "Votre offre « {plan} » est limitée à {max} projet(s). Passez à une offre "
        "supérieure pour en créer davantage."
    ),
    "quota.creditsExhausted": (
        "Crédits IA épuisés pour l'offre « {plan} ». Ils seront rechargés à la "
        "prochaine période, ou passez à une offre supérieure."
    ),
    "quota.creditsInsufficient": (
        "Crédits IA insuffisants : cette génération en coûte {cost} et il vous en reste "
        "{remaining} (offre « {plan} »). Ils seront rechargés à la prochaine période, "
        "ou passez à une offre supérieure."
    ),
    # --- Documents et generation ---
    "document.typeNotApplicable": (
        "Le document « {document} » ne s'applique pas à un projet de type {type}."
    ),
    "document.alreadyExists": (
        "Ce document existe déjà. Activez « remplacer » pour le régénérer."
    ),
    "document.empty": "Ce document est vide : générez-le avant de le retravailler.",
    "screenplay.tooLong": (
        "Durée trop longue pour une génération en une fois : {minutes} minutes "
        "demanderaient {passes} passes, au-delà de la limite de {ceiling}. Maximum "
        "réalisable avec la configuration actuelle : {maximum} minutes."
    ),
    "prompt.notFound": "Aucun prompt n'est défini pour le document « {document} ».",
    "agent.notFound": "Aucun agent n'est défini pour le rôle « {agent} ».",
    "dossier.runNotFound": "Passage introuvable.",
    "export.dossierNotBuilt": (
        "La chaîne d'agents n'a pas encore tourné sur ce projet : il n'y a rien "
        "à exporter."
    ),
    "agent.outputNotJson": (
        "Le modèle n'a pas renvoyé d'objet JSON exploitable pour cette étape."
    ),
    "agent.outputInvalid": "Sortie d'agent invalide : {details}",
    "agent.patchNotAllowed": (
        "L'agent « {agent} » contrôle le dossier et ne peut pas le modifier."
    ),
    "ai.providerUnknown": (
        "Fournisseur IA inconnu : « {name} ». Valeurs acceptées : anthropic, openai, "
        "mock."
    ),
    "ai.modelRequired": (
        "AI_MODEL est requis avec AI_PROVIDER={provider} : aucun modèle par défaut "
        "n'est supposé à votre place."
    ),
    "ai.keyProviderRequired": (
        "Précisez à quel fournisseur cette clé appartient : une clé Anthropic "
        "envoyée à OpenAI apparaîtrait dans les journaux d'un tiers."
    ),
    "ai.keyNotApplicable": (
        "Le fournisseur « {provider} » n'appelle aucun service externe : il n'a "
        "pas de clé."
    ),
    "secret.unreadable": (
        "Un secret enregistré est illisible : la clé de chiffrement du serveur "
        "(SECRETS_KEY, ou JWT_SECRET à défaut) a changé depuis son "
        "enregistrement. Ressaisissez-le."
    ),
    "funding.sourceRequiredToPublish": (
        "Impossible de publier ce dispositif comme ouvert sans son URL source."
    ),
    "funding.sourceRequiredToVerify": (
        "Renseignez l'URL source avant de marquer ce dispositif comme vérifié."
    ),
    # --- Fournisseur d'IA ---
    "ai.keyRequired": "AI_API_KEY est requis lorsque AI_PROVIDER={provider}.",
    # Le motif exact du fournisseur, et non une supposition : un solde épuisé,
    # un modèle retiré et un payload invalide arrivent tous en 400.
    "ai.providerError": "Erreur du fournisseur IA ({status}) : {reason}",
    # --- Veille ---
    "auth.invalidCredentials": "Adresse e-mail ou mot de passe incorrect.",
    "candidate.sourceRequired": "Un candidat sans URL source n'est pas recevable.",
    "candidate.alreadyReviewed": "Ce candidat est déjà « {status} ».",
    "candidate.organizationRequired": (
        "L'organisme est obligatoire : complétez-le avant de publier."
    ),
    # --- Abonnements ---
    "billing.planIsFree": "L'offre gratuite ne se paie pas : elle est déjà active par défaut.",
    "billing.planAlreadyActive": "Vous êtes déjà abonné à l'offre « {plan} ».",
    "billing.paymentAlreadySettled": "Ce paiement est déjà « {status} ».",
    "billing.noPaidSubscription": "Aucun abonnement payant à résilier.",
    # --- Routes ---
    "export.nothingToExport": (
        "Aucun document à exporter : générez d'abord au moins un document."
    ),
    "automation.disabled": "Automatisation désactivée : aucune clé d'API configurée.",
    "automation.invalidKey": "Clé d'API invalide.",
    "automation.unknownTask": "Tâche inconnue : {task}. Disponibles : {available}.",
    "automation.taskRun": "Tâche {task} exécutée : {count} élément(s) traité(s).",
    "billing.cancelledUntil": "Abonnement résilié. Votre offre reste active jusqu'au {date}.",
    "billing.cancelled": "Abonnement résilié.",
    "billing.simulationUnavailable": (
        "Route de simulation indisponible : elle n'existe qu'en développement avec le "
        "prestataire simulé."
    ),
    "billing.simulated": "Paiement simulé : {status}.",
    "billing.invalidSignature": "Signature de notification invalide.",
    "billing.unreadableNotification": "Notification illisible.",
    "billing.notificationHandled": "Notification traitée : paiement {status}.",
    # --- Authentification (reponses) ---
    "auth.verificationSent": (
        "Si cette adresse peut être utilisée, un e-mail de confirmation vient d'être "
        "envoyé. Ouvrez le lien qu'il contient pour activer votre compte."
    ),
    "auth.resetSent": (
        "Si un compte existe pour cette adresse, un lien de réinitialisation vient "
        "d'être envoyé."
    ),
    "auth.devToken": "{message} [DEV] Jeton : {token}",
    # --- Prestataires de paiement ---
    "payment.manualNoNotification": (
        "L'encaissement manuel ne reçoit pas de notification : la validation se fait "
        "depuis l'administration."
    ),
    "payment.referenceMissing": "Notification sans référence de paiement.",
    "payment.unknownStatus": "Statut de paiement inconnu : {status}",
    "payment.unknownProvider": "Prestataire de paiement inconnu : {code}",
    # --- Criteres de compatibilite ---
    "criterion.country": "Pays éligible",
    "criterion.projectType": "Type de projet",
    "criterion.genre": "Genre",
    "criterion.language": "Langue",
    "criterion.duration": "Format et durée",
    "criterion.deadline": "Échéance",
    "criterion.documents": "Documents exigés",
    "match.country.allOpen": "Dispositif ouvert à tous les pays.",
    "match.country.unknown": (
        "Pays du projet non renseigné : l'éligibilité géographique n'a pas pu être "
        "vérifiée."
    ),
    "match.country.met": "{country} figure parmi les pays éligibles.",
    "match.country.unmet": "{country} ne figure pas parmi les pays éligibles ({list}).",
    "match.type.allOpen": "Dispositif ouvert à tous les types de projet.",
    "match.type.met": "Le type de projet correspond au dispositif.",
    "match.type.unmet": (
        "Le type de projet ne fait pas partie de ceux acceptés par ce dispositif."
    ),
    "match.genre.noRestriction": "Aucune restriction de genre.",
    "match.genre.unknown": "Genre du projet non renseigné.",
    "match.genre.met": "Le genre « {genre} » est recherché.",
    "match.genre.close": "Le genre « {genre} » est proche de la ligne éditoriale.",
    "match.genre.unmet": (
        "Le genre « {genre} » ne correspond pas à la ligne éditoriale ({list})."
    ),
    "match.language.noRestriction": "Aucune restriction de langue.",
    "match.language.met": "Le projet est en {language}.",
    "match.language.unmet": (
        "Le dispositif attend un projet en {list} ; le vôtre est en {language}."
    ),
    "match.duration.unknown": "Durée du projet non renseignée.",
    "match.duration.tooLong": (
        "Le dispositif cible les formats courts ; le projet fait {minutes} min."
    ),
    "match.duration.tooShort": (
        "Le dispositif cible les formats longs ; le projet fait {minutes} min."
    ),
    "match.duration.met": "La durée visée ({minutes} min) est cohérente.",
    "match.deadline.closed": "Ce dispositif est clos.",
    "match.deadline.unknown": (
        "Aucune date limite renseignée : vérifiez le calendrier sur le site de "
        "l'organisme."
    ),
    "match.deadline.passed": "La date limite est dépassée depuis le {date}.",
    "match.deadline.tight": (
        "Échéance dans {days} jour(s) : le délai est court pour finaliser un dossier."
    ),
    "match.deadline.met": "Échéance le {date}, soit {days} jours.",
    "match.documents.unknown": (
        "Pièces à fournir non détaillées : consultez le règlement du dispositif."
    ),
    "match.documents.met": "Tous les documents exigés sont rédigés dans votre dossier.",
    "match.documents.unmet": (
        "{written}/{required} document(s) exigé(s) rédigé(s) — manquant(s) : {missing}."
    ),
    # --- Score de maturite ---
    "score.concept": "Concept",
    "score.narration": "Narration",
    "score.characters": "Personnages",
    "score.vision": "Vision artistique",
    "score.feasibility": "Faisabilité",
    "score.budget": "Budget",
    "score.fundingPlan": "Plan de financement",
    "score.market": "Potentiel marché",
    "score.dossier": "Dossier",
    "score.toFill": "À renseigner : {list}",
    "score.missing": "Manquant : {list}",
    "score.fillThem": "Renseignez {list}.",
    "score.addThem": "Ajoutez {list}.",
    "score.completeThem": "Complétez {list}.",
    "score.specifyThem": "Précisez {list}.",
    "score.describeThem": "Décrivez {list}.",
    "score.concept.complete": "Concept complet.",
    "score.field.logline": "la logline",
    "score.field.concept": "le concept",
    "score.field.theme": "le thème",
    "score.field.genre": "le genre",
    "score.field.country": "le pays",
    "score.field.shortSynopsis": "un synopsis court développé",
    "score.field.longSynopsis": "un synopsis long",
    "score.field.treatment": "un traitement ou un scénario",
    "score.field.directorVision": "la vision du réalisateur",
    "score.field.intentNote": "la note d'intention",
    "score.field.directingNote": "la note de réalisation",
    "score.field.duration": "la durée cible",
    "score.field.productionCountry": "le pays de production",
    "score.field.objectives": "les objectifs du projet",
    "score.field.audience": "le public cible",
    "score.field.stakes": "les enjeux",
    "score.narration.solid": "Narration solide.",
    "score.characters.none": "Aucun personnage saisi.",
    "score.characters.noneImprovement": (
        "Saisissez au moins le protagoniste et la force antagoniste."
    ),
    "score.characters.partial": "{described}/{count} personnage(s) décrit(s).",
    "score.characters.partialImprovement": (
        "Complétez la description et l'arc de chaque personnage."
    ),
    "score.characters.documented": "{count} personnage(s) documenté(s).",
    "score.characters.documentedImprovement": "Générez la présentation des personnages.",
    "score.vision.documented": "Vision artistique documentée.",
    "score.feasibility.defined": "Cadre de production défini.",
    "score.budget.missing": "Budget non renseigné.",
    "score.budget.missingImprovement": (
        "Budget non renseigné : construisez le budget prévisionnel."
    ),
    "score.budget.detail": "Budget de {amount} {currency} sur {items} poste(s).",
    "score.budget.detailImprovement": "Détaillez davantage les postes budgétaires.",
    "score.fundingPlan.missing": "Plan de financement absent.",
    "score.fundingPlan.missingImprovement": (
        "Plan de financement absent : listez les sources envisagées."
    ),
    "score.fundingPlan.detail": (
        "{percentage} % du budget couvert par des financements identifiés."
    ),
    "score.fundingPlan.detailImprovement": (
        "Identifiez d'autres sources pour couvrir le financement recherché."
    ),
    "score.market.defined": "Positionnement défini.",
    "score.dossier.detail": "{present}/{total} documents clés rédigés.",
    "score.dossier.improvement": "Il manque {count} document(s) clé(s) au dossier.",
    # --- Notifications ---
    "notification.matchFound.title": "{count} financement(s) compatible(s) avec « {project} »",
    "notification.matchFound.body": (
        "L'analyse a identifié {count} dispositif(s) dont la compatibilité dépasse "
        "{threshold} %. Le score est un indicateur d'aide à la décision, pas une "
        "garantie de financement."
    ),
    "notification.deadlineSoon.title": "Échéance dans {days} jours — {opportunity}",
    "notification.deadlineSoon.body": (
        "La date limite de « {opportunity} » ({organization}) est fixée au {date} pour "
        "votre projet « {project} »."
    ),
    "notification.incompleteFile.title": "Votre dossier est incomplet",
    "notification.incompleteFile.body": (
        "Le projet « {project} » atteint {score}/100. Complétez-le pour améliorer vos "
        "chances auprès des financeurs."
    ),
    "notification.welcome.title": "Bienvenue sur FilmFund Africa",
    "notification.welcome.body": (
        "Votre espace de démonstration est prêt. Les opportunités affichées sont "
        "fictives et marquées « DEMO DATA — NOT REAL »."
    ),
}

EN: dict[str, str] = {
    # --- Generic errors ---
    "error.validation": "Invalid data.",
    "error.database": "Internal database error.",
    # --- Authentication and account ---
    "auth.required": "Authentication required.",
    "auth.tokenInvalidOrExpired": "Token invalid or expired.",
    "auth.tokenInvalid": "Invalid token.",
    "auth.userNotFound": "User not found.",
    "auth.accountSuspended": "This account is suspended.",
    "auth.adminOnly": "Restricted to administrators.",
    "auth.accountNotFound": "Account not found.",
    "auth.accountNotFoundOrSuspended": "Account not found or suspended.",
    "auth.refreshInvalidOrExpired": "Refresh token invalid or expired.",
    "auth.verificationLinkInvalid": "Confirmation link invalid or expired.",
    "auth.resetLinkInvalid": "Reset link invalid or expired.",
    "auth.currentPasswordWrong": "Current password is incorrect.",
    "auth.logout": "Signed out.",
    "auth.passwordUpdatedSignIn": "Password updated. You can now sign in.",
    "auth.passwordUpdated": "Password updated.",
    # --- Projects and documents ---
    "project.notFound": "Project not found.",
    "project.deleted": "Project deleted.",
    "character.notFound": "Character not found.",
    "character.deleted": "Character deleted.",
    "document.notFound": "Document not found.",
    "document.deleted": "Document deleted.",
    "document.versionNotFound": "Version not found.",
    # --- Funding ---
    "funding.opportunityNotFound": "Funding scheme not found.",
    "funding.requirementNotFound": "Requirement not found.",
    "funding.opportunityDeleted": "Scheme deleted.",
    "funding.opportunityPublished": "Scheme published: {name}.",
    "funding.candidateNotFound": "Candidate not found.",
    # --- Budget ---
    "budget.itemNotFound": "Budget line not found.",
    "budget.itemDeleted": "Line deleted.",
    "budget.sourceNotFound": "Funding source not found.",
    "budget.sourceDeleted": "Source deleted.",
    "budget.phaseRemoved": "Phase removed from the schedule.",
    # --- Subscriptions and payments ---
    "billing.paymentNotFound": "Payment not found.",
    "billing.planNotFound": "Plan not found.",
    "billing.planUpdated": "Plan updated.",
    "billing.subscriptionAlreadyCancelled": "This subscription is already cancelled.",
    "billing.planUnavailable": "This plan is no longer offered.",
    "billing.subscriptionClosed": (
        "FilmFund Africa is in private beta: subscribing is closed. Existing "
        "plans and subscriptions are kept, and subscribing reopens at the "
        "commercial launch."
    ),
    # --- Administration ---
    "admin.userNotFound": "User not found.",
    "admin.cannotSuspendSelf": "You cannot suspend your own account.",
    "admin.accountSuspended": "Account suspended.",
    # --- Dashboard ---
    "notification.notFound": "Notification not found.",
    "notification.markedRead": "Notification marked as read.",
    # --- Generation jobs ---
    "job.notFound": "Job not found.",
    "job.alreadyFinished": (
        "This generation has already finished ({status}): there is nothing left to stop."
    ),
    # --- AI provider ---
    "ai.unreachable": "AI provider unreachable: {reason}",
    "ai.emptyResponse": "The AI provider returned an empty response.",
    "ai.refused": (
        "The model declined to handle this request ({reason}). Rephrase it, or "
        "report it if the refusal looks unfounded."
    ),
    # --- Session and quotas ---
    "auth.sessionPasswordChanged": (
        "Session expired: the password was changed. Please sign in again."
    ),
    "auth.registrationClosed": (
        "FilmFund Africa is in private beta: creating an account is closed. "
        "Registration reopens at the commercial launch; if you already have an "
        "account, you can sign in."
    ),
    "quota.exportNotIncluded": (
        "Export is not included in the “{plan}” plan. Move to a higher plan to export "
        "your package."
    ),
    "quota.matchingNotIncluded": (
        "Funding matching is not included in the “{plan}” plan. Search stays open — "
        "you can browse every scheme — but analysing how your project matches them "
        "requires a higher plan."
    ),
    # --- Quotas ---
    "auth.emailNotVerified": (
        "Address not confirmed. Open the link you received by email, or request a new "
        "one."
    ),
    "quota.projectLimit": (
        "Your “{plan}” plan is limited to {max} project(s). Move to a higher plan to "
        "create more."
    ),
    "quota.creditsExhausted": (
        "AI credits exhausted on the “{plan}” plan. They are topped up next period, or "
        "move to a higher plan."
    ),
    "quota.creditsInsufficient": (
        "Not enough AI credits: this generation costs {cost} and you have {remaining} "
        "left (“{plan}” plan). They are topped up next period, or move to a higher "
        "plan."
    ),
    # --- Documents and generation ---
    "document.typeNotApplicable": (
        "The “{document}” document does not apply to a {type} project."
    ),
    "document.alreadyExists": (
        "This document already exists. Turn on “replace” to generate it again."
    ),
    "document.empty": "This document is empty: generate it before reworking it.",
    "screenplay.tooLong": (
        "Too long to generate in one go: {minutes} minutes would take {passes} passes, "
        "beyond the limit of {ceiling}. Maximum achievable with the current settings: "
        "{maximum} minutes."
    ),
    "prompt.notFound": "No prompt is defined for the “{document}” document.",
    "agent.notFound": "No agent is defined for the “{agent}” role.",
    "dossier.runNotFound": "Run not found.",
    "export.dossierNotBuilt": (
        "The agent chain has not run on this project yet: there is nothing to "
        "export."
    ),
    "agent.outputNotJson": (
        "The model did not return a usable JSON object for this step."
    ),
    "agent.outputInvalid": "Invalid agent output: {details}",
    "agent.patchNotAllowed": (
        "The “{agent}” agent reviews the package and cannot modify it."
    ),
    "ai.providerUnknown": (
        "Unknown AI provider: “{name}”. Accepted values: anthropic, openai, mock."
    ),
    "ai.modelRequired": (
        "AI_MODEL is required with AI_PROVIDER={provider}: no default model is "
        "assumed on your behalf."
    ),
    "ai.keyProviderRequired": (
        "State which provider this key belongs to: an Anthropic key sent to "
        "OpenAI would end up in a third party's logs."
    ),
    "ai.keyNotApplicable": (
        "Provider “{provider}” calls no external service: it has no key."
    ),
    "secret.unreadable": (
        "A stored secret cannot be read: the server encryption key (SECRETS_KEY, "
        "or JWT_SECRET as a fallback) changed since it was saved. Enter it again."
    ),
    "funding.sourceRequiredToPublish": (
        "This scheme cannot be published as open without its source URL."
    ),
    "funding.sourceRequiredToVerify": (
        "Enter the source URL before marking this scheme as verified."
    ),
    # --- AI provider ---
    "ai.keyRequired": "AI_API_KEY is required when AI_PROVIDER={provider}.",
    "ai.providerError": "AI provider error ({status}): {reason}",
    # --- Monitoring ---
    "auth.invalidCredentials": "Incorrect email address or password.",
    "candidate.sourceRequired": "A candidate without a source URL cannot be accepted.",
    "candidate.alreadyReviewed": "This candidate is already “{status}”.",
    "candidate.organizationRequired": (
        "The organisation is required: fill it in before publishing."
    ),
    # --- Subscriptions ---
    "billing.planIsFree": "The free plan is not paid for: it is already active by default.",
    "billing.planAlreadyActive": "You are already subscribed to the “{plan}” plan.",
    "billing.paymentAlreadySettled": "This payment is already “{status}”.",
    "billing.noPaidSubscription": "No paid subscription to cancel.",
    # --- Routes ---
    "export.nothingToExport": "Nothing to export: generate at least one document first.",
    "automation.disabled": "Automation disabled: no API key configured.",
    "automation.invalidKey": "Invalid API key.",
    "automation.unknownTask": "Unknown task: {task}. Available: {available}.",
    "automation.taskRun": "Task {task} ran: {count} item(s) processed.",
    "billing.cancelledUntil": "Subscription cancelled. Your plan stays active until {date}.",
    "billing.cancelled": "Subscription cancelled.",
    "billing.simulationUnavailable": (
        "Simulation route unavailable: it only exists in development with the simulated "
        "provider."
    ),
    "billing.simulated": "Payment simulated: {status}.",
    "billing.invalidSignature": "Invalid notification signature.",
    "billing.unreadableNotification": "Unreadable notification.",
    "billing.notificationHandled": "Notification handled: payment {status}.",
    # --- Authentication (responses) ---
    "auth.verificationSent": (
        "If this address can be used, a confirmation email has just been sent. Open the "
        "link it contains to activate your account."
    ),
    "auth.resetSent": "If an account exists for this address, a reset link has just been sent.",
    "auth.devToken": "{message} [DEV] Token: {token}",
    # --- Payment providers ---
    "payment.manualNoNotification": (
        "Manual collection receives no notification: validation happens from the "
        "administration area."
    ),
    "payment.referenceMissing": "Notification without a payment reference.",
    "payment.unknownStatus": "Unknown payment status: {status}",
    "payment.unknownProvider": "Unknown payment provider: {code}",
    # --- Compatibility criteria ---
    "criterion.country": "Eligible country",
    "criterion.projectType": "Project type",
    "criterion.genre": "Genre",
    "criterion.language": "Language",
    "criterion.duration": "Format and running time",
    "criterion.deadline": "Deadline",
    "criterion.documents": "Documents required",
    "match.country.allOpen": "Scheme open to every country.",
    "match.country.unknown": (
        "Project country not filled in: geographic eligibility could not be checked."
    ),
    "match.country.met": "{country} is among the eligible countries.",
    "match.country.unmet": "{country} is not among the eligible countries ({list}).",
    "match.type.allOpen": "Scheme open to every project type.",
    "match.type.met": "The project type matches the scheme.",
    "match.type.unmet": "The project type is not among those the scheme accepts.",
    "match.genre.noRestriction": "No genre restriction.",
    "match.genre.unknown": "Project genre not filled in.",
    "match.genre.met": "The “{genre}” genre is sought.",
    "match.genre.close": "The “{genre}” genre is close to the editorial line.",
    "match.genre.unmet": "The “{genre}” genre does not match the editorial line ({list}).",
    "match.language.noRestriction": "No language restriction.",
    "match.language.met": "The project is in {language}.",
    "match.language.unmet": "The scheme expects a project in {list}; yours is in {language}.",
    "match.duration.unknown": "Project running time not filled in.",
    "match.duration.tooLong": (
        "The scheme targets short formats; the project runs {minutes} min."
    ),
    "match.duration.tooShort": (
        "The scheme targets long formats; the project runs {minutes} min."
    ),
    "match.duration.met": "The target running time ({minutes} min) is consistent.",
    "match.deadline.closed": "This scheme is closed.",
    "match.deadline.unknown": (
        "No deadline recorded: check the calendar on the funder's website."
    ),
    "match.deadline.passed": "The deadline passed on {date}.",
    "match.deadline.tight": (
        "Deadline in {days} day(s): that is a short time to finalise an application."
    ),
    "match.deadline.met": "Deadline on {date}, that is {days} days away.",
    "match.documents.unknown": "Documents required not detailed: check the scheme's own rules.",
    "match.documents.met": "Every document the scheme requires is written in your package.",
    "match.documents.unmet": (
        "{written}/{required} required document(s) written — missing: {missing}."
    ),
    # --- Readiness score ---
    "score.concept": "Concept",
    "score.narration": "Narration",
    "score.characters": "Characters",
    "score.vision": "Artistic vision",
    "score.feasibility": "Feasibility",
    "score.budget": "Budget",
    "score.fundingPlan": "Financing plan",
    "score.market": "Market potential",
    "score.dossier": "Package",
    "score.toFill": "To fill in: {list}",
    "score.missing": "Missing: {list}",
    "score.fillThem": "Fill in {list}.",
    "score.addThem": "Add {list}.",
    "score.completeThem": "Complete {list}.",
    "score.specifyThem": "Specify {list}.",
    "score.describeThem": "Describe {list}.",
    "score.concept.complete": "Concept complete.",
    "score.field.logline": "the logline",
    "score.field.concept": "the concept",
    "score.field.theme": "the theme",
    "score.field.genre": "the genre",
    "score.field.country": "the country",
    "score.field.shortSynopsis": "a developed short synopsis",
    "score.field.longSynopsis": "a long synopsis",
    "score.field.treatment": "a treatment or a screenplay",
    "score.field.directorVision": "the director's vision",
    "score.field.intentNote": "the statement of intent",
    "score.field.directingNote": "the director's statement",
    "score.field.duration": "the target running time",
    "score.field.productionCountry": "the production country",
    "score.field.objectives": "the project's objectives",
    "score.field.audience": "the target audience",
    "score.field.stakes": "the stakes",
    "score.narration.solid": "Narration solid.",
    "score.characters.none": "No character entered.",
    "score.characters.noneImprovement": (
        "Enter at least the protagonist and the antagonistic force."
    ),
    "score.characters.partial": "{described}/{count} character(s) described.",
    "score.characters.partialImprovement": (
        "Complete the description and the arc of every character."
    ),
    "score.characters.documented": "{count} character(s) documented.",
    "score.characters.documentedImprovement": "Generate the character breakdown.",
    "score.vision.documented": "Artistic vision documented.",
    "score.feasibility.defined": "Production framework defined.",
    "score.budget.missing": "Budget not filled in.",
    "score.budget.missingImprovement": "Budget not filled in: build the provisional budget.",
    "score.budget.detail": "Budget of {amount} {currency} across {items} line(s).",
    "score.budget.detailImprovement": "Break the budget lines down further.",
    "score.fundingPlan.missing": "No financing plan.",
    "score.fundingPlan.missingImprovement": "No financing plan: list the sources you envisage.",
    "score.fundingPlan.detail": "{percentage}% of the budget covered by identified funding.",
    "score.fundingPlan.detailImprovement": (
        "Identify further sources to cover the funding still sought."
    ),
    "score.market.defined": "Positioning defined.",
    "score.dossier.detail": "{present}/{total} key documents written.",
    "score.dossier.improvement": "{count} key document(s) still missing from the package.",
    # --- Notifications ---
    "notification.matchFound.title": "{count} matching funding scheme(s) for “{project}”",
    "notification.matchFound.body": (
        "The analysis found {count} scheme(s) scoring above {threshold}%. The score is "
        "a decision aid, not a guarantee of funding."
    ),
    "notification.deadlineSoon.title": "Deadline in {days} days — {opportunity}",
    "notification.deadlineSoon.body": (
        "The deadline for “{opportunity}” ({organization}) is {date}, for your project "
        "“{project}”."
    ),
    "notification.incompleteFile.title": "Your package is incomplete",
    "notification.incompleteFile.body": (
        "The “{project}” project scores {score}/100. Complete it to improve your "
        "chances with funders."
    ),
    "notification.welcome.title": "Welcome to FilmFund Africa",
    "notification.welcome.body": (
        "Your demonstration space is ready. The opportunities shown are fictional and "
        "marked “DEMO DATA — NOT REAL”."
    ),
}

CATALOGS: dict[Locale, dict[str, str]] = {"fr": FR, "en": EN}


def is_locale(value: object) -> bool:
    return isinstance(value, str) and value in LOCALES


def resolve_locale(value: object) -> Locale:
    """Ramene une valeur quelconque a une langue connue."""
    if is_locale(value):
        return value  # type: ignore[return-value]
    return settings.default_locale


def parse_accept_language(header: str | None) -> Locale | None:
    """Premiere langue acceptee que nous savons parler, ou None.

    Lecture volontairement sommaire : les poids `q` sont respectes, le reste
    de la negociation ne l'est pas. Un en-tete mal forme ne doit rien casser,
    seulement laisser la langue par defaut s'appliquer.
    """
    if not header:
        return None

    candidates: list[tuple[float, str]] = []
    for part in header.split(","):
        piece, _, params = part.strip().partition(";")
        tag = piece.strip().lower()
        if not tag:
            continue
        weight = 1.0
        if params.strip().startswith("q="):
            try:
                weight = float(params.strip()[2:])
            except ValueError:
                weight = 0.0
        candidates.append((weight, tag))

    for _, tag in sorted(candidates, key=lambda item: -item[0]):
        # `fr-CA` vaut `fr` : nous ne distinguons pas les variantes regionales.
        base = tag.split("-")[0]
        if base in LOCALES:
            return base  # type: ignore[return-value]
    return None


def request_locale(request: Request) -> Locale:
    """Langue a servir a cet appelant.

    L'ordre suit ce que chacun sait de l'autre : la preference enregistree sur
    le profil, posee par la dependance d'authentification des qu'un compte est
    identifie ; sinon l'en-tete `Accept-Language`, que tout navigateur envoie ;
    sinon la langue par defaut du deploiement.
    """
    stored = getattr(request.state, "locale", None)
    if is_locale(stored):
        return stored  # type: ignore[return-value]
    return parse_accept_language(request.headers.get("accept-language")) or settings.default_locale


def translate(locale: Locale, key: str, **params: Any) -> str:
    """Rend un message. Une cle inconnue se rend elle-meme, jamais une erreur.

    Un message manquant ne doit pas transformer une erreur metier lisible en
    500 : la cle brute est laide, mais elle reste diagnostiquable.
    """
    template = CATALOGS[locale].get(key) or FR.get(key) or key
    if not params:
        return template
    try:
        return template.format(**params)
    except (KeyError, IndexError):  # pragma: no cover - message mal parametre
        return template


def plural(locale: Locale, key: str, count: int, **params: Any) -> str:
    """Choisit `_one` ou `_other` selon la langue. 0 est singulier en francais."""
    singular = count <= 1 if locale == "fr" else count == 1
    suffix = "_one" if singular else "_other"
    return translate(locale, f"{key}{suffix}", count=count, **params)
