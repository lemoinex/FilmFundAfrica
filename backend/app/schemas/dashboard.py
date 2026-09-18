"""Schemas du tableau de bord."""

from __future__ import annotations

from datetime import date, datetime

from pydantic import BaseModel

from app.schemas.project import ProjectSummary


class DashboardStats(BaseModel):
    projects: int
    documents_generated: int
    compatible_opportunities: int
    upcoming_deadlines: int
    ai_credits_remaining: int


class RecommendedOpportunity(BaseModel):
    id: str
    name: str
    organization: str
    amount_label: str | None = None
    deadline: date | None = None
    compatibility: int
    is_demo: bool = False
    #: Tracabilite : jamais d'opportunite presentee sans sa source.
    source_name: str | None = None
    source_url: str | None = None
    last_verified_at: datetime | None = None


class NotificationRead(BaseModel):
    id: str
    title: str
    body: str
    notification_type: str
    link: str | None = None
    is_read: bool
    created_at: datetime


class DashboardResponse(BaseModel):
    welcome_name: str
    stats: DashboardStats
    projects: list[ProjectSummary]
    recommended_opportunities: list[RecommendedOpportunity]
    notifications: list[NotificationRead]
