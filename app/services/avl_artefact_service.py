"""AVL artefact service — build and verify replay-safe AVL snapshots (gh-529).

An ``AvlArtefact`` captures the surface-index map, run-state, and a
geometry hash at AVL invocation time so downstream tools (spar-load
sizing, AVL re-runs at a converged trim point) can validate that the
underlying airplane geometry hasn't drifted out from under them.

Audit reference: gh-525 (epic) finding C4.
"""

from __future__ import annotations

import hashlib
import json
import logging
from datetime import datetime, timezone
from typing import Any

from app.schemas.avl_artefact import (
    AvlArtefact,
    AvlIndexSnapshot,
    AvlReplayMismatch,
    AvlRunState,
)
from app.services.avl_strip_forces import (
    build_yduplicate_sign_map,
    get_control_surface_index_map,
)

logger = logging.getLogger(__name__)


def compute_geometry_hash(airplane: Any) -> str:
    """Return a deterministic SHA-256 of the airplane's control-surface geometry.

    The hash covers ONLY the fields that govern AVL surface indexing:
    wing-order, xsec-order within each wing, and (name, symmetric, hinge_point)
    per control surface. Floating-point coordinates are excluded because
    they're irrelevant to the index map and drift across model edits.

    Two airplanes with the same canonical representation produce the same
    hash; reordering any control surface produces a different hash.
    """
    canonical: list[dict[str, Any]] = []
    for w_idx, wing in enumerate(getattr(airplane, "wings", []) or []):
        wing_entry: dict[str, Any] = {
            "wing_index": w_idx,
            "xsecs": [],
        }
        for x_idx, xsec in enumerate(getattr(wing, "xsecs", []) or []):
            xsec_entry: dict[str, Any] = {"xsec_index": x_idx, "control_surfaces": []}
            for cs in getattr(xsec, "control_surfaces", []) or []:
                xsec_entry["control_surfaces"].append(
                    {
                        "name": str(getattr(cs, "name", "")),
                        "symmetric": bool(getattr(cs, "symmetric", True)),
                        # hinge_point is dimensionless (chord fraction) — included
                        # because moving the hinge produces a different AVL CONTROL
                        # block even with the same name.
                        "hinge_point": round(float(getattr(cs, "hinge_point", 0.75)), 6),
                    }
                )
            wing_entry["xsecs"].append(xsec_entry)
        canonical.append(wing_entry)

    blob = json.dumps(canonical, sort_keys=True, separators=(",", ":")).encode("utf-8")
    return hashlib.sha256(blob).hexdigest()


def build_avl_artefact(
    airplane: Any,
    *,
    alpha_deg: float,
    beta_deg: float,
    velocity_mps: float,
    x_cg_m: float,
    control_deflections_deg: dict[str, float] | None = None,
    mach: float = 0.0,
    run_case_constraints: dict[str, str] | None = None,
    avl_version: str | None = None,
) -> AvlArtefact:
    """Build a complete ``AvlArtefact`` from an airplane + trim state.

    Call this at AVL invocation time so the resulting artefact can be
    persisted alongside the trim result (or attached to an OP's
    ``trim_enrichment``).
    """
    index_snapshot = AvlIndexSnapshot(
        name_to_index=get_control_surface_index_map(airplane),
        yduplicate_sign=build_yduplicate_sign_map(airplane),
        captured_at=datetime.now(timezone.utc),
        geometry_hash=compute_geometry_hash(airplane),
    )
    run_state = AvlRunState(
        alpha_deg=float(alpha_deg),
        beta_deg=float(beta_deg),
        velocity_mps=float(velocity_mps),
        mach=float(mach),
        x_cg_m=float(x_cg_m),
        control_deflections_deg=dict(control_deflections_deg or {}),
        run_case_constraints=dict(run_case_constraints or {}),
    )
    return AvlArtefact(
        index_snapshot=index_snapshot,
        run_state=run_state,
        avl_version=avl_version,
    )


def verify_avl_replay(
    airplane: Any,
    artefact: AvlArtefact,
) -> AvlReplayMismatch | None:
    """Validate that an airplane can replay an artefact's AVL run.

    Returns ``None`` when the airplane geometry matches the snapshot.
    Returns an ``AvlReplayMismatch`` (geometry_hash divergence, index
    drift, or a surface added/removed) when replay must be rejected.

    Callers should treat a non-None result as a hard failure — replaying
    against drifted geometry produces silently mis-mapped AVL surfaces
    (epic gh-525 finding C4).
    """
    current_hash = compute_geometry_hash(airplane)
    if current_hash != artefact.index_snapshot.geometry_hash:
        return AvlReplayMismatch(
            reason="geometry_hash_mismatch",
            expected=artefact.index_snapshot.geometry_hash,
            actual=current_hash,
            details=(
                "Airplane geometry has changed since the AVL artefact was "
                "captured — control-surface indices may no longer match. "
                "Re-run AVL on the live geometry instead of replaying."
            ),
        )

    current_index_map = get_control_surface_index_map(airplane)
    if current_index_map != artefact.index_snapshot.name_to_index:
        # Should be unreachable when the geometry hash matches, but defend
        # against partial hash collisions or model edits that affect the
        # index map without changing the hashed fields.
        return AvlReplayMismatch(
            reason="index_map_drift",
            expected=artefact.index_snapshot.name_to_index,
            actual=current_index_map,
            details=(
                "Surface index map drifted despite matching geometry hash — "
                "investigate compute_geometry_hash coverage."
            ),
        )

    return None
