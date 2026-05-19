"""Resolve a stored, trimmed OperatingPoint into an analysis-ready schema.

Background — gh-577
-------------------
The Trefftz-plane and streamline VLM runs must reflect a trim-consistent
state: α, every control-surface deflection, and the CG (xyz_ref) all
originating from one and the same trim solution. Before this module the
streamline endpoint received an ad-hoc :class:`OperatingPointSchema`
assembled from a free-form frontend form and never carried the trimmed
deflections.

When the inbound schema carries ``operating_point_id``, this resolver loads
:class:`OperatingPointModel` and returns a *new* schema with all flight-state
fields drawn from that record. Two non-obvious translations happen here so
no caller can forget them:

* ``alpha`` / ``beta`` are stored as **radians** on the model but the
  :class:`asb.OperatingPoint` consumer expects **degrees** — we convert.
* The trim solver writes its deflections to ``OperatingPointModel.controls``;
  manual user overrides land in ``control_deflections``. We prefer the
  override when it is populated, otherwise we fall back to ``controls`` so
  the trim solution actually reaches the VLM.
"""

from __future__ import annotations

import math
from typing import TYPE_CHECKING

from app.core.exceptions import NotFoundError, ValidationDomainError
from app.models.analysismodels import OperatingPointModel
from app.schemas.aeroanalysisschema import OperatingPointSchema, OperatingPointStatus

if TYPE_CHECKING:
    from sqlalchemy.orm import Session


def _pick_deflections(op: OperatingPointModel) -> dict[str, float] | None:
    """Manual override wins; otherwise the trim solver's output is used.

    An empty override dict is treated as a no-op and falls back to ``controls``
    so a stale empty override cannot silently erase a fresh trim solution.
    """
    override = op.control_deflections
    if override:  # non-empty dict
        return dict(override)
    controls = op.controls or {}
    return dict(controls) if controls else None


def resolve_operating_point(
    db: "Session",
    op_schema: OperatingPointSchema,
    *,
    require_trimmed: bool = True,
) -> OperatingPointSchema:
    """Return an analysis-ready schema, possibly bound to a stored trimmed OP.

    If ``op_schema.operating_point_id`` is ``None`` the inline schema is
    returned unchanged (diagnostic / manual mode).

    Otherwise the stored :class:`OperatingPointModel` is loaded and its
    fields take precedence over the inline values. ``alpha`` and ``beta``
    are converted from radians to degrees to match the schema contract.

    Raises:
        NotFoundError: ``operating_point_id`` does not exist.
        ValidationDomainError: stored OP is not trimmed and
            ``require_trimmed`` is True (the default).
    """
    if op_schema.operating_point_id is None:
        return op_schema

    op_id = op_schema.operating_point_id
    op = db.query(OperatingPointModel).filter(OperatingPointModel.id == op_id).first()
    if op is None:
        raise NotFoundError(message=f"OperatingPoint {op_id} not found")

    if require_trimmed and op.status != OperatingPointStatus.TRIMMED:
        raise ValidationDomainError(
            message=(
                f"OperatingPoint {op_id} has status {op.status!r}; only "
                f"TRIMMED operating points may drive a trim-consistent "
                f"Trefftz/streamline run (gh-577). Re-trim it or pass "
                f"require_trimmed=False for diagnostic use."
            )
        )

    return OperatingPointSchema(
        name=op.name,
        description=op.description or "",
        velocity=op.velocity,
        alpha=math.degrees(op.alpha),
        beta=math.degrees(op.beta),
        p=op.p or 0.0,
        q=op.q or 0.0,
        r=op.r or 0.0,
        xyz_ref=op.xyz_ref or [0.0, 0.0, 0.0],
        altitude=op.altitude or 0.0,
        cdcl_config=op_schema.cdcl_config,
        spacing_config=op_schema.spacing_config,
        control_deflections=_pick_deflections(op),
        operating_point_id=op_id,
    )
