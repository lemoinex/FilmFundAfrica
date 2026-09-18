"""notifications traduisibles a la lecture

Une notification stockait sa phrase deja redigee : elle restait donc dans la
langue qui avait cours a sa creation, meme relue en anglais. Elle porte
desormais sa cle de message et ses parametres, et le texte est reconstruit
dans la langue de qui lit.

`title` et `body` sont conserves : les notifications ecrites avant cette
migration n'ont pas de cle, et leur texte est le seul qu'on ait. Les effacer
priverait leurs destinataires de messages qu'ils n'ont pas encore lus.

Revision ID: 0006_notification_i18n
Revises: 0005_candidates
Create Date: 2026-09-18 22:10:00.000000
"""
from __future__ import annotations

import sqlalchemy as sa
from alembic import op

revision = '0006_notification_i18n'
down_revision = '0005_candidates'
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.add_column(
        'notifications', sa.Column('title_key', sa.String(length=120), nullable=True)
    )
    op.add_column(
        'notifications', sa.Column('body_key', sa.String(length=120), nullable=True)
    )
    # Non nul avec une valeur par defaut serveur : les lignes existantes
    # recoivent un objet vide sans qu'il faille les parcourir.
    op.add_column(
        'notifications',
        sa.Column('params', sa.JSON(), nullable=False, server_default='{}'),
    )


def downgrade() -> None:
    op.drop_column('notifications', 'params')
    op.drop_column('notifications', 'body_key')
    op.drop_column('notifications', 'title_key')
