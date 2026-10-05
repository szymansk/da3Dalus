import time
import numpy as np
import aerosandbox as asb

m, g = 1.5, 9.81
af = asb.Airfoil("naca2412")
wing = asb.Wing(
    name="Main Wing",
    symmetric=True,
    xsecs=[
        asb.WingXSec(xyz_le=[0, 0, 0], chord=0.20, airfoil=af),
        asb.WingXSec(xyz_le=[0, 0.70, 0], chord=0.20, airfoil=af),
    ],
)
plane = asb.Airplane(name="rc-trainer", xyz_ref=[0.05, 0, 0], wings=[wing])
S = plane.s_ref
atm = asb.Atmosphere(altitude=0)
rho = float(atm.density())

# (a) Fixpunktiteration, wie im Kanon beschrieben
t0 = time.time()
V = 10.0
hist = []
alphas = np.arange(0, 22.01, 0.25)
for _it in range(10):
    r = asb.AeroBuildup(
        plane, asb.OperatingPoint(atm, velocity=np.full_like(alphas, V), alpha=alphas)
    ).run()
    clmax = float(np.max(r["CL"]))
    Vn = np.sqrt(2 * m * g / (rho * S * clmax))
    hist.append(Vn)
    if abs(Vn - V) / V < 1e-4:
        V = Vn
        break
    V = Vn
t_fp = time.time() - t0

# (b) Dem Solver ueberlassen: minimiere V unter L = m g
t0 = time.time()
opti = asb.Opti()
Vo = opti.variable(init_guess=10, lower_bound=2, upper_bound=40)
a = opti.variable(init_guess=10, lower_bound=0, upper_bound=25)
aero = asb.AeroBuildup(plane, asb.OperatingPoint(atm, velocity=Vo, alpha=a)).run()
opti.subject_to(aero["L"] == m * g)
opti.minimize(Vo)
sol = opti.solve(verbose=False)
t_op = time.time() - t0
Vs, As, CL = sol(Vo), sol(a), sol(aero["CL"])

print(
    f"Fixpunkt : V_S = {V:.4f} m/s  nach {len(hist)} Laeufen  ({t_fp:.1f} s)  Verlauf {[round(x, 3) for x in hist]}"
)
print(f"Opti     : V_S = {Vs:.4f} m/s  bei alpha = {As:.2f} deg, C_L = {CL:.4f}  ({t_op:.1f} s)")
print(f"Abweichung: {100 * abs(Vs - V) / V:.3f} %")
print(
    f"Probe: Re an der Fluegelwurzel bei V_S = {rho * Vs * 0.20 / float(atm.dynamic_viscosity()):.0f}"
)
