"""Budget previsionnel, plan de financement et calendrier de production.

Trois regles portent ce module :

* **Aucun montant n'est devine.** La trame propose les postes attendus par un
  comite de lecture ; les quantites et les prix viennent de l'auteur. Un tarif
  plausible invente serait un chiffre faux dans un dossier de financement.
* **Les totaux sont toujours recalcules, jamais saisis.** Le montant d'une
  ligne vaut quantite x prix unitaire, le total du budget la somme des lignes,
  et le plan de financement suit le budget. Un total modifiable a la main
  finirait par contredire ses propres lignes.
* **Le plan de financement ne se paye pas de mots** : « acquis » signifie
  acquis. Une source seulement esperee compte dans le recherche, pas dans le
  finance.
"""

from __future__ import annotations

import logging
from datetime import date

from sqlalchemy import select
from sqlalchemy.orm import Session

from app.models.budget import (
    Budget,
    BudgetItem,
    FundingPlan,
    FundingPlanLine,
    ProductionSchedule,
)
from app.models.enums import BudgetCategory
from app.models.project import Project
from app.services.budget_templates import CATEGORY_ORDER, template_for

logger = logging.getLogger("filmfund.budget")


class BudgetService:
    def __init__(self, db: Session) -> None:
        self.db = db

    # ------------------------------------------------------------------
    # Budget
    # ------------------------------------------------------------------
    def get_or_create(self, project: Project, currency: str | None = None) -> Budget:
        if project.budget is None:
            project.budget = Budget(currency=currency or "XAF")
            self.db.flush()
        elif currency:
            project.budget.currency = currency
        return project.budget

    def generate_from_template(self, project: Project, *, replace: bool = False) -> Budget:
        """Installe les postes attendus pour ce type de projet, sans montants.

        `replace=False` complete un budget existant sans toucher aux lignes
        deja chiffrees : regenerer ne doit jamais effacer le travail de
        l'auteur.
        """
        budget = self.get_or_create(project)

        if replace:
            for item in list(budget.items):
                self.db.delete(item)
            budget.items.clear()
            self.db.flush()

        known = {(item.category, item.label.strip().lower()) for item in budget.items}
        position = max((item.sort_order for item in budget.items), default=-1) + 1

        for line in template_for(project.project_type):
            if (line.category, line.label.strip().lower()) in known:
                continue
            budget.items.append(
                BudgetItem(
                    category=line.category,
                    label=line.label,
                    quantity=line.quantity,
                    unit=line.unit,
                    unit_price=0.0,
                    amount=0.0,
                    sort_order=position,
                )
            )
            position += 1

        self.db.flush()
        self.recompute(project, budget)
        logger.info(
            "trame de budget appliquée",
            extra={"event": "budget_template_applied"},
        )
        return budget

    # ------------------------------------------------------------------
    def add_item(self, project: Project, **fields) -> BudgetItem:
        budget = self.get_or_create(project)
        item = BudgetItem(
            category=fields["category"],
            label=fields["label"],
            quantity=fields.get("quantity", 1.0),
            unit=fields.get("unit"),
            unit_price=fields.get("unit_price", 0.0),
            sort_order=max((line.sort_order for line in budget.items), default=-1) + 1,
        )
        budget.items.append(item)
        self.db.flush()
        self.recompute(project, budget)
        return item

    def update_item(self, project: Project, item: BudgetItem, **fields) -> BudgetItem:
        for name in ("category", "label", "quantity", "unit", "unit_price", "sort_order"):
            if name in fields and fields[name] is not None:
                setattr(item, name, fields[name])
        self.db.flush()
        self.recompute(project, project.budget)
        return item

    def delete_item(self, project: Project, item: BudgetItem) -> None:
        self.db.delete(item)
        self.db.flush()
        self.db.refresh(project.budget)
        self.recompute(project, project.budget)

    def get_owned_item(self, budget: Budget, item_id: str) -> BudgetItem | None:
        return next((item for item in budget.items if item.id == item_id), None)

    # ------------------------------------------------------------------
    def recompute(self, project: Project, budget: Budget | None) -> None:
        """Recalcule les montants de chaque ligne, le total, et suit le plan."""
        if budget is None:
            return
        for item in budget.items:
            item.amount = round(max(item.quantity, 0.0) * max(item.unit_price, 0.0), 2)
        budget.total_amount = round(sum(item.amount for item in budget.items), 2)

        # Le plan de financement se compare toujours au budget courant : sans
        # cette synchronisation, un pourcentage de couverture resterait calcule
        # sur un budget perime.
        plan = project.funding_plan
        if plan is not None:
            plan.total_budget = budget.total_amount
            plan.currency = budget.currency
        self.db.flush()

    def totals_by_category(self, budget: Budget | None) -> list[dict]:
        """Sous-totaux par phase, dans l'ordre de production."""
        if budget is None:
            return []
        grouped: dict[BudgetCategory, float] = {}
        counts: dict[BudgetCategory, int] = {}
        for item in budget.items:
            grouped[item.category] = grouped.get(item.category, 0.0) + item.amount
            counts[item.category] = counts.get(item.category, 0) + 1

        total = budget.total_amount or 0.0
        return [
            {
                "category": category,
                "amount": round(grouped[category], 2),
                "item_count": counts[category],
                "share": round(grouped[category] / total * 100, 2) if total > 0 else 0.0,
            }
            for category in CATEGORY_ORDER
            if category in grouped
        ]

    # ------------------------------------------------------------------
    # Plan de financement
    # ------------------------------------------------------------------
    def get_or_create_plan(self, project: Project) -> FundingPlan:
        if project.funding_plan is None:
            project.funding_plan = FundingPlan(
                currency=project.budget.currency if project.budget else "XAF",
                total_budget=project.budget.total_amount if project.budget else 0.0,
            )
            self.db.flush()
        return project.funding_plan

    def add_plan_line(self, project: Project, **fields) -> FundingPlanLine:
        plan = self.get_or_create_plan(project)
        line = FundingPlanLine(
            source_type=fields["source_type"],
            source_name=fields.get("source_name"),
            amount=max(fields.get("amount", 0.0), 0.0),
            is_secured=fields.get("is_secured", False),
            expected_date=fields.get("expected_date"),
        )
        plan.lines.append(line)
        self.db.flush()
        return line

    def update_plan_line(
        self, plan: FundingPlan, line: FundingPlanLine, **fields
    ) -> FundingPlanLine:
        for name in ("source_type", "source_name", "amount", "is_secured", "expected_date"):
            if name in fields and fields[name] is not None:
                setattr(line, name, fields[name])
        line.amount = max(line.amount, 0.0)
        self.db.flush()
        return line

    def delete_plan_line(self, line: FundingPlanLine) -> None:
        self.db.delete(line)
        self.db.flush()

    def get_owned_plan_line(self, plan: FundingPlan, line_id: str) -> FundingPlanLine | None:
        return next((line for line in plan.lines if line.id == line_id), None)

    @staticmethod
    def plan_summary(plan: FundingPlan | None) -> dict:
        """Chiffres du plan, tous derives des lignes.

        `identified` inclut l'espere, `secured` seulement l'acquis : c'est
        l'ecart entre les deux qui dit ce qu'il reste a decrocher.
        """
        if plan is None:
            return {
                "currency": "XAF",
                "total_budget": 0.0,
                "secured_amount": 0.0,
                "identified_amount": 0.0,
                "sought_amount": 0.0,
                "funded_percentage": 0.0,
                "uncovered_amount": 0.0,
            }
        identified = round(sum(line.amount for line in plan.lines), 2)
        return {
            "currency": plan.currency,
            "total_budget": round(plan.total_budget, 2),
            "secured_amount": round(plan.secured_amount, 2),
            "identified_amount": identified,
            "sought_amount": round(plan.sought_amount, 2),
            "funded_percentage": plan.funded_percentage,
            "uncovered_amount": round(max(plan.total_budget - identified, 0.0), 2),
        }

    # ------------------------------------------------------------------
    # Calendrier
    # ------------------------------------------------------------------
    def list_schedule(self, project: Project) -> list[ProductionSchedule]:
        rows = list(
            self.db.scalars(
                select(ProductionSchedule).where(ProductionSchedule.project_id == project.id)
            )
        )
        return sorted(rows, key=lambda row: CATEGORY_ORDER.index(row.phase))

    def set_schedule_phase(
        self,
        project: Project,
        phase: BudgetCategory,
        *,
        start_date: date | None,
        end_date: date | None,
        notes: str | None,
    ) -> ProductionSchedule:
        """Une seule ligne par phase : reappeler met a jour, n'empile pas."""
        row = self.db.scalar(
            select(ProductionSchedule).where(
                ProductionSchedule.project_id == project.id,
                ProductionSchedule.phase == phase,
            )
        )
        if row is None:
            row = ProductionSchedule(project_id=project.id, phase=phase)
            self.db.add(row)
        row.start_date = start_date
        row.end_date = end_date
        row.notes = notes
        self.db.flush()
        return row

    def delete_schedule_phase(self, project: Project, phase: BudgetCategory) -> None:
        row = self.db.scalar(
            select(ProductionSchedule).where(
                ProductionSchedule.project_id == project.id,
                ProductionSchedule.phase == phase,
            )
        )
        if row is not None:
            self.db.delete(row)
            self.db.flush()
