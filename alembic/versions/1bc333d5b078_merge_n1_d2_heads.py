"""merge_n1_d2_heads

Revision ID: 1bc333d5b078
Revises: 1a39e098d77e, 7cc3eaf27d6b
Create Date: 2026-04-16 20:03:29.511945

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision: str = '1bc333d5b078'
down_revision: Union[str, None] = ('1a39e098d77e', '7cc3eaf27d6b')
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    """Upgrade schema."""
    pass


def downgrade() -> None:
    """Downgrade schema."""
    pass
