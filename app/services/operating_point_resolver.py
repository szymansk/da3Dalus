"""Resolve a stored, trimmed OperatingPoint into an analysis-ready schema.

Background — gh-577
-------------------
The Trefftz-plane and streamline VLM runs must reflect a trim-consistent
state: α, every control-surface deflection, and the CG (xyz_ref) all
originating from one and the same trim solution. Before this module the
streamline endpoint received an ad-hoc :class:`OperatingPointSchema`
assembled from a free-form frontend form and never carried the trimmed
deflections.

When the inbound schema carries ``operating_point_id``, this resolver
loads :class:`OperatingPointModel` and returns a *new* schema with all
flight-state fields drawn from that record. Two non-obvious translations
happen here so no caller can forget them:

* ``alpha`` / ``beta`` are stored as **radians** on the model but the
  :class:`asb.OperatingPoint` consumer expects **degrees** — we convert.
* The trim solver writes its deflections to ``OperatingPointModel.controls``;
  manual user overrides land in ``control_deflections``. We prefer the
  override when it is populated, otherwise we fall back to ``controls`` so
  the trim solution actually reaches the VLM.

A separate helper, :func:`validate_deflections_against_airplane`, guards
against the silent failure mode that originally motivated gh-577: AeroSandbox
``with_control_deflections`` quietly drops dict keys that don't match a
``ControlSurface.name``. If the geometry was renamed or rebuilt since the
trim, the wing would run clean while the UI labelled the plot "trimmed".
The validator fails loudly listing the unknown vs available names so the
user can re-trim.
"""

from __future__ import annotations

import logging
import math
from typing import TYPE_CHECKING

from app.core.exceptions import NotFoundError, ValidationDomainError
from app.models.analysismodels import OperatingPointModel
from app.schemas.aeroanalysisschema import OperatingPointSchema, OperatingPointStatus

if TYPE_CHECKING:
    import aerosandbox as asb
    from sqlalchemy.orm import Session

logger = logging.getLogger(__name__)


def _pick_deflections(op: OperatingPointModel) -> dict[str, float] | None:
    """Manual override wins; otherwise the trim solver's output is used.

    An empty override dict is treated as a no-op and falls back to
    ``controls`` so a stale empty override cannot silently erase a fresh
    trim solution.
    """
    override = op.control_deflections
    if override:  # non-empty dict
        return dict(override)
    controls = op.controls or {}
    return dict(controls) if controls else None


def _require_field(op: OperatingPointModel, field: str):
    """Raise loudly if a NOT-NULL state field arrived as ``None`` (corrupt row).

    The DB columns are declared ``nullable=False``; silently substituting
    ``0.0`` would run the analysis at sea level / zero rates and give
    physically wrong results that look plausible.
    """
    value = getattr(op, field)
    if value is None:
        raise ValidationDomainError(
            message=(
                f"OperatingPoint {op.id} has incomplete state "
                f"(missing {field}). Re-trim the OP before using it for "
                f"a Trefftz/streamline run."
            )
        )
    return value


def resolve_operating_point(
    db: "Session",
    op_schema: OperatingPointSchema,
    *,
    aircraft_pk: int | None = None,
    require_trimmed: bool = True,
) -> OperatingPointSchema:
    """Return an analysis-ready schema, possibly bound to a stored trimmed OP.

    If ``op_schema.operating_point_id`` is ``None`` the inline schema is
    returned unchanged (diagnostic / manual mode).

    Otherwise the stored :class:`OperatingPointModel` is loaded and its
    fields take precedence over the inline values. ``alpha`` and ``beta``
    are converted from radians to degrees to match the schema contract.

    Args:
        db: Active SQLAlchemy session.
        op_schema: Inbound request schema.
        aircraft_pk: When set, the OP lookup is constrained to this
            aircraft (gh-577 review). Prevents cross-aeroplane OP injection:
            a stored OP belonging to airplane B cannot drive a run on
            airplane A's geometry.
        require_trimmed: When True (the default), an OP whose status is
            not ``TRIMMED`` is rejected. Set False for explicit diagnostic
            workflows.

    Raises:
        NotFoundError: ``operating_point_id`` does not exist or does not
            belong to the requested aircraft.
        ValidationDomainError: stored OP is not trimmed (and
            ``require_trimmed`` is True), or required state fields are
            missing.
    """
    if op_schema.operating_point_id is None:
        return op_schema

    op_id = op_schema.operating_point_id
    query = db.query(OperatingPointModel).filter(OperatingPointModel.id == op_id)
    if aircraft_pk is not None:
        query = query.filter(OperatingPointModel.aircraft_id == aircraft_pk)
    op = query.first()
    if op is None:
        detail = (
            f"OperatingPoint {op_id} not found"
            if aircraft_pk is None
            else f"OperatingPoint {op_id} not found on aircraft {aircraft_pk}"
        )
        raise NotFoundError(message=detail)

    if require_trimmed and op.status != OperatingPointStatus.TRIMMED:
        raise ValidationDomainError(
            message=(
                f"OperatingPoint {op_id} has status {op.status!r}; only "
                f"TRIMMED operating points may drive a trim-consistent "
                f"Trefftz/streamline run (gh-577). Re-trim it or pass "
                f"require_trimmed=False for diagnostic use."
            )
        )

    # NOT-NULL state — fail loudly on corrupt rows.
    velocity = _require_field(op, "velocity")
    alpha_rad = _require_field(op, "alpha")
    beta_rad = _require_field(op, "beta")
    altitude = _require_field(op, "altitude")
    xyz_ref = _require_field(op, "xyz_ref")
    if not xyz_ref:  # empty list ≠ valid moment reference
        raise ValidationDomainError(
            message=f"OperatingPoint {op_id} has empty xyz_ref."
        )

    deflections = _pick_deflections(op)
    logger.info(
        "Resolved OperatingPoint %s (aircraft %s): alpha=%.3f deg, "
        "velocity=%.2f m/s, xyz_ref=%s, deflections=%s",
        op_id,
        op.aircraft_id,
        math.degrees(alpha_rad),
        velocity,
        xyz_ref,
        deflections,
    )

    return OperatingPointSchema(
        name=op.name,
        description=op.description or "",
        velocity=velocity,
        alpha=math.degrees(alpha_rad),
        beta=math.degrees(beta_rad),
        p=op.p or 0.0,
        q=op.q or 0.0,
        r=op.r or 0.0,
        xyz_ref=xyz_ref,
        altitude=altitude,
        cdcl_config=op_schema.cdcl_config,
        spacing_config=op_schema.spacing_config,
        control_deflections=deflections,
        operating_point_id=op_id,
    )


def _airplane_surface_names(airplane: "asb.Airplane") -> set[str]:
    """Collect every ``ControlSurface.name`` declared on the airplane."""
    return {
        surf.name
        for wing in (airplane.wings or [])
        for xsec in (wing.xsecs or [])
        for surf in (xsec.control_surfaces or [])
    }


def validate_deflections_against_airplane(
    airplane: "asb.Airplane",
    deflections: dict[str, float] | None,
) -> None:
    """Refuse to run when stored deflections name surfaces that don't exist.

    AeroSandbox' :meth:`Airplane.with_control_deflections` silently drops
    dict keys with no matching ``ControlSurface.name``. If the geometry
    was renamed since the trim, the wing runs clean while the UI labels
    the plot "trimmed" — exactly the class of bug gh-577 set out to fix.
    This guard surfaces the mismatch as a 422 with the unknown / available
    names listed so the user can re-trim.

    No-op when ``deflections`` is None or empty.

    Raises:
        ValidationDomainError: at least one deflection key has no
            matching control surface on the airplane.
    """
    if not deflections:
        return
    available = _airplane_surface_names(airplane)
    unknown = set(deflections) - available
    if unknown:
        raise ValidationDomainError(
            message=(
                f"Control surfaces {sorted(unknown)} from the operating "
                f"point are not present on the current airplane. Available: "
                f"{sorted(available) or '(none)'}. Re-trim the OP against "
                f"the current geometry."
            )
        )
