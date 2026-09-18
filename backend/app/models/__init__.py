"""Import centralise des modeles.

Alembic et `Base.metadata.create_all` dependent de ce module pour connaitre
l'ensemble des tables.
"""

from app.models.base import Base
from app.models.billing import AIUsage, Subscription, SubscriptionPlan
from app.models.budget import (
    Budget,
    BudgetItem,
    FundingPlan,
    FundingPlanLine,
    ProductionSchedule,
)
from app.models.document import Document, DocumentVersion
from app.models.funding import (
    FundingOpportunity,
    FundingRequirement,
    ProjectFundingMatch,
)
from app.models.ingestion import OpportunityCandidate
from app.models.jobs import GenerationJob
from app.models.payment import Payment
from app.models.project import Character, Project
from app.models.system import AppSetting, AuditLog, Notification
from app.models.user import EmailVerificationToken, PasswordResetToken, Profile, User

__all__ = [
    "Base",
    "User",
    "Profile",
    "PasswordResetToken",
    "EmailVerificationToken",
    "Project",
    "Character",
    "Document",
    "DocumentVersion",
    "FundingOpportunity",
    "FundingRequirement",
    "ProjectFundingMatch",
    "Budget",
    "BudgetItem",
    "FundingPlan",
    "FundingPlanLine",
    "ProductionSchedule",
    "SubscriptionPlan",
    "Subscription",
    "AIUsage",
    "Notification",
    "AuditLog",
    "AppSetting",
    "GenerationJob",
    "Payment",
    "OpportunityCandidate",
]
