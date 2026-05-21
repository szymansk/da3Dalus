"""english-only motor_glider and flying_wing labels/description

Revision ID: a85f8972a5df
Revises: 5a0f2c4a9b52
Create Date: 2026-05-21 21:18:26.635995

Follow-up to PR #600: the Python seed in app/services/mission_preset_seed.py
was updated to English-only labels and description, but the earlier Alembic
migrations (e7387f35f31e for motor_glider, 5a0f2c4a9b52 for flying_wing)
had inserted the rows with German parentheticals. The runtime seed function
is insert-only and does not update existing rows, so any DB that ran the
old migrations keeps the German strings. This migration patches them in
place. Idempotent: only updates rows whose label or description still
matches the old German variant.

"""

from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision: str = "a85f8972a5df"
down_revision: Union[str, None] = "5a0f2c4a9b52"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


_MOTOR_GLIDER_LABEL_OLD = "Motorsegler (Motor Glider)"
_MOTOR_GLIDER_LABEL_NEW = "Motor Glider"

_FLYING_WING_LABEL_OLD = "Flying Wing (Nurflügler)"
_FLYING_WING_LABEL_NEW = "Flying Wing"

# These two strings come verbatim from app/services/mission_preset_seed.py;
# kept here so the migration is self-contained and re-runnable on databases
# that have stale German content even if the seed module evolves later.
_FLYING_WING_DESCRIPTION_NEW = (
    "Tailless RC flying wing — longitudinal trim via "
    "sweep + washout + reflex airfoil. Tail-volume sizing not "
    "applicable; static-margin corridor tightened (5–10 % MAC, "
    "default 7.5 %) per #579 — this is a dynamic-stability / "
    "control-power floor, NOT a static-aerodynamic limit (C_m,q "
    "pitch damping is much smaller without a tail moment arm). "
    "Aspect ratio default 8 (range 6–12). Sweep default 25° "
    "leading-edge sweep (range 20–35°); sweep convention is "
    "LE-sweep, NOT c/4 — the two differ by ~5° for typical taper. "
    "Washout default 5° at the mid (range varies by airfoil): "
    "**3–5° for symmetric** sections (NACA 0012-class), "
    "**5–9° for reflex** sections (E184/E230, MH-series) — reflex "
    "sections have less inherent stabilising camber and need MORE "
    "washout, not less (Lennon Ch. 23 + NACA tunnel data). "
    "Taper ratio default 0.5 — HARD CONSTRAINT 0.4 ≤ λ ≤ 0.6 to "
    "avoid tip-stall + nose-up pitch break (Lennon: avoid 4:1 "
    "taper; Sadraey converges). Stability guard: simultaneously "
    "sweep < 20° AND washout < 3° is rejected (C_m,q margin "
    "phugoid-divergent). Airfoil hints: **classic** Eppler E184 "
    "(root) / E230 (tip); **modern** MH-series (MH45, MH60, MH61, "
    "MH64). PREFERRED STRATEGY: HYBRID (moderate reflex + moderate "
    "sweep + moderate washout) per Apogee — best modern flying "
    "wings. Symmetric-airfoil caveat: dx/dα = 0 from the section "
    "alone, so a symmetric airfoil on a flying wing requires "
    "CG BELOW the wing chord plane (pendulum stability) — "
    "otherwise the wing is not statically stable. Penalty of "
    "reflex sections per Apogee: −9–15 % cl_max, −5 % minimum "
    "profile drag (so cl_max = 1.0 is conservative: 1.25 cambered "
    "× 0.85–0.91). YAW STABILITY is out of scope here — drag "
    "rudders / split rudders / vertical fins / winglets are a "
    "separate ticket; see Sadraey §12.2 and Apogee for design "
    "guidance."
)


def upgrade() -> None:
    """Patch motor_glider + flying_wing rows to the English-only form."""
    conn = op.get_bind()

    conn.execute(
        sa.text(
            "UPDATE mission_presets SET label = :new_label "
            "WHERE id = 'motor_glider' AND label = :old_label"
        ),
        {"new_label": _MOTOR_GLIDER_LABEL_NEW, "old_label": _MOTOR_GLIDER_LABEL_OLD},
    )

    conn.execute(
        sa.text(
            "UPDATE mission_presets SET label = :new_label, description = :new_description "
            "WHERE id = 'flying_wing' AND label = :old_label"
        ),
        {
            "new_label": _FLYING_WING_LABEL_NEW,
            "new_description": _FLYING_WING_DESCRIPTION_NEW,
            "old_label": _FLYING_WING_LABEL_OLD,
        },
    )


def downgrade() -> None:
    """Best-effort revert to the original German strings.

    The original flying_wing description still contained two German tokens
    (`Nurflügler`); this restores those exact strings for symmetry with
    e7387f35f31e and 5a0f2c4a9b52 if the migration needs to be rolled back.
    """
    conn = op.get_bind()

    conn.execute(
        sa.text(
            "UPDATE mission_presets SET label = :old_label "
            "WHERE id = 'motor_glider' AND label = :new_label"
        ),
        {"old_label": _MOTOR_GLIDER_LABEL_OLD, "new_label": _MOTOR_GLIDER_LABEL_NEW},
    )

    # Reinstate German tokens in flying_wing description
    flying_wing_description_old = (
        _FLYING_WING_DESCRIPTION_NEW
        .replace(
            "Tailless RC flying wing —",
            "Tailless RC flying wing (Nurflügler) —",
        )
        .replace(
            "symmetric airfoil on a flying wing requires",
            "symmetric airfoil on a Nurflügler requires",
        )
    )

    conn.execute(
        sa.text(
            "UPDATE mission_presets SET label = :old_label, description = :old_description "
            "WHERE id = 'flying_wing' AND label = :new_label"
        ),
        {
            "old_label": _FLYING_WING_LABEL_OLD,
            "old_description": flying_wing_description_old,
            "new_label": _FLYING_WING_LABEL_NEW,
        },
    )
