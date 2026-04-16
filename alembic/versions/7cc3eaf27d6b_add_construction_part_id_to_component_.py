"""add_construction_part_id_to_component_tree

Revision ID: 7cc3eaf27d6b
Revises: 4a9c81984e86
Create Date: 2026-04-16 19:31:14.017382

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision: str = '7cc3eaf27d6b'
down_revision: Union[str, None] = '4a9c81984e86'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    """Add construction_part_id FK to component_tree (gh#57-u4d).

    Two-step pattern (matches 1f3b9c42e3aa): add the bare column first, then
    create the named FK constraint. SQLite needs the constraint to be named
    explicitly when added via batch_alter_table.
    """
    with op.batch_alter_table('component_tree', schema=None) as batch_op:
        batch_op.add_column(
            sa.Column('construction_part_id', sa.Integer(), nullable=True)
        )
        batch_op.create_foreign_key(
            'fk_component_tree_construction_part_id',
            'construction_parts',
            ['construction_part_id'],
            ['id'],
        )


def downgrade() -> None:
    """Drop construction_part_id from component_tree."""
    with op.batch_alter_table('component_tree', schema=None) as batch_op:
        batch_op.drop_constraint(
            'fk_component_tree_construction_part_id', type_='foreignkey'
        )
        batch_op.drop_column('construction_part_id')
