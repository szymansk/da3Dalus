"""gh-772 — role → control-axis decomposition for mixed control surfaces.

Single source of truth shared by the AVL geometry builder, the AeroSandbox
airplane builder, and the trim-enrichment service so all three agree on the
control-variable NAMES, their AVL ``SgnDup`` signs, gains, and which axis is
symmetric (pitch/lift) vs antisymmetric (roll/yaw).

Key decisions (validated by AVL / AeroSandbox / flight-dynamics critique, gh-772):

* A **dual-role** surface (elevon, flaperon, ruddervator) emits TWO AVL CONTROL
  variables on the same section — a primary (symmetric, ``SgnDup=+1``) and a
  secondary (antisymmetric, ``SgnDup=-1``) — so the trimmer drives each axis
  independently. avl_doc §CONTROL (multiple CONTROL lines per section are summed).
* ``SgnDup`` is a SIGN flag, never a differential magnitude. Differential is a
  reporting-only kinematic handled in enrichment, never in the geometry.
* Control-variable names must be globally unique (AVL silently collapses
  same-named CONTROL variables into one DOF, avl_doc 778-789).
"""

from __future__ import annotations

import re
from dataclasses import dataclass

_ROLE_TAG_RE = re.compile(r"^\[(\w+)\](.*)$")

# Roles that combine a symmetric + an antisymmetric axis on one physical surface.
# Order matters: primary (symmetric) axis first, secondary (antisymmetric) second.
_DUAL_ROLE_AXES: dict[str, tuple[str, str]] = {
    "elevon": ("pitch", "roll"),
    "flaperon": ("lift", "roll"),
    "ruddervator": ("pitch", "yaw"),
}

# Axis-label classification for the enrichment L/R reconstruction.
PRIMARY_AXES = {"pitch", "lift"}      # symmetric component
SECONDARY_AXES = {"roll", "yaw"}      # antisymmetric component


@dataclass(frozen=True)
class ControlAxis:
    """One AVL control variable contributing to a physical surface's deflection."""

    name: str          # globally-unique AVL/ASB control-variable name
    sgn_dup: float     # +1 symmetric, -1 antisymmetric (NEVER a differential magnitude)
    gain: float        # AVL gain column (deg deflection per control variable)
    symmetric: bool    # True → pitch/lift axis; False → roll/yaw axis
    hinge_point: float
    deflection: float  # baseline deflection for this axis (antisym dual axis → 0 in ASB)
    role: str
    axis: str          # "pitch" | "lift" | "roll" | "yaw" | "" (single-axis)


def is_dual_role(role: str | None) -> bool:
    return (role or "") in _DUAL_ROLE_AXES


def parse_role_tag(name: str) -> tuple[str | None, str]:
    """Parse a ``[role]display`` tag; returns ``(role, display)`` or ``(None, name)``."""
    m = _ROLE_TAG_RE.match(name)
    if m:
        return m.group(1), m.group(2)
    return None, name


def _sanitize(token: str) -> str:
    """Make a token safe as an AVL control name (no whitespace, no brackets)."""
    return re.sub(r"[^0-9A-Za-z_.-]", "_", token.strip())


def surface_suffix(wing_key: str, xsec_index: int) -> str:
    """The per-surface uniqueness suffix shared by naming and enrichment grouping."""
    return f"{_sanitize(wing_key)}_{xsec_index}"


def axis_control_name(role: str, axis: str, wing_key: str, xsec_index: int) -> str:
    """Build a globally-unique, role-tag-parseable, AVL-safe control-variable name.

    e.g. ``[ruddervator]pitch_htail_1``. Keeps the ``[role]`` prefix so
    ``parse_role_tag`` still recovers the role for enrichment, and the
    ``{axis}_{suffix}`` body so enrichment can regroup the two axes of one
    physical surface.
    """
    return f"[{role}]{_sanitize(axis)}_{surface_suffix(wing_key, xsec_index)}"


def control_axes_for_surface(
    *,
    role: str | None,
    tagged_name: str,
    symmetric: bool,
    hinge_point: float,
    deflection: float,
    mix_gain_primary: float = 1.0,
    mix_gain_secondary: float = 1.0,
    wing_key: str,
    xsec_index: int,
) -> list[ControlAxis]:
    """Decompose one physical control surface into its AVL control axes.

    Single-axis roles (elevator/flap/stabilator/rudder/aileron/other) keep their
    existing tagged name and ``±1`` SgnDup unchanged — exactly one axis. Dual
    roles return two axes (primary symmetric, secondary antisymmetric) with
    unique names; the secondary axis carries ``deflection=0`` so the AeroBuildup
    fallback never feeds a roll/yaw deflection into the single-axis ASB model.
    """
    role_value = (role or "").lower()

    if role_value in _DUAL_ROLE_AXES:
        primary_axis, secondary_axis = _DUAL_ROLE_AXES[role_value]
        return [
            ControlAxis(
                name=axis_control_name(role_value, primary_axis, wing_key, xsec_index),
                sgn_dup=1.0,
                gain=mix_gain_primary,
                symmetric=True,
                hinge_point=hinge_point,
                deflection=deflection,
                role=role_value,
                axis=primary_axis,
            ),
            ControlAxis(
                name=axis_control_name(role_value, secondary_axis, wing_key, xsec_index),
                sgn_dup=-1.0,
                gain=mix_gain_secondary,
                symmetric=False,
                hinge_point=hinge_point,
                deflection=0.0,  # antisymmetric axis: 0 baseline (AeroBuildup fallback)
                role=role_value,
                axis=secondary_axis,
            ),
        ]

    # Single-axis surface: preserve the existing name + sign convention verbatim.
    return [
        ControlAxis(
            name=tagged_name,
            sgn_dup=1.0 if symmetric else -1.0,
            gain=mix_gain_primary,
            symmetric=symmetric,
            hinge_point=hinge_point,
            deflection=deflection,
            role=role_value or None,  # type: ignore[arg-type]
            axis="",
        )
    ]


def assert_unique_control_names(names: list[str]) -> None:
    """Raise if any control-variable name repeats across the aircraft.

    AVL collapses same-named CONTROL variables into a single DOF; an accidental
    collision silently couples unrelated surfaces (avl_doc 778-789).
    """
    seen: set[str] = set()
    dupes: set[str] = set()
    for n in names:
        if n in seen:
            dupes.add(n)
        seen.add(n)
    if dupes:
        raise ValueError(
            f"Duplicate control-variable names would collapse into one AVL DOF: "
            f"{sorted(dupes)}"
        )
