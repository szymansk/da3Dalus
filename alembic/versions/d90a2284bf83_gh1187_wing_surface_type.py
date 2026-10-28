"""gh-1187: explicit wing role ``wings.surface_type`` (+ ``surface_type_inferred``)

Every lifting surface gets an explicit, required role (main_wing, horizontal_tail,
vertical_tail, v_tail, canard, tandem_wing, winglet). Existing rows get a *proposed*
value, derived once by the heuristic below and stored with ``surface_type_inferred = 1``
so the application declares it (ADR 0020) until the user confirms or corrects it.

The heuristic lives ONLY in this migration (maintainer decision 2026-10-28, option (a));
the application code never infers a role (ADR 0021). Per aeroplane, in this order:

1. Name hint (case-insensitive; long words as substrings, short tokens such as ``hlw``
   or ``fin`` only as whole words). First matching group wins:
   canard -> ``canard``; winglet -> ``winglet``; V-tail words -> ``v_tail``;
   fin / rudder / Seitenleitwerk / SLW / vertical -> ``vertical_tail``;
   Hoehenleitwerk / HLW / horizontal / elevator / stabilizer -> ``horizontal_tail``.
2. Main wing: the wing with the largest planform area among the wings WITHOUT a name
   hint; when every wing carries a hint, the largest wing of the aeroplane. It becomes
   ``main_wing`` (so exactly one main wing exists per aeroplane that has wings).
3. Every other unhinted wing (geometry, only because no name says anything): not
   symmetric -> ``vertical_tail``; root leading edge ahead of the main wing's -> ``canard``;
   otherwise -> ``horizontal_tail``.

Revision ID: d90a2284bf83
Revises: a1157f5e11a0
Create Date: 2026-10-28 09:00:00.000000
"""

import json
import re
from typing import Optional, Sequence, Union

import sqlalchemy as sa
from alembic import op

revision: str = "d90a2284bf83"
down_revision: Union[str, None] = "a1157f5e11a0"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None

# (surface_type, substrings, whole-word tokens) in priority order. Short words are tokens
# only: "fin" must not match "final", "ente" must not match "Entenhausen".
_NAME_HINTS: list[tuple[str, tuple[str, ...], tuple[str, ...]]] = [
    ("canard", ("canard",), ("ente",)),
    ("winglet", ("winglet", "randbogen"), ()),
    (
        "v_tail",
        ("v-tail", "v tail", "v_tail", "v-leitwerk", "v leitwerk", "schmetterling", "butterfly"),
        (),
    ),
    (
        "vertical_tail",
        ("vertical", "seitenleitwerk", "seitenruder", "rudder"),
        ("fin", "slw", "vtail", "vtp", "vstab"),
    ),
    (
        "horizontal_tail",
        ("horizontal", "hoehenleitwerk", "höhenleitwerk", "elevator", "stabilizer", "stabiliser"),
        ("hlw", "htail", "htp", "hstab"),
    ),
]


def _name_hint(name: str) -> Optional[str]:
    """Return the role a wing name suggests, or None when it says nothing."""
    lowered = (name or "").lower()
    words = set(re.findall(r"[a-zäöüß0-9]+", lowered))
    for surface_type, substrings, tokens in _NAME_HINTS:
        if any(s in lowered for s in substrings) or any(t in words for t in tokens):
            return surface_type
    return None


def _as_point(value) -> list[float]:
    if isinstance(value, str):
        value = json.loads(value)
    point = [float(v) for v in (value or [])][:3]
    return point + [0.0] * (3 - len(point))


def _planform_area(xsecs: list[tuple[float, list[float]]], symmetric: bool) -> float:
    """Trapezoidal planform area from (chord, xyz_le) ribs, ordered root to tip."""
    total = 0.0
    for (c0, le0), (c1, le1) in zip(xsecs, xsecs[1:], strict=False):
        span = (abs(le1[1] - le0[1]) ** 2 + abs(le1[2] - le0[2]) ** 2) ** 0.5
        total += 0.5 * (c0 + c1) * span
    return total * (2.0 if symmetric else 1.0)


def propose_surface_types(wings: list[dict]) -> dict[int, str]:
    """Propose a role per wing of ONE aeroplane.

    Args:
        wings: dicts with ``id``, ``name``, ``symmetric``, ``area`` and ``root_x``.

    Returns:
        Mapping wing id -> proposed ``surface_type``.
    """
    if not wings:
        return {}
    proposal: dict[int, str] = {}
    unhinted = []
    for wing in wings:
        hint = _name_hint(wing["name"])
        if hint is None:
            unhinted.append(wing)
        else:
            proposal[wing["id"]] = hint
    pool = unhinted or wings
    main = max(pool, key=lambda w: (w["area"], -w["id"]))
    proposal[main["id"]] = "main_wing"
    for wing in unhinted:
        if wing["id"] == main["id"]:
            continue
        if not wing["symmetric"]:
            proposal[wing["id"]] = "vertical_tail"
        elif wing["root_x"] < main["root_x"]:
            proposal[wing["id"]] = "canard"
        else:
            proposal[wing["id"]] = "horizontal_tail"
    return proposal


def _load_wings_by_aeroplane(bind) -> dict[int, list[dict]]:
    wings: dict[int, list[dict]] = {}
    rows = bind.execute(
        sa.text("SELECT id, name, symmetric, aeroplane_id FROM wings ORDER BY id")
    ).fetchall()
    for wing_id, name, symmetric, aeroplane_id in rows:
        ribs = bind.execute(
            sa.text("SELECT chord, xyz_le FROM wing_xsecs WHERE wing_id = :w ORDER BY sort_index"),
            {"w": wing_id},
        ).fetchall()
        xsecs = [(float(chord or 0.0), _as_point(xyz_le)) for chord, xyz_le in ribs]
        is_symmetric = bool(symmetric) if symmetric is not None else True
        wings.setdefault(aeroplane_id, []).append(
            {
                "id": wing_id,
                "name": name,
                "symmetric": is_symmetric,
                "area": _planform_area(xsecs, is_symmetric),
                "root_x": xsecs[0][1][0] if xsecs else 0.0,
            }
        )
    return wings


def upgrade() -> None:
    """Add the columns, propose a role for every existing wing, then make the role required."""
    op.add_column("wings", sa.Column("surface_type", sa.String(), nullable=True))
    op.add_column(
        "wings",
        sa.Column(
            "surface_type_inferred", sa.Boolean(), nullable=False, server_default=sa.false()
        ),
    )
    bind = op.get_bind()
    for wings in _load_wings_by_aeroplane(bind).values():
        for wing_id, surface_type in propose_surface_types(wings).items():
            bind.execute(
                sa.text(
                    "UPDATE wings SET surface_type = :t, surface_type_inferred = :i WHERE id = :w"
                ),
                {"t": surface_type, "i": True, "w": wing_id},
            )
    with op.batch_alter_table("wings") as batch_op:
        batch_op.alter_column("surface_type", existing_type=sa.String(), nullable=False)


def downgrade() -> None:
    """Drop both columns."""
    with op.batch_alter_table("wings") as batch_op:
        batch_op.drop_column("surface_type_inferred")
        batch_op.drop_column("surface_type")
