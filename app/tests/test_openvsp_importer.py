"""Unit tests for the OpenVSP importer skeleton (gh-640).

This module covers the **grundgerüst** — module-level entry point,
warning collection, unit-conversion table, geom-dispatch loop — but
deliberately stops at the component handlers (#641 WING, #643
FUSELAGE, #645 BLANK). Those handlers are added in their own PRs and
this skeleton calls **registered handler callbacks**, so the
component PRs can land in any order without touching the skeleton.

All tests use the `openvsp_adapter` shim from gh-639 and mock the
`vsp` module — no real OpenVSP installation required.
"""

from __future__ import annotations

from types import ModuleType, SimpleNamespace
from typing import cast
from unittest.mock import patch

import pytest

from app.converters import openvsp_adapter, openvsp_importer
from app.converters.openvsp_importer import (
    LEN_UNIT_TO_METERS,
    ImportContext,
    ImportResult,
    ImportWarning,
    import_vsp3,
)


# ---------------------------------------------------------------------------
# Fake VSP module factory
# ---------------------------------------------------------------------------


def _make_fake_vsp(
    geoms: list[tuple[str, str, str]] | None = None,
    length_unit: int = 2,  # LEN_M
    vehicle_id: str = "VEH",
    parm_values: dict[tuple[str, str, str], float] | None = None,
) -> ModuleType:
    """Build a minimal stand-in for the `openvsp` module.

    ``geoms`` is a list of ``(gid, name, type_name)`` triples. Calls
    that retrieve a parm value can be satisfied via ``parm_values``,
    a dict keyed by ``(container_id, parm_name, group_name)``.
    """
    geoms = geoms or []
    parm_values = parm_values or {}

    # SimpleNamespace allows dynamic attribute assignment (unlike ModuleType
    # which Pyright treats as having a fixed attribute set). cast() at return
    # restores the ModuleType contract for the consumers.
    fake = SimpleNamespace()

    # Enum-like constants used by the skeleton.
    fake.LEN_MM = 0
    fake.LEN_CM = 1
    fake.LEN_M = 2
    fake.LEN_IN = 3
    fake.LEN_FT = 4
    fake.LEN_YD = 5
    fake.LEN_UNITLESS = 6
    fake.SYM_XY = 1
    fake.SYM_XZ = 2
    fake.SYM_YZ = 4

    # Bookkeeping for the test asserts.
    fake.calls: list[tuple[str, tuple]] = []  # type: ignore[attr-defined]

    def record(name):
        def _impl(*args, **kwargs):
            fake.calls.append((name, args))  # type: ignore[attr-defined]

        return _impl

    fake.ClearVSPModel = record("ClearVSPModel")
    fake.ReadVSPFile = record("ReadVSPFile")
    fake.Update = record("Update")

    def _set_length_unit(unit):
        fake.calls.append(("SetLengthUnit", (unit,)))  # type: ignore[attr-defined]

    fake.SetLengthUnit = _set_length_unit

    fake.GetVehicleID = lambda: vehicle_id
    fake.FindGeoms = lambda: [gid for gid, _name, _t in geoms]
    fake.GetGeomName = lambda gid: next((n for g, n, _t in geoms if g == gid), "")
    fake.GetGeomTypeName = lambda gid: next((t for g, _n, t in geoms if g == gid), "")

    # Parm-system stubs — keyed by (container, parm, group).
    fake._parm_registry = parm_values  # type: ignore[attr-defined]

    def _find_parm(container_id, parm_name, group_name):
        key = (container_id, parm_name, group_name)
        if key in parm_values:
            return f"PID::{container_id}::{group_name}::{parm_name}"
        return ""

    def _get_parm_val(pid):
        if pid == "":
            return 0.0
        # PID encoding: PID::<container>::<group>::<parm>
        _, container, group, parm = pid.split("::", 3)
        return parm_values.get((container, parm, group), 0.0)

    fake.FindParm = _find_parm
    fake.GetParmVal = _get_parm_val
    return cast(ModuleType, fake)


# ---------------------------------------------------------------------------
# LEN_UNIT_TO_METERS
# ---------------------------------------------------------------------------


class TestLenUnitToMeters:
    def test_table_has_all_known_units(self):
        # mm, cm, m, in, ft, yd, unitless
        for unit in (0, 1, 2, 3, 4, 5, 6):
            assert unit in LEN_UNIT_TO_METERS

    @pytest.mark.parametrize(
        "unit, scale",
        [
            (0, 0.001),  # mm
            (1, 0.01),  # cm
            (2, 1.0),  # m
            (3, 0.0254),  # in
            (4, 0.3048),  # ft
            (5, 0.9144),  # yd
            (6, 1.0),  # unitless → treat as m
        ],
    )
    def test_each_factor_matches_si_definition(self, unit, scale):
        assert LEN_UNIT_TO_METERS[unit] == pytest.approx(scale, rel=1e-9)


# ---------------------------------------------------------------------------
# ImportWarning + ImportContext + ImportResult
# ---------------------------------------------------------------------------


class TestImportContext:
    def test_add_warning_appends(self):
        ctx = ImportContext()
        ctx.add_warning(
            component_type="PROP",
            component_name="MainProp",
            reason="Propellers not supported in Phase 1",
            severity="warning",
        )
        assert len(ctx.warnings) == 1
        w = ctx.warnings[0]
        assert isinstance(w, ImportWarning)
        assert w.component_type == "PROP"
        assert w.component_name == "MainProp"
        assert w.severity == "warning"

    def test_mark_lossy_unique(self):
        ctx = ImportContext()
        ctx.mark_lossy("GEOM1")
        ctx.mark_lossy("GEOM1")  # duplicate ignored
        ctx.mark_lossy("GEOM2")
        assert ctx.lossy_components == ["GEOM1", "GEOM2"]

    def test_severity_must_be_known(self):
        ctx = ImportContext()
        with pytest.raises(ValueError, match="severity"):
            ctx.add_warning(
                component_type="X",
                component_name="Y",
                reason="z",
                severity="catastrophic",  # not allowed
            )


class TestImportResult:
    def test_default_fields(self):
        from app.schemas.aeroplaneschema import AeroplaneSchema

        ap = AeroplaneSchema(name="Empty")
        r = ImportResult(aeroplane=ap)
        assert r.aeroplane is ap
        assert r.warnings == []
        assert r.lossy_components == []
        assert r.weight_items == []


# ---------------------------------------------------------------------------
# import_vsp3 — adapter wiring + ClearVSPModel + Read + Update
# ---------------------------------------------------------------------------


class TestImportVsp3OpenVspMissing:
    def test_raises_clear_import_error(self, tmp_path):
        f = tmp_path / "x.vsp3"
        f.write_text("")
        with patch.object(openvsp_adapter, "_attempt_import", return_value=None):
            openvsp_adapter.reset_for_tests()
            # Force ImportError path.
            with patch.object(
                openvsp_adapter.importlib,
                "import_module",
                side_effect=ImportError("missing"),
            ):
                with pytest.raises(ImportError) as exc_info:
                    import_vsp3(f)
        assert "openvsp" in str(exc_info.value).lower()


class TestImportVsp3FileMissing:
    def test_raises_file_not_found(self, tmp_path):
        path = tmp_path / "no_such_file.vsp3"
        fake = _make_fake_vsp()
        with patch.object(openvsp_adapter, "get_vsp", return_value=fake):
            with pytest.raises(FileNotFoundError):
                import_vsp3(path)


class TestImportVsp3Empty:
    def test_no_geoms_yields_empty_aeroplane(self, tmp_path):
        f = tmp_path / "empty.vsp3"
        f.write_text("")
        fake = _make_fake_vsp(geoms=[])
        with patch.object(openvsp_adapter, "get_vsp", return_value=fake):
            result = import_vsp3(f)
        assert result.aeroplane.name == "empty"  # filename stem
        assert result.warnings == []
        assert result.weight_items == []
        # The skeleton MUST have called these in order on the fake vsp:
        names = [c[0] for c in fake.calls]
        assert names[0] == "ClearVSPModel"
        assert names[1] == "ReadVSPFile"
        assert "SetLengthUnit" in names
        assert "Update" in names

    def test_set_length_unit_called_with_meters(self, tmp_path):
        f = tmp_path / "x.vsp3"
        f.write_text("")
        fake = _make_fake_vsp(geoms=[])
        with patch.object(openvsp_adapter, "get_vsp", return_value=fake):
            import_vsp3(f)
        slu = [c for c in fake.calls if c[0] == "SetLengthUnit"]
        assert slu, "SetLengthUnit must be called"
        assert slu[0][1] == (fake.LEN_M,)


# ---------------------------------------------------------------------------
# Dispatch loop — unhandled geom types produce warnings, not crashes
# ---------------------------------------------------------------------------


class TestDispatchUnknownGeoms:
    @pytest.mark.parametrize(
        "vsp_type",
        ["PROP", "DISK", "MESH", "CUSTOM", "CONFORMAL", "NGON_MESH", "HUMAN"],
    )
    def test_unsupported_geom_emits_warning(self, vsp_type, tmp_path):
        f = tmp_path / "x.vsp3"
        f.write_text("")
        fake = _make_fake_vsp(
            geoms=[(f"GID_{vsp_type}", f"Some{vsp_type}", vsp_type)],
        )
        with patch.object(openvsp_adapter, "get_vsp", return_value=fake):
            result = import_vsp3(f)
        assert len(result.warnings) == 1
        w = result.warnings[0]
        assert w.component_type == vsp_type
        assert w.component_name == f"Some{vsp_type}"
        assert w.severity in ("info", "warning")
        # The component is recorded as lossy / non-imported.
        assert f"GID_{vsp_type}" in result.lossy_components


class TestDispatchRegisteredHandler:
    """The skeleton dispatches WING/FUSELAGE/BLANK to handlers.

    The component PRs (#641, #643, #645) register their own handlers.
    Here we verify the dispatch contract by registering fakes.
    """

    def test_wing_handler_is_invoked(self, tmp_path, monkeypatch):
        f = tmp_path / "x.vsp3"
        f.write_text("")
        fake = _make_fake_vsp(geoms=[("GID1", "MainWing", "WING")])

        recorded: list[tuple[str, str]] = []

        def _wing_handler(gid, name, aeroplane, ctx, vsp):
            recorded.append((gid, name))

        monkeypatch.setitem(openvsp_importer._HANDLERS, "WING", _wing_handler)
        with patch.object(openvsp_adapter, "get_vsp", return_value=fake):
            import_vsp3(f)
        assert recorded == [("GID1", "MainWing")]

    def test_blank_handler_receives_weight_items_sink(self, tmp_path, monkeypatch):
        f = tmp_path / "x.vsp3"
        f.write_text("")
        fake = _make_fake_vsp(geoms=[("B1", "Battery", "BLANK")])

        def _blank_handler(gid, name, aeroplane, ctx, vsp):
            # Skeleton must pass an `ImportContext` that has a way to
            # add weight items so the handler doesn't need to manage
            # cross-cutting state itself.
            from app.schemas.weight_item import WeightItemWrite

            ctx.add_weight_item(WeightItemWrite(name=name, mass_kg=1.5, x_m=0.3))

        monkeypatch.setitem(openvsp_importer._HANDLERS, "BLANK", _blank_handler)
        with patch.object(openvsp_adapter, "get_vsp", return_value=fake):
            result = import_vsp3(f)
        assert len(result.weight_items) == 1
        assert result.weight_items[0].name == "Battery"
        assert result.weight_items[0].mass_kg == 1.5


# ---------------------------------------------------------------------------
# Unit handling — read original LengthUnit + rescale
# ---------------------------------------------------------------------------


class TestUnitHandling:
    @pytest.mark.parametrize(
        "source_unit_name, unit_value",
        [
            ("mm", 0),
            ("cm", 1),
            ("m", 2),
            ("in", 3),
            ("ft", 4),
            ("yd", 5),
        ],
    )
    def test_source_unit_is_read_before_set_length_unit(
        self, source_unit_name, unit_value, tmp_path
    ):
        """The skeleton must read the source unit *before* rescaling."""
        f = tmp_path / "x.vsp3"
        f.write_text("")
        fake = _make_fake_vsp(
            geoms=[],
            parm_values={("VEH", "LengthUnit", "Vehicle_Info"): float(unit_value)},
        )
        with patch.object(openvsp_adapter, "get_vsp", return_value=fake):
            result = import_vsp3(f)
        # The ImportContext records the source unit for downstream
        # handlers that need to do their own scaling (esp. when
        # SetLengthUnit doesn't propagate to a particular parm).
        assert result.source_length_unit == unit_value
        assert result.source_scale_to_meters == pytest.approx(
            LEN_UNIT_TO_METERS[unit_value], rel=1e-9
        )
