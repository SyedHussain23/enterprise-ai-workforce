"""add indexes and unique constraints

Revision ID: b2c3d4e5f6a7
Revises: a516cee4e5ec
Create Date: 2026-05-18 00:01:00.000000

WHY THIS MIGRATION:
- C1: (username, company_id) composite unique constraint was missing — duplicate
  usernames per tenant were possible, breaking multi-tenant auth correctness.
- H3: FK columns had no indexes — every admin/analytics query did full table scans.
  PostgreSQL does NOT auto-create indexes on FK columns unlike MySQL.
"""
from alembic import op
import sqlalchemy as sa

revision = 'b2c3d4e5f6a7'
down_revision = 'a516cee4e5ec'
branch_labels = None
depends_on = None


def upgrade() -> None:
    # ── C1: Unique username per tenant ───────────────────────────────────────
    op.create_unique_constraint(
        'uq_users_username_company',
        'users',
        ['username', 'company_id'],
    )

    # ── H3: FK indexes for foreign-key columns ────────────────────────────────
    # users
    op.create_index('ix_users_company_id',        'users',         ['company_id'])
    op.create_index('ix_users_email',             'users',         ['email'])
    op.create_index('ix_users_is_active',         'users',         ['is_active'])

    # conversations
    op.create_index('ix_conversations_company_id','conversations',  ['company_id'])
    op.create_index('ix_conversations_user_id',   'conversations',  ['user_id'])
    op.create_index('ix_conversations_session_id','conversations',  ['session_id'])

    # messages
    op.create_index('ix_messages_conversation_id','messages',       ['conversation_id'])
    op.create_index('ix_messages_created_at',     'messages',       ['created_at'])

    # workflow_logs
    op.create_index('ix_workflow_logs_company_id','workflow_logs',  ['company_id'])
    op.create_index('ix_workflow_logs_user_id',   'workflow_logs',  ['user_id'])
    op.create_index('ix_workflow_logs_session_id','workflow_logs',  ['session_id'])
    op.create_index('ix_workflow_logs_created_at','workflow_logs',  ['created_at'])

    # actions
    op.create_index('ix_actions_company_id',      'actions',        ['company_id'])
    op.create_index('ix_actions_user_id',         'actions',        ['user_id'])
    op.create_index('ix_actions_status',          'actions',        ['status'])
    op.create_index('ix_actions_created_at',      'actions',        ['created_at'])

    # audit_logs
    op.create_index('ix_audit_logs_company_id',   'audit_logs',     ['company_id'])
    op.create_index('ix_audit_logs_user_id',      'audit_logs',     ['user_id'])
    op.create_index('ix_audit_logs_event_type',   'audit_logs',     ['event_type'])
    op.create_index('ix_audit_logs_created_at',   'audit_logs',     ['created_at'])

    # feedback
    op.create_index('ix_feedback_workflow_log_id','feedback',       ['workflow_log_id'])


def downgrade() -> None:
    op.drop_constraint('uq_users_username_company', 'users', type_='unique')

    for idx, tbl in [
        ('ix_users_company_id',        'users'),
        ('ix_users_email',             'users'),
        ('ix_users_is_active',         'users'),
        ('ix_conversations_company_id','conversations'),
        ('ix_conversations_user_id',   'conversations'),
        ('ix_conversations_session_id','conversations'),
        ('ix_messages_conversation_id','messages'),
        ('ix_messages_created_at',     'messages'),
        ('ix_workflow_logs_company_id','workflow_logs'),
        ('ix_workflow_logs_user_id',   'workflow_logs'),
        ('ix_workflow_logs_session_id','workflow_logs'),
        ('ix_workflow_logs_created_at','workflow_logs'),
        ('ix_actions_company_id',      'actions'),
        ('ix_actions_user_id',         'actions'),
        ('ix_actions_status',          'actions'),
        ('ix_actions_created_at',      'actions'),
        ('ix_audit_logs_company_id',   'audit_logs'),
        ('ix_audit_logs_user_id',      'audit_logs'),
        ('ix_audit_logs_event_type',   'audit_logs'),
        ('ix_audit_logs_created_at',   'audit_logs'),
        ('ix_feedback_workflow_log_id','feedback'),
    ]:
        op.drop_index(idx, table_name=tbl)
