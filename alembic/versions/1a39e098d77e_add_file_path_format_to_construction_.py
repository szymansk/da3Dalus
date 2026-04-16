"""add_file_path_format_to_construction_parts

Revision ID: 1a39e098d77e
Revises: 4a9c81984e86
Create Date: 2026-04-16 19:38:30.843950

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision: str = '1a39e098d77e'
down_revision: Union[str, None] = '4a9c81984e86'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    """Add file_path + file_format columns to construction_parts (gh#57-9uk)."""
    with op.batch_alter_table('construction_parts', schema=None) as batch_op:
        batch_op.add_column(sa.Column('file_path', sa.String(), nullable=True))
        batch_op.add_column(sa.Column('file_format', sa.String(), nullable=True))


def downgrade() -> None:
    """Drop file_path + file_format from construction_parts."""
    with op.batch_alter_table('construction_parts', schema=None) as batch_op:
        batch_op.drop_column('file_format')
        batch_op.drop_column('file_path')
