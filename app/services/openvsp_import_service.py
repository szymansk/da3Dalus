"""Service layer for the OpenVSP `.vsp3` importer (gh-646, gh-693).

Bridges :func:`app.converters.openvsp_importer.import_vsp3` and the
existing aeroplane/wing/fuselage/weight-item services. Persists the
parsed model in a single transaction and returns a structured
response describing which components were imported and which were
dropped with warnings.

Phase 1.5 (gh-693): the importer now persists **all** four component
types — Aeroplane, Wings, Fuselages, and Weight Items. Each component
write is wrapped in its own try/except; a failure on one record adds
a warning instead of rolling back the whole import.

Optional Quick-Scale (gh-695, Variante A)
-----------------------------------------
The importer accepts two **mutually exclusive** scaling options:

* ``target_span_m`` — rescale so the maximum wing physical span equals
  this value in metres.
* ``scale_factor`` — multiply all length-typed fields by this factor.

The helpers below scale **lengths only** (geometry positions,
chords, fuselage radii, weight-item positions). Masses are
**deliberately NOT scaled** — see the ``feedback_openvsp_import_rc_scope``
memory: mass-vs-length scaling is a non-trivial design decision
(length ∝ f, volume mass ∝ f³, electronics independent) and is
covered by Variante B in a follow-up ticket. When scaling is
applied, the response includes a warning that masses were left
untouched so the user knows to adjust them in the mass-properties
panel.
"""

from __future__ import annotations

import logging
from dataclasses import dataclass
from pathlib import Path
from typing import Optional

from sqlalchemy.orm import Session

from app.converters import openvsp_adapter
from app.converters.openvsp_importer import ImportResult, ImportWarning, import_vsp3
from app.schemas.aeroplaneschema import (
    AeroplaneSchema,
    AsbWingGeometryWriteSchema,
)
from app.schemas.weight_item import WeightItemWrite

logger = logging.getLogger(__name__)


# ---------------------------------------------------------------------------
# Scaling configuration (gh-695)
# ---------------------------------------------------------------------------

# Bounds on the user-supplied scaling parameters. Picked to cover the
# RC-scaling use case (1.5 m sailplane up to 5 m airliner-scale) plus
# a safety margin, while keeping the input numerically sane (no
# 1e-12 or 1e+15 to break later CAD/aero stages).
SCALE_FACTOR_MIN: float = 0.001
SCALE_FACTOR_MAX: float = 10.0
TARGET_SPAN_MIN: float = 0.1  # metres
TARGET_SPAN_MAX: float = 50.0  # metres


class ScaleValidationError(ValueError):
    """Raised when the caller-supplied scaling params are invalid.

    Endpoint layer translates this to HTTP 400 (mutex violation) or
    422 (out-of-range numeric / no wings present).
    """


@dataclass
class OpenVspImportResponse:
    """Top-level response from the import endpoint."""

    aeroplane_uuid: str
    aeroplane_name: str
    n_wings: int
    n_fuselages: int
    n_weight_items: int
    warnings: list[dict]
    lossy_components: list[str]


def is_importer_available() -> bool:
    """Return True iff the optional `openvsp` package is installed."""
    return openvsp_adapter.is_available()


# ---------------------------------------------------------------------------
# Scaling helpers (gh-695)
# ---------------------------------------------------------------------------


def _compute_max_wing_span(aeroplane: AeroplaneSchema) -> float:
    """Return the largest physical wingspan across all wings, in metres.

    For a symmetric wing the physical span is ``2 * max|y_le|`` (mirror
    about the XZ plane); for an asymmetric wing it's just the largest
    ``|y_le|``. Returns ``0.0`` when the aeroplane has no wings — the
    caller must validate against that before computing a scale factor.
    """
    wings = aeroplane.wings or {}
    largest = 0.0
    for wing in wings.values():
        if not wing.x_secs:
            continue
        max_y_abs = max(abs(xs.xyz_le[1]) for xs in wing.x_secs)
        physical_span = max_y_abs * (2.0 if wing.symmetric else 1.0)
        largest = max(largest, physical_span)
    return largest


def _scale_aeroplane_lengths(
    aeroplane: AeroplaneSchema,
    factor: float,
    *,
    weight_items: Optional[list[WeightItemWrite]] = None,
) -> None:
    """Multiply every length-typed field by ``factor`` (in-place).

    Scales:

    * Wing x-sec ``xyz_le`` and ``chord``
    * Fuselage x-sec ``xyz`` and superellipse ``a``/``b`` semi-axes
    * Aeroplane ``xyz_ref`` (reference point / CG)
    * Optional weight items' ``x_m``/``y_m``/``z_m`` positions

    Does NOT scale (intentional, per ``feedback_openvsp_import_rc_scope``):

    * Wing-section ``twist`` (angular)
    * Fuselage superellipse ``n`` exponent (dimensionless)
    * Weight items ``mass_kg`` — see Variante B for the mass-scaling story
    * ``total_mass_kg`` on the aeroplane
    """
    # Wings
    for wing in (aeroplane.wings or {}).values():
        for xs in wing.x_secs:
            xs.xyz_le = [v * factor for v in xs.xyz_le]
            xs.chord = xs.chord * factor

    # Fuselages
    for fus in (aeroplane.fuselages or {}).values():
        for fxs in fus.x_secs:
            fxs.xyz = [v * factor for v in fxs.xyz]
            fxs.a = fxs.a * factor
            fxs.b = fxs.b * factor

    # Aeroplane reference point (CG / origin) — also a length
    if aeroplane.xyz_ref is not None:
        aeroplane.xyz_ref = [v * factor for v in aeroplane.xyz_ref]

    # Weight items: positions only, mass intentionally untouched
    if weight_items is not None:
        for item in weight_items:
            item.x_m = item.x_m * factor
            item.y_m = item.y_m * factor
            item.z_m = item.z_m * factor


def _resolve_scale_factor(
    aeroplane: AeroplaneSchema,
    target_span_m: Optional[float],
    scale_factor: Optional[float],
) -> Optional[float]:
    """Validate the scaling inputs and return the effective factor.

    Returns ``None`` when neither input was supplied (no scaling
    requested). Raises :class:`ScaleValidationError` on mutex
    violation, out-of-range values, or a ``target_span_m`` request
    on an aeroplane with no wings.
    """
    if target_span_m is not None and scale_factor is not None:
        raise ScaleValidationError(
            "target_span_m and scale_factor are mutually exclusive; "
            "specify at most one."
        )

    if scale_factor is not None:
        if not (SCALE_FACTOR_MIN < scale_factor < SCALE_FACTOR_MAX):
            raise ScaleValidationError(
                f"scale_factor must be in ({SCALE_FACTOR_MIN}, {SCALE_FACTOR_MAX}), "
                f"got {scale_factor!r}."
            )
        return scale_factor

    if target_span_m is not None:
        if not (TARGET_SPAN_MIN < target_span_m < TARGET_SPAN_MAX):
            raise ScaleValidationError(
                f"target_span_m must be in ({TARGET_SPAN_MIN}, {TARGET_SPAN_MAX}), "
                f"got {target_span_m!r}."
            )
        current_span = _compute_max_wing_span(aeroplane)
        if current_span <= 0.0:
            raise ScaleValidationError(
                "Cannot resolve target_span_m: the imported aeroplane has no "
                "wings (or all wing y_le values are zero). Re-import with "
                "scale_factor or 'import as-is'."
            )
        return target_span_m / current_span

    return None


def _make_scaling_warning(
    applied_factor: float,
    target_span_m: Optional[float],
    scale_factor: Optional[float],
):
    """Build the user-facing scaling-applied warning record.

    Imported here to avoid a top-level circular import (the warning
    type lives in the converter module).
    """
    from app.converters.openvsp_importer import ImportWarning

    if target_span_m is not None:
        request = f"target wingspan {target_span_m:g} m"
    elif scale_factor is not None:
        request = f"explicit scale_factor {scale_factor:g}"
    else:  # pragma: no cover — defensive, callers gate on factor
        request = "scaling"

    return ImportWarning(
        component_type="SCALING",
        component_name="aeroplane",
        reason=(
            f"Scaled all length-typed fields by factor {applied_factor:g} "
            f"({request}). Masses were NOT scaled — adjust manually in the "
            "mass-properties panel if needed."
        ),
        severity="info",
    )


def _resolve_aeroplane_name(
    *,
    explicit_name: Optional[str],
    source_filename: Optional[str],
    parsed_name: Optional[str],
) -> str:
    """Resolve the aeroplane name from the first non-empty source.

    Precedence (each must be a non-empty trimmed string to count):

    1. ``explicit_name`` — user-typed in the import dialog.
    2. ``source_filename`` stem — the original upload's basename
       (so ``cessna172.vsp3`` → ``cessna172``). Avoids leaking the
       ``tmpXXXX`` name of the NamedTemporaryFile the endpoint writes.
    3. ``parsed_name`` — whatever the converter recorded on the
       parsed schema (legacy fallback, may itself be the tempfile
       stem when called via the endpoint).
    4. ``"OpenVSP Import"`` — final hard fallback.
    """
    explicit = (explicit_name or "").strip()
    if explicit:
        return explicit

    if source_filename:
        stem = Path(source_filename).stem.strip()
        if stem:
            return stem

    parsed = (parsed_name or "").strip()
    if parsed:
        return parsed

    return "OpenVSP Import"


def _record_persist_failure(
    result: ImportResult,
    *,
    component_type: str,
    component_name: str,
    exc: Exception,
) -> None:
    """Log a per-component persistence failure and surface it as a
    user-visible warning so the importer banner can show it.

    One failure must not roll back the whole import: the rest of the
    aeroplane (other wings/fuselages/weight items) stays usable.
    """
    logger.warning(
        "Failed to persist %s %r: %s",
        component_type.lower(),
        component_name,
        exc,
        exc_info=True,
    )
    result.warnings.append(
        ImportWarning(
            component_type=component_type,
            component_name=component_name,
            reason=f"Failed to persist {component_type.lower()} to database: {exc}",
            severity="warning",
        )
    )


def _persist_aeroplane(
    db: Session,
    result: ImportResult,
    *,
    name: Optional[str] = None,
    source_filename: Optional[str] = None,
) -> tuple[str, str]:
    """Persist the parsed aeroplane and return (uuid_str, name).

    Writes (gh-693): Aeroplane + Wings + Fuselages + WeightItems. Each
    component is wrapped in its own try/except — a failure on one
    record records a warning but lets the rest of the import succeed,
    so the user never loses an entire aeroplane to a single broken
    fuselage or weight item.
    """
    # Lazy import to avoid pulling sqlalchemy/CAD pieces at module load
    # in environments that only need the importer (e.g. unit tests).
    from app.services import (
        aeroplane_service,
        fuselage_service,
        weight_items_service,
        wing_service,
    )

    resolved_name = _resolve_aeroplane_name(
        explicit_name=name,
        source_filename=source_filename,
        parsed_name=result.aeroplane.name,
    )
    aeroplane = aeroplane_service.create_aeroplane(db, resolved_name)

    # Wings: convert each AsbWingSchema → AsbWingGeometryWriteSchema and
    # delegate to wing_service. The full schema isn't directly accepted
    # by the create_wing service, but the geometry-write schema is.
    if result.aeroplane.wings:
        for wing_name, wing in result.aeroplane.wings.items():
            try:
                write = AsbWingGeometryWriteSchema(
                    name=wing_name,
                    symmetric=wing.symmetric,
                    x_secs=[
                        {
                            "xyz_le": xs.xyz_le,
                            "chord": xs.chord,
                            "twist": xs.twist,
                            "airfoil": str(xs.airfoil),
                            "x_sec_type": xs.x_sec_type,
                            "tip_type": xs.tip_type,
                            "number_interpolation_points": xs.number_interpolation_points,
                        }
                        for xs in wing.x_secs
                    ],
                )
                wing_service.create_wing(db, aeroplane.uuid, wing_name, write)
            except Exception as exc:  # noqa: BLE001 — convert to warning
                _record_persist_failure(
                    result, component_type="WING", component_name=wing_name, exc=exc
                )

    # Fuselages (gh-693): persist each fuselage via fuselage_service.
    # FuselageSchema fields are already in metres (no unit conversion
    # needed — different from wings which are mm-in-schema).
    if result.aeroplane.fuselages:
        for fuse_name, fuse in result.aeroplane.fuselages.items():
            try:
                fuselage_service.create_fuselage(db, aeroplane.uuid, fuse_name, fuse)
            except Exception as exc:  # noqa: BLE001
                _record_persist_failure(
                    result, component_type="FUSELAGE", component_name=fuse_name, exc=exc
                )

    # Weight items (gh-693): persist each WeightItemWrite via the same
    # entry point the manual mass-properties UI uses, so categories,
    # CG-recompute hooks, and validation stay aligned.
    for item in result.weight_items:
        try:
            weight_items_service.create_weight_item(db, aeroplane.uuid, item)
        except Exception as exc:  # noqa: BLE001
            _record_persist_failure(
                result, component_type="WEIGHT_ITEM", component_name=item.name, exc=exc
            )

    return str(aeroplane.uuid), aeroplane.name


def import_openvsp_file(
    db: Session,
    path: Path,
    *,
    target_span_m: Optional[float] = None,
    scale_factor: Optional[float] = None,
    name: Optional[str] = None,
    source_filename: Optional[str] = None,
) -> OpenVspImportResponse:
    """Parse a ``.vsp3`` file and persist its content as a new aeroplane.

    Parameters
    ----------
    db
        Active SQLAlchemy session (commit handled by the FastAPI
        ``get_db`` dependency).
    path
        Filesystem path to the ``.vsp3`` upload.
    target_span_m
        Optional target wingspan in metres. Mutually exclusive with
        ``scale_factor``. When set, computes the factor from the
        currently-largest physical wingspan and applies it to all
        length-typed fields.
    scale_factor
        Optional direct scaling factor. Mutually exclusive with
        ``target_span_m``. Multiplies every length-typed field.
    name
        Optional user-typed aeroplane name from the import dialog. When
        non-empty (after trim) it overrides every other name source.
    source_filename
        Original upload filename (``cessna172.vsp3``). Used as a sane
        fallback for the persisted aeroplane name when ``name`` is not
        supplied — without this the endpoint would persist the
        ``NamedTemporaryFile`` stem (``tmpXXXX``).

    Raises
    ------
    ImportError
        When the optional ``openvsp`` package is not installed.
    FileNotFoundError
        When ``path`` does not exist.
    ScaleValidationError
        When the scaling inputs are invalid (mutex, out-of-range,
        target span on a wingless aeroplane).
    """
    result = import_vsp3(path)

    factor = _resolve_scale_factor(result.aeroplane, target_span_m, scale_factor)
    # S1244: any factor far enough from 1.0 to matter geometrically — using
    # a small epsilon avoids float-equality pitfalls. Threshold 1e-9 is
    # well below any user-typed scale value (UI step is 0.01).
    if factor is not None and abs(factor - 1.0) > 1e-9:
        _scale_aeroplane_lengths(
            result.aeroplane, factor, weight_items=result.weight_items
        )
        # Surface the scaling decision + the mass-not-scaled caveat to
        # the user. The frontend banner renders these alongside any
        # importer-level warnings.
        result.warnings.append(
            _make_scaling_warning(factor, target_span_m, scale_factor)
        )

    uuid, name = _persist_aeroplane(
        db, result, name=name, source_filename=source_filename
    )
    return OpenVspImportResponse(
        aeroplane_uuid=uuid,
        aeroplane_name=name,
        n_wings=len(result.aeroplane.wings or {}),
        n_fuselages=len(result.aeroplane.fuselages or {}),
        n_weight_items=len(result.weight_items),
        warnings=[
            {
                "component_type": w.component_type,
                "component_name": w.component_name,
                "reason": w.reason,
                "severity": w.severity,
            }
            for w in result.warnings
        ],
        lossy_components=list(result.lossy_components),
    )
