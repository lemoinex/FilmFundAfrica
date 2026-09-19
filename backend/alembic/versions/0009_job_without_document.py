"""une tache peut ne produire aucun document

Un passage de la chaine d'agents produit un dossier entier, pas un document :
`document_type` n'a plus de sens pour lui. La colonne devient donc facultative
plutot que de recevoir une valeur choisie au hasard pour satisfaire une
contrainte — une donnee inventee pour faire passer un NOT NULL finit toujours
par etre lue comme vraie.

Revision ID: 0009_job_without_document
Revises: 0008_agent_chain
Create Date: 2026-09-19 03:00:00.000000
"""
from __future__ import annotations

import sqlalchemy as sa
from alembic import op

revision = '0009_job_without_document'
down_revision = '0008_agent_chain'
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.alter_column(
        'generation_jobs', 'document_type', existing_type=sa.String(length=30), nullable=True
    )


def downgrade() -> None:
    # Les taches sans document ne peuvent pas redevenir valides : on les
    # retire plutot que d'inventer un type pour elles.
    op.execute("DELETE FROM generation_jobs WHERE document_type IS NULL")
    op.alter_column(
        'generation_jobs', 'document_type', existing_type=sa.String(length=30), nullable=False
    )
