"""CRRCSim airplane XML (version 2) from analysed numbers: pure conversion, no solver imports.

Every XML attribute is an `Entry(path, attr, value, source)`; the XML file and the markdown mapping
table are both rendered from the same entry list, so the table cannot drift from the file.

Conventions (CRRCSim larcsim.cpp, verified against wasabi.xml / supra_a.xml):
  * stick inputs run -0.5 .. +0.5, so  der_CRRCSim = der_AVL[/deg] * travel_deg / 0.5
  * positive elevator = trailing edge down (same as AVL): Cm_de < 0, CL_de > 0
  * positive aileron  = roll right: Cl_da > 0; AVL's sign is inverted (AVL +d = right TE down)
  * positive rudder   = nose left (left arrow key = +0.05): CY_dr > 0, Cn_dr < 0; AVL's sign inverted
  * Cl_r and Cn_p are scaled by CL_wing / CL_0 inside the simulator: CL_0 must not be 0
"""

from __future__ import annotations

import math
from dataclasses import dataclass
from typing import Any
from xml.sax.saxutils import escape, quoteattr

STICK_FULL = 0.5  # CRRCSim stick input at full deflection
# CL_0 below this makes Cl_r_mod = Cl_r * CL_wing / CL_0 and Cn_p_mod blow up
CL_0_MIN = 0.01
# AVL control derivative sign -> CRRCSim stick sign (see module docstring)
SIGN_ELEVATOR, SIGN_AILERON, SIGN_RUDDER = +1.0, -1.0, -1.0
SLUG_NOTE = "SI throughout (units=1)"


class ExportError(RuntimeError):
    """An input is missing or violates a CRRCSim precondition; the exporter refuses to guess."""


@dataclass(frozen=True)
class Throws:
    """Full-stick control travel in degrees, each direction.

    Required inputs (maintainer rule: deflections are parameters, the geometry's stops are a
    construction result): no defaults, every value positive."""

    elevator_deg: float
    aileron_deg: float
    rudder_deg: float

    def __post_init__(self) -> None:
        for name in ("elevator_deg", "aileron_deg", "rudder_deg"):
            v = getattr(self, name)
            if not (isinstance(v, int | float) and math.isfinite(v) and v > 0):
                raise ExportError(
                    f"control throw {name} must be a positive number of degrees, got {v!r}"
                )


@dataclass(frozen=True)
class Entry:
    path: str  # element path below <CRRCSim_airplane>, e.g. "aero/lift"
    attr: str
    value: float | str
    source: str


@dataclass(frozen=True)
class GyrationRadii:
    """Dimensionless radii of gyration and principal-axis tilt (a declared estimate)."""

    rx_over_b: float
    ry_over_l: float
    rz_over_e: float  # e = (b + l) / 2
    xz_tilt_deg: float
    source: str


@dataclass(frozen=True)
class Inertia:
    ixx: float
    iyy: float
    izz: float
    ixz: float
    basis: str


def control_derivative(avl_per_deg: float, travel_deg: float, sign: float = 1.0) -> float:
    """AVL control derivative [1/deg] -> CRRCSim derivative per unit stick (full stick = 0.5)."""
    if travel_deg <= 0:
        raise ExportError(f"control travel must be positive, got {travel_deg}")
    return sign * avl_per_deg * travel_deg / STICK_FULL


def check_cl0(cl_0: float) -> float:
    """CL_0 scales Cl_r and Cn_p in the simulator (x CL_wing / CL_0): zero or tiny is fatal."""
    if not math.isfinite(cl_0) or abs(cl_0) < CL_0_MIN:
        raise ExportError(
            f"CL_0 = {cl_0!r} is (near) zero: CRRCSim scales Cl_r and Cn_p by CL/CL_0. "
            f"Choose a trim point with |CL| >= {CL_0_MIN}."
        )
    return cl_0


def estimate_inertia(
    mass_kg: float, span_m: float, length_m: float, radii: GyrationRadii
) -> Inertia:
    """I = m R^2 with R from dimensionless radii; I_xz from the principal-axis tilt:
    I_xz = 0.5 (I_zz - I_xx) tan(2 eps); the sign is a declared choice (stock models use both signs)."""
    e = 0.5 * (span_m + length_m)
    ixx = mass_kg * (radii.rx_over_b * span_m) ** 2
    iyy = mass_kg * (radii.ry_over_l * length_m) ** 2
    izz = mass_kg * (radii.rz_over_e * e) ** 2
    ixz = 0.5 * (izz - ixx) * math.tan(2 * math.radians(radii.xz_tilt_deg))
    return Inertia(
        ixx,
        iyy,
        izz,
        ixz,
        f"R_x/b={radii.rx_over_b}, R_y/l={radii.ry_over_l}, R_z/e={radii.rz_over_e} "
        f"(b={span_m:.4f} m, l={length_m:.4f} m, e={e:.4f} m), tilt {radii.xz_tilt_deg} deg; "
        f"{radii.source}",
    )


def inertia_sensitivity(inertia: Inertia, factor: float = 1.5) -> dict[str, tuple[float, float]]:
    """I scaled by 1/factor .. factor (R scales with sqrt(factor)): the range a pilot should expect
    the estimate to be wrong by."""
    return {
        k: (getattr(inertia, k) / factor, getattr(inertia, k) * factor)
        for k in ("ixx", "iyy", "izz")
    }


# ---------------------------------------------------------------------------------------------
@dataclass(frozen=True)
class AeroNumbers:
    """All aerodynamic inputs to the XML, SI, per-radian derivatives, AVL control derivatives per deg."""

    # reference (projected onto the x-y plane)
    c_ref: float
    b_ref: float
    s_ref: float
    v_ref: float
    # trim point (baked into stick-zero)
    alpha_0_rad: float
    cl_0: float
    cm_0: float
    span_eff: float
    eta_loc: float
    cg_arm: float
    # AVL ST
    cl_a: float
    cl_q: float
    cm_a: float
    cm_q: float
    cy_b: float
    cy_p: float
    cy_r: float
    cl_b: float
    cl_p: float
    cl_r: float
    cn_b: float
    cn_p: float
    cn_r: float
    cl_d_elevator: float  # CLd02 [1/deg]
    cm_d_elevator: float  # Cmd02
    cy_d_aileron: float  # CYd01
    cl_d_aileron: float  # Cld01
    cn_d_aileron: float  # Cnd01
    cy_d_rudder: float  # CYd03
    cl_d_rudder: float  # Cld03
    cn_d_rudder: float  # Cnd03
    # polar
    cl_max: float
    cl_min: float
    cl_drop: float
    cl_cd0: float
    cd_prof: float
    uexp_cd: float
    cd_stall: float
    cd_clsq: float
    cd_aisq: float
    cd_elsq: float


def aero_entries(a: AeroNumbers, t: Throws, src: dict[str, str]) -> list[Entry]:
    """The <aero> block. `src` gives the source text per group (keys used below)."""
    check_cl0(a.cl_0)
    de, da, dr = (
        control_derivative(a.cl_d_elevator, t.elevator_deg, SIGN_ELEVATOR),
        control_derivative(a.cy_d_aileron, t.aileron_deg, SIGN_AILERON),
        control_derivative(a.cy_d_rudder, t.rudder_deg, SIGN_RUDDER),
    )
    cm_de = control_derivative(a.cm_d_elevator, t.elevator_deg, SIGN_ELEVATOR)
    cl_da = control_derivative(a.cl_d_aileron, t.aileron_deg, SIGN_AILERON)
    cn_da = control_derivative(a.cn_d_aileron, t.aileron_deg, SIGN_AILERON)
    cl_dr = control_derivative(a.cl_d_rudder, t.rudder_deg, SIGN_RUDDER)
    cn_dr = control_derivative(a.cn_d_rudder, t.rudder_deg, SIGN_RUDDER)
    # physical sign guards: a violated one means the AVL axis/sign assumption above is wrong
    for label, ok in (
        ("Cm_de < 0", cm_de < 0),
        ("CL_de > 0", de > 0),
        ("Cl_da > 0", cl_da > 0),
        ("Cn_dr < 0", cn_dr < 0),
        ("CY_dr > 0", dr > 0),
        ("Cm_a < 0", a.cm_a < 0),
        ("Cl_p < 0", a.cl_p < 0),
        ("Cn_r < 0", a.cn_r < 0),
    ):
        if not ok:
            raise ExportError(
                f"sign check failed: {label} (control-sign mapping or AVL run is off)"
            )
    ele = f"AVL ST d02 (elevator) x {t.elevator_deg} deg / {STICK_FULL}"
    ail = f"AVL ST d01 (aileron) x {t.aileron_deg} deg / {STICK_FULL}, sign inverted (AVL +d = right TE down)"
    rud = f"AVL ST d03 (rudder) x {t.rudder_deg} deg / {STICK_FULL}, sign inverted (CRRCSim +rudder = nose left)"
    E = Entry
    return [
        E("aero/ref", "chord", a.c_ref, src["ref"] + " (MAC, x-y projection)"),
        E("aero/ref", "span", a.b_ref, src["ref"] + " (y extent)"),
        E("aero/ref", "area", a.s_ref, src["ref"] + " (x-y projected planform)"),
        E("aero/ref", "speed", a.v_ref, src["trim"] + ": speed at which CD_prof is valid"),
        E(
            "aero/misc",
            "Alpha_0",
            a.alpha_0_rad,
            "AVL Alpha at the trim point [rad]; trim elevator baked into stick zero",
        ),
        E("aero/misc", "eta_loc", a.eta_loc, src["eta_loc"]),
        E("aero/misc", "CG_arm", a.cg_arm, src["cg_arm"]),
        E("aero/misc", "span_eff", a.span_eff, src["span_eff"]),
        E("aero/m", "Cm_0", a.cm_0, "AVL Cmtot at the trim point (0 by the elevator trim)"),
        E("aero/m", "Cm_a", a.cm_a, "AVL ST `Cma` [1/rad]"),
        E("aero/m", "Cm_q", a.cm_q, "AVL ST `Cmq` (q c/2V)"),
        E("aero/m", "Cm_de", cm_de, "Cmd02: " + ele),
        E("aero/lift", "CL_0", a.cl_0, "AVL CLtot at the trim point (guard: |CL_0| >= 0.01)"),
        E("aero/lift", "CL_max", a.cl_max, src["stall"] + ": first C_L peak"),
        E("aero/lift", "CL_min", a.cl_min, src["stall"] + ": negative stall knee"),
        E("aero/lift", "CL_a", a.cl_a, "AVL ST `CLa` [1/rad]"),
        E("aero/lift", "CL_q", a.cl_q, "AVL ST `CLq` (q c/2V)"),
        E("aero/lift", "CL_de", de, "CLd02: " + ele),
        E("aero/lift", "CL_drop", a.cl_drop, src["stall"] + ": CL_max - mean post-stall plateau"),
        E("aero/lift", "CL_CD0", a.cl_cd0, src["drag"] + ": vertex of the profile parabola"),
        E("aero/drag", "CD_prof", a.cd_prof, src["drag"] + ": parabola minimum at v_ref"),
        E("aero/drag", "Uexp_CD", a.uexp_cd, src["drag"] + ": ln(CD_prof) vs ln(V)"),
        E("aero/drag", "CD_stall", a.cd_stall, src["stall"] + ": CD plateau - CD at the peak"),
        E("aero/drag", "CD_CLsq", a.cd_clsq, src["drag"] + ": parabola curvature"),
        E("aero/drag", "CD_AIsq", a.cd_aisq, src["aileron_drag"]),
        E("aero/drag", "CD_ELsq", a.cd_elsq, "0: CRRCSim documents non-zero only for elevons"),
        E("aero/Y", "CY_b", a.cy_b, "AVL ST `CYb`"),
        E("aero/Y", "CY_p", a.cy_p, "AVL ST `CYp` (p b/2V)"),
        E("aero/Y", "CY_r", a.cy_r, "AVL ST `CYr` (r b/2V)"),
        E("aero/Y", "CY_dr", dr, "CYd03: " + rud),
        E(
            "aero/Y",
            "CY_da",
            control_derivative(a.cy_d_aileron, t.aileron_deg, SIGN_AILERON),
            "CYd01: " + ail,
        ),
        E("aero/l", "Cl_b", a.cl_b, "AVL ST `Clb`"),
        E("aero/l", "Cl_p", a.cl_p, "AVL ST `Clp`"),
        E("aero/l", "Cl_r", a.cl_r, "AVL ST `Clr` (scaled by CL/CL_0 in the simulator)"),
        E("aero/l", "Cl_dr", cl_dr, "Cld03: " + rud),
        E("aero/l", "Cl_da", cl_da, "Cld01: " + ail),
        E("aero/n", "Cn_b", a.cn_b, "AVL ST `Cnb`"),
        E("aero/n", "Cn_p", a.cn_p, "AVL ST `Cnp` (scaled by CL/CL_0 in the simulator)"),
        E("aero/n", "Cn_r", a.cn_r, "AVL ST `Cnr`"),
        E("aero/n", "Cn_dr", cn_dr, "Cnd03: " + rud),
        E("aero/n", "Cn_da", cn_da, "Cnd01: " + ail),
    ]


# ---------------------------------------------------------------------------------------------
def _fmt(v: float | str) -> str:
    if isinstance(v, str):
        return v
    return repr(round(float(v), 8)) if abs(v) >= 1e-3 or v == 0 else f"{float(v):.6g}"


def _element(path: str, entries: list[Entry], indent: int, extra_attrs: str = "") -> str:
    attrs = " ".join(f"{e.attr}={quoteattr(_fmt(e.value))}" for e in entries)
    pad = " " * indent
    return f"{pad}<{path.rsplit('/', 1)[-1]}{extra_attrs} {attrs} />"


def render_aero(entries: list[Entry]) -> str:
    out = ['  <aero version="1" units="1">']
    order: list[str] = []
    for e in entries:
        if e.path not in order:
            order.append(e.path)
    for path in order:
        out.append(_element(path, [e for e in entries if e.path == path], 4))
    out.append("  </aero>")
    return "\n".join(out)


def render_xml(
    *,
    name: str,
    description: str,
    changelog: str,
    aero: list[Entry],
    mass_kg: float,
    inertia: Inertia,
    inertia_comment: str,
    power_xml: str,
    graphics_model: str,
    wheels: list[tuple[float, float, float]],
    wheel_spring: tuple[float, float, float],
    cg: tuple[float, float, float],
    comments: list[str],
) -> str:
    k, c, fmax = wheel_spring
    wheel_xml = "\n".join(
        f'    <wheel percent_brake="0" caster_angle_rad="0">\n'
        f'      <pos x="{x:.5f}" y="{y:.5f}" z="{z:.5f}" />\n'
        f'      <spring constant="{k:g}" damping="{c:g}" max_force="{fmax:g}" />\n'
        f"    </wheel>"
        for x, y, z in wheels
    )
    comment_xml = "\n".join(f"  <!-- {escape(line)} -->" for line in comments)
    return f"""<?xml version="1.0" encoding="iso-8859-1" ?>
<CRRCSim_airplane version="2">
  <name>
    <en>{escape(name)}</en>
  </name>
  <categories>
    <category>Electric</category>
  </categories>
  <description>
    <en>
{escape(description)}
    </en>
  </description>
  <changelog>
    <change>
      <date>2026-10-22</date>
      <author>da3Dalus scripts/sim_export/crrcsim (gh-1195)</author>
      <en>
{escape(changelog)}
      </en>
    </change>
  </changelog>
{comment_xml}
{render_aero(aero)}
  <config version="1">
    <descr_long>
      <en>Mass from the plan reconstruction; inertias are a declared estimate (see comment above).</en>
    </descr_long>
    <descr_short>
      <en>default</en>
    </descr_short>
    <!-- {escape(inertia_comment)} -->
    <mass_inertia version="1" units="1" Mass="{mass_kg:g}" I_xx="{inertia.ixx:.6g}" I_yy="{inertia.iyy:.6g}" I_zz="{inertia.izz:.6g}" I_xz="{inertia.ixz:.6g}" />
    <sound version="1">
      <sample filename="fan.wav" type="1" pitchfactor="0.006" maxvolume="1" />
    </sound>
{power_xml}
  </config>
  <graphics version="1" model="{graphics_model}">
    <descr_long>
      <en>Stock model (size does not match the plane): placeholder until a BRYAN model exists.</en>
    </descr_long>
    <descr_short>
      <en>default</en>
    </descr_short>
  </graphics>
  <wheels version="1" units="1">
{wheel_xml}
  </wheels>
  <CG units="1" x="{cg[0]:.5f}" y="{cg[1]:.5f}" z="{cg[2]:.5f}" />
  <launch>
    <preset name_en="glider default (hand)" altitude="6" velocity_rel="1" angle="0" sal="0" rel_to_player="1" rel_front="0" rel_right="2" />
  </launch>
</CRRCSim_airplane>
"""


def render_mapping_md(title: str, sections: list[tuple[str, list[Entry]]], notes: str) -> str:
    lines = [f"# {title}", "", notes.strip(), ""]
    for heading, entries in sections:
        lines += [f"## {heading}", "", "| XML field | Value | Source |", "|---|---|---|"]
        for e in entries:
            src = e.source.replace("|", "/")
            lines.append(f"| `{e.path}` `{e.attr}` | {_fmt(e.value)} | {src} |")
        lines.append("")
    return "\n".join(lines)


def as_dict(entries: list[Entry]) -> dict[str, Any]:
    return {f"{e.path}.{e.attr}": e.value for e in entries}
