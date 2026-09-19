"""une generation en cours peut etre annulee

Une chaine d'agents coute huit credits et enchaine seize appels au
fournisseur. Lancee par erreur, rien ne permettait de l'arreter : il fallait
attendre la fin et payer l'integralite.

`cancel_requested_at` porte la demande d'arret. C'est une demande et non un
etat : l'arret lui-meme n'a lieu qu'entre deux passes, la ou le travail acquis
est coherent.

Le statut `CANCELLED` ne demande aucune modification de schema — la colonne
est un VARCHAR sans contrainte d'enumeration cote base.

Revision ID: 0010_job_cancellation
Revises: 0009_job_without_document
Create Date: 2026-09-19 10:00:00.000000
"""
from __future__ import annotations

import sqlalchemy as sa
from alembic import op

revision = '0010_job_cancellation'
down_revision = '0009_job_without_document'
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.add_column(
        'generation_jobs',
        sa.Column('cancel_requested_at', sa.DateTime(timezone=True), nullable=True),
    )


def downgrade() -> None:
    # Les taches annulees restent annulees : leur statut est une donnee, pas
    # une consequence de cette colonne. Seule la demande disparait.
    with op.batch_alter_table('generation_jobs') as batch:
        batch.drop_column('cancel_requested_at')
