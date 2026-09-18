"""Agregats du tableau de bord.

La section « opportunités recommandées » lit la base des financements
alimentée en Phase 3. Tant qu'elle est vide (ou ne contient que des données
de démonstration), elle est renvoyée telle quelle, avec la source et la date
de dernière vérification : aucune opportunité n'est présentée comme active
sans ces informations.
"""

from __future__ import annotations

from datetime import date, timedelta

from sqlalchemy import func, select
from sqlalchemy.orm import Session

from app.models.enums import FundingStatus, NotificationType
from app.models.funding import FundingOpportunity, ProjectFundingMatch
from app.models.project import Project
from app.models.system import Notification
from app.models.user import User
from app.repositories.document import DocumentRepository
from app.schemas.dashboard import (
    DashboardResponse,
    DashboardStats,
    NotificationRead,
    RecommendedOpportunity,
)
from app.services.project_service import ProjectService

DEADLINE_WINDOW_DAYS = 45


class DashboardService:
    def __init__(self, db: Session) -> None:
        self.db = db
        self.projects = ProjectService(db)
        self.documents = DocumentRepository(db)

    # ------------------------------------------------------------------
    def build(self, user: User) -> DashboardResponse:
        summaries = self.projects.list_summaries(user, limit=12)
        project_ids = [summary.id for summary in summaries]

        compatible = self._count_compatible(user)
        upcoming = self._count_upcoming_deadlines(project_ids)

        stats = DashboardStats(
            projects=self.projects.projects.count_for_user(user.id),
            documents_generated=self.documents.count_for_user(user.id),
            compatible_opportunities=compatible,
            upcoming_deadlines=upcoming,
            ai_credits_remaining=user.ai_credits_remaining,
        )

        first_name = user.profile.first_name if user.profile else ""
        return DashboardResponse(
            welcome_name=first_name or user.email.split("@")[0],
            stats=stats,
            projects=summaries,
            recommended_opportunities=self._recommended(user),
            notifications=self._notifications(user),
        )

    # ------------------------------------------------------------------
    def _count_compatible(self, user: User) -> int:
        return int(
            self.db.scalar(
                select(func.count(func.distinct(ProjectFundingMatch.opportunity_id)))
                .join(Project, Project.id == ProjectFundingMatch.project_id)
                .where(Project.user_id == user.id)
            )
            or 0
        )

    def _count_upcoming_deadlines(self, project_ids: list[str]) -> int:
        if not project_ids:
            return 0
        horizon = date.today() + timedelta(days=DEADLINE_WINDOW_DAYS)
        return int(
            self.db.scalar(
                select(func.count(func.distinct(FundingOpportunity.id)))
                .join(
                    ProjectFundingMatch,
                    ProjectFundingMatch.opportunity_id == FundingOpportunity.id,
                )
                .where(
                    ProjectFundingMatch.project_id.in_(project_ids),
                    FundingOpportunity.deadline.is_not(None),
                    FundingOpportunity.deadline >= date.today(),
                    FundingOpportunity.deadline <= horizon,
                )
            )
            or 0
        )

    # ------------------------------------------------------------------
    def _recommended(self, user: User, limit: int = 5) -> list[RecommendedOpportunity]:
        rows = self.db.execute(
            select(FundingOpportunity, ProjectFundingMatch.compatibility_score)
            .join(
                ProjectFundingMatch,
                ProjectFundingMatch.opportunity_id == FundingOpportunity.id,
            )
            .join(Project, Project.id == ProjectFundingMatch.project_id)
            .where(Project.user_id == user.id, FundingOpportunity.status != FundingStatus.CLOSED)
            .order_by(ProjectFundingMatch.compatibility_score.desc())
            .limit(limit)
        ).all()

        return [
            RecommendedOpportunity(
                id=opportunity.id,
                name=opportunity.name,
                organization=opportunity.organization,
                amount_label=self._amount_label(opportunity),
                deadline=opportunity.deadline,
                compatibility=score,
                is_demo=opportunity.is_demo,
                source_name=opportunity.source_name,
                source_url=opportunity.source_url,
                last_verified_at=opportunity.last_verified_at,
            )
            for opportunity, score in rows
        ]

    @staticmethod
    def _amount_label(opportunity: FundingOpportunity) -> str | None:
        low, high, currency = (
            opportunity.minimum_budget,
            opportunity.maximum_budget,
            opportunity.currency,
        )
        if low and high:
            return f"{low:,.0f} – {high:,.0f} {currency}".replace(",", " ")
        if high:
            return f"jusqu'à {high:,.0f} {currency}".replace(",", " ")
        if low:
            return f"à partir de {low:,.0f} {currency}".replace(",", " ")
        return None

    # ------------------------------------------------------------------
    def _notifications(self, user: User, limit: int = 8) -> list[NotificationRead]:
        rows = self.db.scalars(
            select(Notification)
            .where(Notification.user_id == user.id)
            .order_by(Notification.created_at.desc())
            .limit(limit)
        )
        return [
            NotificationRead(
                id=item.id,
                title=item.title,
                body=item.body,
                notification_type=str(item.notification_type),
                link=item.link,
                is_read=item.is_read,
                created_at=item.created_at,
            )
            for item in rows
        ]

    # ------------------------------------------------------------------
    def create_notification(
        self,
        user: User,
        *,
        title: str,
        body: str,
        notification_type: NotificationType = NotificationType.SYSTEM,
        link: str | None = None,
    ) -> Notification:
        notification = Notification(
            user_id=user.id,
            title=title,
            body=body,
            notification_type=notification_type,
            link=link,
        )
        self.db.add(notification)
        self.db.commit()
        self.db.refresh(notification)
        return notification
