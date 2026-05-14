"""add mono_account_id to users

Revision ID: a1b2c3d4e5f6
Revises: 69fddb404fc5
Create Date: 2026-05-13 00:00:00.000000
"""
from alembic import op
import sqlalchemy as sa

# revision identifiers, used by Alembic.
revision = 'a1b2c3d4e5f6'
down_revision = '69fddb404fc5'
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.add_column('users', sa.Column('mono_account_id', sa.String(), nullable=True))
    op.create_index(op.f('ix_users_mono_account_id'), 'users', ['mono_account_id'], unique=False)


def downgrade() -> None:
    op.drop_index(op.f('ix_users_mono_account_id'), table_name='users')
    op.drop_column('users', 'mono_account_id')
