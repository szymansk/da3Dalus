"""OpenVSP ``.vsp3`` importer skeleton (gh-640).

This module is the **grundgerüst** of the OpenVSP importer (epic
gh-637). It provides:

* :class:`ImportWarning` — structured, frontend-displayable record of
  something that did not import cleanly.
* :class:`ImportContext` — collector passed through the pipeline so
  individual handlers don't need to manage cross-cutting state.
* :class:`ImportResult` — the top-level return value: parsed
  ``AeroplaneSchema`` + collected weight items + warnings.
* :func:`import_vsp3` — public entry point.
* ``_HANDLERS`` — dispatch table the component PRs (#641 WING,
  #643 FUSELAGE, #645 BLANK, ...) register their handlers into.

Scope
-----

This module deliberately does **not** implement WING/FUSELAGE/BLANK
import. Those handlers live in their own PRs and are registered via
:func:`register_handler` so the component work can land in any order.

Out of scope (per ``feedback_openvsp_import_rc_scope`` memory): no
propulsion, no inertia, no CSGroup gains, no VSPAERO validation —
this importer is for RC-model scaling inspiration only.

Unit handling
-------------

The OpenVSP file format declares its length unit in the Vehicle_Info
container. We:

1. Read the source unit before doing anything else.
2. Call ``vsp.SetLengthUnit(LEN_M)`` to ask OpenVSP to rescale all
   length-typed parms to metres.
3. Also expose the source-unit metadata
   (:attr:`ImportResult.source_length_unit` /
   :attr:`ImportResult.source_scale_to_meters`) for handlers that
   need to do their own conversion as a belt-and-braces fallback
   (some VSP-side parms don't always honour SetLengthUnit reliably —
   see review comment on gh-640).
"""

from __future__ import annotations

from dataclasses import dataclass, field
from pathlib import Path
from types import ModuleType
from typing import Callable, Literal, Optional

from app.converters import openvsp_adapter
from app.schemas.aeroplaneschema import AeroplaneSchema
from app.schemas.weight_item import WeightItemWrite


# ---------------------------------------------------------------------------
# Unit table
# ---------------------------------------------------------------------------

# Maps OpenVSP `LEN_UNITS` enum integer → metres-per-unit scale.
# See ``vsp.LEN_MM`` through ``vsp.LEN_YD`` and ``vsp.LEN_UNITLESS``.
# Used as primary conversion when ``SetLengthUnit`` doesn't propagate.
LEN_UNIT_TO_METERS: dict[int, float] = {
    0: 0.001,  # LEN_MM
    1: 0.01,  # LEN_CM
    2: 1.0,  # LEN_M
    3: 0.0254,  # LEN_IN
    4: 0.3048,  # LEN_FT
    5: 0.9144,  # LEN_YD
    6: 1.0,  # LEN_UNITLESS — treat as metres
}


_VALID_SEVERITIES = ("info", "warning", "error")
Severity = Literal["info", "warning", "error"]


# ---------------------------------------------------------------------------
# Public dataclasses
# ---------------------------------------------------------------------------


@dataclass(frozen=True)
class ImportWarning:
    """A single non-fatal issue surfaced during import.

    Designed to round-trip cleanly to the JSON envelope returned by
    the ``/api/v2/import/openvsp`` endpoint (#646) and rendered by
    the frontend banner (#648).
    """

    component_type: str
    component_name: str
    reason: str
    severity: Severity = "warning"


@dataclass
class ImportContext:
    """Mutable collector threaded through the importer pipeline."""

    warnings: list[ImportWarning] = field(default_factory=list)
    lossy_components: list[str] = field(default_factory=list)
    weight_items: list[WeightItemWrite] = field(default_factory=list)
    source_length_unit: Optional[int] = None
    source_scale_to_meters: Optional[float] = None
    # Map of WING geom-id → schema name. Populated by the WING handler
    # and consumed by post-passes that need to walk wings (e.g.
    # SS_CONTROL → TrailingEdgeDevice in gh-644).
    wing_geom_ids: dict[str, str] = field(default_factory=dict)

    def add_warning(
        self,
        *,
        component_type: str,
        component_name: str,
        reason: str,
        severity: Severity = "warning",
    ) -> None:
        if severity not in _VALID_SEVERITIES:
            raise ValueError(f"severity must be one of {_VALID_SEVERITIES}, got {severity!r}")
        self.warnings.append(
            ImportWarning(
                component_type=component_type,
                component_name=component_name,
                reason=reason,
                severity=severity,
            )
        )

    def mark_lossy(self, gid: str) -> None:
        """Record a geom id as not fully imported (de-duplicated)."""
        if gid not in self.lossy_components:
            self.lossy_components.append(gid)

    def add_weight_item(self, item: WeightItemWrite) -> None:
        self.weight_items.append(item)


@dataclass
class ImportResult:
    """Top-level return value of :func:`import_vsp3`.

    ``aeroplane`` is the parsed geometry. ``weight_items`` is kept
    separate because the persistence layer (#646) attaches them to
    the ``AeroplaneModel`` rather than the schema.
    """

    aeroplane: AeroplaneSchema
    warnings: list[ImportWarning] = field(default_factory=list)
    lossy_components: list[str] = field(default_factory=list)
    weight_items: list[WeightItemWrite] = field(default_factory=list)
    source_length_unit: Optional[int] = None
    source_scale_to_meters: Optional[float] = None


# ---------------------------------------------------------------------------
# Handler registry
# ---------------------------------------------------------------------------

# Component PRs (#641 WING, #643 FUSELAGE, #645 BLANK, ...) register
# themselves here. Signature:
#
#     handler(gid: str, name: str, aeroplane: AeroplaneSchema,
#             ctx: ImportContext, vsp: ModuleType) -> None
#
# The vsp module is passed in (rather than imported at module top)
# so handler bodies remain testable with a fake module.

HandlerFn = Callable[[str, str, AeroplaneSchema, ImportContext, ModuleType], None]
PostPassFn = Callable[[AeroplaneSchema, ImportContext, ModuleType], None]
_HANDLERS: dict[str, HandlerFn] = {}
_POST_PASSES: list[PostPassFn] = []


def register_handler(geom_type: str, handler: HandlerFn) -> None:
    """Register a handler for a VSP geom type (``"WING"``, ``"FUSELAGE"``, ...)."""
    _HANDLERS[geom_type] = handler


def register_post_pass(fn: PostPassFn) -> None:
    """Register a post-pass callable that runs once after the dispatch loop.

    Use for cross-component work like vehicle-CG resolution (#645).
    Post-passes run in registration order and receive the populated
    AeroplaneSchema, the ImportContext, and the live vsp module.
    """
    if fn not in _POST_PASSES:
        _POST_PASSES.append(fn)


# Map of unsupported geom types → frontend-facing reason.
# Sub-issue #648 takes the warning structure and renders it.
_UNSUPPORTED_REASONS: dict[str, str] = {
    "PROP": "Propellers not yet supported (Phase 2 — see issue #649)",
    "DISK": "Actuator disks not yet supported (Phase 2)",
    "MESH": "Imported meshes not yet supported (Phase 2)",
    "CUSTOM": "Custom Geoms (AngelScript) cannot be imported parametrically",
    "CONFORMAL": "Conformal Geoms not yet supported (Phase 2)",
    "NGON_MESH": "N-Gon Mesh imports come in Phase 2",
    "HUMAN": "Human pilot geoms are not part of the aerodynamic model",
    "POD": "Pod/Body-of-Revolution geoms not yet supported (see issue #652)",
    "BOR": "Body-of-Revolution geoms not yet supported (see issue #652)",
    "STACK": "Stack geoms not yet supported in Phase 1",
    "ELLIPSOID": "Ellipsoid geoms not yet supported in Phase 1",
    "WIRE_FRAME": "Wire-frame geoms not part of the aerodynamic model",
    "HINGE": "Hinge geoms not part of the aerodynamic model",
    "PT_CLOUD": "Point-cloud geoms not yet supported",
    "GEAR": "Landing-gear geoms not yet supported",
}


# ---------------------------------------------------------------------------
# Entry point
# ---------------------------------------------------------------------------


def _read_source_length_unit(vsp: ModuleType, vehicle_id: str) -> Optional[int]:
    """Try to read the source-file length unit.

    Returns ``None`` when the parm group cannot be found (e.g. very
    old VSP versions or stub vehicles). Callers must tolerate ``None``.
    """
    try:
        pid = vsp.FindParm(vehicle_id, "LengthUnit", "Vehicle_Info")
        if pid == "":
            return None
        return int(vsp.GetParmVal(pid))
    except Exception:
        # Defensive: never crash because of unit-discovery failure.
        return None


_handlers_loaded = False


def _ensure_handlers_loaded() -> None:
    """Lazy-import + register component handlers on first call.

    Lazy registration avoids a circular import at module-load time
    and lets each handler module live in its own file (one per
    sub-issue).
    """
    global _handlers_loaded
    if _handlers_loaded:
        return
    try:  # pragma: no cover - import side effects
        from app.converters import openvsp_wing_handler

        openvsp_wing_handler.register()
    except ImportError:
        pass
    try:  # pragma: no cover
        from app.converters import openvsp_fuselage_handler

        openvsp_fuselage_handler.register()
    except ImportError:
        pass
    try:  # pragma: no cover
        from app.converters import openvsp_blank_handler

        openvsp_blank_handler.register()
    except ImportError:
        pass
    _handlers_loaded = True


def import_vsp3(path: Path) -> ImportResult:
    """Parse a ``.vsp3`` file → :class:`ImportResult`.

    Raises
    ------
    ImportError
        When the optional ``openvsp`` package is not installed.
        Message includes install hint (see ``openvsp_adapter``).
    FileNotFoundError
        When ``path`` does not exist on disk.
    """
    _ensure_handlers_loaded()
    path = Path(path)
    vsp = openvsp_adapter.get_vsp()  # raises ImportError if missing
    if not path.exists():
        raise FileNotFoundError(f"OpenVSP file not found: {path}")

    # Critical sequence (see gh-640 acceptance criteria): clear → read
    # → set unit → update. Skipping ClearVSPModel makes ReadVSPFile
    # merge into whatever state is already loaded.
    vsp.ClearVSPModel()
    vsp.ReadVSPFile(str(path))

    # Read original unit BEFORE asking OpenVSP to rescale.
    vehicle_id = vsp.GetVehicleID()
    source_unit = _read_source_length_unit(vsp, vehicle_id)
    source_scale = LEN_UNIT_TO_METERS.get(source_unit) if source_unit is not None else None

    # Ask OpenVSP to rescale all length parms to metres.
    vsp.SetLengthUnit(vsp.LEN_M)
    vsp.Update()

    ctx = ImportContext(
        source_length_unit=source_unit,
        source_scale_to_meters=source_scale,
    )

    aeroplane = AeroplaneSchema(name=path.stem)

    # Dispatch loop. Component PRs register handlers via
    # ``register_handler``. Unknown / unsupported geoms become
    # warnings (#648 surfaces them in the UI).
    for gid in vsp.FindGeoms():
        type_name = vsp.GetGeomTypeName(gid)
        name = vsp.GetGeomName(gid) or gid
        handler = _HANDLERS.get(type_name)
        if handler is not None:
            handler(gid, name, aeroplane, ctx, vsp)
        else:
            reason = _UNSUPPORTED_REASONS.get(
                type_name,
                f"Geom type {type_name!r} is not supported in Phase 1",
            )
            ctx.add_warning(
                component_type=type_name,
                component_name=name,
                reason=reason,
                severity="warning",
            )
            ctx.mark_lossy(gid)

    # Post-passes (vehicle-CG, etc.) run once on the populated aeroplane.
    for post_fn in _POST_PASSES:
        try:
            post_fn(aeroplane, ctx, vsp)
        except Exception as exc:  # pragma: no cover - defensive
            ctx.add_warning(
                component_type="POST_PASS",
                component_name=post_fn.__name__,
                reason=f"Post-pass {post_fn.__name__} failed: {exc}",
                severity="warning",
            )

    return ImportResult(
        aeroplane=aeroplane,
        warnings=list(ctx.warnings),
        lossy_components=list(ctx.lossy_components),
        weight_items=list(ctx.weight_items),
        source_length_unit=ctx.source_length_unit,
        source_scale_to_meters=ctx.source_scale_to_meters,
    )
