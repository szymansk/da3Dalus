"""Geometric sanity validation tests for the OpenVSP importer (gh-647).

Per the scope-clarification comment on #647: no VSPAERO roundtrip,
no ASB CL_α comparison. We test:

* Wing span/area/MAC equality (±1%) between importer output and the
  vsp module's reported TotalSpan/TotalProjectedArea/TotalChord.
* Fuselage length equality (±1%) against VSP's Design/Length parm.
* Out-of-tolerance differences produce structured ImportWarnings.
"""

from __future__ import annotations

from collections import OrderedDict
from types import ModuleType, SimpleNamespace
from typing import cast

import pytest

from app.converters.openvsp_validation import (
    compute_fuselage_length,
    compute_wing_metrics,
    validate_geometry,
)
from app.schemas.aeroplaneschema import (
    AeroplaneSchema,
    AsbWingSchema,
    FuselageSchema,
    FuselageXSecSuperEllipseSchema,
    WingXSecSchema,
)


# ---------------------------------------------------------------------------
# Test fixtures: simple aircraft + fake vsp
# ---------------------------------------------------------------------------


def _trapezoid_wing(
    *, name="MainWing", span_half=5.0, c_root=1.0, c_tip=0.5, symmetric=True
) -> AsbWingSchema:
    return AsbWingSchema(
        name=name,
        symmetric=symmetric,
        x_secs=[
            WingXSecSchema(
                xyz_le=[0.0, 0.0, 0.0],
                chord=c_root,
                twist=0.0,
                airfoil="./components/airfoils/naca0012.dat",
                x_sec_type="root",
            ),
            WingXSecSchema(
                xyz_le=[0.0, span_half, 0.0],
                chord=c_tip,
                twist=0.0,
                airfoil="./components/airfoils/naca0012.dat",
            ),
        ],
    )


def _make_vsp(
    *,
    wing_id: str = "WING1",
    wing_total_span: float | None = None,
    wing_total_area: float | None = None,
    wing_total_chord: float | None = None,
    fuse_id: str = "FUSE1",
    fuse_length: float | None = None,
) -> ModuleType:
    fake = SimpleNamespace()  # see test_openvsp_importer for rationale

    parms: dict[tuple[str, str, str], float] = {}
    if wing_total_span is not None:
        parms[(wing_id, "TotalSpan", "WingGeom")] = wing_total_span
    if wing_total_area is not None:
        parms[(wing_id, "TotalProjectedArea", "WingGeom")] = wing_total_area
    if wing_total_chord is not None:
        parms[(wing_id, "TotalChord", "WingGeom")] = wing_total_chord
    if fuse_length is not None:
        parms[(fuse_id, "Length", "Design")] = fuse_length

    def _find_parm(container, parm, group):
        return f"{container}::{group}::{parm}" if (container, parm, group) in parms else ""

    def _get_parm_val(pid):
        if not pid:
            return 0.0
        container, group, parm = pid.split("::", 2)
        return parms.get((container, parm, group), 0.0)

    fake.FindParm = _find_parm
    fake.GetParmVal = _get_parm_val
    return cast(ModuleType, fake)


# ---------------------------------------------------------------------------
# compute_wing_metrics
# ---------------------------------------------------------------------------


class TestComputeWingMetrics:
    def test_full_span_for_symmetric_wing(self):
        w = _trapezoid_wing(span_half=5.0, symmetric=True)
        m = compute_wing_metrics(w)
        # Y goes 0..5 on the imported half — full span is 10.
        assert m.span_m == pytest.approx(10.0)

    def test_half_span_for_asymmetric_wing(self):
        w = _trapezoid_wing(span_half=5.0, symmetric=False)
        m = compute_wing_metrics(w)
        assert m.span_m == pytest.approx(5.0)

    def test_area_for_simple_trapezoid(self):
        # half-area = (1.0 + 0.5)/2 * 5.0 = 3.75; full = 7.5
        w = _trapezoid_wing(span_half=5.0, c_root=1.0, c_tip=0.5, symmetric=True)
        m = compute_wing_metrics(w)
        assert m.area_m2 == pytest.approx(7.5)

    def test_mac_for_uniform_chord(self):
        # constant chord = MAC
        w = _trapezoid_wing(span_half=5.0, c_root=1.0, c_tip=1.0)
        m = compute_wing_metrics(w)
        assert m.mac_m == pytest.approx(1.0)

    def test_mac_for_taper(self):
        # area-weighted mean — for linear taper the MAC is (c_root + c_tip)/2
        # only when the area weight is uniform, which it is here.
        w = _trapezoid_wing(c_root=1.0, c_tip=0.5)
        m = compute_wing_metrics(w)
        assert m.mac_m == pytest.approx(0.75)


# ---------------------------------------------------------------------------
# compute_fuselage_length
# ---------------------------------------------------------------------------


class TestComputeFuselageLength:
    def test_simple_fuselage_length(self):
        f = FuselageSchema(
            name="Fuselage",
            x_secs=[
                FuselageXSecSuperEllipseSchema(xyz=[0.0, 0, 0], a=0, b=0, n=2),
                FuselageXSecSuperEllipseSchema(xyz=[5.0, 0, 0], a=0.5, b=0.5, n=2),
                FuselageXSecSuperEllipseSchema(xyz=[10.0, 0, 0], a=0, b=0, n=2),
            ],
        )
        ap = AeroplaneSchema(name="X", fuselages=OrderedDict([("Fuselage", f)]))
        assert compute_fuselage_length(ap)["Fuselage"] == pytest.approx(10.0)

    def test_no_fuselages_yields_empty_dict(self):
        ap = AeroplaneSchema(name="X")
        assert compute_fuselage_length(ap) == {}


# ---------------------------------------------------------------------------
# validate_geometry — wing checks
# ---------------------------------------------------------------------------


class TestValidateWing:
    def test_within_tolerance_no_warnings(self):
        wing = _trapezoid_wing()  # span 10, area 7.5, MAC 0.75
        ap = AeroplaneSchema(name="X", wings=OrderedDict([("MainWing", wing)]))
        fake = _make_vsp(
            wing_id="W1",
            wing_total_span=10.0,
            wing_total_area=7.5,
            wing_total_chord=0.75,
        )
        w = validate_geometry(ap, fake, {"W1": "MainWing"})
        assert w == []

    def test_span_5pct_off_emits_warning(self):
        wing = _trapezoid_wing()
        ap = AeroplaneSchema(name="X", wings=OrderedDict([("MainWing", wing)]))
        fake = _make_vsp(
            wing_id="W1",
            wing_total_span=10.5,  # 5% off
            wing_total_area=7.5,
            wing_total_chord=0.75,
        )
        w = validate_geometry(ap, fake, {"W1": "MainWing"})
        assert len(w) == 1
        assert "span" in w[0].reason.lower()
        assert "WING" == w[0].component_type
        assert "MainWing" == w[0].component_name

    def test_area_8pct_off_emits_warning(self):
        wing = _trapezoid_wing()
        ap = AeroplaneSchema(name="X", wings=OrderedDict([("MainWing", wing)]))
        fake = _make_vsp(
            wing_id="W1",
            wing_total_span=10.0,
            wing_total_area=8.1,  # 8% off
            wing_total_chord=0.75,
        )
        w = validate_geometry(ap, fake, {"W1": "MainWing"})
        assert len(w) == 1
        assert "area" in w[0].reason.lower()

    def test_mac_2pct_off_emits_warning(self):
        wing = _trapezoid_wing()
        ap = AeroplaneSchema(name="X", wings=OrderedDict([("MainWing", wing)]))
        fake = _make_vsp(
            wing_id="W1",
            wing_total_span=10.0,
            wing_total_area=7.5,
            wing_total_chord=0.765,  # 2% off
        )
        w = validate_geometry(ap, fake, {"W1": "MainWing"})
        assert len(w) == 1
        assert "mac" in w[0].reason.lower()

    def test_vsp_metric_missing_skips_silently(self):
        wing = _trapezoid_wing()
        ap = AeroplaneSchema(name="X", wings=OrderedDict([("MainWing", wing)]))
        fake = _make_vsp(wing_id="W1")  # no metrics declared
        w = validate_geometry(ap, fake, {"W1": "MainWing"})
        assert w == []

    def test_custom_tolerance(self):
        """A relaxed tolerance suppresses small mismatches."""
        wing = _trapezoid_wing()
        ap = AeroplaneSchema(name="X", wings=OrderedDict([("MainWing", wing)]))
        fake = _make_vsp(
            wing_id="W1",
            wing_total_span=10.5,
            wing_total_area=7.5,
            wing_total_chord=0.75,
        )
        # 5% relative error in span; with rel_tol=0.1 (10%), no warning.
        w = validate_geometry(ap, fake, {"W1": "MainWing"}, rel_tol=0.1)
        assert w == []


# ---------------------------------------------------------------------------
# validate_geometry — fuselage check
# ---------------------------------------------------------------------------


class TestValidateFuselage:
    def test_fuselage_length_within_tolerance(self):
        fuse = FuselageSchema(
            name="Fuselage",
            x_secs=[
                FuselageXSecSuperEllipseSchema(xyz=[0.0, 0, 0], a=0, b=0, n=2),
                FuselageXSecSuperEllipseSchema(xyz=[10.0, 0, 0], a=0, b=0, n=2),
            ],
        )
        ap = AeroplaneSchema(name="X", fuselages=OrderedDict([("Fuselage", fuse)]))
        fake = _make_vsp(fuse_id="F1", fuse_length=10.0)
        w = validate_geometry(ap, fake, wing_gid_map={}, fuselage_gid_map={"F1": "Fuselage"})
        assert w == []

    def test_fuselage_length_3pct_off_emits_warning(self):
        fuse = FuselageSchema(
            name="Fuselage",
            x_secs=[
                FuselageXSecSuperEllipseSchema(xyz=[0.0, 0, 0], a=0, b=0, n=2),
                FuselageXSecSuperEllipseSchema(xyz=[10.0, 0, 0], a=0, b=0, n=2),
            ],
        )
        ap = AeroplaneSchema(name="X", fuselages=OrderedDict([("Fuselage", fuse)]))
        fake = _make_vsp(fuse_id="F1", fuse_length=10.3)
        w = validate_geometry(ap, fake, wing_gid_map={}, fuselage_gid_map={"F1": "Fuselage"})
        assert len(w) == 1
        assert "length" in w[0].reason.lower()
        assert "FUSELAGE" == w[0].component_type
