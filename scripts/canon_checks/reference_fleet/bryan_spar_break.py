"""BRYAN main spar: break load factor n_break,+/- (canon spar-break-load-factor) and m_max,struct.

  n_break = min over y  M_cap(y) / |M_1g(y)|        m_max,struct = n_break * m

Spar (bryan.konstruktion.json): I-spar, flanges birch plywood 1.0 x 4.0 mm, flush with the contour,
web balsa 2.0 mm; total height = the spar's local height in bryan.airplane.json; no joiner.
Attachments ignored, strength only (maintainer 2026-10-01, BR-W18).

Declared material assumptions (ADR 0023 — source and its limits):
  * compression flange: birch 3-ply, face grain spanwise -> 2 of 3 plies carry. Yellow birch
    compression parallel to grain 56.3 MPa at 12 % moisture (USDA FPL Wood Handbook, GTR-282,
    Table 5-3b) x 2/3 = 37.5 MPa.
  * tension flange: 3-ply birch tensile parallel to face grain 13,210 psi = 91.1 MPa
    (NACA Report 84, Elmendorf 1920, Table 4).
  * symmetric I-spar: upward bending puts the upper flange in compression, downward the lower;
    the weaker flange (compression) governs both directions.
  * 1 g lift distribution by Schrenk's approximation; wing weight relief neglected
    (conservative); fuselage carry-through as a cantilever from the root.
"""

import json
import pathlib

import numpy as np

HERE = pathlib.Path(__file__).parent / "bryan"
d = json.loads((HERE / "bryan.airplane.json").read_text())
M0, G = d["total_mass_kg"], 9.80665
SIGMA_C, SIGMA_T = 37.5e6, 91.1e6
B_FL, T_FL, T_WEB = 4.0e-3, 1.0e-3, 2.0e-3

wing_d = d["wings"]["Tragflaeche"]
xs = wing_d["x_secs"]

# spar height along the span (main spar = first entry of spare_list)
y_st = np.array([x["xyz_le"][1] for x in xs if x.get("spare_list")])
h_st = np.array([x["spare_list"][0]["spare_support_dimension_height"] for x in xs if x.get("spare_list")])


def m_cap(y):
    h = np.interp(y, y_st, h_st)
    inertia = B_FL * h**3 / 12 - (B_FL - T_WEB) * (h - 2 * T_FL) ** 3 / 12
    return SIGMA_C * inertia / (h / 2), SIGMA_T * inertia / (h / 2), h


# 1 g spanwise lift by Schrenk's approximation (NACA TM 948, 1940): the mean of the planform-
# proportional and the elliptic distribution. (The VLM on this geometry was numerically broken by the
# tiny round-tip sections, so it is not used.)
yc_all = np.array([x["xyz_le"][1] for x in xs])
c_all = np.array([x["chord"] for x in xs])
b_half = yc_all.max()
yr = np.linspace(0.0, b_half, 400)
dy = yr[1] - yr[0]
c_y = np.interp(yr, yc_all, c_all)
s_half = np.trapezoid(c_y, yr)
L_half = M0 * G / 2
l_plan = L_half * c_y / s_half
l_ell = 4 * L_half / (np.pi * b_half) * np.sqrt(np.clip(1 - (yr / b_half) ** 2, 0, None))
fr = 0.5 * (l_plan + l_ell) * dy
print(f"Schrenk: Halbspannweite {b_half*1000:.0f} mm, Halbflügelauftrieb {fr.sum():.3f} N (Soll {L_half:.3f} N)")

ys = np.linspace(0.0, y_st.max(), 60)
rows = []
for y in ys:
    m1g = float(np.sum(fr[yr > y] * (yr[yr > y] - y)))
    mc, mt, h = m_cap(y)
    rows.append((y, h, m1g, mc, mt, mc / m1g if m1g > 1e-6 else np.inf))
rows = np.array(rows)
i = int(np.argmin(rows[:, 5]))
n_break = rows[i, 5]
print("\n   y [mm]  h [mm]  M_1g [Nmm]  M_cap,Druck [Nmm]  n = M_cap/M_1g")
for r in rows[:: max(1, len(rows) // 10)]:
    print(f"   {r[0]*1000:6.1f}  {r[1]*1000:6.2f}  {r[2]*1000:9.1f}  {r[3]*1000:12.0f}      {r[5]:7.1f}")
print(f"\n  maßgebend bei y = {rows[i,0]*1000:.0f} mm (h = {rows[i,1]*1000:.1f} mm)")
print(f"  n_break,+ = n_break,- = {n_break:.1f}   (Druckgurt maßgebend; Zuggurt allein: {rows[i,4]/rows[i,2]:.1f})")
print(f"  m_max,struct = n_break * m = {n_break*M0*1000:.0f} g")
for s in (25e6, 50e6):
    print(f"  Empfindlichkeit: sigma_Druck {s/1e6:.0f} MPa -> n_break {n_break*s/SIGMA_C:.1f}")
