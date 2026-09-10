"""add AR_CHARACTER.character_color

Revision ID: 06835b9ab7af
Revises: 055991cc48ff
Create Date: 2026-09-10 11:00:00.000000

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision: str = '06835b9ab7af'
down_revision: Union[str, Sequence[str], None] = '055991cc48ff'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    """Upgrade schema."""
    op.add_column(
        'AR_CHARACTER',
        sa.Column('character_color', sa.String(length=20), nullable=True, comment='캐릭터 대표 색상'),
    )


def downgrade() -> None:
    """Downgrade schema."""
    op.drop_column('AR_CHARACTER', 'character_color')
