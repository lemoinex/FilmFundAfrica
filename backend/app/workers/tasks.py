"""Taches planifiees, appelables par n8n ou par un ordonnanceur.

Ces fonctions sont synchrones et idempotentes : elles peuvent etre appelees
plusieurs fois sans effet de bord indesirable.
"""

from __future__ import annotations

import logging
from datetime import date, timedelta

from sqlalchemy import select

from app.core.database import SessionLocal
from app.models.enums import FundingStatus, NotificationType
from app.models.funding import FundingOpportunity, ProjectFundingMatch
from app.models.project import Project
from app.models.system import Notification
from app.models.user import User

logger = logging.getLogger("filmfund.workers")

DEADLINE_ALERT_DAYS = 7


def notify_upcoming_deadlines(days: int = DEADLINE_ALERT_DAYS) -> int:
    """Crée une notification par échéance proche sur un financement suivi."""
    target_day = date.today() + timedelta(days=days)
    created = 0

    with SessionLocal() as db:
        rows = db.execute(
            select(Project.user_id, Project.id, Project.title, FundingOpportunity)
            .join(ProjectFundingMatch, ProjectFundingMatch.project_id == Project.id)
            .join(
                FundingOpportunity,
                FundingOpportunity.id == ProjectFundingMatch.opportunity_id,
            )
            .where(
                FundingOpportunity.deadline == target_day,
                FundingOpportunity.status != FundingStatus.CLOSED,
            )
        ).all()

        for user_id, project_id, project_title, opportunity in rows:
            link = f"/projets/{project_id}"
            already = db.scalar(
                select(Notification).where(
                    Notification.user_id == user_id,
                    Notification.link == link,
                    Notification.title.like(f"%{opportunity.name}%"),
                )
            )
            if already is not None:
                continue
            db.add(
                Notification(
                    user_id=user_id,
                    notification_type=NotificationType.DEADLINE_SOON,
                    title=f"Deadline dans {days} jours — {opportunity.name}",
                    body=(
                        f"La date limite de « {opportunity.name} » "
                        f"({opportunity.organization}) est fixée au "
                        f"{opportunity.deadline:%d/%m/%Y} pour votre projet "
                        f"« {project_title} »."
                    ),
                    link=link,
                )
            )
            created += 1
        db.commit()

    logger.info("notifications d'échéance créées : %s", created, extra={"event": "deadline_scan"})
    return created


def notify_incomplete_projects(threshold: int = 50) -> int:
    """Signale les dossiers dont le score de maturité reste faible."""
    created = 0
    with SessionLocal() as db:
        projects = db.scalars(
            select(Project).where(
                Project.readiness_score.is_not(None), Project.readiness_score < threshold
            )
        )
        for project in projects:
            link = f"/projets/{project.id}"
            already = db.scalar(
                select(Notification).where(
                    Notification.user_id == project.user_id,
                    Notification.link == link,
                    Notification.notification_type == NotificationType.INCOMPLETE_FILE,
                    Notification.is_read.is_(False),
                )
            )
            if already is not None:
                continue
            db.add(
                Notification(
                    user_id=project.user_id,
                    notification_type=NotificationType.INCOMPLETE_FILE,
                    title="Votre dossier est incomplet",
                    body=(
                        f"Le projet « {project.title} » atteint "
                        f"{project.readiness_score}/100. Complétez-le pour améliorer "
                        "vos chances auprès des financeurs."
                    ),
                    link=link,
                )
            )
            created += 1
        db.commit()
    return created


def reset_monthly_credits() -> int:
    """Recharge les crédits IA des comptes dont la période est écoulée."""
    from app.services.credit_service import CreditService

    updated = 0
    with SessionLocal() as db:
        service = CreditService(db)
        for user in db.scalars(select(User).where(User.is_active.is_(True))):
            before = user.ai_credits_remaining
            service.refresh_period_if_needed(user)
            if user.ai_credits_remaining != before:
                updated += 1
        db.commit()
    return updated
