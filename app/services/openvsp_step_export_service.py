"""Per-geom STEP-file export at OpenVSP-import time (gh-729).

The pipeline:

1. ``openvsp_import_service._persist_aeroplane`` calls
   :func:`export_geom_step` for every imported fuselage / custom geom,
   right after the row lands via ``fuselage_service.create_fuselage``.
2. We tag exactly that geom in user-set 3 (clean per-geom isolation,
   gh-719 pattern) and call ``vsp.ExportFile(..., SET_USER, EXPORT_STEP)``.
3. The file lives at
   ``${ARTIFACTS_BASE_DIR}/openvsp_imports/<aeroplane_uuid>/<sanitized>.stp``;
   the relative path goes into ``FuselageModel.step_path``.

VSP's STEP export is Surface-only — a collection of B-spline patches,
no closed Solid. That's the input to the gh-730 sewing pipeline and
to the gh-731 slicer-driven FuselageSchema rebuild.
"""

from __future__ import annotations

import logging
import re
from pathlib import Path
from types import ModuleType
from typing import Optional

from app.core.config import settings

logger = logging.getLogger(__name__)


# OpenVSP user-set index reserved for the per-geom isolation trick.
# Match the gh-719 pattern so concurrent imports can't trample each
# other's tag state — each call sets the flag immediately before
# ``ExportFile`` and clears it on exit.
_VSP_USER_SET = 3

# Where per-aeroplane STEP files land, relative to
# ``settings.ARTIFACTS_BASE_DIR``. Kept under a single sub-tree so
# the DELETE-aeroplane cleanup is one ``rmtree`` call.
_STEP_SUBDIR = "openvsp_imports"

# Filename sanitiser
# ----------------
# VSP geom names are user-typed — they can contain spaces, parens,
# accented characters, and path separators. ``Engine carter (type
# fuselage)`` is a real one from the Diamond DA42 test file. Collapse
# anything that isn't ASCII alphanumeric / hyphen / underscore down to
# ``_`` and cap at 64 chars so the resulting filename is portable
# across macOS / Linux / Windows and short enough for typical FS
# limits when nested under a UUID directory.
_SAFE_CHAR = re.compile(r"[^A-Za-z0-9._-]+")
_MAX_NAME_LEN = 64


def sanitize_geom_filename(name: str) -> str:
    """Map a user-typed VSP geom name to a filesystem-safe stem.

    Defensive against the OWASP path-traversal pattern: strips ``..``
    segments, leading dots, and any sequence of non-alphanumeric
    characters; falls back to ``geom`` for an empty / dot-only input.
    """
    cleaned = _SAFE_CHAR.sub("_", name).strip("._")
    # Strip path-traversal artefacts that survived the substitution.
    cleaned = cleaned.replace("..", "_")
    if not cleaned:
        cleaned = "geom"
    return cleaned[:_MAX_NAME_LEN]


def step_storage_dir(aeroplane_uuid: str) -> Path:
    """Resolve (and create) the per-aeroplane STEP-storage directory."""
    base = Path(settings.ARTIFACTS_BASE_DIR) / _STEP_SUBDIR / str(aeroplane_uuid)
    base.mkdir(parents=True, exist_ok=True)
    return base


def _set_step_export_length_unit_metres(vsp: ModuleType) -> None:
    """Force ``STEPSettings.LenUnit`` to ``LEN_M`` before ExportFile.

    Lives on the Vehicle container. We resolve the parm-id via
    ``FindContainerParm`` (silent-fail in OpenVSP 3.50, hence the
    explicit guard) and update only when needed so re-exports are cheap.
    """
    try:
        vid = vsp.FindContainer("Vehicle", 0)
        if not vid:
            return
        # OpenVSP 3.50 uses ``FindParm(container_id, name, group)`` —
        # earlier ``FindContainerParm`` was removed. Returns "" silently
        # when the parm doesn't exist.
        pid = vsp.FindParm(vid, "LenUnit", "STEPSettings")
        if not pid:
            return
        current = vsp.GetParmVal(pid)
        if abs(current - float(vsp.LEN_M)) > 1e-9:
            vsp.SetParmVal(pid, float(vsp.LEN_M))
            vsp.Update()
            logger.debug(
                "Set STEPSettings.LenUnit %g → %g (LEN_M) before STEP export.",
                current,
                float(vsp.LEN_M),
            )
    except Exception as exc:  # noqa: BLE001 — defensive, never abort
        logger.warning(
            "Could not set STEPSettings.LenUnit to LEN_M (%s) — falling back to "
            "VSP default (typically FOOT).",
            exc,
        )


def export_geom_step(
    vsp: ModuleType,
    gid: str,
    geom_name: str,
    aeroplane_uuid: str,
) -> Optional[str]:
    """Export one VSP geom as a per-geom STEP file. Returns the
    **relative** path (under ``ARTIFACTS_BASE_DIR``) for the DB row,
    or ``None`` on any failure (logged + swallowed — the rest of the
    import must still succeed).
    """
    try:
        # Tag only this geom in the user set, then untag every other
        # known geom so the export is clean.
        for other_gid in vsp.FindGeoms():
            vsp.SetSetFlag(other_gid, _VSP_USER_SET, other_gid == gid)

        # gh-732: force METRE units for STEP export. OpenVSP defaults
        # ``STEPSettings.LenUnit`` to ``LEN_FT=4`` (foot). The exporter
        # then writes geometry **numeric values in metres** but flags
        # the file as ``CONVERSION_BASED_UNIT('FOOT', 304.8)`` — every
        # conformant STEP reader (OCC/cadquery) applies the foot→mm
        # conversion and produces a fuselage that is exactly 0.3048 ×
        # too small. Setting it to ``LEN_M=2`` writes the file with a
        # plain ``SI_UNIT(.MILLI.,.METRE.)`` declaration that round-trips
        # to the correct physical scale.
        _set_step_export_length_unit_metres(vsp)

        out_dir = step_storage_dir(aeroplane_uuid)
        safe_stem = sanitize_geom_filename(geom_name)
        # Dedupe on collision (multiple geoms whose names sanitise to
        # the same stem — rare but possible).
        target = out_dir / f"{safe_stem}.stp"
        suffix_idx = 2
        while target.exists():
            target = out_dir / f"{safe_stem}_{suffix_idx}.stp"
            suffix_idx += 1

        vsp.ExportFile(str(target), _VSP_USER_SET, vsp.EXPORT_STEP)

        if not target.exists() or target.stat().st_size == 0:
            logger.warning(
                "STEP export for geom %r produced no file at %s",
                geom_name,
                target,
            )
            return None

        rel = target.relative_to(Path(settings.ARTIFACTS_BASE_DIR))
        return str(rel)
    except Exception as exc:  # noqa: BLE001 — defensive, never abort import
        logger.warning(
            "STEP export failed for geom %r (gid=%s): %s",
            geom_name,
            gid,
            exc,
            exc_info=True,
        )
        return None


def scale_geom_step(rel_step_path: str, factor: float, aeroplane_uuid: str) -> Optional[str]:
    """Scale a stored STEP file uniformly by ``factor`` about the origin,
    in place, and return its (unchanged) relative path (gh-769).

    OpenVSP exports the STEP from the **unscaled** model; this brings the
    precise download geometry to the same model scale as the rest of the
    imported aeroplane (so it matches the scaled xsecs and is usable for
    internal-installation work). Scaling the actual solid — rather than
    fudging the STEP unit declaration — avoids the foot/metre
    reader-interpretation footgun seen in gh-732.

    ``factor == 1.0`` is a no-op (returns the path unchanged). Returns
    ``None`` when CadQuery is unavailable or the transform/export fails;
    the caller then keeps the unscaled file (best-effort, never aborts
    the import). ``aeroplane_uuid`` is accepted for symmetry with
    :func:`export_geom_step`.
    """
    if abs(factor - 1.0) < 1e-9:
        return rel_step_path
    try:
        import cadquery as cq
        from cadquery import exporters
        from OCP.BRepBuilderAPI import BRepBuilderAPI_Transform
        from OCP.gp import gp_Pnt, gp_Trsf
    except ImportError:
        logger.info("CadQuery unavailable — leaving STEP %r unscaled.", rel_step_path)
        return None
    try:
        full_path = Path(settings.ARTIFACTS_BASE_DIR) / rel_step_path
        if not full_path.exists():
            return None
        # ``.vals()`` (not ``.val()``) so multi-shell STEPs — e.g. a
        # symmetric fuselage whose export holds both halves — are scaled
        # in full instead of silently dropping all but the first shell.
        shapes = cq.importers.importStep(str(full_path)).vals()
        if not shapes:
            return None
        trsf = gp_Trsf()
        trsf.SetScale(gp_Pnt(0.0, 0.0, 0.0), float(factor))
        scaled = [
            cq.Shape.cast(BRepBuilderAPI_Transform(s.wrapped, trsf, True).Shape()) for s in shapes
        ]
        # ``exporters.export`` accepts a Shape or an iterable of Shapes.
        out = scaled[0] if len(scaled) == 1 else scaled
        exporters.export(out, str(full_path), exporters.ExportTypes.STEP)
        return rel_step_path
    except Exception as exc:  # noqa: BLE001 — best effort, never abort import
        logger.warning(
            "Failed to scale STEP %r by %g (%s) — keeping unscaled.",
            rel_step_path,
            factor,
            exc,
        )
        return None


def cleanup_aeroplane_step_files(aeroplane_uuid: str) -> None:
    """Best-effort removal of the per-aeroplane STEP directory on
    ``DELETE /aeroplanes/<uuid>``. Errors are logged but never raised
    — the DB cascade has already run by this point.
    """
    import shutil

    target = Path(settings.ARTIFACTS_BASE_DIR) / _STEP_SUBDIR / str(aeroplane_uuid)
    try:
        if target.exists():
            shutil.rmtree(target, ignore_errors=False)
            logger.info("Removed STEP storage for aeroplane %s", aeroplane_uuid)
    except OSError as exc:
        logger.warning(
            "Failed to remove STEP storage for aeroplane %s: %s",
            aeroplane_uuid,
            exc,
        )
