"""ACQUIRED_AR_CHARACTER.acquired_mission_id nullable

Revision ID: 1a2efce63def
Revises: 06835b9ab7af
Create Date: 2026-09-10 11:30:00.000000

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision: str = '1a2efce63def'
down_revision: Union[str, Sequence[str], None] = '06835b9ab7af'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    """Upgrade schema."""
    op.alter_column(
        'ACQUIRED_AR_CHARACTER',
        'acquired_mission_id',
        existing_type=sa.BigInteger(),
        nullable=True,
    )
    # 컬럼이 NULL 을 허용하게 되면서 미션 삭제 시 동작도 CASCADE → SET NULL 로 바꾼다.
    # (획득 기록은 남기고 출처만 비운다)
    op.drop_constraint('fk_acquired__mission', 'ACQUIRED_AR_CHARACTER', type_='foreignkey')
    op.create_foreign_key(
        'fk_acquired__mission',
        'ACQUIRED_AR_CHARACTER',
        'MISSION',
        ['acquired_mission_id'],
        ['id'],
        ondelete='SET NULL',
    )


def downgrade() -> None:
    """Downgrade schema."""
    op.drop_constraint('fk_acquired__mission', 'ACQUIRED_AR_CHARACTER', type_='foreignkey')
    op.create_foreign_key(
        'fk_acquired__mission',
        'ACQUIRED_AR_CHARACTER',
        'MISSION',
        ['acquired_mission_id'],
        ['id'],
        ondelete='CASCADE',
    )
    # NOT NULL 로 되돌리려면 출처가 비어 있는 행이 없어야 한다.
    op.execute(sa.text('DELETE FROM `ACQUIRED_AR_CHARACTER` WHERE `acquired_mission_id` IS NULL'))
    op.alter_column(
        'ACQUIRED_AR_CHARACTER',
        'acquired_mission_id',
        existing_type=sa.BigInteger(),
        nullable=False,
    )
