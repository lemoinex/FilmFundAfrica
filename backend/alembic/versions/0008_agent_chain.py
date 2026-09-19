"""la chaine d'agents survit a la session

Cinq tables. Le dossier (`project_dossiers`) porte les sections produites par
les agents, en JSON : un plan de production n'a pas la meme forme d'un projet a
l'autre, et les figer en colonnes reviendrait a decider aujourd'hui de ce qu'un
agent aura le droit de produire demain.

Les constats et les traces de modification sont normalises, eux. On veut
pouvoir demander « quels blocages restent ouverts » ou « qui a touche au budget,
et pourquoi » sans relire du JSON — sans quoi la tracabilite ne sert a rien.

`project_dossiers` est distinct de `projects` a dessein : ces sections sont
produites par les agents, alors que la fiche projet porte ce que l'auteur a
saisi. Les confondre ferait ecraser sa saisie par une production d'agent.

Revision ID: 0008_agent_chain
Revises: 0007_document_language
Create Date: 2026-09-19 02:00:00.000000
"""
from __future__ import annotations

from alembic import op
import sqlalchemy as sa


revision = '0008_agent_chain'
down_revision = '0007_document_language'
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.create_table('project_dossiers',
    sa.Column('project_id', sa.String(length=36), nullable=False),
    sa.Column('project_identity', sa.JSON(), nullable=False),
    sa.Column('logline', sa.JSON(), nullable=True),
    sa.Column('concept', sa.JSON(), nullable=False),
    sa.Column('synopsis', sa.JSON(), nullable=False),
    sa.Column('characters', sa.JSON(), nullable=False),
    sa.Column('screenplay', sa.JSON(), nullable=False),
    sa.Column('director_vision', sa.JSON(), nullable=False),
    sa.Column('production_plan', sa.JSON(), nullable=False),
    sa.Column('budget', sa.JSON(), nullable=False),
    sa.Column('financing_plan', sa.JSON(), nullable=False),
    sa.Column('cultural_analysis', sa.JSON(), nullable=False),
    sa.Column('impact_analysis', sa.JSON(), nullable=False),
    sa.Column('final_documents', sa.JSON(), nullable=False),
    sa.Column('id', sa.String(length=36), nullable=False),
    sa.Column('created_at', sa.DateTime(timezone=True), server_default=sa.text('now()'), nullable=False),
    sa.Column('updated_at', sa.DateTime(timezone=True), server_default=sa.text('now()'), nullable=False),
    sa.ForeignKeyConstraint(['project_id'], ['projects.id'], ondelete='CASCADE'),
    sa.PrimaryKeyConstraint('id')
    )
    op.create_index(op.f('ix_project_dossiers_project_id'), 'project_dossiers', ['project_id'], unique=True)
    op.create_table('agent_runs',
    sa.Column('dossier_id', sa.String(length=36), nullable=False),
    sa.Column('status', sa.Enum('QUEUED', 'RUNNING', 'SUCCEEDED', 'FAILED', name='jobstatus', native_enum=False, length=20), nullable=False),
    sa.Column('verdict', sa.Enum('PASS', 'PASS_WITH_WARNINGS', 'REQUIRES_CORRECTION', 'BLOCKED', name='validationverdict', native_enum=False, length=25), nullable=True),
    sa.Column('rounds', sa.Integer(), nullable=False),
    sa.Column('exhausted', sa.Boolean(), nullable=False),
    sa.Column('stalled', sa.Boolean(), nullable=False),
    sa.Column('error', sa.Text(), nullable=True),
    sa.Column('finished_at', sa.DateTime(timezone=True), nullable=True),
    sa.Column('id', sa.String(length=36), nullable=False),
    sa.Column('created_at', sa.DateTime(timezone=True), server_default=sa.text('now()'), nullable=False),
    sa.Column('updated_at', sa.DateTime(timezone=True), server_default=sa.text('now()'), nullable=False),
    sa.ForeignKeyConstraint(['dossier_id'], ['project_dossiers.id'], ondelete='CASCADE'),
    sa.PrimaryKeyConstraint('id')
    )
    op.create_index(op.f('ix_agent_runs_dossier_id'), 'agent_runs', ['dossier_id'], unique=False)
    op.create_table('agent_steps',
    sa.Column('run_id', sa.String(length=36), nullable=False),
    sa.Column('sequence', sa.Integer(), nullable=False),
    sa.Column('agent', sa.Enum('DEVELOPMENT', 'SCREENWRITER', 'DIRECTOR', 'PRODUCER', 'FINANCING', 'IMPACT', 'CONSISTENCY_VALIDATOR', 'FUNDING_PACKAGE_VALIDATOR', name='agentrole', native_enum=False, length=30), nullable=False),
    sa.Column('agent_version', sa.String(length=20), nullable=False),
    sa.Column('analysis', sa.Text(), nullable=False),
    sa.Column('rationale', sa.Text(), nullable=False),
    sa.Column('next_agent_instructions', sa.Text(), nullable=False),
    sa.Column('verdict', sa.Enum('PASS', 'PASS_WITH_WARNINGS', 'REQUIRES_CORRECTION', 'BLOCKED', name='validationverdict', native_enum=False, length=25), nullable=True),
    sa.Column('changeset', sa.JSON(), nullable=False),
    sa.Column('decisions', sa.JSON(), nullable=False),
    sa.Column('provider', sa.String(length=40), nullable=True),
    sa.Column('model', sa.String(length=120), nullable=True),
    sa.Column('input_tokens', sa.Integer(), nullable=False),
    sa.Column('output_tokens', sa.Integer(), nullable=False),
    sa.Column('latency_ms', sa.Integer(), nullable=False),
    sa.Column('id', sa.String(length=36), nullable=False),
    sa.Column('created_at', sa.DateTime(timezone=True), server_default=sa.text('now()'), nullable=False),
    sa.Column('updated_at', sa.DateTime(timezone=True), server_default=sa.text('now()'), nullable=False),
    sa.ForeignKeyConstraint(['run_id'], ['agent_runs.id'], ondelete='CASCADE'),
    sa.PrimaryKeyConstraint('id')
    )
    op.create_index(op.f('ix_agent_steps_run_id'), 'agent_steps', ['run_id'], unique=False)
    op.create_table('dossier_findings',
    sa.Column('dossier_id', sa.String(length=36), nullable=False),
    sa.Column('run_id', sa.String(length=36), nullable=True),
    sa.Column('severity', sa.Enum('CRITICAL', 'MAJOR', 'MINOR', 'PASS', name='severity', native_enum=False, length=10), nullable=False),
    sa.Column('element', sa.String(length=255), nullable=False),
    sa.Column('description', sa.Text(), nullable=False),
    sa.Column('owner', sa.Enum('DEVELOPMENT', 'SCREENWRITER', 'DIRECTOR', 'PRODUCER', 'FINANCING', 'IMPACT', 'CONSISTENCY_VALIDATOR', 'FUNDING_PACKAGE_VALIDATOR', name='agentrole', native_enum=False, length=30), nullable=True),
    sa.Column('suggested_correction', sa.Text(), nullable=True),
    sa.Column('resolved_at', sa.DateTime(timezone=True), nullable=True),
    sa.Column('id', sa.String(length=36), nullable=False),
    sa.Column('created_at', sa.DateTime(timezone=True), server_default=sa.text('now()'), nullable=False),
    sa.Column('updated_at', sa.DateTime(timezone=True), server_default=sa.text('now()'), nullable=False),
    sa.ForeignKeyConstraint(['dossier_id'], ['project_dossiers.id'], ondelete='CASCADE'),
    sa.ForeignKeyConstraint(['run_id'], ['agent_runs.id'], ondelete='SET NULL'),
    sa.PrimaryKeyConstraint('id')
    )
    op.create_index(op.f('ix_dossier_findings_dossier_id'), 'dossier_findings', ['dossier_id'], unique=False)
    op.create_table('dossier_modifications',
    sa.Column('dossier_id', sa.String(length=36), nullable=False),
    sa.Column('run_id', sa.String(length=36), nullable=True),
    sa.Column('agent', sa.Enum('DEVELOPMENT', 'SCREENWRITER', 'DIRECTOR', 'PRODUCER', 'FINANCING', 'IMPACT', 'CONSISTENCY_VALIDATOR', 'FUNDING_PACKAGE_VALIDATOR', name='agentrole', native_enum=False, length=30), nullable=False),
    sa.Column('element', sa.String(length=255), nullable=False),
    sa.Column('previous_value', sa.Text(), nullable=True),
    sa.Column('new_value', sa.Text(), nullable=True),
    sa.Column('reason', sa.Text(), nullable=False),
    sa.Column('impact', sa.Text(), nullable=False),
    sa.Column('validation_status', sa.Enum('PASS', 'PASS_WITH_WARNINGS', 'REQUIRES_CORRECTION', 'BLOCKED', name='validationverdict', native_enum=False, length=25), nullable=True),
    sa.Column('version', sa.Integer(), nullable=False),
    sa.Column('id', sa.String(length=36), nullable=False),
    sa.Column('created_at', sa.DateTime(timezone=True), server_default=sa.text('now()'), nullable=False),
    sa.Column('updated_at', sa.DateTime(timezone=True), server_default=sa.text('now()'), nullable=False),
    sa.ForeignKeyConstraint(['dossier_id'], ['project_dossiers.id'], ondelete='CASCADE'),
    sa.ForeignKeyConstraint(['run_id'], ['agent_runs.id'], ondelete='SET NULL'),
    sa.PrimaryKeyConstraint('id')
    )
    op.create_index(op.f('ix_dossier_modifications_dossier_id'), 'dossier_modifications', ['dossier_id'], unique=False)


def downgrade() -> None:
    op.drop_index(op.f('ix_dossier_modifications_dossier_id'), table_name='dossier_modifications')
    op.drop_table('dossier_modifications')
    op.drop_index(op.f('ix_dossier_findings_dossier_id'), table_name='dossier_findings')
    op.drop_table('dossier_findings')
    op.drop_index(op.f('ix_agent_steps_run_id'), table_name='agent_steps')
    op.drop_table('agent_steps')
    op.drop_index(op.f('ix_agent_runs_dossier_id'), table_name='agent_runs')
    op.drop_table('agent_runs')
    op.drop_index(op.f('ix_project_dossiers_project_id'), table_name='project_dossiers')
    op.drop_table('project_dossiers')
