"""Full-throttle thrust from the coupled motor-propeller equilibrium, and its sensitivity to the
winding resistance R_m, which the parts catalogue does not carry (Gates fit R = 0.0467*I0^-1.892
as stand-in, varied x0.5 / x2). Motor AL 28-13 from the DB, APC 6x4E measured table, 2S nominal."""

import sqlite3
import numpy as np
from scipy.optimize import brentq

c = sqlite3.connect("db/test.db")
pid, D_in = c.execute(
    "select id,diameter_in from propeller_polars where name='APC 6x4E'"
).fetchone()
rows = np.array(
    c.execute(
        "select rpm,J,Ct,Cp from propeller_polar_samples where propeller_id=?", (pid,)
    ).fetchall()
)
D = D_in * 0.0254
rho = 1.225
RPMS = np.unique(rows[:, 0])


def tab(col):
    def f(rpm, J):
        i = np.clip(np.searchsorted(RPMS, rpm), 1, len(RPMS) - 1)
        r0, r1 = RPMS[i - 1], RPMS[i]

        def g(r):
            return np.interp(J, rows[rows[:, 0] == r, 1], rows[rows[:, 0] == r, col])

        w = (rpm - r0) / (r1 - r0)
        return (1 - w) * g(r0) + w * g(r1)

    return f


ct = tab(2)
cp = tab(3)
kv, I0, U = 1360, 0.4, 2 * 3.7  # D-Power AL 28-13 (DB), 2S nominal
R0 = 0.0467 * I0**-1.892  # Gates fit


def point(V, R):
    def f(n):  # motor torque - prop torque, n in rev/s
        rpm = n * 60
        J = V / (n * D)
        current = (U - rpm / kv) / R
        Qm = (current - I0) / (kv * np.pi / 30)
        Qp = cp(rpm, J) * rho * n**2 * D**5 / (2 * np.pi)
        return Qm - Qp

    lo = max(rows[:, 0].min() / 60, V / (D * 0.6))
    n = brentq(f, lo, U * kv / 60 * 0.999)
    rpm = n * 60
    J = V / (n * D)
    return ct(rpm, J) * rho * n**2 * D**4, rpm, (U - rpm / kv) / R


print(f"AL 28-13 (1360 Kv, I0 0.4 A) + APC 6x4E an 2S 7,4 V; R aus Gates-Fit = {R0:.3f} Ohm")
for V in (0, 6, 8, 10):
    out = [point(V, R0 * k) for k in (0.5, 1, 2)]
    T = [o[0] for o in out]
    print(
        f"V={V:2d} m/s  T[N] R/2={T[0]:.2f}  R={T[1]:.2f}  2R={T[2]:.2f}   (rpm {out[1][1]:.0f}, I {out[1][2]:.1f} A)  Spanne {100 * (T[0] - T[2]) / T[1]:.0f} %"
    )
