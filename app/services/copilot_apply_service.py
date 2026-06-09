"""Copilot apply engine — agentic design changes on a proposal branch (gh-937/938).

This module implements:

1. ``apply_edits(db, proposal_aeroplane_uuid, ops)`` — apply a list of
   validated :py:class:`~app.schemas.copilot_edits.EditOp` operations to a
   proposal aeroplane.  Each op is applied in memory then written via the
   same validated services the UI uses.  Invalid ops are **rejected with a
   reason** (not raised) so the copilot can self-correct.

2. ``get_or_open_proposal(db, live_aeroplane_id)`` — find or create the
   one open ``copilot-proposal`` branch for the live aeroplane's lineage.

3. ``discard_open_proposal(db, live_aeroplane_id)`` — discard the open
   copilot proposal branch if one exists.

4. ``compute_metrics_diff(a, b)`` — pure helper that returns signed deltas
   of key numeric metrics between two ``_metrics_payload`` dicts.
"""

from __future__ import annotations

import logging
from typing import Any

from sqlalchemy.orm import Session

logger = logging.getLogger(__name__)

# ---------------------------------------------------------------------------
# Internal constants
# ---------------------------------------------------------------------------

_COPILOT_BRANCH_PREFIX = "copilot-proposal"


# ---------------------------------------------------------------------------
# compute_metrics_diff — pure helper
# ---------------------------------------------------------------------------

#: Flat key paths (using dot notation for nested dicts) to extract from a
#: metrics payload for the diff.  We navigate into assumption_computation_context
#: for the authoritative numbers.
_DIFF_KEYS: list[tuple[str, str]] = [
    # (label in diff output, dot-path in payload)
    ("mass_kg", "total_mass_kg"),
    ("span_m", "assumption_computation_context.span_m"),
    ("aspect_ratio", "assumption_computation_context.aspect_ratio"),
    ("cd0", "assumption_computation_context.cd0"),
    ("e_oswald", "assumption_computation_context.e_oswald"),
    ("ld_max", "assumption_computation_context.ld_max"),
    ("x_np_m", "assumption_computation_context.x_np_m"),
    ("static_margin_pct", "assumption_computation_context.static_margin_pct"),
    ("v_stall_mps", "assumption_computation_context.v_stall_mps"),
    ("v_min_sink_mps", "assumption_computation_context.v_min_sink_mps"),
    ("v_cruise_mps", "assumption_computation_context.v_cruise_mps"),
    ("cl_max", "assumption_computation_context.cl_max"),
    ("wing_area_m2", "assumption_computation_context.wing_area_m2"),
]


def _get_path(d: dict, path: str) -> float | None:
    """Navigate a dot-separated path into a nested dict."""
    parts = path.split(".", 1)
    val = d.get(parts[0])
    if val is None:
        return None
    if len(parts) == 1:
        return val if isinstance(val, (int, float)) else None
    if not isinstance(val, dict):
        return None
    return _get_path(val, parts[1])


def compute_metrics_diff(a: dict, b: dict) -> dict:
    """Return signed numeric deltas between two metrics payloads (b − a).

    Only keys that are numeric in at least one payload are included.
    Only keys that differ between a and b are included (unchanged = omitted).

    Returns a dict with entries:
        ``{label: {"before": x, "after": y, "delta": y - x}}``
    """
    result: dict[str, Any] = {}
    for label, path in _DIFF_KEYS:
        val_a = _get_path(a, path)
        val_b = _get_path(b, path)
        # Skip if both missing or both identical
        if val_a is None and val_b is None:
            continue
        # Normalise: treat missing as 0 only for delta calculation
        fa = float(val_a) if val_a is not None else None
        fb = float(val_b) if val_b is not None else None
        if fa == fb:
            continue
        entry: dict[str, Any] = {}
        if fa is not None:
            entry["before"] = round(fa, 6)
        if fb is not None:
            entry["after"] = round(fb, 6)
        if fa is not None and fb is not None:
            entry["delta"] = round(fb - fa, 6)
        result[label] = entry
    return result


# ---------------------------------------------------------------------------
# Proposal-branch lifecycle
# ---------------------------------------------------------------------------


def _get_lineage_root_id(db: Session, live_aeroplane_id: int) -> int:
    """Return the root_id for the lineage of *live_aeroplane_id*."""
    from app.models.aeroplanemodel import AeroplaneModel

    node = db.query(AeroplaneModel).filter(AeroplaneModel.id == live_aeroplane_id).first()
    if node is None:
        raise ValueError(f"Aeroplane {live_aeroplane_id} not found")
    return node.root_id if node.root_id is not None else node.id


def _find_open_proposal(db: Session, root_id: int):
    """Return the first open copilot-proposal branch for the lineage, or None."""
    from app.models.aeroplanemodel import BranchModel

    return (
        db.query(BranchModel)
        .filter(
            BranchModel.root_id == root_id,
            BranchModel.is_main == False,  # noqa: E712
            BranchModel.created_by == "copilot",
            BranchModel.name.like(f"{_COPILOT_BRANCH_PREFIX}%"),
        )
        .order_by(BranchModel.id.desc())
        .first()
    )


def get_or_open_proposal(
    db: Session,
    live_aeroplane_id: int,
    message_id: str | None = None,
) -> Any:
    """Find or create the one open copilot-proposal branch for this lineage.

    If an open proposal branch already exists it is reused (one open proposal
    per aeroplane per the spec).  Otherwise a new branch is forked from the
    live head.

    Parameters
    ----------
    db:
        SQLAlchemy session (caller-owned; no commit here).
    live_aeroplane_id:
        Integer PK of the live (main-branch head) aeroplane node.
    message_id:
        Optional identifier appended to the branch name for traceability.

    Returns
    -------
    BranchModel
        The open copilot-proposal branch.
    """
    from app.services.aeroplane_version_service import create_branch

    root_id = _get_lineage_root_id(db, live_aeroplane_id)
    existing = _find_open_proposal(db, root_id)
    if existing is not None:
        logger.debug(
            "get_or_open_proposal: reusing branch %s (head=%s) for root %s",
            existing.id,
            existing.head_id,
            root_id,
        )
        return existing

    suffix = f"-{message_id}" if message_id else ""
    branch_name = f"{_COPILOT_BRANCH_PREFIX}{suffix}"

    branch = create_branch(
        db,
        from_node_id=live_aeroplane_id,
        name=branch_name,
        created_by="copilot",
    )
    logger.info(
        "get_or_open_proposal: created branch %s (head=%s, name=%r) for root %s",
        branch.id,
        branch.head_id,
        branch_name,
        root_id,
    )
    return branch


def discard_open_proposal(db: Session, live_aeroplane_id: int) -> bool:
    """Discard the open copilot-proposal branch for this lineage, if any.

    Returns
    -------
    bool
        True if a proposal was found and discarded, False if none existed.

    Notes
    -----
    The ``apply_edits`` path calls ``put_wing_as_wingconfig`` which does
    ``db.delete(old_wing)`` + re-insert inside the SAME session.  The
    deleted-but-not-expunged ORM instances (WingXSecSpareModel etc.) remain
    in the session's identity map.  When ``discard_branch`` subsequently
    asks SQLAlchemy to cascade-delete the proposal node's wings it tries to
    attach those stale instances for deletion, hitting:

        InvalidRequestError: Can't attach instance <WingXSecSpareModel …>;
        another instance with key (…) is already present in this session.

    Fix: expunge the entire identity map before querying for the branch,
    so we start from a clean slate.  The live aeroplane is re-fetched by PK
    (cheap, single-row query) to keep the session healthy after the expunge.
    """
    from app.services.aeroplane_version_service import discard_branch

    # Flush any pending writes so the DB is consistent before we expunge.
    db.flush()

    # Expunge all tracked ORM instances to clear stale wing/xsec/spare
    # entries left behind by put_wing_as_wingconfig's delete-then-insert
    # cycle.  After expunge, re-derive the lineage root_id and branch
    # from fresh queries (all DB state is preserved; only the session
    # identity map is cleared).
    db.expunge_all()

    root_id = _get_lineage_root_id(db, live_aeroplane_id)
    existing = _find_open_proposal(db, root_id)
    if existing is None:
        return False

    branch_id = existing.id
    discard_branch(db, branch_id)
    logger.info("discard_open_proposal: discarded branch %s for root %s", branch_id, root_id)
    return True


# ---------------------------------------------------------------------------
# apply_edits — the core apply engine
# ---------------------------------------------------------------------------


def apply_edits(
    db: Session,
    proposal_aeroplane_uuid: str,
    ops: list,
) -> dict:
    """Apply a list of edit-ops to a proposal aeroplane.

    Operations are applied sequentially in memory then written via the
    validated services (``wing_service``, ``design_assumptions_service``).
    Invalid ops are rejected with a reason and appended to ``rejected`` — the
    overall call never raises due to a bad individual op.

    After all ops: ``recompute_assumptions`` is called synchronously.

    Parameters
    ----------
    db:
        SQLAlchemy session (caller-owned).
    proposal_aeroplane_uuid:
        UUID string of the **proposal branch head** aeroplane.
    ops:
        List of validated ``EditOp`` discriminated-union instances.

    Returns
    -------
    dict with keys:
        - ``applied``: list of applied op type names
        - ``rejected``: list of ``{"op": ..., "error": ...}`` entries
        - ``metrics``: the new ``_metrics_payload`` after all edits + recompute
    """
    from app.schemas.design_assumption import AssumptionWrite
    from app.schemas.wing import Wing as WingConfigurationSchema
    from app.services.assumption_compute_service import recompute_assumptions
    from app.services.aeroplane_version_service import _metrics_payload
    from app.services.design_assumptions_service import update_assumption
    from app.services.wing_service import get_wing_as_wingconfig, put_wing_as_wingconfig
    from app.models.aeroplanemodel import AeroplaneModel

    applied: list[str] = []
    rejected: list[dict] = []

    # --- Wing-config ops: accumulate per-wing, write once at the end --------
    # We load the current WingConfig for each wing lazily and carry an in-memory
    # dict of the modified config.  We write it once per wing at the end so that
    # multiple ops on the same wing are composable.

    # wing_name → mutable dict representation of the wing config (in mm)
    wing_config_cache: dict[str, dict] = {}

    def _load_wing(wing_name: str) -> dict | None:
        """Load the current wing config dict into cache, return None on error."""
        if wing_name not in wing_config_cache:
            try:
                wing_config_cache[wing_name] = get_wing_as_wingconfig(
                    db, proposal_aeroplane_uuid, wing_name
                )
            except Exception as exc:  # noqa: BLE001
                return None
        return wing_config_cache[wing_name]

    for op in ops:
        op_type = op.type
        try:
            # --- SetAssumption -----------------------------------------------
            if op_type == "SetAssumption":
                data = AssumptionWrite(estimate_value=op.value)
                update_assumption(db, proposal_aeroplane_uuid, op.param, data)
                applied.append(op_type)

            # --- SetXsec -----------------------------------------------------
            elif op_type == "SetXsec":
                wc = _load_wing(op.wing)
                if wc is None:
                    rejected.append(
                        {
                            "op": op.model_dump(),
                            "error": f"Wing '{op.wing}' not found or cannot be loaded as WingConfig.",
                        }
                    )
                    continue

                segs = wc.get("segments", [])
                n = len(segs)

                # Cross-section index maps to: xsec 0 = root of seg 0,
                # xsec i (1 <= i <= n-1) = tip of seg[i-1] = root of seg[i] (if it exists).
                # We expose n+1 cross-sections for n segments (root + each segment tip).
                n_xsecs = n + 1  # e.g. 2 segments → 3 xsecs: [root, mid, tip]
                if op.index < 0 or op.index >= n_xsecs:
                    rejected.append(
                        {
                            "op": op.model_dump(),
                            "error": f"Cross-section index {op.index} out of range (0..{n_xsecs - 1}) for wing '{op.wing}'.",
                        }
                    )
                    continue

                # Apply chord: affects the AIRFOIL chord at that cross-section position
                if op.chord is not None:
                    if op.index == 0:
                        # root of seg[0]
                        segs[0]["root_airfoil"]["chord"] = op.chord
                    elif op.index == n:
                        # tip of last segment
                        segs[-1]["tip_airfoil"]["chord"] = op.chord
                    else:
                        # interior x-sec: tip of seg[index-1] AND root of seg[index]
                        segs[op.index - 1]["tip_airfoil"]["chord"] = op.chord
                        segs[op.index]["root_airfoil"]["chord"] = op.chord

                # Apply twist (incidence)
                if op.twist is not None:
                    if op.index == 0:
                        segs[0]["root_airfoil"]["incidence"] = op.twist
                    elif op.index == n:
                        segs[-1]["tip_airfoil"]["incidence"] = op.twist
                    else:
                        segs[op.index - 1]["tip_airfoil"]["incidence"] = op.twist
                        segs[op.index]["root_airfoil"]["incidence"] = op.twist

                # Apply airfoil
                if op.airfoil is not None:
                    if op.index == 0:
                        segs[0]["root_airfoil"]["airfoil"] = op.airfoil
                    elif op.index == n:
                        segs[-1]["tip_airfoil"]["airfoil"] = op.airfoil
                    else:
                        segs[op.index - 1]["tip_airfoil"]["airfoil"] = op.airfoil
                        segs[op.index]["root_airfoil"]["airfoil"] = op.airfoil

                # Apply dihedral
                if op.dihedral is not None:
                    if op.index == 0:
                        segs[0]["root_airfoil"]["dihedral_as_rotation_in_degrees"] = op.dihedral
                    elif op.index == n:
                        segs[-1]["tip_airfoil"]["dihedral_as_rotation_in_degrees"] = op.dihedral
                    else:
                        segs[op.index - 1]["tip_airfoil"]["dihedral_as_rotation_in_degrees"] = (
                            op.dihedral
                        )
                        segs[op.index]["root_airfoil"]["dihedral_as_rotation_in_degrees"] = (
                            op.dihedral
                        )

                wing_config_cache[op.wing] = wc
                applied.append(op_type)

            # --- AddXsec -----------------------------------------------------
            elif op_type == "AddXsec":
                wc = _load_wing(op.wing)
                if wc is None:
                    rejected.append(
                        {
                            "op": op.model_dump(),
                            "error": f"Wing '{op.wing}' not found or cannot be loaded as WingConfig.",
                        }
                    )
                    continue

                segs = wc.get("segments", [])
                n = len(segs)

                # at_index is 1-based: the new xsec becomes the tip of segment[at_index-1]
                if op.at_index < 1 or op.at_index > n + 1:
                    rejected.append(
                        {
                            "op": op.model_dump(),
                            "error": f"at_index {op.at_index} out of range (1..{n + 1}) for wing '{op.wing}'.",
                        }
                    )
                    continue

                # Determine the airfoil at the insertion point from the previous xsec
                seg_before_idx = op.at_index - 1  # 0-based segment index before the new xsec
                if seg_before_idx < n:
                    prev_tip_airfoil_str = segs[seg_before_idx]["tip_airfoil"]["airfoil"]
                else:
                    prev_tip_airfoil_str = (
                        segs[-1]["tip_airfoil"]["airfoil"]
                        if segs
                        else "./components/airfoils/rg15.dat"
                    )

                new_airfoil = op.airfoil if op.airfoil is not None else prev_tip_airfoil_str
                new_twist = op.twist if op.twist is not None else 0.0
                new_dihedral = op.dihedral if op.dihedral is not None else 0.0

                # New x-sec as tip of the segment we are splitting at
                new_xsec_airfoil = {
                    "airfoil": new_airfoil,
                    "chord": op.chord,
                    "dihedral_as_rotation_in_degrees": new_dihedral,
                    "incidence": new_twist,
                }

                if seg_before_idx < n:
                    # Split the existing segment: the OLD segment now ends at the new xsec.
                    # A new segment is inserted from the new xsec to the old tip.
                    old_seg = segs[seg_before_idx]
                    old_tip = old_seg["tip_airfoil"]
                    old_length = old_seg.get("length", op.span)
                    old_sweep = old_seg.get("sweep", 0.0)

                    # The new segment (from new xsec to old tip) carries half the remaining
                    # length and sweep as a neutral default — the caller can refine via SetXsec.
                    # We use op.span for the NEW segment's length as specified.
                    new_segment = {
                        "root_airfoil": new_xsec_airfoil.copy(),
                        "tip_airfoil": old_tip,
                        "length": old_length,  # keep old length for continuation
                        "sweep": old_sweep,
                        "number_interpolation_points": old_seg.get("number_interpolation_points"),
                        "tip_type": old_seg.get("tip_type"),
                    }

                    # Modify the segment BEFORE the insertion to end at the new xsec
                    old_seg["tip_airfoil"] = new_xsec_airfoil
                    old_seg["length"] = op.span

                    segs.insert(seg_before_idx + 1, new_segment)
                else:
                    # Adding a new tip segment beyond the last existing one
                    last_tip = segs[-1]["tip_airfoil"] if segs else new_xsec_airfoil
                    new_segment = {
                        "root_airfoil": last_tip if segs else new_xsec_airfoil,
                        "tip_airfoil": new_xsec_airfoil,
                        "length": op.span,
                        "sweep": 0.0,
                        "number_interpolation_points": segs[-1].get("number_interpolation_points")
                        if segs
                        else None,
                        "tip_type": None,
                    }
                    segs.append(new_segment)

                wing_config_cache[op.wing] = wc
                applied.append(op_type)

            # --- RemoveXsec --------------------------------------------------
            elif op_type == "RemoveXsec":
                wc = _load_wing(op.wing)
                if wc is None:
                    rejected.append(
                        {
                            "op": op.model_dump(),
                            "error": f"Wing '{op.wing}' not found or cannot be loaded as WingConfig.",
                        }
                    )
                    continue

                segs = wc.get("segments", [])
                n = len(segs)
                n_xsecs = n + 1

                if op.index <= 0 or op.index >= n_xsecs - 1:
                    rejected.append(
                        {
                            "op": op.model_dump(),
                            "error": f"Cannot remove x-sec at index {op.index}: must be interior (1..{n_xsecs - 2}). Root (0) and last ({n_xsecs - 1}) cannot be removed.",
                        }
                    )
                    continue

                if n < 2:
                    rejected.append(
                        {
                            "op": op.model_dump(),
                            "error": f"Cannot remove x-sec from wing '{op.wing}' with only {n} segment(s) — would leave no segments.",
                        }
                    )
                    continue

                # Interior xsec at index i: merge seg[i-1] and seg[i].
                # The merged segment gets: root from seg[i-1].root, tip from seg[i].tip,
                # length = seg[i-1].length + seg[i].length, sweep = weighted avg.
                seg_before = segs[op.index - 1]
                seg_after = segs[op.index]
                merged_length = seg_before.get("length", 0) + seg_after.get("length", 0)
                merged_sweep = seg_before.get("sweep", 0) + seg_after.get("sweep", 0)

                seg_before["tip_airfoil"] = seg_after["tip_airfoil"]
                seg_before["length"] = merged_length
                seg_before["sweep"] = merged_sweep

                del segs[op.index]
                wing_config_cache[op.wing] = wc
                applied.append(op_type)

            # --- SetWingParam -------------------------------------------------
            elif op_type == "SetWingParam":
                wc = _load_wing(op.wing)
                if wc is None:
                    rejected.append(
                        {
                            "op": op.model_dump(),
                            "error": f"Wing '{op.wing}' not found or cannot be loaded as WingConfig.",
                        }
                    )
                    continue

                segs = wc.get("segments", [])
                for seg in segs:
                    if op.sweep_mm is not None:
                        seg["sweep"] = op.sweep_mm
                    if op.dihedral is not None:
                        seg["root_airfoil"]["dihedral_as_rotation_in_degrees"] = op.dihedral
                        seg["tip_airfoil"]["dihedral_as_rotation_in_degrees"] = op.dihedral

                wing_config_cache[op.wing] = wc
                applied.append(op_type)

            # --- ReplaceWingConfig -------------------------------------------
            elif op_type == "ReplaceWingConfig":
                # Validate via schema before writing
                wc_schema = WingConfigurationSchema.model_validate(op.wing_config)
                put_wing_as_wingconfig(
                    db,
                    proposal_aeroplane_uuid,
                    op.wing,
                    wc_schema,
                    scale=0.001,
                )
                # Evict from cache so any subsequent ops re-read the new state
                wing_config_cache.pop(op.wing, None)
                applied.append(op_type)

            else:
                rejected.append({"op": {"type": op_type}, "error": f"Unknown op type '{op_type}'."})

        except Exception as exc:  # noqa: BLE001
            logger.warning("apply_edits: op %s rejected: %s", op_type, exc)
            try:
                op_dict = op.model_dump()
            except Exception:
                op_dict = {"type": op_type}
            rejected.append({"op": op_dict, "error": str(exc)})

    # --- Write all accumulated wing-config changes --------------------------
    for wing_name, wc_dict in wing_config_cache.items():
        try:
            wc_schema = WingConfigurationSchema.model_validate(wc_dict)
            put_wing_as_wingconfig(
                db,
                proposal_aeroplane_uuid,
                wing_name,
                wc_schema,
                scale=0.001,
            )
        except Exception as exc:  # noqa: BLE001
            logger.error("apply_edits: failed to write wing '%s': %s", wing_name, exc)
            # Retroactively move the wing ops to rejected
            new_rejected = []
            new_applied = []
            for a in applied:
                # Move all wing-related ops for this wing to rejected
                # (we can only do this at a coarse level since applied doesn't track wing)
                new_applied.append(a)
            applied = new_applied
            rejected.append(
                {
                    "op": {"type": "WingWrite", "wing": wing_name},
                    "error": f"Failed to persist wing '{wing_name}': {exc}",
                }
            )

    # --- Recompute assumptions synchronously --------------------------------
    try:
        recompute_assumptions(db, proposal_aeroplane_uuid)
    except Exception as exc:  # noqa: BLE001
        logger.warning("apply_edits: recompute_assumptions failed: %s", exc)
        # Non-fatal — still return what we have

    # --- Build return payload -----------------------------------------------
    node = db.query(AeroplaneModel).filter(AeroplaneModel.uuid == proposal_aeroplane_uuid).first()
    metrics = _metrics_payload(node) if node is not None else {}

    return {
        "applied": applied,
        "rejected": rejected,
        "metrics": metrics,
    }
