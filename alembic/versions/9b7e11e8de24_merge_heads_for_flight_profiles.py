"""merge alembic heads for flight profile feature

Revision ID: 9b7e11e8de24
Revises: df18c9f3ba1d, 6d2bb7cc35f4
Create Date: 2026-02-13 19:20:00.000000

"""
from typing import Sequence, Union


# revision identifiers, used by Alembic.
revision: str = "9b7e11e8de24"
down_revision: Union[str, Sequence[str], None] = ("df18c9f3ba1d", "6d2bb7cc35f4")
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    pass


def downgrade() -> None:
    pass
