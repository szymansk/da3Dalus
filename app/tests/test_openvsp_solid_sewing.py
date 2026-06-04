"""Tests for the gh-731 OpenVSP-Solid sewing service.

Pure-Python tests on filename helpers run anywhere; the OCC-backed
tests gate on ``cadquery`` / ``OCP`` via ``pytest.importorskip`` so
the suite still passes on platforms that exclude CadQuery
(linux/aarch64, see ``pyproject.toml`` env markers). No ``slow``
marker — the box / split-shell fixtures complete in well under a
second and we want them in the SonarCloud new-coverage pool.
"""

from __future__ import annotations

from pathlib import Path

import pytest

from app.services.openvsp_solid_sewing_service import (
    _compound_of_solids,
    _make_solid_oriented,
    _sew_faces,
    solid_step_filename,
    sew_to_solid_step,
    sew_imported_geom_to_solid,
)


# ---------------------------------------------------------------------------
# Pure-Python tests
# ---------------------------------------------------------------------------


class TestSolidStepFilename:
    def test_appends_solid_suffix(self):
        assert solid_step_filename("Fuselage") == "Fuselage_solid.stp"

    def test_sanitises_unsafe_stem(self):
        # Mirrors the gh-729 sanitisation rules.
        assert solid_step_filename("Engine carter (type fuselage)") == (
            "Engine_carter_type_fuselage_solid.stp"
        )

    def test_strips_path_traversal(self):
        out = solid_step_filename("../etc/passwd")
        assert ".." not in out
        assert "/" not in out
        assert out.endswith("_solid.stp")


# ---------------------------------------------------------------------------
# OCC-backed tests
# ---------------------------------------------------------------------------


# Gate on cadquery — the rest of OCP comes along with it on platforms
# where cadquery is available (mac/linux x86_64). Skip silently on
# linux/aarch64 where pyproject.toml excludes both.
cq = pytest.importorskip("cadquery")


def _export_box_as_surface_step(target_path: Path, size: float = 10.0) -> Path:
    """Build a closed box and export its **faces** (not the solid) as
    STEP — mimics VSP's surface-only output. cadquery's exporter
    writes solids by default, so we extract the faces into a Compound
    and write that instead.
    """
    from OCP.BRep import BRep_Builder
    from OCP.IFSelect import IFSelect_RetDone
    from OCP.STEPControl import STEPControl_AsIs, STEPControl_Writer
    from OCP.TopoDS import TopoDS_Compound

    box = cq.Workplane("XY").box(size, size, size)
    faces = box.faces().vals()

    compound = TopoDS_Compound()
    builder = BRep_Builder()
    builder.MakeCompound(compound)
    for face in faces:
        builder.Add(compound, face.wrapped)

    writer = STEPControl_Writer()
    writer.Transfer(compound, STEPControl_AsIs)
    status = writer.Write(str(target_path))
    assert status == IFSelect_RetDone
    return target_path


def _export_open_box_step(target_path: Path, size: float = 10.0) -> Path:
    """Same as :func:`_export_box_as_surface_step` but drop one face
    so the result is topologically *open* — sewing should still
    produce a shell but :func:`_make_solid_oriented` should reject it
    because the volume is NaN / zero.
    """
    from OCP.BRep import BRep_Builder
    from OCP.IFSelect import IFSelect_RetDone
    from OCP.STEPControl import STEPControl_AsIs, STEPControl_Writer
    from OCP.TopoDS import TopoDS_Compound

    box = cq.Workplane("XY").box(size, size, size)
    faces = list(box.faces().vals())[:-1]  # drop the last face

    compound = TopoDS_Compound()
    builder = BRep_Builder()
    builder.MakeCompound(compound)
    for face in faces:
        builder.Add(compound, face.wrapped)

    writer = STEPControl_Writer()
    writer.Transfer(compound, STEPControl_AsIs)
    status = writer.Write(str(target_path))
    assert status == IFSelect_RetDone
    return target_path


def _export_two_separated_boxes_step(target_path: Path) -> Path:
    """Mimics a symmetric VSP geom: two disjoint closed shells (the
    left & right strut) in one STEP. Sewing yields two shells, each
    healable into its own Solid. The merge step then has to fall back
    to a Compound because they share no face.
    """
    from OCP.BRep import BRep_Builder
    from OCP.IFSelect import IFSelect_RetDone
    from OCP.STEPControl import STEPControl_AsIs, STEPControl_Writer
    from OCP.TopoDS import TopoDS_Compound

    left = cq.Workplane("XY").box(5, 5, 5).translate((-10, 0, 0))
    right = cq.Workplane("XY").box(5, 5, 5).translate((10, 0, 0))

    compound = TopoDS_Compound()
    builder = BRep_Builder()
    builder.MakeCompound(compound)
    for face in left.faces().vals():
        builder.Add(compound, face.wrapped)
    for face in right.faces().vals():
        builder.Add(compound, face.wrapped)

    writer = STEPControl_Writer()
    writer.Transfer(compound, STEPControl_AsIs)
    status = writer.Write(str(target_path))
    assert status == IFSelect_RetDone
    return target_path


def _solid_count(step_path: Path) -> int:
    """Count TopoDS_Solid entries in a STEP file by re-importing it."""
    shape = cq.importers.importStep(str(step_path))
    return len(shape.solids().vals())


def _grep_step_for_solid_brep(step_path: Path) -> bool:
    """Acceptance-criterion check: confirm the STEP body actually
    contains a ``MANIFOLD_SOLID_BREP`` entity (the marker that the
    sewing worked, vs the surface-only ``B_SPLINE_SURFACE_WITH_KNOTS``
    input).
    """
    text = step_path.read_text(errors="ignore")
    return "MANIFOLD_SOLID_BREP" in text


class TestSewToSolidStep:
    def test_sews_closed_box_into_single_solid(self, tmp_path):
        source = _export_box_as_surface_step(tmp_path / "box_surfaces.stp")
        target = tmp_path / "box_solid.stp"

        ok = sew_to_solid_step(source, target)

        assert ok is True
        assert target.exists()
        assert target.stat().st_size > 0
        assert _solid_count(target) == 1
        # Acceptance criterion: primary entity must be MANIFOLD_SOLID_BREP.
        assert _grep_step_for_solid_brep(target)

    def test_returns_false_when_source_missing(self, tmp_path):
        target = tmp_path / "out.stp"
        ok = sew_to_solid_step(tmp_path / "does_not_exist.stp", target)
        assert ok is False
        assert not target.exists()

    def test_open_shell_returns_false(self, tmp_path):
        """An open box (one face removed) cannot heal into a closed
        Solid — the service must refuse rather than writing a bogus
        STEP with NaN volume."""
        source = _export_open_box_step(tmp_path / "open_box.stp")
        target = tmp_path / "open_box_solid.stp"

        ok = sew_to_solid_step(source, target)

        assert ok is False

    def test_separated_pair_packs_into_compound(self, tmp_path):
        """Two disjoint closed boxes in one STEP — the merge step
        must fall back to a Compound rather than a bool-fused solid.
        The output STEP should still load and contain both solids.
        """
        source = _export_two_separated_boxes_step(tmp_path / "pair.stp")
        target = tmp_path / "pair_solid.stp"

        ok = sew_to_solid_step(source, target)

        assert ok is True
        # The output should reimport as 2 solids (independent of
        # whether the merger fused them or packed them into a
        # Compound — both yield 2 solids on import).
        assert _solid_count(target) == 2


class TestSewImportedGeomToSolid:
    def test_round_trip_writes_under_artifacts_root(self, tmp_path, monkeypatch):
        from app.core import config as core_config

        monkeypatch.setattr(core_config.settings, "ARTIFACTS_BASE_DIR", tmp_path)

        # Mimic the gh-729 directory layout.
        uuid = "abcd-1234"
        per_aeroplane_dir = tmp_path / "openvsp_imports" / uuid
        per_aeroplane_dir.mkdir(parents=True)
        source_full = _export_box_as_surface_step(per_aeroplane_dir / "MyFuselage.stp")
        source_rel = str(source_full.relative_to(tmp_path))

        rel_out = sew_imported_geom_to_solid(source_rel, uuid, "MyFuselage")

        assert rel_out is not None
        assert rel_out.endswith("MyFuselage_solid.stp")
        full_out = tmp_path / rel_out
        assert full_out.exists()
        assert full_out.parent == per_aeroplane_dir
        assert _solid_count(full_out) == 1

    def test_rejects_path_traversal(self, tmp_path, monkeypatch):
        from app.core import config as core_config

        monkeypatch.setattr(core_config.settings, "ARTIFACTS_BASE_DIR", tmp_path)
        # ``..`` segments resolve outside the artifacts root.
        result = sew_imported_geom_to_solid("../etc/passwd", "uuid", "evil")
        assert result is None

    def test_returns_none_on_missing_source(self, tmp_path, monkeypatch):
        from app.core import config as core_config

        monkeypatch.setattr(core_config.settings, "ARTIFACTS_BASE_DIR", tmp_path)
        # Plausible-looking path, but the file is not on disk.
        result = sew_imported_geom_to_solid("openvsp_imports/uuid/missing.stp", "uuid", "missing")
        assert result is None

    def test_dedupes_when_target_already_exists(self, tmp_path, monkeypatch):
        """Two consecutive imports of geoms whose names sanitise to
        the same stem must each produce a non-clobbering file.
        Exercises the ``while target.exists()`` rename loop.
        """
        from app.core import config as core_config

        monkeypatch.setattr(core_config.settings, "ARTIFACTS_BASE_DIR", tmp_path)

        uuid = "dedupe-test"
        per_aeroplane_dir = tmp_path / "openvsp_imports" / uuid
        per_aeroplane_dir.mkdir(parents=True)
        source_full = _export_box_as_surface_step(per_aeroplane_dir / "MyFuse.stp")
        source_rel = str(source_full.relative_to(tmp_path))

        first = sew_imported_geom_to_solid(source_rel, uuid, "MyFuse")
        second = sew_imported_geom_to_solid(source_rel, uuid, "MyFuse")

        assert first is not None
        assert second is not None
        assert first != second
        assert first.endswith("MyFuse_solid.stp")
        assert second.endswith("_solid.stp")
        # Sanity: the dedupe must not have overwritten the first file.
        assert (tmp_path / first).exists()
        assert (tmp_path / second).exists()


class TestPipelineInternals:
    """Coverage for the otherwise-unreachable internals: empty STEP,
    compound packer, and the ``BRepBuilderAPI_MakeSolid`` rejection
    path. Direct unit tests are necessary because shaping cadquery
    output to hit each branch through the public surface is awkward.
    """

    def test_sew_to_solid_returns_false_on_face_less_step(self, tmp_path):
        """An empty Compound (no faces) — the ``not faces`` branch of
        ``_sew_and_solidify`` must short-circuit cleanly without
        crashing OCP.
        """
        from OCP.BRep import BRep_Builder
        from OCP.IFSelect import IFSelect_RetDone
        from OCP.STEPControl import STEPControl_AsIs, STEPControl_Writer
        from OCP.TopoDS import TopoDS_Compound

        source = tmp_path / "no_faces.stp"
        compound = TopoDS_Compound()
        builder = BRep_Builder()
        builder.MakeCompound(compound)
        # Write the empty compound — OCP accepts it.
        writer = STEPControl_Writer()
        writer.Transfer(compound, STEPControl_AsIs)
        status = writer.Write(str(source))
        assert status == IFSelect_RetDone

        target = tmp_path / "no_faces_solid.stp"
        ok = sew_to_solid_step(source, target)
        assert ok is False

    def test_compound_of_solids_packs_n_solids(self):
        """``_compound_of_solids`` collects an arbitrary list of
        ``TopoDS_Solid`` into one ``TopoDS_Compound``. Reimporting
        the resulting shape via cadquery must yield N solids back.
        """
        # Build 3 boxes → 3 closed shells → 3 oriented solids.
        boxes = [cq.Workplane("XY").box(2, 2, 2).translate((10 * i, 0, 0)) for i in range(3)]
        solids = []
        for box in boxes:
            shells = _sew_faces(box.faces().vals(), 0.001)
            assert len(shells) == 1
            solid = _make_solid_oriented(shells[0])
            assert solid is not None
            solids.append(solid)

        compound = _compound_of_solids(solids)
        wp = cq.Workplane(cq.Shape(compound))
        assert len(wp.solids().vals()) == 3
