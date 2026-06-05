"""Query-time role-tag heuristics for airfoil suitability (gh-835).

Tags are computed from already-stored geometry metrics + per-Re polars.
NO new DB columns; NO migration; NO backfill.

## Tag definitions (non-exclusive — an airfoil can carry several)

v_stabilizer
    Symmetric airfoil, thin enough for a vertical stabiliser:
    family == 'symmetric' AND max_camber_pct <= 0.5 AND 6 <= t <= 15

h_stabilizer
    Same gate as v_stabilizer — an airfoil suitable for a horizontal
    stabiliser (roughly co-occurs; kept as a separate tag for UX clarity
    so users can filter by role explicitly):
    family == 'symmetric' AND max_camber_pct <= 0.5 AND 6 <= t <= 15

acro
    Symmetric, thin, aerobatic cross-section:
    family == 'symmetric' AND max_camber_pct <= 0.5 AND 7 <= t <= 12

winglet
    Thin, low-camber, aerodynamically clean — suitable for a winglet:
    max_thickness_pct <= 10 AND family in {symmetric, semi_symmetric, reflexed}
    AND max_camber_pct <= 3
    AND at least one non-degenerate polar row at Re <= 150 000
      (min_analysis_confidence >= LOW_RE_CONFIDENCE_GATE)

low_re
    Genuinely good at low Reynolds numbers (e.g. Re <= 150 000):
    At least one polar row with Re <= LOW_RE_UPPER_BOUND and
    min_analysis_confidence >= LOW_RE_CONFIDENCE_GATE.
    Documents: derived from per-Re polars; threshold Re = 150 000.

high_re
    Best performer at the upper edge of our grid (Re ~ 500 000–750 000).
    APPROXIMATE — our grid tops at 750 000; tag means the airfoil has
    at least one polar row at Re >= HIGH_RE_LOWER_BOUND (500 000) with
    min_analysis_confidence >= LOW_RE_CONFIDENCE_GATE.
    Clearly marked as approximate (see module docstring).

## Module constants
LOW_RE_UPPER_BOUND      = 150_000   (Re threshold for low_re tag)
HIGH_RE_LOWER_BOUND     = 500_000   (Re threshold for high_re tag)
LOW_RE_CONFIDENCE_GATE  = 0.85      (min_analysis_confidence for a row
                                     to count as "non-degenerate")
"""

from __future__ import annotations

from typing import Any

# ── Tuneable thresholds (exported for tests) ────────────────────────────────
LOW_RE_UPPER_BOUND: int = 150_000
HIGH_RE_LOWER_BOUND: int = 500_000
LOW_RE_CONFIDENCE_GATE: float = 0.85

# Families that qualify for winglet tag
_WINGLET_FAMILIES = {"symmetric", "semi_symmetric", "reflexed"}

# All valid tag literals — used for input validation
ALL_ROLE_TAGS: frozenset[str] = frozenset(
    {"v_stabilizer", "h_stabilizer", "acro", "winglet", "low_re", "high_re"}
)

# All valid family literals — matches AirfoilFamily in schemas/airfoil.py
ALL_FAMILIES: frozenset[str] = frozenset(
    {"flat_bottom", "semi_symmetric", "symmetric", "cambered", "reflexed"}
)


def compute_tags(
    *,
    family: str,
    max_thickness_pct: float,
    max_camber_pct: float,
    polars: list[dict[str, Any]],
) -> list[str]:
    """Compute role tags for a single airfoil from its geometry + per-Re polars.

    Parameters
    ----------
    family : str
        Airfoil family label ('symmetric', 'reflexed', etc.)
    max_thickness_pct : float
        Maximum thickness as % of chord (e.g. 12.0 for 12 % t/c).
    max_camber_pct : float
        Maximum camber as % of chord.
    polars : list[dict]
        Per-Re polar rows.  Each dict must contain at least:
          - 'reynolds'              : float  (Reynolds number)
          - 'min_analysis_confidence' : float | None

    Returns
    -------
    list[str]
        Sorted list of tag strings (alphabetically, for determinism).
    """
    t = max_thickness_pct
    c = max_camber_pct
    fam = (family or "").lower()

    tags: list[str] = []

    # ── v_stabilizer ──────────────────────────────────────────────────────────
    # Symmetric, low camber, 6–15 % thickness
    if fam == "symmetric" and c <= 0.5 and 6.0 <= t <= 15.0:
        tags.append("v_stabilizer")

    # ── h_stabilizer ─────────────────────────────────────────────────────────
    # Same gate as v_stabilizer — separate tag for UX
    if fam == "symmetric" and c <= 0.5 and 6.0 <= t <= 15.0:
        tags.append("h_stabilizer")

    # ── acro ──────────────────────────────────────────────────────────────────
    # Symmetric, thin, aerobatic (slightly tighter thickness window)
    if fam == "symmetric" and c <= 0.5 and 7.0 <= t <= 12.0:
        tags.append("acro")

    # ── winglet ───────────────────────────────────────────────────────────────
    # Thin, low-camber, appears in the right family, has ≥1 confident low-Re polar
    if (
        t <= 10.0
        and fam in _WINGLET_FAMILIES
        and c <= 3.0
        and _has_confident_polar_at_or_below(polars, LOW_RE_UPPER_BOUND)
    ):
        tags.append("winglet")

    # ── low_re ────────────────────────────────────────────────────────────────
    # Genuinely good at low Re: at least one confident polar at Re <= 150k
    if _has_confident_polar_at_or_below(polars, LOW_RE_UPPER_BOUND):
        tags.append("low_re")

    # ── high_re ───────────────────────────────────────────────────────────────
    # Good at upper grid edge (Re >= 500k). APPROXIMATE — grid tops at 750k.
    if _has_confident_polar_at_or_above(polars, HIGH_RE_LOWER_BOUND):
        tags.append("high_re")

    return sorted(tags)


def _has_confident_polar_at_or_below(polars: list[dict[str, Any]], re_limit: float) -> bool:
    """Return True if any polar row has Re <= re_limit with confidence >= gate."""
    for p in polars:
        re = p.get("reynolds")
        conf = p.get("min_analysis_confidence")
        if re is None or conf is None:
            continue
        if float(re) <= re_limit and float(conf) >= LOW_RE_CONFIDENCE_GATE:
            return True
    return False


def _has_confident_polar_at_or_above(polars: list[dict[str, Any]], re_limit: float) -> bool:
    """Return True if any polar row has Re >= re_limit with confidence >= gate."""
    for p in polars:
        re = p.get("reynolds")
        conf = p.get("min_analysis_confidence")
        if re is None or conf is None:
            continue
        if float(re) >= re_limit and float(conf) >= LOW_RE_CONFIDENCE_GATE:
            return True
    return False
