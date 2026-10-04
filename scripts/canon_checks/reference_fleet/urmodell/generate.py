"""Urmodell generator prototype (README §3 of _reversa_sdd/calculations/auswahl/) for the reference fleet.

NOT the app generator (#1152): a validation prototype that turns every all-typical combination of the
selection graph into a da3Dalus geometry file (fleet/<id>.airplane.json) so the canon can be run on a
broad fleet. Bands and their sources: BAENDER.md (§2 statistics [T], §3 vault [V], §3a–3f decisions).

Declared defaults (no source, BAENDER §3f principle "must fly, not be perfect"):
  D1 airfoil per mission = a representative of the BAENDER profile class (not yet the DB ranking):
     trainer/park Clark Y (flat-bottom), sport/scale NACA 2412 (semi-symmetric), aerobatic/3D NACA 0015
     (symmetric 10–15 %), speed E374 (Lennon: thin, little camber), e-glider/thermal SD7037, glider
     trainer S3021, slope RG15, hand-launch AG35, flying wing MH45 (reflex); tails NACA 0009
  D2 shoulder-wing dihedral interpolated between Lennon's high and mid wing
  D3 fuselage stations as fractions of length and a maximum diameter of 0.1 L (BAENDER §3f)
  D4 flying wing: washout 3 deg (Lennon 2–5 / Panknin start), aspect ratio from the flying-wing statistics,
     central fin 10 % of S on the centre section, trailing edges flush (2026-10-04: was placed at the
     tip-TE station and floated behind the wing without a boom), winglets 4 % of S each
  D5 biplane: two equal wings, gap = chord, upper stagger 0.3 chord forward, aspect ratio per wing = band
  D6 control-surface hinge lines and span fractions (ailerons 0.6–0.95 b/2 at 25 % chord, Lennon)
  D9 spars as the app's spar planner places them (spar_plan_service / SparPlanRequest defaults): front spar
     at the section's max-thickness x/c, rear spar at 0.65 c on main wings, both full span, solid carbon
     rod (500 MPa, DB material "Carbon Fiber (structural)"), diameter from the root moment of an elliptic
     load M = m g b / (3 pi) x g_limit 3 x j 1.5 with W = d^3/10 (the solver's convention), capped at
     packing 0.8 x root thickness; rear spar 0.6 x front diameter (torsion-sized in the app — placeholder);
     tails: one spar at max thickness, min(0.5 x main d, 0.6 x root thickness). Visual only: the app re-sizes spars.
  D8 flying-wing mass = mission wing-loading median x area (the span fit is built on tailed aircraft)
  D7 CG from the FORWARD edge of the geometric neutral-point worlds (textbook, Pappas) minus SM target
"""

from __future__ import annotations

import json
import math
import pathlib

HERE = pathlib.Path(__file__).parent
ROOT = HERE.parents[3]
STATS = json.loads((ROOT / "_reversa_sdd/calculations/auswahl/flottenstatistik.json").read_text())

# --- bands per mission ------------------------------------------------------------------------------
# taper [V wing-taper-ratio; sailplanes 0.3–0.7 -> 0.5]; SM target [Q-MS-14 / BAENDER §3b,§3e];
# V_H [V tail-horizontal… for trainer/sport/aero; Drela 0.4–0.45 gliders]; tail arm in MAC [V
# fuselage-tail-lever-arm] (None = 0.6 L for gliders, BAENDER §3b); airfoil D1; incidence [Lelke]
GLIDER = {"elektrosegler", "segel_trainer", "thermik", "hang", "wurf", "scale_segler", "speed"}
BAND = {
    "trainer":       dict(taper=0.9,  sm=0.15,  vh=0.65, arm=2.85, foil="clarky",   inc=1.0),
    "park":          dict(taper=0.9,  sm=0.15,  vh=0.65, arm=2.85, foil="clarky",   inc=1.0),
    "sport":         dict(taper=0.65, sm=0.10,  vh=0.55, arm=2.5,  foil="naca2412", inc=1.0),
    "scale":         dict(taper=0.65, sm=0.10,  vh=0.55, arm=2.5,  foil="naca2412", inc=1.0),
    "kunstflug":     dict(taper=0.5,  sm=0.03,  vh=0.50, arm=2.15, foil="naca0015", inc=0.0),
    "3d":            dict(taper=0.5,  sm=0.03,  vh=0.50, arm=2.15, foil="naca0015", inc=0.0),
    "speed":         dict(taper=0.5,  sm=0.065, vh=0.45, arm=None, foil="e374",     inc=1.0),
    "elektrosegler": dict(taper=0.5,  sm=0.10,  vh=0.45, arm=None, foil="sd7037",   inc=2.0),
    "segel_trainer": dict(taper=0.5,  sm=0.135, vh=0.45, arm=None, foil="s3021",    inc=2.0),
    "thermik":       dict(taper=0.5,  sm=0.10,  vh=0.45, arm=None, foil="sd7037",   inc=2.0),
    "hang":          dict(taper=0.5,  sm=0.08,  vh=0.45, arm=None, foil="rg15",     inc=1.5),
    "wurf":          dict(taper=0.5,  sm=0.065, vh=0.45, arm=None, foil="ag35",     inc=2.0),
    "scale_segler":  dict(taper=0.5,  sm=0.10,  vh=0.45, arm=None, foil="sd7037",   inc=2.0),
}
LENNON_DIHEDRAL = {"hochdecker": (2.0, 5.0), "schulterdecker": (2.5, 5.5), "mitteldecker": (3.0, 6.0),
                   "tiefdecker": (4.0, 7.0)}  # (with ailerons, rudder-only) [lennon-wing-position-dihedral]
NF = {"nf_mitte", "nf_winglet", "nf_ohne"}


def foil(name):
    return f"./airfoils/{name}.dat"


def wing_sections(span, c_root, taper, sweep_c4_deg, dihedral_deg, twist_root, twist_tip, cuts, x0=0.0, z0=0.0):
    """Half-wing sections at the span fractions `cuts` (0 … 1), trapezoid, quarter-chord sweep."""
    out = []
    for f in cuts:
        y = f * span / 2
        c = c_root * (1 + (taper - 1) * f)
        x_c4 = x0 + 0.25 * c_root + y * math.tan(math.radians(sweep_c4_deg))
        out.append(dict(xyz_le=[x_c4 - 0.25 * c, y, z0 + y * math.tan(math.radians(dihedral_deg))],
                        chord=c, twist=twist_root + (twist_tip - twist_root) * f))
    return out


def foil_shape(name):
    """(t/c, x/c of max thickness) of a coordinate file in fleet/airfoils/."""
    import numpy as np
    pts = []
    for line in (HERE / "fleet" / "airfoils" / f"{name}.dat").read_text().splitlines():
        try:
            a, b = (float(v) for v in line.split()[:2])
        except ValueError:
            continue
        if a <= 1.5:
            pts.append((a, b))
    pts = np.array(pts)
    i0 = int(np.argmin(pts[:, 0]))
    up, lo = pts[: i0 + 1][::-1], pts[i0:]
    xg = np.linspace(0.01, 0.99, 197)
    th = np.interp(xg, up[:, 0], up[:, 1]) - np.interp(xg, lo[:, 0], lo[:, 1])
    if np.median(th) < 0:
        th = -th
    k = int(np.argmax(th))
    return float(th[k]), float(xg[k])


def add_spars(wings, mass, span):
    """D9: front/rear spar on every main-wing segment, one spar on tail segments (metres)."""
    g = 9.80665
    m_design = mass * g * span / (3 * math.pi) * 3.0 * 1.5
    d_req = (10 * m_design / 500e6) ** (1 / 3)
    for name, w in wings.items():
        xs = w["x_secs"]
        tc, xmax = foil_shape(pathlib.Path(xs[0]["airfoil"]).stem)
        t_root = tc * xs[0]["chord"]
        main = name in ("Tragflaeche", "Oberfluegel")
        d = min(d_req, 0.8 * t_root) if main else min(0.5 * d_req, 0.6 * t_root)
        spars = [{"spare_position_factor": round(xmax, 3), "spare_support_dimension_width": d,
                  "spare_support_dimension_height": d, "spare_start": 0.0, "spare_mode": "standard"}]
        if main:
            spars.append({"spare_position_factor": 0.65, "spare_support_dimension_width": 0.6 * d,
                          "spare_support_dimension_height": 0.6 * d, "spare_start": 0.0, "spare_mode": "standard"})
        for x in xs[:-1]:
            x["spare_list"] = [dict(s) for s in spars]


def surface_geom(xs):
    """Area, MAC, x of the aerodynamic centre of a symmetric surface from its sections (trapezoid strips)."""
    S = mac_int = xac_int = 0.0
    for a, b in zip(xs, xs[1:], strict=False):
        dy = abs(b["xyz_le"][1] - a["xyz_le"][1]) or 0.0
        dl = math.hypot(dy, b["xyz_le"][2] - a["xyz_le"][2])
        ca, cb = a["chord"], b["chord"]
        s = 0.5 * (ca + cb) * dl
        c2 = (ca * ca + ca * cb + cb * cb) / 3
        xm = 0.5 * (a["xyz_le"][0] + 0.25 * ca + b["xyz_le"][0] + 0.25 * cb)
        S += s
        mac_int += c2 * dl
        xac_int += xm * s
    return 2 * S, mac_int / S, xac_int / S


def np_worlds(S, AR, xac_w, S_h, AR_h, xac_h):
    """Geometric NP worlds (canon neutral-point.md): textbook (eta 0.9) and Pappas."""
    k_t = 0.9 * (1 - 4 / (AR + 2)) * (AR_h / (AR_h + 2)) / (AR / (AR + 2))
    k_p = (1 - 3.24 / AR) * (1 / (1 + 2 / AR_h)) / (1 / (1 + 2 / AR))
    return [(S * xac_w + k * S_h * xac_h) / (S + k * S_h) for k in (k_t, k_p)]


def geo_np(wings: dict) -> dict:
    """Reference geometry and the geometric NP worlds from the BUILT surfaces (one function for the
    generator and the evaluation). Biplane: both wings, area-weighted AC, MAC of the lower wing.
    Reference leading edge = AC - MAC/4. V-tail: pitch-effective area S cos^2(nu) (Drela's A_H),
    aspect ratio = projected span^2 / projected area S cos(nu). Tailless: both worlds = wing AC."""
    main = [wings[k]["x_secs"] for k in ("Tragflaeche", "Oberfluegel") if k in wings]
    geo = [surface_geom(x) for x in main]
    S_w = sum(g[0] for g in geo)
    xac_w = sum(g[0] * g[2] for g in geo) / S_w
    mac = geo[0][1]
    b = 2 * main[0][-1]["xyz_le"][1]
    AR = b * b / geo[0][0]
    out = {"S": S_w, "mac": mac, "x_le": xac_w - 0.25 * mac, "AR": AR, "b": b}
    tail = wings.get("Hoehenleitwerk") or wings.get("V-Leitwerk")
    if tail is None:
        out["worlds"] = [xac_w, xac_w]
        return out
    xs = tail["x_secs"]
    S_t, _m, xac_t = surface_geom(xs)
    y_t = xs[-1]["xyz_le"][1] - xs[0]["xyz_le"][1]
    if "V-Leitwerk" in wings:
        nu = math.atan2(xs[-1]["xyz_le"][2] - xs[0]["xyz_le"][2], y_t)
        ar_t = (2 * y_t) ** 2 / (S_t * math.cos(nu))
        S_t = S_t * math.cos(nu) ** 2
    else:
        ar_t = (2 * y_t) ** 2 / S_t
    out["worlds"] = np_worlds(S_w, AR, xac_w, S_t, ar_t, xac_t)
    return out


def cs(name, hinge, symmetric):
    return {"name": name, "hinge_point": hinge, "symmetric": symmetric, "deflection": 0.0}


def build(combo: dict, span: float) -> dict:
    m = combo["mission"]
    band = BAND[m]
    nf = combo["leitwerk"] in NF
    st = STATS["nurfluegel" if nf else m]
    AR = st["ar"][1]
    C, k, _sig, _n = STATS[m]["mass_fit"]
    mass = C * span ** k                                           # BAENDER §2, mission fit
    glider = m in GLIDER
    axes = combo["steuerung"]
    biplane = combo["trag"] == "doppeldecker"

    # ---- wing --------------------------------------------------------------------------------------
    taper = 0.55 if nf else band["taper"]
    S_total = span ** 2 / AR * (2 if biplane else 1)
    c_root = 2 * (S_total / (2 if biplane else 1)) / (span * (1 + taper))
    if nf:  # D8: the mission mass fit is built on tailed aircraft; a flying wing has the higher AR of the
        # flying-wing statistics and so less area per span -> take the mission wing loading instead
        mass = STATS[m]["wl"][1] * S_total * 100 / 1000
    if nf:
        sweep, dih, tw_t = 17.0, 0.0, band["inc"] - 3.0              # BAENDER §3c, D4
    else:
        sweep, tw_t = 0.0, band["inc"]
        if glider:
            dih = None                                               # from Drela B below
        elif combo["lage"] in LENNON_DIHEDRAL:
            dih = LENNON_DIHEDRAL[combo["lage"]][1 if axes == "hs" else 0]
        else:
            dih = 2.0                                                # D5 biplane lower wing
    cuts = {"hs": [0, 1], "hsq": [0, 0.6, 0.95, 1], "hsqk": [0, 0.1, 0.6, 0.95, 1],
            "hq": [0, 0.6, 0.95, 1], "elevon": [0, 0.3, 0.95, 1], "elevon_s": [0, 0.3, 0.95, 1]}[axes]
    z_wing = {"hochdecker": 0.0, "schulterdecker": -0.15, "mitteldecker": -0.5, "tiefdecker": -1.0,
              "ohne_rumpf": -0.5, None: -0.5}[combo["lage"]]       # in fuselage diameters, see below

    # ---- tail sizing needs MAC, so build a provisional wing at dihedral 0 first --------------------
    xs0 = wing_sections(span, c_root, taper, sweep, 0.0, band["inc"], tw_t, cuts)
    _s, mac, xac_w = surface_geom(xs0)
    L = st["len_span"][1] * span                                     # BAENDER §2 [T]
    D = 0.10 * L                                                     # D3
    if nf:
        arm = 0.0
    elif band["arm"] is None:
        arm = 0.6 * L                                                # BAENDER §3b
    else:
        arm = min(band["arm"] * mac, 0.6 * L)                        # [V] fuselage-tail-lever-arm
    vv = None
    if glider and not nf:
        vv = 0.055 if m == "wurf" else (0.03 if axes == "hs" else 0.025)   # Drela
        B_par = 5.25 if axes == "hs" else 3.0                        # Drela preferred
        cl_th = 0.6 if m == "wurf" else 0.7
        dih = B_par * cl_th * span / arm                             # Gamma_eq [deg] = B*C_L*b/l_V (Drela)
        dih = min(dih, 12.0)
    wing_xs = wing_sections(span, c_root, taper, sweep, dih, band["inc"], tw_t, cuts, z0=z_wing * D)

    # control surfaces on the wing (segment start sections)
    def put(i, surf):
        wing_xs[i]["control_surface"] = surf
    if axes in ("hsq", "hq"):
        put(1, cs("aileron", 0.75, False))
        put(2, None)
    if axes == "hsqk":
        put(1, cs("flap", 0.75, True))
        put(2, cs("aileron", 0.75, False))
    if axes in ("elevon", "elevon_s"):
        put(1, [cs("elevon_pitch", 0.8, True), cs("elevon_roll", 0.8, False)])   # mixer: pitch + roll
    for x in wing_xs:
        if x.get("control_surface") is None:
            x.pop("control_surface", None)
        x["airfoil"] = foil("mh45" if nf else band["foil"])

    wings = {"Tragflaeche": {"symmetric": True, "x_secs": wing_xs}}
    if biplane:
        stag, gap = 0.3 * c_root, c_root
        upper = wing_sections(span, c_root, taper, 0.0, 0.0, band["inc"], tw_t, cuts, x0=-stag, z0=z_wing * D + gap)
        for x in upper:
            x["airfoil"] = foil(band["foil"])
        wings = {"Tragflaeche": wings["Tragflaeche"], "Oberfluegel": {"symmetric": True, "x_secs": upper}}
    S_w, mac, xac_w = surface_geom(wing_xs)
    if biplane:  # D5: both wings, area-weighted aerodynamic centre, MAC of one wing
        S_u, _m, xac_u = surface_geom(wings["Oberfluegel"]["x_secs"])
        xac_w = (S_w * xac_w + S_u * xac_u) / (S_w + S_u)
        S_w = S_w + S_u

    # ---- tail ----------------------------------------------------------------------------------
    lw = combo["leitwerk"]
    if not nf:
        S_h = band["vh"] * S_w * mac / arm
        S_v = (vv * S_w * span / arm) if glider else 0.4 * S_h       # Lennon SV/SH 35–50 % (powered)
        AR_h, taper_t = 4.0, 0.7
        xac_h = xac_w + arm
        z_boom = -0.5 * D
        if lw == "v":
            A = S_h + S_v
            nu = math.degrees(math.atan(math.sqrt(S_v / S_h)))      # Drela
            b_v = math.sqrt(AR_h * A)
            c_r = 2 * A / (b_v * (1 + taper_t))
            vt = wing_sections(b_v, c_r, taper_t, 10.0, nu, 0.0, 0.0, [0, 1], x0=xac_h - 0.25 * c_r, z0=z_boom)
            for x in vt[:1]:
                x["control_surface"] = [cs("ruddervator_pitch", 0.7, True),        # mixer: pitch + yaw
                                        cs("ruddervator_yaw", 0.7, False)]
            wings["V-Leitwerk"] = {"symmetric": True, "x_secs": vt}
        else:
            b_h = math.sqrt(AR_h * S_h)
            c_r = 2 * S_h / (b_h * (1 + taper_t))
            h_v = math.sqrt(1.5 * S_v)                               # fin aspect ratio 1.5
            c_v = S_v / h_v
            z_h = {"normal": z_boom, "h": z_boom, "kreuz": z_boom + 0.5 * h_v, "t": z_boom + h_v,
                   "dach": z_boom}.get(lw, z_boom)
            ht = wing_sections(b_h, c_r, taper_t, 5.0, 0.0, 0.0, 0.0, [0, 1], x0=xac_h - 0.25 * c_r, z0=z_h)
            ht[0]["control_surface"] = cs("elevator", 0.7, True)
            wings["Hoehenleitwerk"] = {"symmetric": True, "x_secs": ht}
            fin = [dict(xyz_le=[xac_h - 0.25 * c_v, 0.0, z_boom], chord=c_v * 1.15, twist=0.0,
                        control_surface=cs("rudder", 0.65, True)),
                   dict(xyz_le=[xac_h - 0.25 * c_v + 0.3 * c_v, 0.0, z_boom + h_v], chord=c_v * 0.85, twist=0.0)]
            wings["Seitenleitwerk"] = {"symmetric": False, "x_secs": fin}
        for name in ("V-Leitwerk", "Hoehenleitwerk", "Seitenleitwerk"):
            for x in wings.get(name, {}).get("x_secs", []):
                x["airfoil"] = foil("naca0009")
    else:
        tip = wing_xs[-1]
        if lw == "nf_mitte":
            S_f = 0.10 * S_w
            h = math.sqrt(1.5 * S_f)
            c = S_f / h
            root = wing_xs[0]
            x_te = root["xyz_le"][0] + root["chord"]   # fin sits on the centre section, TE flush (no boom)
            fin = [dict(xyz_le=[x_te - c, 0.0, 0.0], chord=c, twist=0.0,
                        **({"control_surface": cs("rudder", 0.65, True)} if axes == "elevon_s" else {})),
                   dict(xyz_le=[x_te - 0.7 * c, 0.0, h], chord=0.6 * c, twist=0.0)]
            wings["Seitenleitwerk"] = {"symmetric": False, "x_secs": fin}
        elif lw == "nf_winglet":
            S_f = 0.04 * S_w
            h = math.sqrt(1.2 * S_f)
            c = S_f / h
            y, z = tip["xyz_le"][1], tip["xyz_le"][2]
            wl = [dict(xyz_le=[tip["xyz_le"][0], y, z], chord=c, twist=0.0),
                  dict(xyz_le=[tip["xyz_le"][0] + 0.3 * c, y, z + h], chord=0.6 * c, twist=0.0)]
            wings["Winglet"] = {"symmetric": True, "x_secs": wl}
        for name in ("Seitenleitwerk", "Winglet"):
            for x in wings.get(name, {}).get("x_secs", []):
                x["airfoil"] = foil("naca0009")

    # ---- fuselage ------------------------------------------------------------------------------
    fuselages = {}
    if combo["lage"] != "ohne_rumpf":
        tail_end = max(x["xyz_le"][0] + x["chord"] for w in wings.values() for x in w["x_secs"])
        x_nose = tail_end - L
        zc = -0.5 * D
        prof = ([(0, .3), (.1, 1), (.3, 1), (.4, .35), (1, .3)] if glider else
                [(0, .2), (.08, .8), (.2, 1), (.4, 1), (.6, .5), (1, .25)])
        if nf:
            prof = [(0, .2), (.15, 1), (.5, 1), (1, .3)]
            x_nose, L_f = -0.35 * L, 0.6 * L
        else:
            L_f = L
        fuselages["Rumpf"] = {"x_secs": [{"xyz": [x_nose + f * L_f, 0.0, zc], "a": r * D / 2, "b": r * D / 2, "n": 2.0}
                                         for f, r in prof]}

    # ---- CG from the forward edge of the geometric NP worlds (D7) --------------------------------
    ref = geo_np(wings)
    x_np = min(ref["worlds"])
    x_cg = x_np - band["sm"] * ref["mac"]

    add_spars(wings, mass, span)
    for w in wings.values():
        for x in w["x_secs"]:
            c = x.pop("control_surface", None)
            if c:
                x["control_surfaces"] = c if isinstance(c, list) else [c]
    return {"name": combo_id(combo, span), "total_mass_kg": round(mass, 4), "xyz_ref": [x_cg, 0.0, -0.5 * D],
            "wings": wings, "fuselages": fuselages,
            "urmodell": {**combo, "span_m": span, "AR": ref["AR"], "S_m2": ref["S"], "mac_m": ref["mac"],
                         "x_le_ref": ref["x_le"], "x_np_geo_fwd": x_np,
                         "sm_target": band["sm"], "tail_arm_m": arm, "dihedral_deg": dih}}


def combo_id(c, span):
    return "-".join(str(c[k]) for k in ("motor", "mission", "trag", "lage", "leitwerk", "steuerung")) + f"-{int(span*1000)}"


if __name__ == "__main__":
    import shutil
    import sys

    sys.path.insert(0, str(HERE))
    from combos import combos  # noqa: E402

    spans = json.loads((HERE / "spannweiten.json").read_text())
    out = HERE / "fleet"
    out.mkdir(exist_ok=True)
    (out / "airfoils").mkdir(exist_ok=True)
    for f in {"clarky", "naca2412", "naca0015", "e374", "sd7037", "s3021", "rg15", "ag35", "mh45", "naca0009"}:
        shutil.copy(ROOT / "components" / "airfoils" / f"{f}.dat", out / "airfoils" / f"{f}.dat")
    n = 0
    for c in combos():
        span_mm = spans["spannweite_mm"][c["mission"]]
        if c["leitwerk"] in NF and f"{c['mission']}/nurfluegel" in spans.get("nach_bauart_mm", {}):
            span_mm = spans["nach_bauart_mm"][f"{c['mission']}/nurfluegel"]   # hotwing cluster
        a = build(c, span_mm / 1000)
        (out / f"{a['name']}.airplane.json").write_text(json.dumps(a, indent=1))
        n += 1
    print(f"{n} Urmodelle -> {out}")
