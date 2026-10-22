"""Tests for the CRRCSim exporter (gh-1195): unit conversion, guards, XML shape, polar post-processing.

The conversion tests use values from the stock wasabi.xml, whose header documents the hand mapping
from AVL ST output (the reference the exporter must reproduce). One slow test runs AVL +
AeroBuildup on BRYAN end to end.
"""

from __future__ import annotations

import dataclasses
import pathlib
import sys
import xml.etree.ElementTree as ET

import numpy as np
import pytest

CRRC_DIR = pathlib.Path(__file__).resolve().parents[1]
sys.path.insert(0, str(CRRC_DIR))

import crrcsim_model as cm  # noqa: E402
import polar  # noqa: E402

# every attribute larcsim.cpp (LoadFromXML) reads without a default
REQUIRED_AERO = {
    "ref": {"chord", "span", "area", "speed"},
    "misc": {"Alpha_0", "eta_loc", "CG_arm", "span_eff"},
    "m": {"Cm_0", "Cm_a", "Cm_q", "Cm_de"},
    "lift": {"CL_0", "CL_max", "CL_min", "CL_a", "CL_q", "CL_de", "CL_drop", "CL_CD0"},
    "drag": {"CD_prof", "Uexp_CD", "CD_stall", "CD_CLsq", "CD_AIsq", "CD_ELsq"},
    "Y": {"CY_b", "CY_p", "CY_r", "CY_dr", "CY_da"},
    "l": {"Cl_b", "Cl_p", "Cl_r", "Cl_dr", "Cl_da"},
    "n": {"Cn_b", "Cn_p", "Cn_r", "Cn_dr", "Cn_da"},
}


def numbers(**over) -> cm.AeroNumbers:
    base = dict(
        c_ref=0.1328, b_ref=0.546, s_ref=0.0699, v_ref=7.82,
        alpha_0_rad=0.027, cl_0=0.5656, cm_0=0.0, span_eff=0.95, eta_loc=0.45, cg_arm=0.064,
        cl_a=4.6, cl_q=7.2, cm_a=-0.077, cm_q=-6.2,
        cy_b=-0.26, cy_p=0.1, cy_r=0.28, cl_b=-0.066, cl_p=-0.35, cl_r=0.136,
        cn_b=0.122, cn_p=-0.038, cn_r=-0.162,
        cl_d_elevator=0.0074, cm_d_elevator=-0.0159,
        cy_d_aileron=-7e-6, cl_d_aileron=-0.0049, cn_d_aileron=-8.5e-5,
        cy_d_rudder=-0.0018, cl_d_rudder=-0.00015, cn_d_rudder=0.0011,
        cl_max=1.33, cl_min=-0.5, cl_drop=0.28, cl_cd0=0.24, cd_prof=0.043, uexp_cd=-0.47,
        cd_stall=0.16, cd_clsq=0.047, cd_aisq=0.04, cd_elsq=0.0,
    )  # fmt: skip
    return cm.AeroNumbers(**(base | over))


SRC = {
    k: "test"
    for k in ("ref", "trim", "eta_loc", "cg_arm", "span_eff", "stall", "drag", "aileron_drag")
}
THROWS = cm.Throws(elevator_deg=10.0, aileron_deg=12.0, rudder_deg=15.0)


# --- unit conversion -----------------------------------------------------------------------------
def test_control_derivative_reproduces_wasabi_hand_mapping():
    # wasabi.xml header: AVL per deg, travel de=8, dr=20, da=15  ->  Cm_de -0.600, CY_dr 0.154, Cl_da 0.315
    assert cm.control_derivative(-0.0375, 8, cm.SIGN_ELEVATOR) == pytest.approx(-0.600, abs=1e-3)
    assert cm.control_derivative(0.0134, 8, cm.SIGN_ELEVATOR) == pytest.approx(0.214, abs=1e-3)
    assert cm.control_derivative(-0.00384, 20, cm.SIGN_RUDDER) == pytest.approx(0.154, abs=1e-3)
    assert cm.control_derivative(-0.0105, 15, cm.SIGN_AILERON) == pytest.approx(0.315, abs=1e-3)
    assert cm.control_derivative(0.00146, 20, cm.SIGN_RUDDER) == pytest.approx(-0.0584, abs=1e-3)


def test_control_derivative_is_linear_in_travel():
    one = cm.control_derivative(0.01, 5)
    assert cm.control_derivative(0.01, 10) == pytest.approx(2 * one)


def test_aero_entries_scale_with_the_throws():
    base = {(e.path, e.attr): e.value for e in cm.aero_entries(numbers(), THROWS, SRC)}
    doubled = cm.Throws(20.0, 24.0, 30.0)
    big = {(e.path, e.attr): e.value for e in cm.aero_entries(numbers(), doubled, SRC)}
    for key in (("aero/m", "Cm_de"), ("aero/l", "Cl_da"), ("aero/n", "Cn_dr"), ("aero/Y", "CY_dr")):
        assert big[key] == pytest.approx(2 * base[key])


def test_aero_entries_signs_follow_crrcsim_convention():
    d = {(e.path, e.attr): e.value for e in cm.aero_entries(numbers(), THROWS, SRC)}
    assert d[("aero/m", "Cm_de")] < 0 < d[("aero/lift", "CL_de")]
    assert d[("aero/l", "Cl_da")] > 0
    assert d[("aero/n", "Cn_dr")] < 0 < d[("aero/Y", "CY_dr")]


def test_wrong_physical_sign_fails_loudly():
    with pytest.raises(cm.ExportError, match="Cm_de < 0"):
        cm.aero_entries(numbers(cm_d_elevator=+0.0159), THROWS, SRC)
    with pytest.raises(cm.ExportError, match="Cl_p < 0"):
        cm.aero_entries(numbers(cl_p=+0.35), THROWS, SRC)


# --- CL_0 guard ----------------------------------------------------------------------------------
@pytest.mark.parametrize("bad", [0.0, 1e-4, -0.005, float("nan"), float("inf")])
def test_cl0_guard_rejects_zero_and_tiny_and_nonfinite(bad):
    with pytest.raises(cm.ExportError, match="CL_0"):
        cm.check_cl0(bad)


def test_cl0_guard_is_applied_when_building_entries():
    with pytest.raises(cm.ExportError, match="CL_0"):
        cm.aero_entries(numbers(cl_0=0.0), THROWS, SRC)


def test_cl0_guard_accepts_a_trim_value():
    assert cm.check_cl0(0.5656) == 0.5656


# --- throws are required --------------------------------------------------------------------------
def test_throws_have_no_defaults():
    with pytest.raises(TypeError):
        cm.Throws()  # type: ignore[call-arg]
    with pytest.raises(TypeError):
        cm.Throws(elevator_deg=10.0)  # type: ignore[call-arg]


@pytest.mark.parametrize("bad", [0.0, -3.0, float("nan"), None, "14"])
def test_throws_reject_non_positive_or_non_numeric(bad):
    with pytest.raises(cm.ExportError):
        cm.Throws(elevator_deg=bad, aileron_deg=10.0, rudder_deg=10.0)  # type: ignore[arg-type]


def test_cli_requires_every_throw_and_the_speed(capsys):
    import export_bryan

    for argv in (
        ["--speed", "7.8", "--out", "x.xml"],
        [
            "--speed",
            "7.8",
            "--elevator-throw-deg",
            "10",
            "--aileron-throw-deg",
            "10",
            "--out",
            "x.xml",
        ],
        [
            "--elevator-throw-deg",
            "10",
            "--aileron-throw-deg",
            "10",
            "--rudder-throw-deg",
            "10",
            "--out",
            "x.xml",
        ],
    ):
        with pytest.raises(SystemExit) as exc:
            export_bryan.main(argv)
        assert exc.value.code == 2
    assert "required" in capsys.readouterr().err


# --- inertia -------------------------------------------------------------------------------------
RADII = cm.GyrationRadii(0.25, 0.38, 0.46, 2.0, "test source")


def test_inertia_is_mass_times_radius_squared():
    i = cm.estimate_inertia(0.151, 0.546, 0.469, RADII)
    e = 0.5 * (0.546 + 0.469)
    assert i.ixx == pytest.approx(0.151 * (0.25 * 0.546) ** 2)
    assert i.iyy == pytest.approx(0.151 * (0.38 * 0.469) ** 2)
    assert i.izz == pytest.approx(0.151 * (0.46 * e) ** 2)
    assert i.ixz == pytest.approx(0.5 * (i.izz - i.ixx) * np.tan(np.radians(4.0)))
    assert "test source" in i.basis


def test_inertia_sensitivity_band_brackets_the_estimate():
    i = cm.estimate_inertia(0.151, 0.546, 0.469, RADII)
    for key, (lo, hi) in cm.inertia_sensitivity(i).items():
        assert lo < getattr(i, key) < hi


# --- XML -----------------------------------------------------------------------------------------
def render(**over) -> str:
    aero = cm.aero_entries(numbers(), THROWS, SRC)
    inertia = cm.estimate_inertia(0.151, 0.546, 0.469, RADII)
    kw = dict(
        name="BRYAN", description="d", changelog="c", aero=aero, mass_kg=0.151, inertia=inertia,
        inertia_comment="DECLARED ESTIMATE test", power_xml="    <power units=\"1\"></power>",
        graphics_model="mav.ac", wheels=[(0.1, 0.0, 0.02), (-0.2, 0.27, 0.0)],
        wheel_spring=(1000.0, 2.0, 30.0), cg=(0.0, 0.0, 0.0), comments=["hello & <world>"],
    )  # fmt: skip
    return cm.render_xml(**(kw | over))


def test_xml_is_well_formed_and_carries_every_attribute_the_simulator_reads():
    root = ET.fromstring(render().encode("iso-8859-1"))
    assert root.tag == "CRRCSim_airplane" and root.get("version") == "2"
    aero = root.find("aero")
    assert aero is not None and aero.get("units") == "1"
    for tag, attrs in REQUIRED_AERO.items():
        node = aero.find(tag)
        assert node is not None, tag
        assert attrs <= set(node.attrib), (tag, attrs - set(node.attrib))
        for a in attrs:
            float(node.attrib[a])  # numeric


def test_xml_has_mass_inertia_wheels_cg_and_the_estimate_comment():
    text = render()
    root = ET.fromstring(text.encode("iso-8859-1"))
    mi = root.find("config/mass_inertia")
    assert mi is not None
    assert set(mi.attrib) >= {"Mass", "I_xx", "I_yy", "I_zz", "I_xz", "units"}
    assert float(mi.attrib["Mass"]) == pytest.approx(0.151)
    wheels = root.findall("wheels/wheel")
    assert len(wheels) == 2
    assert all(w.get("percent_brake") == "0" for w in wheels)  # RC equipment: no wheel brakes
    assert root.find("wheels").get("units") == "1"
    assert root.find("CG") is not None
    assert "DECLARED ESTIMATE" in text
    assert root.find("graphics").get("model") == "mav.ac"


def test_xml_escapes_comment_text():
    text = render()
    assert "hello &amp; &lt;world&gt;" in text
    ET.fromstring(text.encode("iso-8859-1"))


def test_mapping_table_lists_every_entry_with_its_source():
    entries = cm.aero_entries(numbers(), THROWS, SRC)
    md = cm.render_mapping_md("t", [("aero", entries)], "notes")
    for e in entries:
        assert f"`{e.path}` `{e.attr}`" in md
    assert "AVL ST `Cma`" in md


# --- polar post-processing -----------------------------------------------------------------------
def synthetic_polar():
    a = np.arange(-20.0, 30.5, 0.5)
    cl = np.where(a <= 12, 0.1 * (a + 4.0), 0.0)
    cl = np.where(a > 12, 1.6 - 0.05 * (a - 12), cl)
    cl = np.where(a > 16, 1.4 - 0.0 * a, cl)  # plateau at 1.4 after a drop from 1.6 at 12
    cl = np.where(a < -11, -0.7, cl)  # negative-side stall plateau
    cd = 0.04 + 0.03 * (cl - 0.2) ** 2 + cl**2 / (np.pi * 4.0 * 0.9)
    cd = cd + 0.02 * np.clip(a - 12, 0, None)  # separated-flow drag rise behind the peak
    return a, cl, cd


def test_first_peak_ignores_negative_side_bumps_and_lower_plateau():
    a, cl, _ = synthetic_polar()
    cl = cl + 0.02 * np.sin(a * 3) * (a < -5)  # bumps on the negative side
    k = polar.first_peak_index(cl)
    assert a[k] == pytest.approx(12.0)


def test_stall_data_reports_peak_knee_and_drop():
    a, cl, cd = synthetic_polar()
    s = polar.stall_data(a, cl, cd)
    assert s.alpha_peak_deg == pytest.approx(12.0)
    assert s.cl_max == pytest.approx(1.6)
    assert s.cl_min < -0.5
    assert s.cl_drop == pytest.approx(0.2, abs=0.05)
    assert s.cd_stall > 0


def test_profile_fit_recovers_known_parabola():
    a = np.linspace(-2, 10, 60)
    cl = 0.1 * (a + 4)
    ar, e = 4.0, 0.9
    cd = 0.04 + 0.03 * (cl - 0.2) ** 2 + polar.induced_cd(cl, ar, e)
    fit = polar.fit_profile_drag(a, cl, cd, ar, e, 0.0, 1.0, alpha_max=10)
    assert fit.cd_prof == pytest.approx(0.04, rel=1e-6)
    assert fit.cd_clsq == pytest.approx(0.03, rel=1e-6)
    assert fit.cl_cd0 == pytest.approx(0.2, rel=1e-6)


def test_profile_fit_refuses_concave_drag():
    a = np.linspace(-2, 10, 60)
    cl = 0.1 * (a + 4)
    cd = 0.1 - 0.02 * (cl - 0.5) ** 2
    with pytest.raises(polar.PolarError, match="convex"):
        polar.fit_profile_drag(a, cl, cd, 4.0, 0.9, 0.0, 1.0, alpha_max=10)


def test_profile_fit_excludes_post_stall_points():
    a, cl, cd = synthetic_polar()
    fit = polar.fit_profile_drag(a, cl, cd, 4.0, 0.9, 0.0, 1.4, alpha_max=12.0)
    assert fit.residual_rms < 1e-6


def test_reynolds_exponent_is_the_loglog_slope():
    v = np.array([4.0, 8.0, 16.0])
    assert polar.reynolds_exponent(v, 0.05 * (v / 8.0) ** -0.4) == pytest.approx(-0.4)


def test_alpha_at_cl_interpolates_on_the_prestall_branch_only():
    a, cl, _ = synthetic_polar()
    assert polar.alpha_at_cl(a, cl, 0.8) == pytest.approx(4.0)
    with pytest.raises(polar.PolarError):
        polar.alpha_at_cl(a, cl, 5.0)


# --- end to end ----------------------------------------------------------------------------------
@pytest.mark.slow
@pytest.mark.aero
def test_bryan_export_end_to_end(tmp_path):
    pytest.importorskip("aerosandbox")
    pytest.importorskip("avl_binary")
    import export_bryan

    out = tmp_path / "BRYAN.xml"
    md = tmp_path / "MAPPING.md"
    rc = export_bryan.main(
        ["--speed", "7.82", "--elevator-throw-deg", "14", "--aileron-throw-deg", "15",
         "--rudder-throw-deg", "20", "--out", str(out), "--mapping-md", str(md)]
    )  # fmt: skip
    assert rc == 0
    root = ET.fromstring(out.read_bytes())
    aero = root.find("aero")
    lift = aero.find("lift").attrib
    assert float(lift["CL_0"]) == pytest.approx(0.5656, abs=0.01)  # m g / (q S_ref) at 7.82 m/s
    assert float(aero.find("m").attrib["Cm_a"]) < 0
    assert float(aero.find("ref").attrib["area"]) == pytest.approx(0.0699, abs=1e-3)
    assert float(root.find("config/mass_inertia").attrib["Mass"]) == pytest.approx(0.151)
    assert "DECLARED ESTIMATE" in out.read_text(encoding="iso-8859-1")
    assert "`aero/lift` `CL_0`" in md.read_text()


@pytest.mark.slow
@pytest.mark.aero
def test_avl_control_derivatives_are_per_degree_and_aileron_sign_is_inverted(tmp_path):
    """Finite difference over 1 deg of AVL deflection must equal the ST label the exporter reads."""
    pytest.importorskip("aerosandbox")
    avl_binary = pytest.importorskip("avl_binary")
    import re
    import subprocess

    import aerosandbox as asb
    import bryan_aero as ba

    b = ba.build_bryan()
    geom = ba.write_avl_geometry(
        b, tmp_path, asb.OperatingPoint(b.atmosphere, velocity=7.8, alpha=1)
    )

    def run(control: str, deg: float) -> dict[str, float]:
        cmds = ["oper", "a a 1.5", f"{control} {control} {deg}", "x", "", "quit"]
        out = subprocess.run(
            [str(avl_binary.avl_path()), str(geom)], input="\n".join(cmds) + "\n",
            capture_output=True, text=True, cwd=tmp_path, timeout=60, check=False,
        ).stdout  # fmt: skip
        return {
            k: float(re.findall(rf"\b{k}\s*=\s*(-?[\d.]+)", out)[0]) for k in ("Cmtot", "Cltot")
        }

    d_elevator = run("d2", 1.0)["Cmtot"] - run("d2", 0.0)["Cmtot"]
    d_aileron = run("d1", 1.0)["Cltot"] - run("d1", 0.0)["Cltot"]
    st = ba.run_avl_trimmed(b, 0.5656, 7.82)
    assert d_elevator == pytest.approx(st["Cmd02"], rel=0.03)
    assert d_aileron == pytest.approx(st["Cld01"], rel=0.03)
    assert st["Cld01"] < 0  # +AVL aileron rolls left; CRRCSim +aileron rolls right -> SIGN_AILERON


def test_dataclasses_are_frozen():
    with pytest.raises(dataclasses.FrozenInstanceError):
        THROWS.elevator_deg = 1.0  # type: ignore[misc]


# --- component build-up ---------------------------------------------------------------------------
def test_buildup_point_masses_match_analytic_values():
    import inertia_buildup as ib

    pts = [
        ib.PointMass("a", 1.0, 0.5, 0.0, 0.0, "t"),  # geometry x aft
        ib.PointMass("b", 1.0, -0.5, 0.0, 0.0, "t"),
        ib.PointMass("c", 2.0, 0.0, 0.3, 0.0, "t"),
    ]
    r = ib.buildup(pts, [])
    assert r.cg_geometry == pytest.approx((0.0, 0.15, 0.0))
    # about the CG: y offsets are -0.15 (a, b) and +0.15 (c)
    assert r.ixx == pytest.approx(2 * 0.15**2 + 2 * 0.15**2)
    assert r.iyy == pytest.approx(2 * 0.5**2)
    assert r.izz == pytest.approx(2 * (0.5**2 + 0.15**2) + 2 * 0.15**2)
    assert r.ixz == pytest.approx(0.0)


def test_buildup_rod_adds_its_own_inertia_and_conserves_mass():
    import inertia_buildup as ib

    r = ib.buildup([], [ib.Rod("f", 0.06, 0.0, 0.5, 0.0, "t")])
    assert r.iyy == pytest.approx(0.06 * 0.5**2 / 12)
    assert r.izz == pytest.approx(r.iyy)
    assert r.ixx == pytest.approx(0.0)
    assert r.mass_kg == pytest.approx(0.06)


def test_bryan_buildup_is_below_the_radius_of_gyration_upper_bound():
    pytest.importorskip("aerosandbox")
    import bryan_aero as ba
    import export_bryan

    inertia, basis, bound = export_bryan.bryan_inertia(ba.build_bryan())
    assert inertia.ixz == 0.0 and "declared" in basis.lower()
    for k in ("ixx", "iyy", "izz"):
        assert 0 < getattr(inertia, k) <= getattr(bound, k)


# --- AC3D model ----------------------------------------------------------------------------------
GEO_DIR = CRRC_DIR.parents[1] / "canon_checks" / "reference_fleet" / "bryan"


@pytest.fixture(scope="module")
def ac_model():
    import json

    import ac3d

    geo = json.loads((GEO_DIR / "bryan.airplane.json").read_text())
    af = {
        "./bryan_profil.dat": ac3d.read_dat(GEO_DIR / "bryan_profil.dat"),
        "./bryan_platte.dat": ac3d.read_dat(GEO_DIR / "bryan_platte.dat"),
    }
    meshes, hinges = ac3d.build_model(geo, af)
    return geo, meshes, hinges, ac3d.render_ac(meshes)


def test_ac_is_well_formed_and_counts_match_the_header(ac_model):
    _, meshes, _, text = ac_model
    lines = text.splitlines()
    assert lines[0] == "AC3Db"
    assert sum(1 for ln in lines if ln.startswith("OBJECT poly")) == len(meshes)
    assert sum(len(m.verts) for m in meshes) == sum(
        int(ln.split()[1]) for ln in lines if ln.startswith("numvert")
    )
    n_surf = sum(len(m.faces) for m in meshes)
    assert n_surf == sum(1 for ln in lines if ln.startswith("SURF"))
    for m in meshes:  # every face index points into its own object's vertex list
        assert all(0 <= i < len(m.verts) for f in m.faces for i in f)
        assert all(len(f) >= 3 for f in m.faces)


def test_ac_span_and_length_match_the_geometry_and_axes(ac_model):
    import numpy as np

    geo, _, _, text = ac_model
    import ac3d

    v = np.array([p for vs in ac3d.parse_ac(text).values() for p in vs])
    span_geo = 2 * max(s["xyz_le"][1] for s in geo["wings"]["Tragflaeche"]["x_secs"])
    assert v[:, 0].max() - v[:, 0].min() == pytest.approx(span_geo, abs=2e-3)  # AC3D X = lateral
    x_all = [s["xyz_le"][0] + s["chord"] for w in geo["wings"].values() for s in w["x_secs"]]
    x_all += [s["xyz"][0] for f in geo["fuselages"].values() for s in f["x_secs"]]
    length_geo = max(x_all) - min(s["xyz"][0] for s in geo["fuselages"]["Rumpf"]["x_secs"])
    assert v[:, 2].max() - v[:, 2].min() == pytest.approx(
        length_geo, abs=3.5e-3
    )  # AC3D Z = forward; thinning drops sliver sections (<= 3 mm)
    assert v[:, 2].max() == pytest.approx(geo["xyz_ref"][0], abs=1e-3)  # nose at x = 0, CG origin
    assert v[:, 1].max() > 0.05  # fin rises above the CG (AC3D Y = up)


def test_ac_has_the_four_animated_control_surface_objects(ac_model):
    _, meshes, hinges, _ = ac_model
    names = {m.name for m in meshes}
    assert {
        "aileron_r",
        "aileron_l",
        "elevator",
        "rudder",
        "wing",
        "htail",
        "fin",
        "fuselage",
    } <= names
    assert {h.object_name for h in hinges} == {"aileron_r", "aileron_l", "elevator", "rudder"}


def test_hinge_axes_give_the_crrcsim_stick_senses(ac_model):
    """Right-hand rule about p1 -> p2: +elevator axis +y (TE down), +rudder axis +z/down (TE left),
    +aileron: right axis -y (TE up), left axis +y (TE down) = roll right."""
    _, _, hinges, _ = ac_model
    ax = {h.object_name: [b - a for a, b in zip(h.p1, h.p2, strict=True)] for h in hinges}
    assert ax["elevator"][1] > 0.1 and abs(ax["elevator"][0]) < 1e-3
    assert ax["rudder"][2] > 0.03 and abs(ax["rudder"][1]) < 1e-3
    assert ax["aileron_r"][1] < 0 < ax["aileron_l"][1]


def test_animations_xml_references_existing_objects_and_uses_the_throws(ac_model):
    import ac3d

    _, meshes, hinges, _ = ac_model
    xml = ac3d.animations_xml(hinges, {"AILERON": 32.0, "ELEVATOR": 14.0, "RUDDER": 35.0})
    root = ET.fromstring(xml)
    objs = {a.find("object").get("name"): a for a in root.findall("animation")}
    assert set(objs) <= {m.name for m in meshes}
    assert float(objs["elevator"].find("object").get("max_angle")) == pytest.approx(
        np.radians(14.0), abs=1e-4
    )
    assert float(objs["rudder"].find("object").get("max_angle")) == pytest.approx(
        np.radians(35.0), abs=1e-4
    )
    assert all(len(a.findall("hinge")) == 2 for a in root.findall("animation"))
