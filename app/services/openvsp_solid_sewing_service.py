"""Sew per-geom OpenVSP Surface STEP into a closed-Solid STEP (gh-731).

OpenVSP's ``ExportFile(..., EXPORT_STEP)`` writes a collection of
B-spline surface patches — no ``MANIFOLD_SOLID_BREP`` entity. That is
the input to gh-729's ``step_path``. For the user's CAD-construction
pipeline (battery bay cuts, servo-mount unions, carbon-tube
reinforcement bores, Spanten-Slicing) we need a **closed Solid**, so
this service stitches the patches into a Shell with
``BRepBuilderAPI_Sewing`` and then walks the result into one or more
``TopoDS_Solid`` instances.

The flow in :func:`sew_to_solid_step`:

1. Load the source STEP through cadquery (which wraps OCP / OCCT).
2. Sew all faces at a tight 1 mm tolerance. If nothing comes out, retry
   at 5 mm — VSP exports the occasional very leaky patch and the
   looser tolerance bridges those gaps.
3. Walk every ``TopoDS_Shell`` the sewing produced (symmetric geoms
   yield 2 shells), wrap each with ``BRepBuilderAPI_MakeSolid``, run
   ``ShapeFix_Solid``, and reverse if the resulting volume is
   negative (surface normals pointed inward).
4. When more than one solid survives the round trip, try to fuse them
   with ``BRepAlgoAPI_Fuse``. If that fails — typical for
   left-strut / right-strut pairs that don't share any face — collect
   them in a ``TopoDS_Compound`` instead. Both shapes are valid input
   for downstream CAD operations.
5. Write the result with ``STEPControl_Writer``.

Failures never raise — they log a warning and return ``False`` /
``None`` so the surrounding OpenVSP-import never aborts on a single
bad fuselage.
"""

from __future__ import annotations

import logging
from pathlib import Path
from typing import Optional

from app.core.config import settings
from app.services.openvsp_step_export_service import (
    sanitize_geom_filename,
    step_storage_dir,
)

logger = logging.getLogger(__name__)


# Tight sew tolerance (millimetres). VSP surface patches generally
# meet to within ~0.1 mm; 1 mm safely bridges the typical gap without
# fusing unrelated detail features. Picked empirically on the Cessna
# 172 fuselage and validated on the Diamond DA42 multi-body case.
_SEW_TOLERANCE_TIGHT_MM = 0.001

# Looser fallback when the tight pass produces no shells at all. Five
# millimetres is the most we'll bridge without risking that the
# nose-cap stitches itself to the tail. Above this the result is
# usually unusable anyway and we'd rather null the solid_step_path.
_SEW_TOLERANCE_LOOSE_MM = 0.005

# Suffix appended to the sanitized geom stem to distinguish the
# sewed-Solid file from gh-729's surface STEP next to it in the same
# per-aeroplane directory.
_SOLID_SUFFIX = "_solid.stp"


def solid_step_filename(stem: str) -> str:
    """Filename for the sewed-Solid output given a (possibly raw) stem."""
    return f"{sanitize_geom_filename(stem)}{_SOLID_SUFFIX}"


def sew_to_solid_step(source_step_path: Path, target_step_path: Path) -> bool:
    """Sew the surface STEP into a closed-Solid STEP at the target path.

    Returns True only when a non-empty STEP file is produced. Logs a
    warning and returns False on any failure so callers can ignore
    the result and proceed.
    """
    try:
        if not source_step_path.exists():
            logger.warning("Source STEP missing: %s", source_step_path)
            return False

        shape = _sew_and_solidify(source_step_path)
        if shape is None:
            logger.info(
                "Solid sewing produced no valid result for %s — leaving solid_step_path null.",
                source_step_path,
            )
            return False

        _write_step(shape, target_step_path)
        return target_step_path.exists() and target_step_path.stat().st_size > 0
    except Exception as exc:  # noqa: BLE001 — defensive, never abort import
        logger.warning(
            "Solid sewing failed for %s: %s",
            source_step_path, exc, exc_info=True,
        )
        return False


def sew_imported_geom_to_solid(
    source_rel_step: str,
    aeroplane_uuid: str,
    geom_name: str,
) -> Optional[str]:
    """High-level wrapper used by the OpenVSP-import pipeline.

    Reads the gh-729 surface STEP under ``settings.ARTIFACTS_BASE_DIR``,
    sews it into a closed Solid, writes the result alongside the
    source, and returns the **relative** path for
    ``FuselageModel.solid_step_path``. Returns ``None`` on any failure
    (logged + swallowed).
    """
    artifacts_root = Path(settings.ARTIFACTS_BASE_DIR).resolve()
    source = (artifacts_root / source_rel_step).resolve()
    # Defence in depth: refuse to follow a path that escapes the
    # artifacts root, even though the source came from our own DB.
    if artifacts_root not in source.parents:
        logger.warning(
            "Surface STEP path %r escapes artifacts root — refusing to sew.",
            source_rel_step,
        )
        return None

    out_dir = step_storage_dir(aeroplane_uuid)
    target = out_dir / solid_step_filename(geom_name)
    # Dedupe filenames if a previous geom in the same import already
    # claimed the same sanitized stem (rare but possible: ``Strut_L``
    # and ``Strut/L`` both sanitize to ``Strut_L``).
    suffix_idx = 2
    while target.exists():
        target = out_dir / f"{sanitize_geom_filename(geom_name)}_{suffix_idx}{_SOLID_SUFFIX}"
        suffix_idx += 1

    if not sew_to_solid_step(source, target):
        return None
    try:
        return str(target.relative_to(artifacts_root))
    except ValueError:
        # Should never happen given step_storage_dir lives under the
        # artifacts root, but be defensive.
        logger.warning("Solid STEP target %s outside artifacts root", target)
        return None


# ---------------------------------------------------------------------------
# Internals — split out for unit-test addressability
# ---------------------------------------------------------------------------


def _sew_and_solidify(source_step_path: Path):
    """Run the full sew → MakeSolid → heal → merge pipeline.

    Returns a ``TopoDS_Shape`` (a single ``TopoDS_Solid`` for a
    one-shell geom, a fused Solid or a ``TopoDS_Compound`` for a
    multi-shell symmetric geom) or ``None`` when nothing healed
    into a valid solid.
    """
    import cadquery as cq

    workplane = cq.importers.importStep(str(source_step_path))
    faces = workplane.faces().vals()
    if not faces:
        logger.info("No faces in %s — nothing to sew.", source_step_path)
        return None

    shells = _sew_faces(faces, _SEW_TOLERANCE_TIGHT_MM)
    if not shells:
        logger.debug(
            "Tight sew (%g mm) produced no shells; retrying loose (%g mm).",
            _SEW_TOLERANCE_TIGHT_MM, _SEW_TOLERANCE_LOOSE_MM,
        )
        shells = _sew_faces(faces, _SEW_TOLERANCE_LOOSE_MM)
    if not shells:
        return None

    solids = []
    for shell in shells:
        solid = _make_solid_oriented(shell)
        if solid is not None:
            solids.append(solid)
    if not solids:
        return None
    if len(solids) == 1:
        return solids[0]
    return _merge_solids(solids)


def _sew_faces(faces, tolerance_mm: float):
    """Sew an iterable of cq.Face objects into a list of TopoDS_Shell."""
    from OCP.BRepBuilderAPI import BRepBuilderAPI_Sewing
    from OCP.TopAbs import TopAbs_SHELL
    from OCP.TopExp import TopExp_Explorer
    from OCP.TopoDS import TopoDS

    sewer = BRepBuilderAPI_Sewing(tolerance_mm)
    for face in faces:
        sewer.Add(face.wrapped)
    sewer.Perform()
    sewn = sewer.SewedShape()
    if sewn is None or sewn.IsNull():
        return []

    shells = []
    explorer = TopExp_Explorer(sewn, TopAbs_SHELL)
    while explorer.More():
        shells.append(TopoDS.Shell_s(explorer.Current()))
        explorer.Next()
    return shells


def _make_solid_oriented(shell):
    """Build a Solid from a Shell, run ShapeFix, orient outward.

    Returns ``None`` when MakeSolid can't proceed, the healed solid
    fails ``BRepCheck_Analyzer.IsValid()`` (open shell), or the
    resulting volume is zero / NaN.

    The ``BRepCheck`` gate matters: ``ShapeFix_Solid`` is generous —
    even an open box yields a finite positive volume because OCC
    integrates by divergence on the partial surface. The check
    distinguishes a *topologically* closed Solid from a partial one.
    """
    from OCP.BRepBuilderAPI import BRepBuilderAPI_MakeSolid
    from OCP.BRepCheck import BRepCheck_Analyzer
    from OCP.BRepGProp import BRepGProp
    from OCP.GProp import GProp_GProps
    from OCP.ShapeFix import ShapeFix_Solid

    builder = BRepBuilderAPI_MakeSolid(shell)
    builder.Build()
    if not builder.IsDone():
        return None
    solid = builder.Solid()

    fixer = ShapeFix_Solid(solid)
    fixer.Perform()
    healed = fixer.Solid()

    if not BRepCheck_Analyzer(healed).IsValid():
        return None

    props = GProp_GProps()
    BRepGProp.VolumeProperties_s(healed, props)
    volume = props.Mass()
    if volume != volume:  # NaN — defensive, BRepCheck should already reject
        return None
    if volume == 0:
        return None
    if volume < 0:
        # Surface normals point inward — flip the orientation. Reversed()
        # on a TopoDS_Solid returns a TopoDS_Solid.
        return _downcast_to_solid(healed.Reversed())
    return healed


def _merge_solids(solids):
    """Try boolean-fusing solids; fall back to a Compound on failure.

    Symmetric VSP geoms (left strut + right strut, etc.) often don't
    share any face, so ``BRepAlgoAPI_Fuse`` legitimately fails. A
    ``TopoDS_Compound`` holding both Solids is still a valid STEP
    payload and works as input to downstream CAD ops.
    """
    from OCP.BRepAlgoAPI import BRepAlgoAPI_Fuse

    fused = solids[0]
    for other in solids[1:]:
        try:
            op = BRepAlgoAPI_Fuse(fused, other)
            op.Build()
            if not op.IsDone():
                raise RuntimeError("BRepAlgoAPI_Fuse did not converge")
            fused = op.Shape()
        except Exception as exc:  # noqa: BLE001 — fall back, not fatal
            logger.info(
                "Boolean Fuse failed (%s); falling back to Compound of %d solids.",
                exc, len(solids),
            )
            return _compound_of_solids(solids)
    return fused


def _compound_of_solids(solids):
    """Pack a list of TopoDS_Solid into a TopoDS_Compound."""
    from OCP.BRep import BRep_Builder
    from OCP.TopoDS import TopoDS_Compound

    compound = TopoDS_Compound()
    builder = BRep_Builder()
    builder.MakeCompound(compound)
    for solid in solids:
        builder.Add(compound, solid)
    return compound


def _downcast_to_solid(shape):
    """``Reversed()`` on TopoDS_Solid returns the right subtype already,
    but the type-checker can't see through it — wrap so callers stay
    typed against TopoDS_Solid."""
    from OCP.TopoDS import TopoDS

    try:
        return TopoDS.Solid_s(shape)
    except Exception:  # noqa: BLE001
        return shape


def _write_step(shape, target_path: Path) -> None:
    """Write a shape to disk as a STEP file (AP-214)."""
    from OCP.IFSelect import IFSelect_RetDone
    from OCP.STEPControl import STEPControl_AsIs, STEPControl_Writer

    target_path.parent.mkdir(parents=True, exist_ok=True)
    writer = STEPControl_Writer()
    writer.Transfer(shape, STEPControl_AsIs)
    status = writer.Write(str(target_path))
    if status != IFSelect_RetDone:
        raise RuntimeError(f"STEP write returned status {status}")
