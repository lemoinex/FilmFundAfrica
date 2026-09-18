"""un document retient la langue dans laquelle il a ete redige

Le retravail d'un document (ameliorer, raccourcir, corriger) ne recevait
aucune langue et repartait donc sur le francais. Sur un document anglais,
« corriger » appliquait la typographie francaise — espaces insecables et
guillemets « » — a un texte qui n'en veut pas.

La langue ne se deduit ni du projet ni du compte : `projects.language` est
celle de l'oeuvre, et un film en wolof se presente en francais a un fonds
francophone. Elle est donc retenue a la generation.

Les documents anterieurs ont ete produits par un frontend qui imposait `fr` :
la valeur par defaut dit ce qui s'est reellement passe, elle ne le suppose pas.

Revision ID: 0007_document_language
Revises: 0006_notification_i18n
Create Date: 2026-09-18 23:05:00.000000
"""
from __future__ import annotations

import sqlalchemy as sa
from alembic import op

revision = '0007_document_language'
down_revision = '0006_notification_i18n'
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.add_column(
        'documents',
        sa.Column('language', sa.String(length=2), nullable=False, server_default='fr'),
    )


def downgrade() -> None:
    op.drop_column('documents', 'language')
