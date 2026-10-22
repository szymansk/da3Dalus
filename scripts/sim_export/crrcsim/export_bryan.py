"""Export BRYAN to a CRRCSim airplane XML (gh-1195 step 2, script prototype).

    poetry run python scripts/sim_export/crrcsim/export_bryan.py --speed 7.82 \\
        --elevator-throw-deg E --aileron-throw-deg A --rudder-throw-deg R \\
        --out /path/BRYAN.xml [--mapping-md scripts/sim_export/crrcsim/MAPPING.md]

The three control throws and the trim speed are required: there are no defaults, and the geometry's
deflection stops are never read (maintainer rule: deflections are parameters).

Trim: level flight at --speed, C_L = m g / (q S_ref), elevator trimmed to Cm = 0 about the plan CG in
AVL. The trim deflection is baked into stick-zero (CL_0, Cm_0 = 0, Alpha_0 are the trimmed values).
"""

from __future__ import annotations

import argparse
import pathlib
import sys

import numpy as np

HERE = pathlib.Path(__file__).resolve().parent
sys.path.insert(0, str(HERE))

import bryan_aero as ba  # noqa: E402
import crrcsim_model as cm  # noqa: E402
import inertia_buildup as ib  # noqa: E402
import polar  # noqa: E402

REF_TOL = 1e-3  # relative tolerance between ASB reference values and what AVL reports

# --- declared estimates (ADR 0020: nothing silent) -------------------------------------------------
# Radii of gyration: only a plausibility UPPER BOUND for the component build-up (Scholz-skill answer:
# the vault has no RC/glider values; Roskam/Raymer single-engine radii, from memory and unverified,
# over-predict even a Cessna 182 by ~30 %, so for a pod-and-boom model they bound from above).
RADII = cm.GyrationRadii(
    rx_over_b=0.25,
    ry_over_l=0.38,
    rz_over_e=0.39,
    xz_tilt_deg=0.0,
    source="Roskam/Raymer single-engine R_x/b, R_y/L, R_z/e (memory, unverified); upper bound only",
)
# Component build-up (Sadraey 11.7). Masses [g] from bryan.konstruktion.json komponenten unless noted.
M_MOTOR, M_PROP, M_ESC, M_BATT, M_RX, M_SERVO = 19.0, 4.568, 7.0, 28.0, 5.0, 4.8
X_MOTOR, X_PROP, X_ESC, X_BATT, X_RX = 0.010, -0.005, 0.050, 0.1103, 0.150
X_SERVO_TAIL, Y_SERVO_AIL, X_SERVO_AIL = 0.2195, 0.10, 0.165
# remainder of the 0.151 kg (structure, gear, wire, hatch, glue, covering) split by declared shares
# 0.4/0.4/0.2 puts the build-up CG 29 mm behind the plan CG; 0.6/0.3/0.1 reduces that to ~12 mm
# (a boom-and-pod model carries most structure mass in the wing and nose). Not matched exactly.
STRUCT_SHARE = {"wing": 0.60, "fuselage": 0.30, "tail": 0.10}
# Power chain, variant A of BRYAN_Motorisierung.md (Pulsar Micro 1510, 2000 KV, 6x4, 2S 450 mAh).
KV = 2000.0
PROP_D_M, PROP_H_M = 6 * 0.0254, 4 * 0.0254
PROP_J = 4.0e-6  # APC 6x4E, db/test.db propeller_polars.inertia_kg_m2 (APC PER3 file)
ENGINE_R_I = 0.15  # ohm, declared estimate (no datasheet value)
ENGINE_I_0 = 0.6  # A, declared estimate (no datasheet value)
ENGINE_J_M = 1.0e-6  # kg m^2, declared estimate (CRRCSim doc: "just guessed" is the norm)
BATTERY_C_AH, BATTERY_U0, BATTERY_UOFF, BATTERY_RI = 0.45, 7.4, 6.0, 0.06
BATTERY_U0REL = (1.14, 1.09, 1.05, 1.03, 1.02, 1.01, 0.99, 0.92)  # models/battery/lipo3s_2200.xml
# Hard points: stock wasabi.xml hard point (500 lbf/ft, 1 lbf s/ft, 50 lbf) scaled by mass ratio.
WASABI_MASS = 1.095
WASABI_SPRING = (500 * 14.5939, 1 * 14.5939, 50 * 4.44822)  # N/m, N s/m, N

POLAR_ALPHA = np.arange(-20.0, 30.5, 0.5)
REYNOLDS_SCAN = (0.6, 1.0, 1.6)  # multiples of the trim speed
SPAN_EFF_CAP = 0.95  # CRRCSim documentation: "0.95 for most planes"
# CRRCSim doc 3.5: CD_AIsq = 0.01 / (max_aileron)^2, max stick = 0.5. AeroBuildup's deflected-surface
# drag is not quadratic here (CD rise: 5 deg -0.0007, 10 deg +0.004, 15 deg +0.039, 20 deg +0.14).
CD_AISQ = 0.01 / cm.STICK_FULL**2


def semi_wing_eta(wing) -> float:
    """2 * (area-centroid y of one half wing) / span."""
    xs = [x for x in wing.xsecs]
    num = den = 0.0
    for a, b in zip(xs[:-1], xs[1:], strict=True):
        dy = abs(b.xyz_le[1] - a.xyz_le[1])
        area = 0.5 * (a.chord + b.chord) * dy
        num += area * 0.5 * (abs(a.xyz_le[1]) + abs(b.xyz_le[1]))
        den += area
    return 2 * (num / den) / (2 * max(abs(x.xyz_le[1]) for x in xs))


def analyse(speed: float) -> dict:
    b = ba.build_bryan()
    wing = b.airplane.wings[0]
    rho = float(b.atmosphere.density())
    weight = b.mass_kg * ba.G
    cl_trim = weight / (0.5 * rho * speed**2 * b.ref.s_ref)
    avl = ba.run_avl_trimmed(b, cl_trim, speed)
    for key, mine in (("Sref", b.ref.s_ref), ("Cref", b.ref.c_ref), ("Bref", b.ref.b_ref)):
        if abs(avl[key] - mine) / mine > REF_TOL:
            raise cm.ExportError(f"AVL reports {key} {avl[key]} but ASB reference is {mine}")
    e_trim = avl["elevator_trim_deg"]

    # AeroBuildup polar with the trimmed elevator (same configuration AVL describes)
    b_trim = ba.build_bryan({"elevator": e_trim})
    pol = ba.ab_polar(b_trim, speed, POLAR_ALPHA)
    st = polar.stall_data(pol["alpha"], pol["CL"], pol["CD"])
    ar = b.ref.b_ref**2 / b.ref.s_ref
    span_eff = min(SPAN_EFF_CAP * avl["e"], SPAN_EFF_CAP)
    fit_lo, fit_hi = 0.0, polar.FIT_CL_FRACTION_OF_MAX * st.cl_max
    fit = polar.fit_profile_drag(
        pol["alpha"], pol["CL"], pol["CD"], ar, span_eff, fit_lo, fit_hi, st.alpha_peak_deg
    )

    prof_at_trim = []
    speeds = np.array(REYNOLDS_SCAN) * speed
    for v in speeds:
        p = ba.ab_polar(b_trim, float(v), POLAR_ALPHA)
        stv = polar.stall_data(p["alpha"], p["CL"], p["CD"])
        f = polar.fit_profile_drag(
            p["alpha"],
            p["CL"],
            p["CD"],
            ar,
            span_eff,
            fit_lo,
            polar.FIT_CL_FRACTION_OF_MAX * stv.cl_max,
            stv.alpha_peak_deg,
        )
        prof_at_trim.append(f.cd_prof + f.cd_clsq * (cl_trim - f.cl_cd0) ** 2)
    uexp = polar.reynolds_exponent(speeds, np.array(prof_at_trim))

    numbers = dict(
        b=b,
        avl=avl,
        pol=pol,
        st=st,
        fit=fit,
        uexp=uexp,
        cl_trim=cl_trim,
        span_eff=span_eff,
        ar=ar,
        e_trim=e_trim,
        wing=wing,
        rho=rho,
        weight=weight,
    )
    return numbers


def build_aero_numbers(num: dict, throws: cm.Throws, speed: float) -> cm.AeroNumbers:
    avl, st, fit, b = num["avl"], num["st"], num["fit"], num["b"]
    wing = num["wing"]
    x_ac = float(wing.aerodynamic_center()[0])
    return cm.AeroNumbers(
        c_ref=b.ref.c_ref,
        b_ref=b.ref.b_ref,
        s_ref=b.ref.s_ref,
        v_ref=speed,
        alpha_0_rad=float(np.radians(avl["alpha_deg"])),
        cl_0=avl["CL"],
        cm_0=avl["Cm"],
        span_eff=num["span_eff"],
        eta_loc=semi_wing_eta(wing),
        cg_arm=(b.xyz_cg[0] - x_ac) / b.ref.c_ref,
        cl_a=avl["CLa"],
        cl_q=avl["CLq"],
        cm_a=avl["Cma"],
        cm_q=avl["Cmq"],
        cy_b=avl["CYb"],
        cy_p=avl["CYp"],
        cy_r=avl["CYr"],
        cl_b=avl["Clb"],
        cl_p=avl["Clp"],
        cl_r=avl["Clr"],
        cn_b=avl["Cnb"],
        cn_p=avl["Cnp"],
        cn_r=avl["Cnr"],
        cl_d_elevator=avl["CLd02"],
        cm_d_elevator=avl["Cmd02"],
        cy_d_aileron=avl["CYd01"],
        cl_d_aileron=avl["Cld01"],
        cn_d_aileron=avl["Cnd01"],
        cy_d_rudder=avl["CYd03"],
        cl_d_rudder=avl["Cld03"],
        cn_d_rudder=avl["Cnd03"],
        cl_max=st.cl_max,
        cl_min=st.cl_min,
        cl_drop=st.cl_drop,
        cl_cd0=fit.cl_cd0,
        cd_prof=fit.cd_prof,
        uexp_cd=num["uexp"],
        cd_stall=st.cd_stall,
        cd_clsq=fit.cd_clsq,
        cd_aisq=CD_AISQ,
        cd_elsq=0.0,
    )


def power_xml() -> tuple[str, list[cm.Entry]]:
    k_m = 60.0 / (2 * np.pi * KV)
    e = cm.Entry
    entries = [
        e(
            "config/power/engine",
            "k_M",
            k_m,
            "60 / (2 pi KV), KV 2000 (BRYAN_Motorisierung.md variant A)",
        ),
        e(
            "config/power/engine",
            "R_I",
            ENGINE_R_I,
            "DECLARED ESTIMATE: db components id 629 (Pulsar Micro 1510) states Ri, Io not published",
        ),
        e(
            "config/power/engine",
            "I_0",
            ENGINE_I_0,
            "DECLARED ESTIMATE: db components id 629 (Pulsar Micro 1510) states Ri, Io not published",
        ),
        e(
            "config/power/engine",
            "J_M",
            ENGINE_J_M,
            "DECLARED ESTIMATE (CRRCSim: rotor inertia is normally guessed)",
        ),
        e(
            "config/power/battery",
            "C",
            BATTERY_C_AH,
            "LiPo 2S 450 mAh (BRYAN_Motorisierung.md), in Ah",
        ),
        e("config/power/battery", "U_0", BATTERY_U0, "2S nominal 3.7 V per cell"),
        e(
            "config/power/battery",
            "U_off",
            BATTERY_UOFF,
            "3.0 V per cell cut-off (stock lipo3s_2200.xml)",
        ),
        e("config/power/battery", "R_I", BATTERY_RI, "DECLARED ESTIMATE for a 450 mAh pack"),
        e("config/power/propeller", "D", PROP_D_M, "6 x 4 in (BRYAN_Motorisierung.md): 6 in"),
        e("config/power/propeller", "H", PROP_H_M, "pitch 4 in"),
        e("config/power/propeller", "J", PROP_J, "APC 6x4E inertia, db/test.db propeller_polars"),
        e(
            "config/power/shaft",
            "J",
            0.0,
            "no gearbox, no folding (RC electric, no brake: ADR 0028)",
        ),
    ]
    rel = "\n".join(f"            {v};" for v in BATTERY_U0REL)
    xml = f"""    <power units="1">
      <battery C="{BATTERY_C_AH}" U_0="{BATTERY_U0}" U_off="{BATTERY_UOFF}" R_I="{BATTERY_RI}" throttle_min="0">
        <U_0rel>
{rel}
        </U_0rel>
        <shaft J="0" brake="0">
          <engine k_M="{k_m:.4e}" R_I="{ENGINE_R_I}" J_M="{ENGINE_J_M:g}" I_0="{ENGINE_I_0}" />
          <propeller D="{PROP_D_M:.5f}" H="{PROP_H_M:.5f}" J="{PROP_J:g}" n_fold="-1" />
        </shaft>
      </battery>
    </power>"""
    return xml, entries


def hard_points(b: ba.Bryan) -> list[tuple[float, float, float]]:
    """CRRCSim body axes (x forward, y right, z down) relative to the CG."""
    xc, _, zc = b.xyz_cg

    def pt(x: float, y: float, z: float) -> tuple[float, float, float]:
        return (xc - x, y, zc - z)

    g = b.geometry
    wing = g["wings"]["Tragflaeche"]["x_secs"][-1]
    stab = g["wings"]["Hoehenleitwerk"]["x_secs"][-1]
    fin = max(g["wings"]["Seitenleitwerk"]["x_secs"], key=lambda s: s["xyz_le"][2])
    fus = g["fuselages"]["Rumpf"]["x_secs"]
    nose, tail = fus[0]["xyz"], fus[-1]["xyz"]
    belly = min(fus, key=lambda s: abs(s["xyz"][0] - xc))
    pts = [
        pt(nose[0], 0.0, nose[2]),
        pt(tail[0], 0.0, tail[2]),
        pt(belly["xyz"][0], 0.0, belly["xyz"][2] - belly["b"]),
        pt(wing["xyz_le"][0] + 0.5 * wing["chord"], wing["xyz_le"][1], wing["xyz_le"][2]),
        pt(wing["xyz_le"][0] + 0.5 * wing["chord"], -wing["xyz_le"][1], wing["xyz_le"][2]),
        pt(stab["xyz_le"][0] + 0.5 * stab["chord"], stab["xyz_le"][1], stab["xyz_le"][2]),
        pt(stab["xyz_le"][0] + 0.5 * stab["chord"], -stab["xyz_le"][1], stab["xyz_le"][2]),
        pt(fin["xyz_le"][0] + 0.5 * fin["chord"], 0.0, fin["xyz_le"][2]),
    ]
    return pts


def bryan_inertia(b: ba.Bryan) -> tuple[cm.Inertia, str, cm.Inertia]:
    """Component build-up about the build-up CG; I_xz declared 0. Returns (inertia, basis text,
    radius-of-gyration upper bound)."""
    g = b.geometry
    kg = 1e-3
    pts = [
        ib.PointMass("motor", M_MOTOR * kg, X_MOTOR, 0.0, 0.0, "konstruktion komponenten.motor.masse"),
        ib.PointMass("propeller", M_PROP * kg, X_PROP, 0.0, 0.0, "db propeller_polars APC 6x4E weight_g"),
        ib.PointMass("ESC", M_ESC * kg, X_ESC, 0.0, -0.010, "konstruktion komponenten.regler.masse, Nasenboden"),
        ib.PointMass("battery", M_BATT * kg, X_BATT, 0.0, 0.0, "konstruktion komponenten.akku (x range mid 99.5..121.1 mm)"),
        ib.PointMass("receiver", M_RX * kg, X_RX, 0.0, -0.005, "konstruktion komponenten.empfaenger, wing root rib"),
        ib.PointMass("elevator servo", M_SERVO * kg, X_SERVO_TAIL, 0.0, 0.0, "konstruktion servos, x 205.5..233.5"),
        ib.PointMass("rudder servo", M_SERVO * kg, X_SERVO_TAIL, 0.0, 0.0, "konstruktion servos, x 205.5..233.5"),
        ib.PointMass("aileron servo R", M_SERVO * kg, X_SERVO_AIL, Y_SERVO_AIL, -0.014, "konstruktion servos, wing rib 24.b (position estimated)"),
        ib.PointMass("aileron servo L", M_SERVO * kg, X_SERVO_AIL, -Y_SERVO_AIL, -0.014, "konstruktion servos, wing rib 24.b (position estimated)"),
    ]  # fmt: skip
    listed = sum(p.mass_kg for p in pts)
    rest = b.mass_kg - listed
    if rest <= 0:
        raise cm.ExportError(
            f"listed component masses {listed:.4f} kg exceed the total {b.mass_kg} kg"
        )
    st = "remainder of the total mass (structure, gear, linkage, hatch, glue, covering)"
    wings = g["wings"]
    xs = lambda name: b.airplane.wings[[w.name for w in b.airplane.wings].index(name)].xsecs  # noqa: E731
    pts += ib.strip_masses("wing", xs("Tragflaeche"), rest * STRUCT_SHARE["wing"], True, st)
    tail_area = {}
    for name in ("Hoehenleitwerk", "Seitenleitwerk"):
        xsecs = xs(name)
        tail_area[name] = sum(
            0.5 * (a.chord + c.chord) * float(np.hypot(c.xyz_le[1] - a.xyz_le[1], c.xyz_le[2] - a.xyz_le[2]))
            * (2 if wings[name]["symmetric"] else 1)
            for a, c in zip(xsecs[:-1], xsecs[1:], strict=True)
        )  # fmt: skip
    for name, area in tail_area.items():
        pts += ib.strip_masses(
            name,
            xs(name),
            rest * STRUCT_SHARE["tail"] * area / sum(tail_area.values()),
            wings[name]["symmetric"],
            st,
        )
    fus = g["fuselages"]["Rumpf"]["x_secs"]
    rods = [
        ib.Rod(
            "fuselage",
            rest * STRUCT_SHARE["fuselage"],
            fus[0]["xyz"][0],
            fus[-1]["xyz"][0],
            0.0,
            st,
        )
    ]
    res = ib.buildup(pts, rods)
    dx = (res.cg_geometry[0] - b.xyz_cg[0]) * 1000
    basis = (
        f"Sadraey 11.7 component build-up I = sum(I_c + m d^2) about the build-up CG; listed components "
        f"{listed * 1000:.1f} g (motor {M_MOTOR}, prop {M_PROP}, ESC {M_ESC}, battery {M_BATT}, receiver {M_RX}, "
        f"4 servos {M_SERVO} each; positions from bryan.konstruktion.json, aileron servo and ESC/receiver heights estimated), "
        f"remainder {rest * 1000:.1f} g split wing {STRUCT_SHARE['wing']:.0%} (area-weighted strips) / fuselage "
        f"{STRUCT_SHARE['fuselage']:.0%} (uniform rod, I_c=mL^2/12) / tail {STRUCT_SHARE['tail']:.0%} (area-weighted); "
        f"component self-inertia neglected; build-up CG x = {res.cg_geometry[0] * 1000:.1f} mm vs plan CG "
        f"{b.xyz_cg[0] * 1000:.1f} mm (offset {dx:+.1f} mm, inertia not shifted to the plan CG); I_xz declared 0"
    )
    bound = cm.estimate_inertia(
        b.mass_kg,
        float(b.airplane.wings[0].span("yz")),
        float(fus[-1]["xyz"][0]),
        RADII,
    )
    return cm.Inertia(res.ixx, res.iyy, res.izz, 0.0, basis), basis, bound


def export(
    speed: float, throws: cm.Throws, graphics_model: str = "mav.ac", throws_note: str = ""
) -> dict:
    num = analyse(speed)
    a = build_aero_numbers(num, throws, speed)
    b, avl, st, fit = num["b"], num["avl"], num["st"], num["fit"]
    src = {
        "ref": "ASB geometry, projected onto the x-y plane; passed explicitly to AVL and AeroBuildup",
        "trim": f"level flight at {speed} m/s, C_L = m g / (q S_ref) = {num['cl_trim']:.4f}",
        "eta_loc": "geometry: 2 * area-centroid y of the half wing / span (stock models use 0.25-0.3)",
        "cg_arm": "geometry: (x_CG - x_AC,wing) / c_ref (stalled wing lift acts at the wing AC)",
        "span_eff": f"min(0.95 * AVL e, 0.95): AVL e = {avl['e']:.3f} > 1 (AVL discretisation, see MAPPING notes); "
        "CRRCSim documents 0.95 for conventional aft-tail planes",
        "stall": f"AeroBuildup polar at {speed} m/s, trimmed elevator {num['e_trim']:.2f} deg",
        "drag": f"AeroBuildup polar at {speed} m/s minus induced C_L^2/(pi AR {num['ar']:.3f} span_eff)",
        "aileron_drag": "CRRCSim doc 3.5 rule 0.01 / (max stick 0.5)^2; AeroBuildup deflected-surface drag is not quadratic (5 deg: -0.0007, 10: +0.004, 15: +0.039, 20: +0.14)",
    }
    aero = cm.aero_entries(a, throws, src)
    inertia, basis, bound = bryan_inertia(b)
    sens = cm.inertia_sensitivity(inertia)
    pxml, pentries = power_xml()
    wheels = hard_points(b)
    scale = b.mass_kg / WASABI_MASS
    spring = tuple(v * scale for v in WASABI_SPRING)
    est = "DECLARED ESTIMATE (component build-up, not measured): " + basis
    body_entries = [
        cm.Entry(
            "config/mass_inertia",
            "Mass",
            b.mass_kg,
            "bryan.airplane.json total_mass_kg (plan reconstruction)",
        ),
        cm.Entry("config/mass_inertia", "I_xx", inertia.ixx, est),
        cm.Entry("config/mass_inertia", "I_yy", inertia.iyy, est),
        cm.Entry("config/mass_inertia", "I_zz", inertia.izz, est),
        cm.Entry(
            "config/mass_inertia",
            "I_xz",
            inertia.ixz,
            "DECLARED: 0 for the first export (small for a laterally symmetric model)",
        ),
        cm.Entry(
            "CG",
            "x, y, z",
            "0, 0, 0",
            "plan CG (bryan.airplane.json xyz_ref) is the origin of the hard-point frame",
        ),
        cm.Entry(
            "graphics",
            "model",
            graphics_model,
            "stock model placeholder; size does not match BRYAN",
        ),
        cm.Entry(
            "wheels",
            "pos (x8)",
            "; ".join(f"({x:.3f}, {y:.3f}, {z:.3f})" for x, y, z in wheels),
            "geometry: nose, tail, belly at CG, wing tips, stabiliser tips, fin top; CRRCSim axes relative to CG [m]",
        ),
        cm.Entry(
            "wheels/spring",
            "constant, damping, max_force",
            f"{spring[0]:.0f} N/m, {spring[1]:.2f} N s/m, {spring[2]:.0f} N",
            "wasabi.xml hard point (500 lbf/ft, 1 lbf s/ft, 50 lbf) scaled by m / 1.095 kg",
        ),
    ]
    inertia_comment = (
        "DECLARED ESTIMATE (not measured): "
        + basis
        + f". I_xx={inertia.ixx:.3g}, I_yy={inertia.iyy:.3g}, I_zz={inertia.izz:.3g}, I_xz=0 kg m^2. "
        + "Sensitivity band (x1/1.5..x1.5): "
        + ", ".join(f"{k} {lo:.3g}..{hi:.3g}" for k, (lo, hi) in sens.items())
        + ". Plausibility upper bound from radii of gyration (Roskam/Raymer single-engine, unverified): "
        + f"I_xx={bound.ixx:.3g}, I_yy={bound.iyy:.3g}, I_zz={bound.izz:.3g}. "
        + "Low I_xx/I_yy speeds up roll/pitch response, high I_zz slows yaw; measure with a bifilar pendulum when possible."
    )
    throw_comments = []
    if throws_note:
        throw_comments.append(f"Throws provenance: {throws_note}")
    if max(throws.elevator_deg, throws.aileron_deg, throws.rudder_deg) > 20:
        throw_comments.append(
            "AVL control derivatives are linear in deflection: effectiveness at throws above ~20 deg "
            "is overestimated (flow separation and hinge-gap losses are not modelled)."
        )
    comments = [
        f"Generated by scripts/sim_export/crrcsim/export_bryan.py (gh-1195). Trim: {src['trim']}; elevator trim {num['e_trim']:.2f} deg is baked into stick zero.",
        f"Throws (full stick, deg): elevator {throws.elevator_deg}, aileron {throws.aileron_deg}, rudder {throws.rudder_deg}; derivative = AVL_per_deg * travel / 0.5.",
        "Reference values are projected onto the x-y plane (S, b, MAC). Origin of the wheel/CG frame is the plan CG.",
        "Power: engine k_M from KV 2000; R_I, I_0, J_M and battery R_I are DECLARED ESTIMATES (no datasheet).",
        "Graphics: stock mav.ac placeholder, its size does not match BRYAN.",
    ]
    xml = cm.render_xml(
        name="BRYAN",
        description=(
            "BRYAN (FlugModell 06/26), 547 mm electric trainer, plan CG, mass 151 g.\n"
            "Derivatives: AVL stability run (trimmed) + AeroBuildup polar; see MAPPING.md in the da3Dalus repo."
        ),
        changelog="Generated from bryan.airplane.json (gh-1195). All coefficient sources are in MAPPING.md.",
        aero=aero,
        mass_kg=b.mass_kg,
        inertia=inertia,
        inertia_comment=inertia_comment,
        power_xml=pxml,
        graphics_model=graphics_model,
        wheels=wheels,
        wheel_spring=spring,  # type: ignore[arg-type]
        cg=(0.0, 0.0, 0.0),
        comments=comments,
    )
    # report
    sm = (avl["Xnp"] - b.xyz_cg[0]) / b.ref.c_ref
    vs = float(np.sqrt(2 * num["weight"] / (num["rho"] * b.ref.s_ref * st.cl_max)))
    report = {
        "trim_cl": num["cl_trim"],
        "trim_alpha_deg": avl["alpha_deg"],
        "trim_elevator_deg": num["e_trim"],
        "static_margin_avl_pct_mac": 100 * sm,
        "cl_a_avl": avl["CLa"],
        "cl_a_ab": float(
            np.polyfit(
                np.radians(
                    num["pol"]["alpha"][(num["pol"]["alpha"] > -3) & (num["pol"]["alpha"] < 8)]
                ),
                num["pol"]["CL"][(num["pol"]["alpha"] > -3) & (num["pol"]["alpha"] < 8)],
                1,
            )[0]
        ),
        "stall_alpha_ab_deg": st.alpha_peak_deg,
        "stall_alpha_crrcsim_deg": float(
            avl["alpha_deg"] + np.degrees((st.cl_max - a.cl_0) / a.cl_a)
        ),
        "v_stall_ms": vs,
        "fit_rms": fit.residual_rms,
        "inertia": inertia,
        "inertia_sens": sens,
        "inertia_comment": inertia_comment,
        "aero_entries": aero,
        "body_entries": body_entries,
        "throw_entries": [
            cm.Entry("controls", f"{n} full-stick throw [deg]", v, throws_note or "CLI argument")
            for n, v in (
                ("elevator", throws.elevator_deg),
                ("aileron", throws.aileron_deg),
                ("rudder", throws.rudder_deg),
            )
        ],
        "power_entries": pentries,
        "wheels": wheels,
        "xml": xml,
        "avl": {k: v for k, v in avl.items() if k != "raw_output"},
    }
    return report


MAPPING_NOTES = """
Generated by `export_bryan.py --mapping-md` from the same entry list that renders the XML, so the
table cannot drift from the file. Values are from the last generation (command at the bottom).

## Method

- **Trim point:** level flight at `--speed`, C_L = m g / (q S_ref), elevator trimmed to Cm = 0 about
  the plan CG in AVL (`a c <CL>`, `d2 pm 0`). The trim deflection is baked into stick zero:
  `Alpha_0`, `CL_0` and `Cm_0` are the trimmed values, so stick zero is the trimmed cruise.
- **Reference values (maintainer decision 2026-10-22):** S_ref, b_ref, c_ref are projected onto the
  x-y plane and passed explicitly to AVL and AeroBuildup. The exporter fails if AVL reports other values.
- **Sources:** AVL ST (stability axes) gives all linear derivatives and control derivatives;
  the AeroBuildup polar (whole airplane, trimmed elevator, Re of the trim speed) gives the non-linear
  items (CL_max, CL_min, CL_drop, drag parabola, Reynolds exponent, CD_stall).
- **Control derivatives:** `der_CRRCSim = der_AVL[/deg] * throw_deg / 0.5` (full stick is 0.5). The
  throws are required exporter inputs; the geometry's deflection stops are never read. AVL's aileron
  and rudder signs are inverted (CRRCSim +aileron = roll right, +rudder = nose left, taken from
  larcsim.cpp and the keyboard handler); the exporter refuses to write the file if the resulting signs
  are not physical (Cm_de < 0, CL_de > 0, Cl_da > 0, Cn_dr < 0, CY_dr > 0, Cm_a < 0, Cl_p < 0, Cn_r < 0).
  The conversion reproduces the hand mapping documented in the stock wasabi.xml (unit test).
- **CL_0 guard:** the simulator scales Cl_r and Cn_p by CL/CL_0, so the exporter fails if |CL_0| < 0.01.
- **Frame:** wheel/CG coordinates are CRRCSim body axes (x forward, y right, z down) with the plan CG
  as origin (`CG` is therefore 0,0,0); geometry x aft / z up is converted.

## Declared estimates and substitutions (ADR 0020, nothing silent)

- **Inertia** I_xx, I_yy, I_zz, I_xz: not measured. Radius-of-gyration method, values and source in the
  XML comment and below; sensitivity band x1/1.5 .. x1.5 in I.
- **Power:** BRYAN_Motorisierung.md variant A fixes KV (2000), propeller (6 x 4), battery (2S 450 mAh)
  but gives no engine resistance, no-load current or pack resistance: those are estimates (marked
  DECLARED ESTIMATE in the table). The CRRCSim `automagic` design was not used because it would invent
  the KV as well.
- **AVL discretisation:** one spanwise strip per geometry segment. More strips make the longitudinal
  results drift without converging (static margin 6.1 / 4.0 / 1.7 / -1.5 / -6.5 % MAC for 1..5 strips per
  segment; lateral derivatives do not move): the tail lies within ~0.02 m of the wing's trailing-vortex
  plane and strips narrower than that are ill-conditioned. Merging the section clusters (min spacing
  8..20 mm) gives 5.4..6.2 % at one strip per segment, so the one-strip value is the stable one.
- **span_eff:** AVL's e is about 1.10 (Sref 0.069905 m2, Bref 0.54603 m, Cref 0.13280 m, as passed and
  echoed by AVL). e > 1 is a property of AVL's discretisation, not of the references: a planar rectangular
  wing of the same aspect ratio through the same pipeline gives e = 1.16 (3 strips) and 1.04 (10 strips)
  with the correct Bref, and the wing alone on BRYAN gives about the same e as the whole airplane.
  min(0.95 e, 0.95) = 0.95, the CRRCSim documented value for conventional aft-tail planes, is used.
- **Neutral point worlds:** AVL (with downwash) puts the neutral point near 37.5 % MAC (static margin about
  6 % at the plan CG 31.4 %); AeroBuildup (no downwash) 43.8 % (12.3 %); the known worlds in
  ERGEBNISSE_STABILITAET.md span 32.9..36.9 % MAC (1.5..5.5 % margin).
- **CD_AIsq:** CRRCSim documented rule, because AeroBuildup's deflected-surface drag is not quadratic.
- **CG_arm, eta_loc:** from the geometry (no stall-moment data in AeroBuildup: its Cm follows the linear
  extrapolation through the stall).
- **Rudder sections with hinge_point < 0.3** (the slender lower trailing blade, hinge_point 0.0/0.002)
  are not hinged surfaces and carry no control in AVL/AeroBuildup.
- **Graphics:** stock `mav.ac` placeholder; hard points from the geometry (nose, tail, belly, wing tips,
  stabiliser tips, fin top), spring/damper/max force of the stock wasabi hard point scaled by mass,
  no wheel brakes (`percent_brake=0`, RC equipment, ADR 0028).
"""


def main(argv: list[str] | None = None) -> int:
    ap = argparse.ArgumentParser(
        description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter
    )
    ap.add_argument("--speed", type=float, required=True, help="trim speed [m/s]")
    ap.add_argument("--elevator-throw-deg", type=float, required=True)
    ap.add_argument("--aileron-throw-deg", type=float, required=True)
    ap.add_argument("--rudder-throw-deg", type=float, required=True)
    ap.add_argument("--out", type=pathlib.Path, required=True)
    ap.add_argument("--mapping-md", type=pathlib.Path)
    ap.add_argument("--graphics-model", default="mav.ac")
    ap.add_argument(
        "--throws-note", default="", help="provenance of the throws, written into the XML"
    )
    args = ap.parse_args(argv)
    throws = cm.Throws(args.elevator_throw_deg, args.aileron_throw_deg, args.rudder_throw_deg)
    rep = export(args.speed, throws, args.graphics_model, args.throws_note)
    args.out.write_text(rep["xml"], encoding="iso-8859-1")
    print(f"wrote {args.out}")
    for k in (
        "trim_cl", "trim_alpha_deg", "trim_elevator_deg", "static_margin_avl_pct_mac",
        "cl_a_avl", "cl_a_ab", "stall_alpha_ab_deg", "stall_alpha_crrcsim_deg", "v_stall_ms", "fit_rms",
    ):  # fmt: skip
        print(f"  {k}: {rep[k]:.4g}")
    print("  inertia estimate:", rep["inertia_comment"])
    if args.mapping_md:
        cmd = (
            f"python export_bryan.py --speed {args.speed} --elevator-throw-deg {args.elevator_throw_deg} "
            f"--aileron-throw-deg {args.aileron_throw_deg} --rudder-throw-deg {args.rudder_throw_deg}"
        )
        md = cm.render_mapping_md(
            "CRRCSim BRYAN.xml: field mapping",
            [
                ("Aerodynamics `<aero>`", rep["aero_entries"]),
                ("Control throws (required inputs)", rep["throw_entries"]),
                ("Mass, inertia, hard points, graphics", rep["body_entries"]),
                ("Power chain `<power>`", rep["power_entries"]),
            ],
            MAPPING_NOTES + f"\nCommand: `{cmd}`\n",
        )
        args.mapping_md.write_text(md)
        print(f"wrote {args.mapping_md}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
