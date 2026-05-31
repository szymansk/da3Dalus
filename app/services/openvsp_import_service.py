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
from typing import Callable, Optional


# Progress callback signature: ``(step, pct, detail)``.
# Used by gh-737 to drive a frontend progress bar via SSE. Called
# synchronously from inside the import flow — the caller is
# responsible for hopping the data over thread boundaries (typically
# via ``loop.call_soon_threadsafe(queue.put_nowait, ...)``).
ProgressCallback = Callable[[str, int, str], None]


def _noop_progress(_step: str, _pct: int, _detail: str) -> None:  # pragma: no cover
    """No-op default callback so the import flow doesn't need to
    check ``if progress_cb is not None`` at every checkpoint."""


from sqlalchemy.orm import Session

from app.converters import openvsp_adapter
from app.converters.openvsp_importer import ImportResult, ImportWarning, import_vsp3
from app.schemas.aeroplaneschema import (
    AeroplaneSchema,
    AsbWingGeometryWriteSchema,
    FuselageSchema,
    FuselageXSecSuperEllipseSchema,
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
    * Aeroplane ``xyz_ref`` (reference point / CG)
    * Optional weight items' ``x_m``/``y_m``/``z_m`` positions

    Does NOT scale here:

    * **Fuselages** — scaled in ``_persist_aeroplane`` via
      :func:`_scale_fuselage_xsecs`, *after* the slicer refinement which
      must run in the unscaled STEP frame (gh-765). Scaling them here
      would force the slicer to unscale/rescale around the import factor.
    * Wing-section ``twist`` (angular)
    * Weight items ``mass_kg`` / ``total_mass_kg`` (per
      ``feedback_openvsp_import_rc_scope`` — see Variante B)
    """
    # Wings
    for wing in (aeroplane.wings or {}).values():
        for xs in wing.x_secs:
            xs.xyz_le = [v * factor for v in xs.xyz_le]
            xs.chord = xs.chord * factor

    # Aeroplane reference point (CG / origin) — also a length
    if aeroplane.xyz_ref is not None:
        aeroplane.xyz_ref = [v * factor for v in aeroplane.xyz_ref]

    # Weight items: positions only, mass intentionally untouched
    if weight_items is not None:
        for item in weight_items:
            item.x_m = item.x_m * factor
            item.y_m = item.y_m * factor
            item.z_m = item.z_m * factor


def _scale_fuselage_xsecs(
    x_secs: list[FuselageXSecSuperEllipseSchema], factor: float
) -> list[FuselageXSecSuperEllipseSchema]:
    """Return a new xsec list scaled by ``factor`` (gh-765).

    Applied once in ``_persist_aeroplane`` after the slicer refinement,
    which runs in the unscaled STEP frame. Scales the length-typed fields
    (``xyz`` position, ``a``/``b`` semi-axes); the dimensionless
    super-ellipse exponent ``n`` is left untouched.
    """
    return [
        FuselageXSecSuperEllipseSchema(
            xyz=[v * factor for v in xs.xyz],
            a=xs.a * factor,
            b=xs.b * factor,
            n=xs.n,
        )
        for xs in x_secs
    ]


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
            "target_span_m and scale_factor are mutually exclusive; specify at most one."
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


def _set_fuselage_step_path(db: Session, aeroplane_uuid, fuse_name: str, rel_path: str) -> None:
    """Write the per-geom Surface-STEP path onto an already-persisted
    ``FuselageModel`` row (gh-729)."""
    _update_fuselage_field(db, aeroplane_uuid, fuse_name, "step_path", rel_path)


def _set_fuselage_solid_step_path(
    db: Session, aeroplane_uuid, fuse_name: str, rel_path: str
) -> None:
    """Write the sewed-Solid-STEP path onto an already-persisted
    ``FuselageModel`` row (gh-731). Done as a second-pass update for
    the same reason as :func:`_set_fuselage_step_path`."""
    _update_fuselage_field(db, aeroplane_uuid, fuse_name, "solid_step_path", rel_path)


def _replace_fuselage_xsecs(db: Session, aeroplane_uuid, fuse_name: str, new_xsecs) -> bool:
    """Replace the existing fuselage's ``x_secs`` rows with new ones
    (gh-732). Pure mutation of the persisted row — keeps the gh-729
    Surface STEP path and the gh-731 Solid STEP path intact.

    ``new_xsecs`` is a list of ``FuselageXSecSuperEllipseSchema`` (or
    dict-form equivalents). The ``cascade=all, delete-orphan`` on
    ``FuselageModel.x_secs`` handles row-deletion for the old xsecs
    as soon as we clear the list.

    Returns True on success, False if the fuselage row could not be
    located (the slicer refinement is purely opportunistic, so the
    caller must be able to ignore failure).
    """
    from app.models.aeroplanemodel import (
        AeroplaneModel,
        FuselageModel,
        FuselageXSecSuperEllipseModel,
    )

    aeroplane = db.query(AeroplaneModel).filter(AeroplaneModel.uuid == aeroplane_uuid).first()
    if aeroplane is None:
        return False
    fuse_row = (
        db.query(FuselageModel)
        .filter(
            FuselageModel.aeroplane_id == aeroplane.id,
            FuselageModel.name == fuse_name,
        )
        .first()
    )
    if fuse_row is None:
        return False

    fuse_row.x_secs.clear()
    for i, xs in enumerate(new_xsecs):
        payload = xs.model_dump() if hasattr(xs, "model_dump") else dict(xs)
        # ``name`` doesn't live on the xsec model; ``sort_index`` is
        # set explicitly below to keep ordering stable.
        payload.pop("name", None)
        payload.pop("sort_index", None)
        fuse_row.x_secs.append(FuselageXSecSuperEllipseModel(sort_index=i, **payload))
    db.flush()
    return True


# Scale factor between cadquery's internal mm units (what
# ``slice_step_to_fuselage`` returns) and the FuselageSchema's metres.
# OCC's STEP reader normalises every length to mm regardless of the
# file's declared unit, so 1 mm = 0.001 m.
_MM_TO_M = 0.001


def _is_x_dominant_fuselage(handler_xsec_dicts: list[dict]) -> bool:
    """True when the handler-built schema's xsec positions are
    X-dominant — i.e. the long axis is world X.

    Using **handler xsec positions** (not the STEP bbox) is critical
    for paired symmetric sub-fuselages: the STEP file contains BOTH
    halves of a ``symmetric=True`` geom (e.g. cessna's MainFairing at
    y = ±1.27 m), so the STEP bbox spans 2.76 m in Y but only 1.1 m
    in X — falsely flagging the geom as Y-dominant. The handler schema
    contains only ONE side (the convention) and shows the true long
    axis directly.

    Margin of 1.2 keeps borderline cases (length:width ≈ 1) out of
    the refinement path so we don't replace a fine handler schema
    with marginal slicer output.
    """
    if len(handler_xsec_dicts) < 2:
        return False
    import numpy as np

    xs = np.array([[d["xyz"][0], d["xyz"][1], d["xyz"][2]] for d in handler_xsec_dicts])
    extents = xs.max(axis=0) - xs.min(axis=0)
    if extents[0] <= 1e-6:
        return False
    # Cast to plain Python bool — numpy's bool_ doesn't satisfy ``is True``
    # / ``is False`` identity checks, which trips up test assertions.
    return bool(extents[0] >= 1.2 * extents[1] and extents[0] >= 1.2 * extents[2])


# Bounds for the slicer-vs-handler frame check (gh-803). The slicer
# slices the STEP at the handler's anchor X-stations, so a faithful
# refinement must reproduce the handler's overall X-extent. A gross
# mismatch means the STEP and handler schema are in different
# frames/units: gh-732 forces the exported STEP to metres, but the
# importer keeps handler values in raw source units (OpenVSP 3.50 no
# longer exposes the length unit, so a feet-unit model like cessna337
# stays unconverted). The metric STEP then sits at ~0.305× the handler
# extent, the slices truncate/shrink, and accepting them would desync
# the fuselage from the (handler-frame) wings. Bounds are generous so
# only gross unit/frame mismatches trip — a real refinement is ≈ 1.0.
_SLICER_FRAME_RATIO_MIN = 0.5
_SLICER_FRAME_RATIO_MAX = 2.0


def _x_span(x_secs: list[FuselageXSecSuperEllipseSchema]) -> float:
    xs = [s.xyz[0] for s in x_secs]
    return (max(xs) - min(xs)) if xs else 0.0


def _slicer_frame_matches_handler(
    refined: list[FuselageXSecSuperEllipseSchema],
    handler_x_secs: list[FuselageXSecSuperEllipseSchema],
) -> bool:
    """True when the slicer output shares the handler's X-frame (gh-803).

    Compares the X-extent of the slicer result against the handler
    anchors. A ratio far from 1.0 signals a unit/frame mismatch — the
    refinement must then be rejected so the handler schema (which is
    consistent with the wings) is kept.
    """
    h_span = _x_span(handler_x_secs)
    r_span = _x_span(refined)
    if h_span <= 1e-9 or r_span <= 1e-9:
        return False
    ratio = r_span / h_span
    return _SLICER_FRAME_RATIO_MIN <= ratio <= _SLICER_FRAME_RATIO_MAX


def _try_slicer_refinement(
    rel_step_path: str,
    handler_fuse: FuselageSchema,
    fuse_name: str,
) -> list[FuselageXSecSuperEllipseSchema] | None:
    """Slice the gh-729/731 STEP file into a finer xsec list (gh-732).

    Returns a list of ``FuselageXSecSuperEllipseSchema`` in metres, or
    ``None`` when slicing fails / produces too few points to be useful
    / the fuselage isn't X-dominant in world frame. Failure is **silent
    on purpose** — the slicer is a refinement, not a requirement, and
    the handler-built schema is always the fallback.

    Frame-pure (gh-765): both the handler anchors and the STEP are in the
    **unscaled** OpenVSP frame, so this just converts the slicer's mm
    output to metres. The import scale factor is applied once afterwards,
    in :func:`_persist_aeroplane` via :func:`_scale_fuselage_xsecs` (xsecs)
    and ``scale_geom_step`` (the stored STEP files).
    """
    from app.core.config import settings

    full_path = Path(settings.ARTIFACTS_BASE_DIR) / rel_step_path
    if not full_path.exists():
        return None

    try:
        from cad_designer.aerosandbox.slicing import (
            slice_step_at_stations,
            slice_step_to_fuselage,
            vsp_anchored_x_stations,
        )
    except ImportError:
        logger.info(
            "cadquery / slicer unavailable — leaving handler-built schema for %r.",
            fuse_name,
        )
        return None

    # gh-732: stations are driven by VSP handler anchors when we have
    # them — every VSP-defined xsec is a mandatory anchor and the
    # remaining intermediate budget is distributed weighted by shape
    # change between consecutive anchors. This preserves the VSP-defined
    # positions exactly and concentrates extra slices where the spline
    # actually curves. Falls back to cadquery's XZ-profile curvature
    # for the rare case where the handler list is empty / has < 2 xsecs.
    try:
        handler_xsec_dicts = [
            {"xyz": list(xs.xyz), "a": xs.a, "b": xs.b, "n": xs.n} for xs in handler_fuse.x_secs
        ]

        # Frame-safety gate: only refine fuselages whose long axis is
        # X in world frame. Cessna sub-fuselages (NoseStrut, Struts,
        # MainStrut) are rotated 90° in OpenVSP — slicing them along
        # X would produce garbage. The check uses **handler xsec
        # positions** (not the STEP bbox) so that a symmetric pair —
        # whose STEP holds both halves and looks Y-dominant by bbox —
        # is correctly classified by the single-half handler schema.
        if not _is_x_dominant_fuselage(handler_xsec_dicts):
            logger.info(
                "Skipping slicer refinement for %r — not X-dominant in world frame.",
                fuse_name,
            )
            return None
        if len(handler_xsec_dicts) >= 2:
            # Budget proportional to VSP handler-xsec count: every
            # VSP-defined section gets ~5 intermediate stations plus
            # the two anchors. Floor at 15 (so tiny 2-3-xsec geoms
            # still get a reasonable refinement) and cap at 80
            # (Diamond DA42 main-fuselage with ~12 VSP xsecs would
            # otherwise blow past 70). This stops small sub-fuselages
            # (NoseFairing with ~6 VSP xsecs) from getting the same
            # 60-station treatment as the main fuselage — they
            # previously came out unnecessarily detailed compared to
            # their X-dominance-gated peers (MainFairing etc.).
            n_handler = len(handler_xsec_dicts)
            budget = min(80, max(15, n_handler + 5 * (n_handler - 1)))
            x_stations_mm = vsp_anchored_x_stations(
                handler_xsec_dicts,
                total_stations=budget,
                scale_to_mm=True,
            )
            # gh-732: for ``symmetric=True`` geoms (cessna MainFairing
            # at y=+1.27 m, paired with mirror at y=-1.27 m), the STEP
            # holds both halves. Clip to the side matching the handler
            # schema so each slice yields a single clean outline.
            keep_y_side: Optional[str] = None
            if getattr(handler_fuse, "symmetric", False):
                mean_y_m = sum(d["xyz"][1] for d in handler_xsec_dicts) / len(handler_xsec_dicts)
                if mean_y_m > 1e-3:
                    keep_y_side = "positive"
                elif mean_y_m < -1e-3:
                    keep_y_side = "negative"
                # else: handler centred on symmetry plane → no clip
            slicer_xsecs, metrics = slice_step_at_stations(
                str(full_path),
                x_stations_mm=x_stations_mm,
                points_per_slice=30,
                slice_axis="x",
                fuselage_name=fuse_name,
                keep_y_side=keep_y_side,
            )
        else:
            slicer_xsecs, metrics = slice_step_to_fuselage(
                str(full_path),
                number_of_slices=30,
                points_per_slice=30,
                slice_axis="x",
                fuselage_name=fuse_name,
                adaptive=True,
                curvature_weight=0.7,
            )
    except Exception as exc:  # noqa: BLE001 — refinement is best-effort
        logger.info(
            "Slicer refinement skipped for %r (%s) — keeping handler-built schema.",
            fuse_name,
            exc,
        )
        return None

    # FuselageSchema demands min_length=2.
    if len(slicer_xsecs) < 2:
        logger.info(
            "Slicer produced %d xsec(s) for %r — too few to refine; keeping handler schema.",
            len(slicer_xsecs),
            fuse_name,
        )
        return None

    refined = []
    for xs in slicer_xsecs:
        refined.append(
            FuselageXSecSuperEllipseSchema(
                xyz=[v * _MM_TO_M for v in xs["xyz"]],
                a=max(float(xs["a"]) * _MM_TO_M, 0.0),
                b=max(float(xs["b"]) * _MM_TO_M, 0.0),
                n=max(float(xs["n"]), 1.0),
            )
        )

    # gh-803: reject a refinement that doesn't share the handler's frame
    # (gross X-extent mismatch → unit/frame desync, e.g. cessna337's
    # feet-unit handler vs the metre-forced STEP). Keep the handler schema
    # so the fuselage stays consistent with the (handler-frame) wings.
    if not _slicer_frame_matches_handler(refined, handler_fuse.x_secs):
        logger.info(
            "Slicer refinement for %r diverges from the handler frame "
            "(refined X-span %.2f m vs handler %.2f m) — likely a unit/frame "
            "mismatch (gh-803); keeping handler schema.",
            fuse_name,
            _x_span(refined),
            _x_span(handler_fuse.x_secs),
        )
        return None

    logger.info(
        "Slicer refinement for %r: %d→%d xsecs (area_ratio=%.3f, vol_ratio=%.3f).",
        fuse_name,
        len(handler_fuse.x_secs),
        len(refined),
        metrics.get("area_ratio") or 0.0,
        metrics.get("volume_ratio") or 0.0,
    )
    return refined


def _update_fuselage_field(
    db: Session, aeroplane_uuid, fuse_name: str, attr: str, value: str
) -> None:
    """Common second-pass update for ``FuselageModel`` text columns
    that the create_fuselage path doesn't know about (gh-729 / gh-731).
    """
    from app.models.aeroplanemodel import AeroplaneModel, FuselageModel

    aeroplane = db.query(AeroplaneModel).filter(AeroplaneModel.uuid == aeroplane_uuid).first()
    if aeroplane is None:
        return
    fuse_row = (
        db.query(FuselageModel)
        .filter(
            FuselageModel.aeroplane_id == aeroplane.id,
            FuselageModel.name == fuse_name,
        )
        .first()
    )
    if fuse_row is None:
        return
    setattr(fuse_row, attr, value)
    db.flush()


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
    progress_cb: ProgressCallback = _noop_progress,
    scale_factor: float = 1.0,
) -> tuple[str, str]:
    """Persist the parsed aeroplane and return (uuid_str, name).

    Writes (gh-693): Aeroplane + Wings + Fuselages + WeightItems. Each
    component is wrapped in its own try/except — a failure on one
    record records a warning but lets the rest of the import succeed,
    so the user never loses an entire aeroplane to a single broken
    fuselage or weight item.

    ``progress_cb`` (gh-737) gets called at each major persistence
    checkpoint so a streaming endpoint can drive a frontend progress
    bar. Signature: ``(step, pct, detail)`` — see ProgressCallback.
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
    progress_cb("aeroplane", 20, f"Created aeroplane {resolved_name!r}")

    # Wings: convert each AsbWingSchema → AsbWingGeometryWriteSchema and
    # delegate to wing_service. The full schema isn't directly accepted
    # by the create_wing service, but the geometry-write schema is.
    if result.aeroplane.wings:
        n_wings = len(result.aeroplane.wings)
        for i, (wing_name, wing) in enumerate(result.aeroplane.wings.items()):
            progress_cb(
                "wing",
                25 + int(5 * (i + 1) / max(n_wings, 1)),
                f"Wing {i + 1}/{n_wings}: {wing_name}",
            )
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
    #
    # gh-729: also export a per-geom Surface STEP file and record its
    # relative path on the FuselageModel row. The geom→schema-name
    # mapping comes from ``result.fuselage_geom_ids``; we look the
    # gid up by schema name when persisting.
    #
    # gh-731: when the Surface STEP succeeded, sew it into a closed
    # Solid STEP (for the CAD-construction pipeline) and record its
    # path too. Sewing failures stay null and never abort the import.
    if result.aeroplane.fuselages:
        # Invert the gid → name map for name-based lookup. (Importer
        # may have renamed colliding names — gh-705 dedupe — so the
        # ``ctx`` map is the authoritative source.)
        name_to_gid = {n: g for g, n in (result.fuselage_geom_ids or {}).items()}
        from app.converters import openvsp_adapter
        from app.services import (
            openvsp_solid_sewing_service,
            openvsp_step_export_service,
        )

        vsp = openvsp_adapter.get_vsp() if openvsp_adapter.is_available() else None
        # gh-737: fuselages dominate the import wall-clock time (per-geom
        # STEP export + sewing + slicer refinement). Allocate 30–85 % of
        # the progress range to them; each fuselage gets a base pct plus
        # sub-events for the slow stages.
        n_fuselages = len(result.aeroplane.fuselages)
        fuselage_span_pct = 55  # 30 → 85
        fuselage_step_pct = fuselage_span_pct / max(n_fuselages, 1)

        for i, (fuse_name, fuse) in enumerate(result.aeroplane.fuselages.items()):
            base_pct = 30 + int(fuselage_step_pct * i)
            progress_cb(
                "fuselage",
                base_pct,
                f"Fuselage {i + 1}/{n_fuselages}: {fuse_name}",
            )
            try:
                fuselage_service.create_fuselage(db, aeroplane.uuid, fuse_name, fuse)
            except Exception as exc:  # noqa: BLE001
                _record_persist_failure(
                    result, component_type="FUSELAGE", component_name=fuse_name, exc=exc
                )
                continue
            # gh-765: STEP export + sewing + slicer refinement all run in
            # the UNSCALED OpenVSP frame. The import scale is applied once
            # afterwards — to the xsecs (``_scale_fuselage_xsecs``) and to
            # the stored STEP download files (``scale_geom_step``, gh-769).
            gid = name_to_gid.get(fuse_name)
            rel_step: Optional[str] = None
            rel_solid: Optional[str] = None
            refined_xsecs = None
            if vsp is not None and gid is not None:
                progress_cb(
                    "fuselage_step",
                    base_pct + int(fuselage_step_pct * 0.25),
                    f"{fuse_name}: exporting STEP",
                )
                rel_step = openvsp_step_export_service.export_geom_step(
                    vsp=vsp,
                    gid=gid,
                    geom_name=fuse_name,
                    aeroplane_uuid=str(aeroplane.uuid),
                )
                if rel_step:
                    _set_fuselage_step_path(db, aeroplane.uuid, fuse_name, rel_step)
                    progress_cb(
                        "fuselage_sew",
                        base_pct + int(fuselage_step_pct * 0.5),
                        f"{fuse_name}: sewing closed Solid",
                    )
                    rel_solid = openvsp_solid_sewing_service.sew_imported_geom_to_solid(
                        source_rel_step=rel_step,
                        aeroplane_uuid=str(aeroplane.uuid),
                        geom_name=fuse_name,
                    )
                    if rel_solid:
                        _set_fuselage_solid_step_path(db, aeroplane.uuid, fuse_name, rel_solid)

                    # gh-732: refine the schema's xsecs from the just-exported
                    # (unscaled) STEP. Solid STEP gives the slicer a real
                    # volume metric for logging; fall back to the Surface STEP
                    # when sewing failed. The handler-built schema stays if the
                    # slicer fails or produces too few points.
                    progress_cb(
                        "fuselage_slice",
                        base_pct + int(fuselage_step_pct * 0.75),
                        f"{fuse_name}: slicing for finer xsecs",
                    )
                    slicer_source = rel_solid or rel_step
                    refined_xsecs = _try_slicer_refinement(slicer_source, fuse, fuse_name)

            # gh-765: apply the import scale ONCE, after refinement (the
            # slicer ran in the unscaled STEP frame). When scaling, persist
            # the scaled xsecs — slicer output or handler fallback. When
            # not scaling, only the slicer result needs writing; the
            # handler xsecs are already correct from ``create_fuselage``.
            scaling = abs(scale_factor - 1.0) > 1e-9
            if scaling:
                final_xsecs = refined_xsecs if refined_xsecs is not None else fuse.x_secs
                _replace_fuselage_xsecs(
                    db,
                    aeroplane.uuid,
                    fuse_name,
                    _scale_fuselage_xsecs(final_xsecs, scale_factor),
                )
            elif refined_xsecs is not None:
                _replace_fuselage_xsecs(db, aeroplane.uuid, fuse_name, refined_xsecs)

            # gh-769: scale the stored STEP download files to model scale.
            # Done AFTER slicing (which needed the unscaled frame). The
            # precise STEP is what the user downloads / uses for internal
            # installations, so it must match the scaled aeroplane.
            # ``scale_geom_step`` overwrites in place and returns the same
            # path, so the DB row (set above) already points at the scaled
            # file — only re-set on the (future-proof) chance it relocates.
            if scaling:
                for setter, rel in (
                    (_set_fuselage_step_path, rel_step),
                    (_set_fuselage_solid_step_path, rel_solid),
                ):
                    if not rel:
                        continue
                    scaled_rel = openvsp_step_export_service.scale_geom_step(
                        rel, scale_factor, str(aeroplane.uuid)
                    )
                    if scaled_rel and scaled_rel != rel:
                        setter(db, aeroplane.uuid, fuse_name, scaled_rel)

    # Weight items (gh-693): persist each WeightItemWrite via the same
    # entry point the manual mass-properties UI uses, so categories,
    # CG-recompute hooks, and validation stay aligned.
    if result.weight_items:
        progress_cb(
            "weight_items",
            90,
            f"Persisting {len(result.weight_items)} weight items",
        )
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
    progress_cb: ProgressCallback = _noop_progress,
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
    progress_cb("parsing", 5, "Reading .vsp3 file")
    result = import_vsp3(path)
    progress_cb(
        "parsing",
        15,
        f"Parsed {len(result.aeroplane.wings or {})} wing(s), "
        f"{len(result.aeroplane.fuselages or {})} fuselage(s)",
    )

    factor = _resolve_scale_factor(result.aeroplane, target_span_m, scale_factor)
    # S1244: any factor far enough from 1.0 to matter geometrically — using
    # a small epsilon avoids float-equality pitfalls. Threshold 1e-9 is
    # well below any user-typed scale value (UI step is 0.01).
    if factor is not None and abs(factor - 1.0) > 1e-9:
        progress_cb("scaling", 18, f"Scaling by {factor:g}")
        _scale_aeroplane_lengths(result.aeroplane, factor, weight_items=result.weight_items)
        # Surface the scaling decision + the mass-not-scaled caveat to
        # the user. The frontend banner renders these alongside any
        # importer-level warnings.
        result.warnings.append(_make_scaling_warning(factor, target_span_m, scale_factor))

    uuid, name = _persist_aeroplane(
        db,
        result,
        name=name,
        source_filename=source_filename,
        progress_cb=progress_cb,
        # gh-765: the fuselage slicer refinement reads a STEP exported
        # from the unscaled OpenVSP model, so it needs the factor to
        # rescale its output to match the already-scaled schema.
        scale_factor=factor if factor is not None else 1.0,
    )
    progress_cb("finalising", 95, "Finalising aeroplane")
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
