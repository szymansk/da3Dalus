"""Intelligent AVL panel spacing optimisation based on geometry features."""

from __future__ import annotations

import copy
import math

from app.avl.geometry import AvlSurface
from app.schemas.aeroanalysisschema import SpacingConfig


def _has_control_surfaces(surface: AvlSurface) -> bool:
    """Return True if any section defines a control surface."""
    return any(sec.controls for sec in surface.sections)


def _is_unswept(surface: AvlSurface, threshold_deg: float = 5.0) -> bool:
    """Check if wing has negligible sweep (LE x-offset vs span)."""
    if len(surface.sections) < 2:
        return True
    root = surface.sections[0]
    tip = surface.sections[-1]
    dx = abs(tip.xyz_le[0] - root.xyz_le[0])
    dy = abs(tip.xyz_le[1] - root.xyz_le[1])
    dz = abs(tip.xyz_le[2] - root.xyz_le[2])
    span = math.sqrt(dy**2 + dz**2)
    if span < 1e-9:
        return True
    sweep_rad = math.atan2(dx, span)
    return math.degrees(sweep_rad) < threshold_deg


def _has_centreline_break(surface: AvlSurface) -> bool:
    """Check if any mid-span section sits at the centreline (y=0)."""
    if len(surface.sections) <= 2:
        return False
    for sec in surface.sections[1:-1]:
        if abs(sec.xyz_le[1]) < 1e-6:
            return True
    return False


def _required_nspan_for_section_density(
    surface: AvlSurface, safety_margin: int = 2
) -> int:
    """Minimum ``Nspan`` that lets AVL allocate ≥ 1 panel per inter-section gap.

    AVL refuses with ``Cannot adjust spanwise spacing at section N`` /
    ``Insufficient number of spanwise vortices to work with`` when the
    surface-level ``Nspan`` cannot fit a panel into the tightest
    inter-section gap. The binding threshold matches ``ceil(span / min_gap)``
    empirically (gh-590), regardless of the ``s_space`` choice — cosine
    edge-concentration doesn't loosen the constraint.

    Coincident sections (chord-/twist-discontinuity at the same Y) are
    ignored when picking the smallest gap so they don't force ``Nspan`` to
    infinity. Surfaces with < 2 sections or zero span return 0 (no
    constraint).
    """
    if len(surface.sections) < 2:
        return 0
    y_positions = sorted(sec.xyz_le[1] for sec in surface.sections)
    span = y_positions[-1] - y_positions[0]
    if span <= 0:
        return 0
    gaps = [
        b - a
        for a, b in zip(y_positions, y_positions[1:], strict=False)
        if b - a > 1e-9
    ]
    if not gaps:
        return 0
    min_gap = min(gaps)
    return math.ceil(span / min_gap) + safety_margin


def optimise_surface_spacing(surface: AvlSurface, config: SpacingConfig) -> AvlSurface:
    """Apply intelligent spacing rules to a surface, returning a modified copy.

    When ``config.auto_optimise`` is True the following rules are applied:

    - Control surfaces present: increase ``n_chord`` to at least 16 so the
      hinge line is adequately resolved.
    - Unswept wing without a centreline break: switch spanwise spacing to
      -sine (``s_space = -2.0``) which concentrates panels at tip and root
      where induced drag gradients are steepest.
    - **Tight section density** (gh-590): bump ``n_span`` to satisfy AVL's
      per-section panel constraint so wings with near-coincident sections
      at spar / control-surface boundaries don't crash with
      ``Cannot adjust spanwise spacing at section N``.
    """
    result = copy.copy(surface)
    result.n_chord = config.n_chord
    result.c_space = config.c_space
    result.n_span = config.n_span
    result.s_space = config.s_space

    if not config.auto_optimise:
        return result

    # Rule: increase Nchord when control surfaces present (hinge line resolution)
    if _has_control_surfaces(surface):
        result.n_chord = max(result.n_chord, 16)

    # Rule: unswept wings without centreline break use -sine spacing
    if _is_unswept(surface) and not _has_centreline_break(surface):
        result.s_space = -2.0

    # Rule: bump Nspan if tight section gaps would crash AVL (gh-590)
    result.n_span = max(result.n_span, _required_nspan_for_section_density(surface))

    return result
