"""BRYAN (FlugModell 06/26) through the canon's extremal closures.

First member of the reference fleet built from real plans. Geometry from the
maintainer's plan-reconstruction plugin. Assumptions are printed, not hidden:
  * tail airfoil: the plugin's 2 mm balsa plate (bryan_platte.dat)
  * fuselage a, b are half-axes (schema); ASB width/height are full -> 2a, 2b
"""
import json, pathlib, numpy as np, aerosandbox as asb

HERE = pathlib.Path(__file__).parent / "bryan"
d = json.loads((HERE / "bryan.airplane.json").read_text())
plate = asb.Airfoil("bryan_platte", coordinates=str(HERE / "bryan_platte.dat"))
af = {"./bryan_profil.dat": asb.Airfoil("bryan", coordinates=str(HERE / "bryan_profil.dat")),
      "./bryan_platte.dat": plate}

wings = [asb.Wing(name=n, symmetric=w["symmetric"],
                  xsecs=[asb.WingXSec(xyz_le=x["xyz_le"], chord=x["chord"], twist=x["twist"],
                                      airfoil=af[x["airfoil"]]) for x in w["x_secs"]])
         for n, w in d["wings"].items()]
def fus(full):
    return [asb.Fuselage(name=n, xsecs=[asb.FuselageXSec(xyz_c=x["xyz"],
              width=x["a"] * (2 if full else 1), height=x["b"] * (2 if full else 1), shape=x["n"])
              for x in f["x_secs"]]) for n, f in d["fuselages"].items()]

m, g = d["total_mass_kg"], 9.80665
atm = asb.Atmosphere(altitude=0)

def build(full=True):
    return asb.Airplane(name="BRYAN", xyz_ref=d["xyz_ref"], wings=wings, fuselages=fus(full),
                        s_ref=wings[0].area(), c_ref=wings[0].mean_aerodynamic_chord(),
                        b_ref=wings[0].span())

def opt(plane, objective):
    o = asb.Opti()
    V = o.variable(init_guess=8, lower_bound=1, upper_bound=40)
    a = o.variable(init_guess=4, lower_bound=-5, upper_bound=25)
    r = asb.AeroBuildup(plane, asb.OperatingPoint(atm, velocity=V, alpha=a)).run()
    o.subject_to(r["L"] == m * g)
    o.minimize({"V": V, "D": r["D"], "DV": r["D"] * V}[objective])
    s = o.solve(verbose=False, max_iter=300)
    return s(V), s(a), s(r["CL"]), s(r["D"])

plane = build()
w = wings[0]
print("Geometrie        gerechnet     Plan")
print(f"  Spannweite     {w.span()*1000:7.1f} mm   547 mm")
print(f"  Fluegelflaeche {w.area()*100:7.2f} dm2  6,3 dm2")
print(f"  Flaechenbel.   {m*1000/(w.area()*100):7.1f} g/dm2 ab 24 g/dm2")
print(f"  Masse          {m*1000:7.0f} g     ab 150 g")
print(f"  c_MAC          {w.mean_aerodynamic_chord()*1000:7.1f} mm   AR {w.aspect_ratio():.2f}")
print()
for full in (True, False):
    p = build(full)
    print("Rumpf", "voll (2a, 2b) — Schema-konform" if full else "halb (a, b) — wie die App heute")
    for k, name in (("V", "V_S  (min V)"), ("D", "V_md (min D)"), ("DV", "V_mp (min D*V)")):
        V, a, CL, D = opt(p, k)
        Re = atm.density() * V * w.mean_aerodynamic_chord() / atm.dynamic_viscosity()
        print(f"  {name:15s} V={V:6.2f} m/s  alpha={a:6.2f}  CL={CL:5.3f}  "
              f"L/D={m*g/D:5.2f}  sink={D*V/(m*g):5.3f} m/s  Re={Re:,.0f}"
              + ("   [alpha an Schranke]" if abs(a - 25) < 1e-3 or abs(a + 5) < 1e-3 else ""))
    print()
