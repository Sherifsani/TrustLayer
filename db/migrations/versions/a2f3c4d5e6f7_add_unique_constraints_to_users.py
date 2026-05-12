"""add unique constraints to users

Revision ID: a2f3c4d5e6f7
Revises: 69fddb404fc5
Create Date: 2026-05-12 00:00:00.000000

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision: str = 'a2f3c4d5e6f7'
down_revision: Union[str, Sequence[str], None] = '18bb77a42ca0'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    # Create unique constraints for email, bvn_hash and nin_hash
    with op.batch_alter_table('users') as batch_op:
        batch_op.create_unique_constraint('uq_users_email', ['email'])
        batch_op.create_unique_constraint('uq_users_bvn_hash', ['bvn_hash'])
        batch_op.create_unique_constraint('uq_users_nin_hash', ['nin_hash'])


def downgrade() -> None:
    with op.batch_alter_table('users') as batch_op:
        batch_op.drop_constraint('uq_users_nin_hash', type_='unique')
        batch_op.drop_constraint('uq_users_bvn_hash', type_='unique')
        batch_op.drop_constraint('uq_users_email', type_='unique')
