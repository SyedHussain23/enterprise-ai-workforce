"""add notifications table and action comment support

Revision ID: c3d4e5f6a7b8
Revises: b2c3d4e5f6a7
Create Date: 2026-05-19 00:01:00.000000

WHY THIS MIGRATION:
- Adds the `notifications` table — surface for in-app updates on request
  approvals, rejections, comments, escalations.
- Adds `action_comments` join table for threaded discussion on a single
  request, used by both employees and approvers.

Both are additive — no data backfill, safe to roll forward and back.
"""
from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql

revision = 'c3d4e5f6a7b8'
down_revision = 'b2c3d4e5f6a7'
branch_labels = None
depends_on = None


def upgrade() -> None:
    # ── notifications ─────────────────────────────────────────────────────────
    op.create_table(
        'notifications',
        sa.Column('id', postgresql.UUID(as_uuid=True), primary_key=True),
        sa.Column('company_id', postgresql.UUID(as_uuid=True),
                  sa.ForeignKey('companies.id', ondelete='CASCADE'), nullable=False),
        sa.Column('recipient_id', postgresql.UUID(as_uuid=True),
                  sa.ForeignKey('users.id', ondelete='CASCADE'), nullable=False),
        sa.Column('actor_id', postgresql.UUID(as_uuid=True),
                  sa.ForeignKey('users.id', ondelete='SET NULL'), nullable=True),
        sa.Column('kind', sa.String(40), nullable=False),
        sa.Column('title', sa.String(200), nullable=False),
        sa.Column('message', sa.String(800), nullable=False),
        sa.Column('entity_type', sa.String(40), nullable=True),
        sa.Column('entity_id', postgresql.UUID(as_uuid=True), nullable=True),
        sa.Column('payload', postgresql.JSONB, nullable=True),
        sa.Column('read_at', sa.DateTime(timezone=True), nullable=True),
        sa.Column('is_read', sa.Boolean, nullable=False, server_default=sa.text('false')),
        sa.Column('created_at', sa.DateTime(timezone=True),
                  server_default=sa.text('now()'), nullable=False),
        sa.Column('updated_at', sa.DateTime(timezone=True),
                  server_default=sa.text('now()'), nullable=False),
    )
    op.create_index('ix_notifications_company_id',   'notifications', ['company_id'])
    op.create_index('ix_notifications_recipient_id', 'notifications', ['recipient_id'])
    op.create_index('ix_notifications_kind',         'notifications', ['kind'])
    op.create_index('ix_notifications_is_read',      'notifications', ['is_read'])
    op.create_index('ix_notifications_read_at',      'notifications', ['read_at'])
    # The single query the UI runs constantly:
    op.create_index(
        'ix_notifications_recipient_unread',
        'notifications',
        ['recipient_id', 'is_read', 'created_at'],
    )

    # ── action_comments ───────────────────────────────────────────────────────
    op.create_table(
        'action_comments',
        sa.Column('id', postgresql.UUID(as_uuid=True), primary_key=True),
        sa.Column('action_id', postgresql.UUID(as_uuid=True),
                  sa.ForeignKey('actions.id', ondelete='CASCADE'), nullable=False),
        sa.Column('author_id', postgresql.UUID(as_uuid=True),
                  sa.ForeignKey('users.id', ondelete='SET NULL'), nullable=True),
        sa.Column('body', sa.Text, nullable=False),
        sa.Column('created_at', sa.DateTime(timezone=True),
                  server_default=sa.text('now()'), nullable=False),
        sa.Column('updated_at', sa.DateTime(timezone=True),
                  server_default=sa.text('now()'), nullable=False),
    )
    op.create_index('ix_action_comments_action_id', 'action_comments', ['action_id'])


def downgrade() -> None:
    op.drop_index('ix_action_comments_action_id', table_name='action_comments')
    op.drop_table('action_comments')

    op.drop_index('ix_notifications_recipient_unread', table_name='notifications')
    op.drop_index('ix_notifications_read_at',      table_name='notifications')
    op.drop_index('ix_notifications_is_read',      table_name='notifications')
    op.drop_index('ix_notifications_kind',         table_name='notifications')
    op.drop_index('ix_notifications_recipient_id', table_name='notifications')
    op.drop_index('ix_notifications_company_id',   table_name='notifications')
    op.drop_table('notifications')
