"""unify spare origin vector units to mm gh402

Revision ID: b2ce6f00fe42
Revises: 87bb4e31e610
Create Date: 2026-05-03 17:07:38.785374

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision: str = 'b2ce6f00fe42'
down_revision: Union[str, None] = '87bb4e31e610'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.execute("""
        UPDATE wing_xsec_spares
        SET spare_origin = json_array(
              json_extract(spare_origin, '$[0]') * 1000,
              json_extract(spare_origin, '$[1]') * 1000,
              json_extract(spare_origin, '$[2]') * 1000
            )
        WHERE spare_origin IS NOT NULL
    """)
    op.execute("""
        UPDATE wing_xsec_spares
        SET spare_vector = json_array(
              json_extract(spare_vector, '$[0]') * 1000,
              json_extract(spare_vector, '$[1]') * 1000,
              json_extract(spare_vector, '$[2]') * 1000
            )
        WHERE spare_vector IS NOT NULL
    """)


def downgrade() -> None:
    op.execute("""
        UPDATE wing_xsec_spares
        SET spare_origin = json_array(
              json_extract(spare_origin, '$[0]') * 0.001,
              json_extract(spare_origin, '$[1]') * 0.001,
              json_extract(spare_origin, '$[2]') * 0.001
            )
        WHERE spare_origin IS NOT NULL
    """)
    op.execute("""
        UPDATE wing_xsec_spares
        SET spare_vector = json_array(
              json_extract(spare_vector, '$[0]') * 0.001,
              json_extract(spare_vector, '$[1]') * 0.001,
              json_extract(spare_vector, '$[2]') * 0.001
            )
        WHERE spare_vector IS NOT NULL
    """)
