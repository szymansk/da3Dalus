"""Pydantic schemas for AVL reproducibility artefacts (gh-529).

An ``AvlArtefact`` packages the information required to **replay** an
AVL trim solution exactly: which positional indices (``d1``, ``d2``, …)
mapped to which control-surface names at solve time, what the operating
point state was, and a canonical hash of the airplane geometry used to
produce the result.

Audit reference: gh-525 (epic) finding C4 — without this, AVL re-runs
silently use mis-mapped surface indices whenever the user reorders xsec
control surfaces.
"""

from __future__ import annotations

from datetime import datetime
from typing import Any

from pydantic import BaseModel, Field


class AvlIndexSnapshot(BaseModel):
    """The control-surface ↔ AVL d-index map at AVL invocation time.

    AVL assigns ``d1``, ``d2``, …  in input-parse order (avl_doc §SECTION
    / §CONTROL).  The mapping shifts silently if the user reorders xsec
    control surfaces in the source geometry — this snapshot pins the
    binding for the OP's lifetime.
    """

    name_to_index: dict[str, int] = Field(
        ...,
        description=(
            "Control-surface name → 1-based AVL d-index (``d1``, ``d2``, …) "
            "at the time AVL was invoked."
        ),
    )
    yduplicate_sign: dict[str, float] = Field(
        default_factory=dict,
        description=(
            "Per-surface ``SgnDup`` factor for YDUPLICATE-deflected pairs: "
            "+1 for symmetric (flaps), -1 for antisymmetric (aileron pair)."
        ),
    )
    captured_at: datetime = Field(..., description="UTC timestamp when the snapshot was produced.")
    geometry_hash: str = Field(
        ...,
        description=(
            "SHA-256 of the canonicalised airplane geometry (independent of "
            "float-formatting drift). Used by ``verify_avl_replay`` to reject "
            "replays against a modified airplane."
        ),
        min_length=64,
        max_length=64,
    )


class AvlRunState(BaseModel):
    """The full AVL run-case state at solve time — enough to re-run AVL
    later (e.g. for spar-load sizing at the same trim point) without
    re-deriving anything from the OP.
    """

    alpha_deg: float = Field(..., description="Angle of attack [deg]")
    beta_deg: float = Field(..., description="Sideslip angle [deg]")
    velocity_mps: float = Field(..., description="True airspeed [m/s]")
    mach: float = Field(0.0, description="Mach number (0 for incompressible)")
    x_cg_m: float = Field(..., description="CG x-location [m] used as moment reference")
    control_deflections_deg: dict[str, float] = Field(
        default_factory=dict,
        description=(
            "Control-surface deflections at trim, keyed by **name** (not "
            "AVL index — those drift on geometry edits)."
        ),
    )
    run_case_constraints: dict[str, str] = Field(
        default_factory=dict,
        description=(
            "AVL run-case constraints in source form, e.g. "
            "``{'C1': 'bank=0', 'C2': 'velocity=22.0'}``."
        ),
    )


class AvlArtefact(BaseModel):
    """Bundle of ``AvlIndexSnapshot`` + ``AvlRunState`` — the canonical
    payload stored on an ``OperatingPoint.trim_enrichment.avl`` when the
    trim ran through AVL.
    """

    index_snapshot: AvlIndexSnapshot
    run_state: AvlRunState
    avl_version: str | None = Field(
        None, description="AVL binary version string (parsed from runner stderr)."
    )

    def control_name_for_index(self, idx: int) -> str | None:
        """Reverse lookup: which control surface name owns AVL index ``idx``?"""
        for name, i in self.index_snapshot.name_to_index.items():
            if i == idx:
                return name
        return None


class AvlReplayMismatch(BaseModel):
    """Structured result of a failed replay precondition check."""

    reason: str = Field(..., description="Short label, e.g. 'geometry_hash_mismatch'")
    expected: Any = Field(..., description="Value from the snapshot")
    actual: Any = Field(..., description="Value derived from the current airplane")
    details: str | None = Field(None, description="Free-form explanation for logs / UI")
