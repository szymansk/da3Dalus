"""Copilot tool facade — curated registry for the AI copilot (gh-917).

This module exposes a SMALL, carefully chosen set of tools that the copilot
agent may call.  It is intentionally NOT the full 51-tool MCP surface — only
the tools that are safe, fast, and meaningful for an advisory interaction.

Tool contract
-------------
- Each tool impl has the signature ``fn(db, aeroplane_id, **kwargs) -> dict``.
- Return value must be JSON-serializable (all SI/m units — no mm).
- Errors are returned as ``{"error": "<message>"}`` — never raised raw.
- ``run_analysis`` has a configurable timeout; on expiry it returns a status
  dict so the copilot can tell the user to check the Analysis tab.

Registry shape
--------------
``TOOL_REGISTRY``  dict[str, ToolEntry]

``list_schemas()``   -> list[dict]   (OpenAI function-calling schemas)
``execute(name, db, aeroplane_id, **kwargs) -> dict``
"""

from __future__ import annotations

import asyncio
import logging
from dataclasses import dataclass, field
from typing import Any, Callable

from sqlalchemy.orm import Session

from app.schemas.copilot_edits import edit_ops_array_schema

logger = logging.getLogger(__name__)

# ---------------------------------------------------------------------------
# Default timeout for run_analysis (seconds).
# Override via dependency injection or monkeypatching in tests.
# ---------------------------------------------------------------------------
DEFAULT_ANALYSIS_TIMEOUT_S: float = 60.0

# ---------------------------------------------------------------------------
# Tool entry
# ---------------------------------------------------------------------------


@dataclass
class ToolEntry:
    """Registry entry: OpenAI function schema + synchronous implementation."""

    schema: dict  # the full OpenAI function-calling object (type="function")
    impl: Callable[..., dict]


# ---------------------------------------------------------------------------
# Tool implementations
# ---------------------------------------------------------------------------


def _get_design_snapshot(db: Session, aeroplane_id: int) -> dict:
    """Return full metrics payload for the current design state."""
    try:
        from app.services.aeroplane_version_service import _metrics_payload
        from app.models.aeroplanemodel import AeroplaneModel

        node = db.query(AeroplaneModel).filter(AeroplaneModel.id == aeroplane_id).first()
        if node is None:
            return {"error": f"Aeroplane {aeroplane_id} not found"}
        return _metrics_payload(node)
    except Exception as exc:
        logger.exception("get_design_snapshot failed for aeroplane_id=%s", aeroplane_id)
        return {"error": str(exc)}


def _run_analysis(db: Session, aeroplane_id: int, kind: str = "polar") -> dict:
    """Trigger a fast analysis and return a concise summary dict.

    Parameters
    ----------
    kind:
        ``"polar"``     — AeroBuildup alpha sweep (α: −10 … +15 deg) returning
                          CL/CD/efficiency characteristics.
        ``"stability"`` — AeroBuildup-based static-margin & stability
                          derivatives.
    """
    kind = kind.lower()
    if kind not in ("polar", "stability"):
        return {"error": f"Unsupported kind {kind!r}. Supported: 'polar', 'stability'."}

    from app.models.aeroplanemodel import AeroplaneModel

    node = db.query(AeroplaneModel).filter(AeroplaneModel.id == aeroplane_id).first()
    if node is None:
        return {"error": f"Aeroplane {aeroplane_id} not found"}

    aeroplane_uuid = str(node.uuid)

    try:
        # ``_run_analysis`` is always called from a worker thread (via
        # ``asyncio.to_thread`` in ``run_turn``), so there is NO running event
        # loop here.  Use ``asyncio.run`` — it creates a fresh loop, runs the
        # coroutine, and closes the loop when done.  This is safe and correct;
        # do NOT use ``asyncio.new_event_loop().run_until_complete`` because
        # that leaks the loop and fails if accidentally called on the main
        # thread while a loop is already running.
        if kind == "polar":
            coro = _run_polar_async(db, aeroplane_uuid)
        else:
            coro = _run_stability_async(db, aeroplane_uuid)

        result = asyncio.run(asyncio.wait_for(coro, timeout=DEFAULT_ANALYSIS_TIMEOUT_S))
        return result
    except asyncio.TimeoutError:
        return {
            "status": "timeout",
            "note": (
                f"The {kind} analysis did not complete within "
                f"{DEFAULT_ANALYSIS_TIMEOUT_S:.0f} s. "
                "Check the Analysis tab for results once it finishes."
            ),
        }
    except Exception as exc:
        logger.exception("_run_analysis(%s) failed for aeroplane_id=%s", kind, aeroplane_id)
        return {"error": str(exc)}


def _drag_breakdown(
    cl: float | None, cd_total: float | None, ar: float | None, e: float | None
) -> dict | None:
    """Deterministic induced/parasitic drag split at one operating point.

    The LLM is unreliable at this arithmetic (it has produced both
    physically-impossible splits and 10x errors), so we compute it here and
    let the model simply report it. Induced drag uses the lifting-line form
    CD_i = CL^2 / (pi * AR * e); parasitic is the remainder of the polar's
    own total CD — one consistent source, never mixing snapshot cd0 with a
    polar total.
    """
    import math

    if cl is None or cd_total is None or ar is None or e is None:
        return None
    if ar <= 0 or e <= 0 or cd_total <= 0:
        return None
    cd_i = cl**2 / (math.pi * ar * e)
    cd_par = cd_total - cd_i
    if cd_i < 0 or cd_par < 0 or cd_i > cd_total:
        # Inconsistent — surface the raw inputs rather than a wrong split.
        return {
            "note": (
                "induced-drag estimate is inconsistent with the polar total "
                "(possible non-parabolic polar or e/AR mismatch); not decomposed"
            ),
            "cl": round(float(cl), 4),
            "cd_total": round(float(cd_total), 5),
            "aspect_ratio": round(float(ar), 3),
            "e_oswald": round(float(e), 4),
        }
    return {
        "cl": round(float(cl), 4),
        "cd_total": round(float(cd_total), 5),
        "cd_induced": round(float(cd_i), 5),
        "cd_parasite": round(float(cd_par), 5),
        "induced_fraction": round(float(cd_i / cd_total), 3),
        "parasite_fraction": round(float(cd_par / cd_total), 3),
        "aspect_ratio": round(float(ar), 3),
        "e_oswald": round(float(e), 4),
        "operating_point": "best_glide (max L/D)",
        "method": "CD_i = CL^2/(pi*AR*e); CD_parasite = CD_total - CD_i",
    }


def _polar_drag_breakdown(db: Session, aeroplane_uuid: str, cl_values, cd_values) -> dict | None:
    """Best-glide drag split for a polar sweep, using AR/e from the snapshot.

    Pulls AR and Oswald e from the design snapshot's computation context (the
    same source as the polar's `e`), picks the max-L/D point from the sweep,
    and delegates the arithmetic to :func:`_drag_breakdown`. Best-effort: any
    failure (missing context, empty arrays) returns ``None`` and the polar
    summary simply omits the breakdown.
    """
    import numpy as np

    if cl_values is None or cd_values is None:
        return None
    try:
        ratio = cl_values / np.where(cd_values > 0, cd_values, np.nan)
        idx = int(np.nanargmax(ratio))
        from app.models.aeroplanemodel import AeroplaneModel
        from app.services.aeroplane_version_service import _metrics_payload

        node = db.query(AeroplaneModel).filter(AeroplaneModel.uuid == aeroplane_uuid).first()
        ctx = (
            (_metrics_payload(node) or {}).get("assumption_computation_context", {})
            if node is not None
            else {}
        )
        return _drag_breakdown(
            cl=float(cl_values[idx]),
            cd_total=float(cd_values[idx]),
            ar=ctx.get("aspect_ratio"),
            e=ctx.get("e_oswald"),
        )
    except Exception:  # noqa: BLE001 — breakdown is best-effort
        logger.debug("drag_breakdown computation skipped", exc_info=True)
        return None


async def _run_polar_async(db: Session, aeroplane_uuid: str) -> dict:
    """Run an AeroBuildup alpha sweep and return key polar numbers."""
    import numpy as np
    from app.schemas.AeroplaneRequest import AlphaSweepRequest, AnalysisToolUrlType
    from app.schemas.aeroanalysisschema import OperatingPointSchema
    from app.services.analysis_service import (
        get_aeroplane_schema_or_raise,
        _extract_alpha_sweep_arrays,
        _compute_alpha_sweep_characteristic_points,
    )
    from app.converters.model_schema_converters import aeroplane_schema_to_asb_airplane_async
    from app.api.utils import analyse_aerodynamics

    sweep_request = AlphaSweepRequest(
        altitude=0.0,
        velocity=20.0,
        alpha_start=-10.0,
        alpha_end=15.0,
        alpha_num=26,
    )

    plane_schema = get_aeroplane_schema_or_raise(db, aeroplane_uuid)
    asb_airplane = aeroplane_schema_to_asb_airplane_async(plane_schema=plane_schema)

    operating_point = OperatingPointSchema(
        altitude=sweep_request.altitude,
        velocity=sweep_request.velocity,
        alpha=np.linspace(
            sweep_request.alpha_start, sweep_request.alpha_end, sweep_request.alpha_num
        ),
        beta=sweep_request.beta,
        p=sweep_request.p,
        q=sweep_request.q,
        r=sweep_request.r,
        xyz_ref=sweep_request.xyz_ref,
    )

    result, _ = analyse_aerodynamics(AnalysisToolUrlType.AEROBUILDUP, operating_point, asb_airplane)

    alpha_array, cl_values, cd_values, cm_values = _extract_alpha_sweep_arrays(
        result, sweep_request
    )
    char_points = _compute_alpha_sweep_characteristic_points(
        alpha_array, cl_values, cd_values, cm_values
    )

    # Build a concise summary (SI/dimensionless)
    summary: dict[str, Any] = {"status": "ok", "kind": "polar"}
    if cl_values is not None:
        summary["cl_max"] = float(np.nanmax(cl_values))
        summary["cl_min"] = float(np.nanmin(cl_values))
    if cd_values is not None:
        summary["cd_min"] = float(np.nanmin(cd_values))
    if cl_values is not None and cd_values is not None:
        ratio = cl_values / np.where(cd_values > 0, cd_values, np.nan)
        summary["cl_cd_max"] = float(np.nanmax(ratio))

        # Deterministic drag breakdown at the best-glide (max L/D) point, so
        # the model reports it instead of doing the error-prone arithmetic.
        breakdown = _polar_drag_breakdown(db, aeroplane_uuid, cl_values, cd_values)
        if breakdown:
            summary["drag_breakdown"] = breakdown

    # Include key characteristic points (rename keys for LLM clarity)
    _char_map = {
        "maximum_lift_to_drag_ratio_point": "best_glide",
        "minimum_drag_coefficient_point": "min_drag",
        "maximum_lift_coefficient_point": "cl_max_point",
        "stall_point": "stall",
    }
    char_summary: dict[str, Any] = {}
    for raw_key, friendly_key in _char_map.items():
        pt = char_points.get(raw_key)
        if pt:
            char_summary[friendly_key] = {
                k: (float(v) if isinstance(v, (int, float)) else v)
                for k, v in pt.items()
                if isinstance(v, (int, float, str))
            }
    if char_summary:
        summary["characteristic_points"] = char_summary

    return summary


async def _run_stability_async(db: Session, aeroplane_uuid: str) -> dict:
    """Run AeroBuildup stability analysis and return key stability numbers."""
    from app.models.aeroplanemodel import AeroplaneModel
    from app.schemas.aeroanalysisschema import OperatingPointSchema
    from app.schemas.AeroplaneRequest import AnalysisToolUrlType
    from app.services.stability_service import get_stability_summary

    # gh-924: evaluate stability at the SAME cruise design point (α=0, V_cruise)
    # as the authoritative neutral point computed by assumption_compute_service.
    # The neutral point is a configuration property (dC_m/dα = 0, α-independent
    # in the linear range — Anderson §4.9); evaluating it at an arbitrary
    # off-design point (the old α=2°, V=20 m/s) gave a second, divergent x_np
    # (0.109 m vs the dashboard's 0.080 m). One op-point → one neutral point.
    plane = db.query(AeroplaneModel).filter(AeroplaneModel.uuid == aeroplane_uuid).first()
    ctx = (plane.assumption_computation_context or {}) if plane is not None else {}
    v_cruise = ctx.get("v_cruise_mps")
    operating_point = OperatingPointSchema(
        altitude=0.0,
        velocity=float(v_cruise) if v_cruise and v_cruise > 0 else 20.0,
        alpha=0.0,
    )

    summary = await get_stability_summary(
        db,
        aeroplane_uuid,
        operating_point=operating_point,
        analysis_tool=AnalysisToolUrlType.AEROBUILDUP,
    )

    # gh-924: report the single authoritative neutral point — the one the
    # dashboard shows (assumption_compute_service, cruise design point with the
    # main-wing reference). The two stability paths normalise x_np against
    # different reference chords, so a fresh run here would otherwise surface a
    # second, divergent value. One neutral point across the app.
    ctx_xnp = ctx.get("x_np_m")
    neutral_point = ctx_xnp if ctx_xnp is not None else summary.neutral_point_x
    static_margin = summary.static_margin_pct
    if ctx_xnp is not None and summary.cg_x is not None and summary.mac:
        static_margin = (ctx_xnp - summary.cg_x) / summary.mac * 100.0

    return {
        "status": "ok",
        "kind": "stability",
        "static_margin_pct": static_margin,
        "stability_class": summary.stability_class,
        "neutral_point_x_m": neutral_point,
        "cg_x_m": summary.cg_x,
        "Cma": summary.Cma,
        "Cnb": summary.Cnb,
        "Clb": summary.Clb,
        "is_statically_stable": summary.is_statically_stable,
        "is_directionally_stable": summary.is_directionally_stable,
        "is_laterally_stable": summary.is_laterally_stable,
        "mac_m": summary.mac,
        "cg_range_forward_m": summary.cg_range_forward,
        "cg_range_aft_m": summary.cg_range_aft,
    }


def _get_version_tree(db: Session, aeroplane_id: int) -> dict:
    """Return the version lineage (branches + snapshots) for the aeroplane."""
    try:
        from app.services.aeroplane_version_service import list_tree
        from app.models.aeroplanemodel import AeroplaneModel

        node = db.query(AeroplaneModel).filter(AeroplaneModel.id == aeroplane_id).first()
        if node is None:
            return {"error": f"Aeroplane {aeroplane_id} not found"}

        # Determine lineage root
        root_id = node.root_id if node.root_id is not None else node.id

        nodes, branches = list_tree(db, root_id)

        serialized_nodes = [
            {
                "id": n.id,
                "uuid": str(n.uuid),
                "name": n.name,
                "version_label": n.version_label,
                "is_immutable": n.is_immutable,
                "predecessor_id": n.predecessor_id,
                "branch_id": n.branch_id,
                "created_at": n.created_at.isoformat() if n.created_at else None,
            }
            for n in nodes
        ]
        serialized_branches = [
            {
                "id": b.id,
                "name": b.name,
                "is_main": b.is_main,
                "head_id": b.head_id,
                "root_id": b.root_id,
            }
            for b in branches
        ]
        return {
            "root_id": root_id,
            "nodes": serialized_nodes,
            "branches": serialized_branches,
        }
    except Exception as exc:
        logger.exception("get_version_tree failed for aeroplane_id=%s", aeroplane_id)
        return {"error": str(exc)}


# ---------------------------------------------------------------------------
# OpenAI function-calling schemas
# ---------------------------------------------------------------------------

_SCHEMA_GET_DESIGN_SNAPSHOT = {
    "type": "function",
    "function": {
        "name": "get_design_snapshot",
        "description": (
            "Retrieve the full current design metrics for the active aeroplane: "
            "geometry (span, area, AR), mass, balance/CG, speeds, stability summary, "
            "tail sizing, and powertrain.  Call this first to ground any analysis in "
            "real numbers.  All values are in SI units (m, kg, m/s)."
        ),
        "parameters": {
            "type": "object",
            "properties": {},
            "required": [],
        },
    },
}

_SCHEMA_RUN_ANALYSIS = {
    "type": "function",
    "function": {
        "name": "run_analysis",
        "description": (
            "Trigger a fast aerodynamic analysis and return key results. "
            "Use kind='polar' for the lift/drag polar (CL, CD, best-glide, stall). "
            "Use kind='stability' for static margin, neutral point, CG range, "
            "and longitudinal/directional/lateral derivatives. "
            "Analysis runs with AeroBuildup (fast, no AVL). "
            "If it times out you will get a status='timeout' response — tell the "
            "user to check the Analysis tab."
        ),
        "parameters": {
            "type": "object",
            "properties": {
                "kind": {
                    "type": "string",
                    "enum": ["polar", "stability"],
                    "description": (
                        "'polar' — alpha sweep returning CL/CD characteristics; "
                        "'stability' — static margin, neutral point, derivatives."
                    ),
                }
            },
            "required": ["kind"],
        },
    },
}

_SCHEMA_GET_VERSION_TREE = {
    "type": "function",
    "function": {
        "name": "get_version_tree",
        "description": (
            "Return the version lineage for the active aeroplane: all design "
            "snapshots and branches with their labels, immutability status, "
            "and predecessor links.  Use this to answer questions like 'what "
            "versions do I have?' or to identify which snapshot to compare."
        ),
        "parameters": {
            "type": "object",
            "properties": {},
            "required": [],
        },
    },
}

# ---------------------------------------------------------------------------
# Read-retargeting helper (gh-938)
# ---------------------------------------------------------------------------


def _effective_target_id(db: Session, aeroplane_id: int) -> int:
    """Return the OPEN proposal head id if one exists for this aeroplane's lineage.

    While the copilot has an open proposal branch, read tools
    (``get_design_snapshot``, ``run_analysis``) auto-target the proposal head
    so the copilot sees its own edits.  ``get_version_tree`` always targets the
    live lineage and is NOT retargeted.

    Parameters
    ----------
    db:
        SQLAlchemy session.
    aeroplane_id:
        The live aeroplane PK (from the copilot loop).

    Returns
    -------
    int
        Proposal head PK if an open proposal exists, else ``aeroplane_id``.
    """
    try:
        from app.services.copilot_apply_service import (
            _find_open_proposal,
            _get_lineage_root_id,
        )

        root_id = _get_lineage_root_id(db, aeroplane_id)
        proposal = _find_open_proposal(db, root_id)
        if proposal is not None:
            return proposal.head_id
    except Exception:  # noqa: BLE001
        pass
    return aeroplane_id


# ---------------------------------------------------------------------------
# New write-tool implementations (gh-937/938)
# ---------------------------------------------------------------------------


def _apply_design_edits(db: Session, aeroplane_id: int, *, ops: list) -> dict:
    """Apply a list of edit-ops to the copilot proposal branch.

    Opens (or reuses) the copilot proposal branch for the live aeroplane,
    applies the ops to the PROPOSAL head (never to the live head), and
    returns the result plus a before/after metrics diff.

    Parameters
    ----------
    ops:
        List of edit-op dicts, each with a ``type`` discriminator field.
        Supported types: SetAssumption, SetXsec, AddXsec, RemoveXsec,
        SetWingParam, ReplaceWingConfig.
    """
    from typing import get_args

    from pydantic import TypeAdapter

    from app.schemas.copilot_edits import EditOp
    from app.services.aeroplane_version_service import _metrics_payload
    from app.services.copilot_apply_service import (
        apply_edits,
        compute_metrics_diff,
        get_or_open_proposal,
    )
    from app.models.aeroplanemodel import AeroplaneModel

    # 1. Validate ops via the discriminated union
    adapter = TypeAdapter(list[EditOp])
    try:
        validated_ops = adapter.validate_python(ops)
    except Exception as exc:  # noqa: BLE001
        return {"error": f"Invalid ops payload: {exc}"}

    # 2. Get live metrics for the diff baseline
    live_node = db.query(AeroplaneModel).filter(AeroplaneModel.id == aeroplane_id).first()
    if live_node is None:
        return {"error": f"Aeroplane {aeroplane_id} not found"}
    live_metrics = _metrics_payload(live_node)

    # 3. Open (or reuse) the proposal branch
    try:
        branch = get_or_open_proposal(db, aeroplane_id)
    except Exception as exc:  # noqa: BLE001
        logger.exception("_apply_design_edits: get_or_open_proposal failed")
        return {"error": f"Failed to open proposal branch: {exc}"}

    proposal_node = db.query(AeroplaneModel).filter(AeroplaneModel.id == branch.head_id).first()
    if proposal_node is None:
        return {"error": "Proposal branch head not found"}
    proposal_uuid = str(proposal_node.uuid)

    # 4. Apply edits to the PROPOSAL (never to the live head)
    try:
        result = apply_edits(db, proposal_uuid, validated_ops)
    except Exception as exc:  # noqa: BLE001
        logger.exception("_apply_design_edits: apply_edits failed")
        return {"error": f"Failed to apply edits: {exc}"}

    # 5. Compute diff
    diff = compute_metrics_diff(live_metrics, result.get("metrics", {}))

    return {
        "branch_id": branch.id,
        "branch_uuid": str(proposal_node.uuid),  # proposal head uuid
        "applied": result.get("applied", []),
        "rejected": result.get("rejected", []),
        "diff_vs_live": diff,
    }


def _discard_proposal(db: Session, aeroplane_id: int) -> dict:
    """Discard the open copilot proposal branch for this aeroplane's lineage.

    Returns ``{"discarded": true}`` if a proposal was found and discarded,
    ``{"discarded": false}`` if none existed.
    """
    from app.services.copilot_apply_service import discard_open_proposal

    try:
        discarded = discard_open_proposal(db, aeroplane_id)
        return {"discarded": discarded}
    except Exception as exc:  # noqa: BLE001
        logger.exception("_discard_proposal failed for aeroplane_id=%s", aeroplane_id)
        return {"error": str(exc)}


# ---------------------------------------------------------------------------
# OpenAI function-calling schemas — new write tools
# ---------------------------------------------------------------------------

_SCHEMA_APPLY_DESIGN_EDITS = {
    "type": "function",
    "function": {
        "name": "apply_design_edits",
        "description": (
            "Propose design changes by applying a list of edit operations to a "
            "PROPOSAL BRANCH — never to the live design.  The user reviews the "
            "proposal in the Versions panel and adopts or discards it.  "
            "Returns the branch id, applied/rejected ops, and a before/after "
            "metrics diff so you can show the user what changed.  "
            "FIRST call get_design_snapshot to get: (1) wing names (wing_names), "
            "(2) per-wing cross-section counts (wings[i].n_xsecs). "
            "Wing identifiers in ops are NAMES e.g. 'main_wing'.  "
            "To add a winglet: AddXsec with at_index = n_xsecs and a dihedral knee.  "
            "All chord/span units are millimetres; angles in degrees.  "
            "Call run_analysis after applying to verify, then iterate if needed."
        ),
        "parameters": {
            "type": "object",
            "properties": {"ops": edit_ops_array_schema()},
            "required": ["ops"],
        },
    },
}

_SCHEMA_DISCARD_PROPOSAL = {
    "type": "function",
    "function": {
        "name": "discard_proposal",
        "description": (
            "Discard the current copilot proposal branch (if any).  "
            "Use this when your current working branch has led to a dead end "
            "and you want to start fresh.  The user can also discard proposals "
            "from the Versions panel.  "
            "Returns {discarded: true} if a proposal was found and removed."
        ),
        "parameters": {
            "type": "object",
            "properties": {},
            "required": [],
        },
    },
}

# ---------------------------------------------------------------------------
# Registry
# ---------------------------------------------------------------------------

TOOL_REGISTRY: dict[str, ToolEntry] = {
    "get_design_snapshot": ToolEntry(
        schema=_SCHEMA_GET_DESIGN_SNAPSHOT,
        impl=_get_design_snapshot,
    ),
    "run_analysis": ToolEntry(
        schema=_SCHEMA_RUN_ANALYSIS,
        impl=_run_analysis,
    ),
    "get_version_tree": ToolEntry(
        schema=_SCHEMA_GET_VERSION_TREE,
        impl=_get_version_tree,
    ),
    "apply_design_edits": ToolEntry(
        schema=_SCHEMA_APPLY_DESIGN_EDITS,
        impl=_apply_design_edits,
    ),
    "discard_proposal": ToolEntry(
        schema=_SCHEMA_DISCARD_PROPOSAL,
        impl=_discard_proposal,
    ),
}


# ---------------------------------------------------------------------------
# Public API
# ---------------------------------------------------------------------------


def list_schemas() -> list[dict]:
    """Return OpenAI function-calling schemas for all registered tools."""
    return [entry.schema for entry in TOOL_REGISTRY.values()]


def execute(name: str, db: Session, aeroplane_id: int, **kwargs: Any) -> dict:
    """Execute a registered tool by name.

    Read tools (``get_design_snapshot``, ``run_analysis``) are retargeted to
    the open proposal head when one exists — so the copilot reads its own edits
    while iterating.  ``get_version_tree`` is always on the live lineage.
    Write tools (``apply_design_edits``, ``discard_proposal``) always receive
    the live ``aeroplane_id`` so they can find/open the proposal branch.

    Parameters
    ----------
    name:
        Tool name (must be in ``TOOL_REGISTRY``).
    db:
        SQLAlchemy session (caller-owned; this function does NOT commit).
    aeroplane_id:
        Integer PK of the target aeroplane.
    **kwargs:
        Tool-specific arguments (validated by the tool impl).

    Returns
    -------
    dict
        JSON-serializable result.  On unknown tool: ``{"error": "..."}``.
    """
    entry = TOOL_REGISTRY.get(name)
    if entry is None:
        known = ", ".join(sorted(TOOL_REGISTRY))
        return {"error": f"Unknown tool {name!r}. Known tools: {known}"}

    # Read-retargeting: resolve to proposal head for read tools when a proposal is open.
    _READ_RETARGETED_TOOLS = {"get_design_snapshot", "run_analysis"}
    effective_id = (
        _effective_target_id(db, aeroplane_id) if name in _READ_RETARGETED_TOOLS else aeroplane_id
    )

    return entry.impl(db, effective_id, **kwargs)
