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
    # `batch_alter_table` et non `alter_column` : SQLite ne sait pas relacher
    # un NOT NULL en place, il faut reconstruire la table. Sur PostgreSQL le
    # mode par lot se ramene a un simple ALTER, donc la meme migration vaut
    # pour les deux — et la pile de bout en bout tourne sur SQLite.
    with op.batch_alter_table('generation_jobs') as batch:
        batch.alter_column(
            'document_type', existing_type=sa.String(length=30), nullable=True
        )


def downgrade() -> None:
    # Les taches sans document ne peuvent pas redevenir valides : on les
    # retire plutot que d'inventer un type pour elles.
    op.execute("DELETE FROM generation_jobs WHERE document_type IS NULL")
    with op.batch_alter_table('generation_jobs') as batch:
        batch.alter_column(
            'document_type', existing_type=sa.String(length=30), nullable=False
        )
