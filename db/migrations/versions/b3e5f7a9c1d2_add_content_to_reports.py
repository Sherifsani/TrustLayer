"""add content column to reports

Revision ID: b3e5f7a9c1d2
Revises: a2f3c4d5e6f7
Create Date: 2026-05-12 10:00:00.000000

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


revision: str = 'b3e5f7a9c1d2'
down_revision: Union[str, Sequence[str], None] = 'a2f3c4d5e6f7'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.add_column('reports', sa.Column('content', sa.JSON(), nullable=True))


def downgrade() -> None:
    op.drop_column('reports', 'content')
