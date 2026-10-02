"""BRYAN through the canon's stability entries and the mass envelope.

Canon entries computed (formulas/*.md):
  neutral-point, static-margin, cg-for-target-margin, lateral-static-stability-md/-app,
  mass-envelope (V_S(m), V_max(m), ROC_max(m), m_max,level, m_max,TO, CG envelope).

Declared assumptions (printed again in the output):
  * geometry, mass 151 g and the plan CG (xyz_ref) from the plan reconstruction (bryan.airplane.json)
  * fuselage a, b are half-axes (schema) -> ASB width/height 2a, 2b
  * thrust: variant A (Pulsar 1510, 2000 KV, 2S, APC 6x4E), route A power-limited to 45 W x 0.85
    (O11); propeller drag beyond zero thrust not modelled
  * elevator throw +-14 deg as constructed (positive = trailing edge down, ASB convention)
  * k_S: V_TO = 1.2 V_S,TO and V_app = 1.3 V_S0 (open canon item k_S; BRYAN has no flaps,
    so V_S,TO = V_S0 = V_S)
"""

import json
import pathlib
import sqlite3

import aerosandbox as asb
import aerosandbox.numpy as anp
import numpy as np
from scipy.optimize import brentq

HERE = pathlib.Path(__file__).parent / "bryan"
d = json.loads((HERE / "bryan.airplane.json").read_text())
AF = {
    "./bryan_profil.dat": asb.Airfoil("bryan", coordinates=str(HERE / "bryan_profil.dat")),
    "./bryan_platte.dat": asb.Airfoil("bryan_platte", coordinates=str(HERE / "bryan_platte.dat")),
}
M0, G = d["total_mass_kg"], 9.80665
X_CG_PLAN, Z_REF = d["xyz_ref"][0], d["xyz_ref"][2]
atm = asb.Atmosphere(altitude=0)
RHO = float(atm.density())
K_TO, K_APP, DELTA_E = 1.2, 1.3, 14.0


def build(delta_e=0.0, x_ref=X_CG_PLAN):
    wings = []
    for name, w in d["wings"].items():
        xs = []
        for x in w["x_secs"]:
            cs = []
            if "control_surface" in x and x["control_surface"]["name"] == "Hoehenruder":
                cs = [asb.ControlSurface(name="elevator", symmetric=True,
                                         hinge_point=x["control_surface"]["hinge_point"],
                                         deflection=delta_e)]
            xs.append(asb.WingXSec(xyz_le=x["xyz_le"], chord=x["chord"], twist=x["twist"],
                                   airfoil=AF[x["airfoil"]], control_surfaces=cs))
        wings.append(asb.Wing(name=name, symmetric=w["symmetric"], xsecs=xs))
    fus = [asb.Fuselage(name=n, xsecs=[asb.FuselageXSec(xyz_c=x["xyz"], width=2 * x["a"],
                                                         height=2 * x["b"], shape=x["n"])
                                        for x in f["x_secs"]])
           for n, f in d["fuselages"].items()]
    return asb.Airplane(name="BRYAN", xyz_ref=[x_ref, 0, Z_REF], wings=wings, fuselages=fus,
                        s_ref=wings[0].area(), c_ref=wings[0].mean_aerodynamic_chord(),
                        b_ref=wings[0].span())


plane = build()
W = plane.wings[0]
MAC = W.mean_aerodynamic_chord()
X_MAC_LE = W.aerodynamic_center()[0] - 0.25 * MAC


def sc(v):
    return float(np.ravel(v)[0])


def pct(x):
    return 100 * (x - X_MAC_LE) / MAC


# --- thrust, route A power-limited (same model as bryan_route_a.py) -------------------------
db = sqlite3.connect(pathlib.Path(__file__).parents[3] / "db" / "test.db")
pid, d_in = db.execute("select id,diameter_in from propeller_polars where name='APC 6x4E'").fetchone()
rows = np.array(db.execute("select rpm,J,Ct,Cp from propeller_polar_samples where propeller_id=?",
                           (pid,)).fetchall())
DP, RPMS = d_in * 0.0254, np.unique(rows[:, 0])


def coef(rpm, J, col):
    i = int(np.clip(np.searchsorted(RPMS, rpm), 1, len(RPMS) - 1))
    r0, r1 = RPMS[i - 1], RPMS[i]

    def f(r):
        return np.interp(J, rows[rows[:, 0] == r, 1], rows[rows[:, 0] == r, col], right=0.0)

    w = np.clip((rpm - r0) / (r1 - r0), 0, 1)
    return (1 - w) * f(r0) + w * f(r1)


RPM_FREE, P_SHAFT = 2000 * 2 * 3.7, 45 * 0.85


def thrust(V):
    def p_excess(r):
        return coef(r, V / (r / 60 * DP), 3) * RHO * (r / 60) ** 3 * DP ** 5 - P_SHAFT

    rpm = brentq(p_excess, 3000, RPM_FREE) if p_excess(RPM_FREE) > 0 else RPM_FREE
    n = rpm / 60
    return max(coef(rpm, V / (n * DP), 2), 0) * RHO * n ** 2 * DP ** 4


VG = np.linspace(0, 40, 81)
TM = asb.InterpolatedModel({"V": VG}, np.array([thrust(v) for v in VG]), method="bspline")


# --- canon problems ----------------------------------------------------------------------------
def aero(p, V, a):
    return asb.AeroBuildup(p, asb.OperatingPoint(atm, velocity=V, alpha=a)).run()


def level(m, objective, V0=10.0):
    """Level flight L = m g; objective 'VS' (min V), 'Vmd' (min D), 'Vmax' (max V, T >= D)."""
    o = asb.Opti()
    V = o.variable(init_guess=V0, lower_bound=1, upper_bound=40)
    a = o.variable(init_guess=3, lower_bound=-8, upper_bound=25)
    r = aero(plane, V, a)
    o.subject_to(r["L"] == m * G)
    if objective == "VS":
        o.minimize(V)
    elif objective == "Vmd":
        o.minimize(r["D"])
    else:
        o.subject_to(TM({"V": V}) >= r["D"])
        o.maximize(V)
    s = o.solve(verbose=False, max_iter=500)
    return float(s(V)), float(s(a))


def vmax(m):
    best = None
    for v0 in (12, 20, 30):
        try:
            v = level(m, "Vmax", v0)
            best = v if best is None or v[0] > best[0] else best
        except RuntimeError:
            pass
    return best


def roc_max(m):
    o = asb.Opti()
    V = o.variable(init_guess=10, lower_bound=2, upper_bound=40)
    a = o.variable(init_guess=3, lower_bound=-8, upper_bound=25)
    gam = o.variable(init_guess=0.3, lower_bound=0, upper_bound=np.pi / 2)
    r = aero(plane, V, a)
    o.subject_to([r["L"] == m * G * anp.cos(gam), TM({"V": V}) - r["D"] >= m * G * anp.sin(gam)])
    o.maximize(V * anp.sin(gam))
    s = o.solve(verbose=False, max_iter=500)
    return float(s(V * anp.sin(gam))), float(s(V))


def excess_thrust_at(m, V):
    o = asb.Opti()
    a = o.variable(init_guess=5, lower_bound=-8, upper_bound=25)
    r = aero(plane, V, a)
    o.subject_to(r["L"] == m * G)
    o.minimize(r["D"])
    s = o.solve(verbose=False, max_iter=500)
    return float(TM({"V": V})) - float(s(r["D"]))


def stab(V, m, x_ref=X_CG_PLAN):
    o = asb.Opti()
    a = o.variable(init_guess=3, lower_bound=-8, upper_bound=25)
    o.subject_to(aero(plane, V, a)["L"] == m * G)
    al = float(o.solve(verbose=False, max_iter=500)(a))
    return asb.AeroBuildup(build(0.0, x_ref), asb.OperatingPoint(atm, velocity=V, alpha=al)) \
        .run_with_stability_derivatives(), al


def trim_cg_at_alpha(m, alpha, delta_e, x_max):
    """Forward limit (Sadraey Eq. 12.90): x_CG at which full up elevator just holds the stall angle
    alpha (C_L,max); the speed is free because the tail download raises the trimmed stall speed."""
    o = asb.Opti()
    V = o.variable(init_guess=8, lower_bound=1, upper_bound=40)
    # the forward limit lies ahead of the neutral point; behind it Cm = 0 has a second, unstable root
    x = o.variable(init_guess=X_CG_PLAN - 0.03, lower_bound=-0.5, upper_bound=x_max)
    r = aero(build(delta_e, x), V, alpha)
    o.subject_to([r["L"] == m * G, r["Cm"] == 0])
    s = o.solve(verbose=False, max_iter=500)
    return float(s(x)), float(s(V))


def trim_cg(m, V, delta_e):
    """x_CG at which the aircraft trims (L = m g, Cm = 0) at speed V with elevator delta_e."""
    o = asb.Opti()
    a = o.variable(init_guess=4, lower_bound=-8, upper_bound=25)
    x = o.variable(init_guess=X_CG_PLAN, lower_bound=-0.5, upper_bound=1.5)
    r = aero(build(delta_e, x), V, a)
    o.subject_to([r["L"] == m * G, r["Cm"] == 0])
    s = o.solve(verbose=False, max_iter=500)
    return float(s(x)), float(s(a))


# --- run ---------------------------------------------------------------------------------------
print("Annahmen: Rumpf-Halbachsen x2; Schub Route A leistungsbegrenzt (45 W x 0,85, APC 6x4E, 2S);")
print(f"          Höhenruder ±{DELTA_E:.0f}° wie gebaut; k_S Start {K_TO}, Anflug {K_APP} (k_S offen)")
print(f"\nGeometrie: MAC {MAC*1000:.1f} mm, MAC-Vorderkante x = {X_MAC_LE*1000:.1f} mm, "
      f"S = {W.area()*1e4:.1f} cm², m = {M0*1000:.0f} g")

v_md, _ = level(M0, "Vmd")
r_md, a_md = stab(v_md, M0)
x_np = sc(r_md["x_np"])
sm = (x_np - X_CG_PLAN) / MAC
print("\n== Längsstabilität (neutral-point, static-margin)")
print(f"  V_md = {v_md:.2f} m/s, alpha = {a_md:.2f}°")
print(f"  Neutralpunkt x_NP = {x_np*1000:.1f} mm  = {pct(x_np):.1f} % MAC")
print(f"  Schwerpunkt Plan  = {X_CG_PLAN*1000:.1f} mm  = {pct(X_CG_PLAN):.1f} % MAC")
print(f"  Stabilitätsmaß SM = {100*sm:.1f} % MAC")
for t in (0.05, 0.10, 0.15):
    print(f"  cg-for-target-margin SM {t:.0%}: x_CG = {(x_np - t*MAC)*1000:.1f} mm = {pct(x_np - t*MAC):.1f} % MAC")

v_s, _ = level(M0, "VS")
print("\n== Seitenstabilität (lateral-static-stability)")
for label, V in (("V_md", v_md), (f"Anflug {K_APP}·V_S", K_APP * v_s)):
    r, al = stab(V, M0)
    clb, cnb, clr, cnr = (sc(r[k]) for k in ("Clb", "Cnb", "Clr", "Cnr"))
    print(f"  {label:14s} V={V:5.2f} alpha={al:5.2f}°  C_lβ={clb:+.4f}  C_nβ={cnb:+.4f}  "
          f"C_lr={clr:+.4f}  C_nr={cnr:+.4f}  E_spiral={clb*cnr - cnb*clr:+.5f}")

print("\n== Massenhüllkurve (mass-envelope)")
print(f"   m [g]  V_S    V_max  ROC_max  T-D bei V_TO   x_fwd %MAC (getrimmtes V_S)   x_aft %MAC (Ruder)   [NP {pct(x_np):.1f} %MAC, Plan-SP {pct(X_CG_PLAN):.1f} %MAC]")
def tryf(f):
    try:
        return f()
    except RuntimeError:
        return None


def fmt(v, spec):
    return format(v, spec) if v is not None else "  –  "


for m in (0.10, 0.151, 0.20, 0.30, 0.50, 0.80, 1.10):
    vsa = tryf(lambda m=m: level(m, "VS"))
    vs = vsa[0] if vsa else None
    vm = tryf(lambda m=m: vmax(m))
    rc = tryf(lambda m=m: roc_max(m)[0])
    ex = tryf(lambda m=m, vs=vs: excess_thrust_at(m, K_TO * vs)) if vs else None
    xfv = tryf(lambda m=m, vsa=vsa: trim_cg_at_alpha(m, vsa[1], -DELTA_E, x_np)) if vsa else None
    xf = pct(xfv[0]) if xfv else None
    xa = tryf(lambda m=m, vm=vm: pct(trim_cg(m, vm[0], +DELTA_E)[0])) if vm else None
    print(f"   {m*1000:5.0f}  {fmt(vs, '5.2f')}  {fmt(vm[0] if vm else None, '5.2f')}  {fmt(rc, '6.2f')}   "
          f"{fmt(ex, '+6.3f')} N     {fmt(xf, '7.1f')} (V {fmt(xfv[1] if xfv else None, '4.1f')})   "
          f"{fmt(xa, '7.1f')}" + ("  -> hinten begrenzt zuerst der NP" if xa is not None and xa > pct(x_np) else ""))

o = asb.Opti()
mm = o.variable(init_guess=0.3, lower_bound=0.05, upper_bound=2.0)
V = o.variable(init_guess=10, lower_bound=2, upper_bound=40)
a = o.variable(init_guess=5, lower_bound=-8, upper_bound=25)
r = aero(plane, V, a)
o.subject_to([r["L"] == mm * G, TM({"V": V}) >= r["D"]])
o.maximize(mm)
s = o.solve(verbose=False, max_iter=800)
print(f"\n  m_max,level = {float(s(mm))*1000:.0f} g  (bei V = {float(s(V)):.2f} m/s)")


def ex_to(m):
    return excess_thrust_at(m, K_TO * level(m, "VS")[0])


m_to = brentq(ex_to, 0.15, float(s(mm)) - 1e-3, xtol=1e-3)
print(f"  m_max,TO    = {m_to*1000:.0f} g  (Schubüberschuss bei V_TO = {K_TO}·V_S verschwindet)")
