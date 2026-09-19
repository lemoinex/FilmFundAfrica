"""Enumerations metier partagees entre modeles, schemas et prompts."""

from __future__ import annotations

from enum import StrEnum


class UserType(StrEnum):
    AUTHOR = "AUTHOR"
    DIRECTOR = "DIRECTOR"
    PRODUCER = "PRODUCER"
    INSTITUTION = "INSTITUTION"
    ADMIN = "ADMIN"


class ProjectType(StrEnum):
    DOCUMENTARY = "DOCUMENTARY"
    FEATURE_FILM = "FEATURE_FILM"
    SHORT_FILM = "SHORT_FILM"
    TV_SERIES = "TV_SERIES"
    WEB_SERIES = "WEB_SERIES"
    ANIMATION = "ANIMATION"


class ProjectStatus(StrEnum):
    IDEA = "IDEA"
    DEVELOPMENT = "DEVELOPMENT"
    WRITING = "WRITING"
    PRE_PRODUCTION = "PRE_PRODUCTION"
    PRODUCTION = "PRODUCTION"
    POST_PRODUCTION = "POST_PRODUCTION"
    COMPLETED = "COMPLETED"


class DocumentType(StrEnum):
    LOGLINE = "LOGLINE"
    SHORT_SYNOPSIS = "SHORT_SYNOPSIS"
    LONG_SYNOPSIS = "LONG_SYNOPSIS"
    INTENT_NOTE = "INTENT_NOTE"
    DIRECTING_NOTE = "DIRECTING_NOTE"
    TREATMENT = "TREATMENT"
    CHARACTER_SHEET = "CHARACTER_SHEET"
    ORAL_PITCH = "ORAL_PITCH"
    WRITTEN_PITCH = "WRITTEN_PITCH"
    SERIES_BIBLE = "SERIES_BIBLE"
    SCREENPLAY = "SCREENPLAY"


#: Sous-ensemble des documents generables par l'IA a ce stade du MVP.
GENERATABLE_DOCUMENTS: frozenset[DocumentType] = frozenset(DocumentType)


class DocumentStatus(StrEnum):
    DRAFT = "DRAFT"
    IN_REVIEW = "IN_REVIEW"
    FINAL = "FINAL"


class FundingCategory(StrEnum):
    FUND = "FUND"
    GRANT = "GRANT"
    RESIDENCY = "RESIDENCY"
    FESTIVAL = "FESTIVAL"
    LAB = "LAB"
    WORKSHOP = "WORKSHOP"
    COPRODUCTION = "COPRODUCTION"
    BURSARY = "BURSARY"
    PITCHING_FORUM = "PITCHING_FORUM"


class FundingStatus(StrEnum):
    OPEN = "OPEN"
    CLOSED = "CLOSED"
    UPCOMING = "UPCOMING"
    UNVERIFIED = "UNVERIFIED"


class PlanCode(StrEnum):
    FREE = "FREE"
    PRO_AUTHOR = "PRO_AUTHOR"
    PRODUCER = "PRODUCER"


class SubscriptionStatus(StrEnum):
    ACTIVE = "ACTIVE"
    CANCELLED = "CANCELLED"
    EXPIRED = "EXPIRED"


class PaymentStatus(StrEnum):
    """Cycle de vie d'un paiement.

    `PENDING` couvre l'attente d'une confirmation du prestataire — en mobile
    money, la personne doit encore valider sur son telephone. Seul `SUCCEEDED`
    donne droit a quoi que ce soit.
    """

    PENDING = "PENDING"
    SUCCEEDED = "SUCCEEDED"
    FAILED = "FAILED"
    CANCELLED = "CANCELLED"
    REFUNDED = "REFUNDED"

    @property
    def is_final(self) -> bool:
        return self is not PaymentStatus.PENDING


class CandidateStatus(StrEnum):
    """Etat d'un candidat de la veille automatisee.

    Un candidat n'atteint la base vivante qu'apres passage par `APPROVED`,
    decide par une personne.
    """

    PENDING = "PENDING"
    APPROVED = "APPROVED"
    REJECTED = "REJECTED"


class NotificationType(StrEnum):
    NEW_OPPORTUNITY = "NEW_OPPORTUNITY"
    DEADLINE_SOON = "DEADLINE_SOON"
    INCOMPLETE_FILE = "INCOMPLETE_FILE"
    MATCH_FOUND = "MATCH_FOUND"
    SYSTEM = "SYSTEM"


class BudgetCategory(StrEnum):
    DEVELOPMENT = "DEVELOPMENT"
    PRE_PRODUCTION = "PRE_PRODUCTION"
    PRODUCTION = "PRODUCTION"
    POST_PRODUCTION = "POST_PRODUCTION"
    DISTRIBUTION = "DISTRIBUTION"


class FundingSourceType(StrEnum):
    PRODUCER = "PRODUCER"
    PUBLIC_FUND = "PUBLIC_FUND"
    TELEVISION = "TELEVISION"
    COPRODUCER = "COPRODUCER"
    INVESTOR = "INVESTOR"
    SPONSOR = "SPONSOR"
    OTHER = "OTHER"


class AIOperation(StrEnum):
    GENERATE_DOCUMENT = "GENERATE_DOCUMENT"
    IMPROVE_DOCUMENT = "IMPROVE_DOCUMENT"
    SCORE_PROJECT = "SCORE_PROJECT"
    MATCH_FUNDING = "MATCH_FUNDING"
    #: Un passage de la chaine d'agents. Facture a l'appel, pas au forfait :
    #: huit agents, c'est huit appels au fournisseur.
    RUN_AGENT_CHAIN = "RUN_AGENT_CHAIN"


class JobKind(StrEnum):
    """Nature d'une tache de generation."""

    GENERATE_DOCUMENT = "GENERATE_DOCUMENT"
    REFINE_DOCUMENT = "REFINE_DOCUMENT"
    RUN_AGENT_CHAIN = "RUN_AGENT_CHAIN"


class JobStatus(StrEnum):
    """Cycle de vie d'une tache de generation.

    `QUEUED` -> `RUNNING` -> `SUCCEEDED` ou `FAILED`. Une tache ne repasse
    jamais a un etat anterieur : le frontend peut arreter de l'interroger des
    qu'elle est dans un etat terminal.
    """

    QUEUED = "QUEUED"
    RUNNING = "RUNNING"
    SUCCEEDED = "SUCCEEDED"
    FAILED = "FAILED"

    @property
    def is_final(self) -> bool:
        return self in (JobStatus.SUCCEEDED, JobStatus.FAILED)


class AgentRole(StrEnum):
    """Les huit agents de la chaine, dans l'ordre ou ils interviennent.

    L'ordre de declaration est celui du pipeline : `AGENT_PIPELINE` s'en sert
    plutot que de redire la sequence ailleurs.
    """

    DEVELOPMENT = "DEVELOPMENT"
    SCREENWRITER = "SCREENWRITER"
    DIRECTOR = "DIRECTOR"
    PRODUCER = "PRODUCER"
    FINANCING = "FINANCING"
    IMPACT = "IMPACT"
    CONSISTENCY_VALIDATOR = "CONSISTENCY_VALIDATOR"
    FUNDING_PACKAGE_VALIDATOR = "FUNDING_PACKAGE_VALIDATOR"


class ConfidenceStatus(StrEnum):
    """Statut d'une information portee par l'etat du projet.

    Aucune information n'est nue : elle porte toujours d'ou elle vient. C'est
    ce qui permet de refuser qu'une hypothese soit presentee comme un fait, et
    de savoir ce qu'il reste a verifier avant de soumettre un dossier.
    """

    VERIFIED = "VERIFIED"
    PROVIDED_BY_USER = "PROVIDED_BY_USER"
    INFERRED = "INFERRED"
    ASSUMPTION = "ASSUMPTION"
    TO_BE_VERIFIED = "TO_BE_VERIFIED"
    UNKNOWN = "UNKNOWN"


class Severity(StrEnum):
    """Gravite d'un constat, des validateurs jusqu'aux drapeaux du dossier."""

    CRITICAL = "CRITICAL"
    MAJOR = "MAJOR"
    MINOR = "MINOR"
    PASS = "PASS"


class ValidationVerdict(StrEnum):
    """Verdict rendu par un validateur.

    `BLOCKED` n'est pas un echec technique mais un refus motive : le dossier
    existe, il ne doit simplement pas partir en l'etat.
    """

    PASS = "PASS"
    PASS_WITH_WARNINGS = "PASS_WITH_WARNINGS"
    REQUIRES_CORRECTION = "REQUIRES_CORRECTION"
    BLOCKED = "BLOCKED"
