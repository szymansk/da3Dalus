"""Per-mission statistics from the RC-Network model table (2,674 RC models) for the Urmodell bands.

    python3 scripts/selection_fleet_stats.py _reversa_sdd/calculations/auswahl/flottenstatistik.json

The table lives in the rc-aircraft-designer skill vault (not in this repo); the result is
committed as a snapshot. Medians with interquartile range, and a mass fit m = C * b^k
(kg, m) per mission with its scatter factor exp(sigma) of the log residuals.
"""

import json
import math
import re
import sqlite3
import statistics as st
import sys

DB = "/Users/szymanski/expert-skills/rc-aircraft-designer/skills/rc-aircraft-designer/vault/data/flugmodelle.sqlite"
c = sqlite3.connect(DB)
M = {
    "trainer": ["Trainer"],
    "kunstflugtrainer": ["Kunstflugtrainer"],
    "sport": ["Motorflugmodell", "RC-Motorflugmodell", "Motorflugzeug", "Funflyer"],
    "kunstflug": ["Kunstflugmodell", "F3A- Kunstflugmodell", "Kunstflug- Doppeldecker"],
    "3d": ["3D- Kunstflugmodell"],
    "speed": ["Hotliner", "Elektrosegler Hotliner", "Speedmodell"],
    "elektrosegler": ["Elektrosegler", "Einsteiger- Elektrosegler", "Motorsegler"],
    "scale": [
        "Vorbildähnliches Motorflugmodell",
        "Warbird",
        "Scale- Motorflugmodell",
        "Vorbildähnliches Kunstflugmodell",
    ],
    "park": ["Parkflyer", "Kunstflug- Parkflyer"],
    "segel_trainer": ["Einsteiger- Segelflugmodell"],
    "thermik": ["Thermiksegler", "Thermiksegler Klasse RES", "F3J- Segelflugmodell"],
    "hang": ["Hangsegler"],
    "wurf": ["HLG"],
    "scale_segler": ["Vorbildähnliches Segelflugmodell"],
    "nurfluegel": ["Nurflügel", "Nurflügel- Segelflugmodell"],
}


def q(xs):
    xs = sorted(xs)
    if len(xs) < 4:
        return None
    qs = st.quantiles(xs, n=4)
    return (round(qs[0], 1), round(st.median(xs), 1), round(qs[2], 1), len(xs))


out = {}
for m, types in M.items():
    rows = c.execute(
        f"select span_mm,weight_g,wing_area_dm2,aspect_ratio,wing_loading_g_dm2,length_mm,tail_area_dm2 from models where type in ({','.join('?' * len(types))})",
        types,
    ).fetchall()
    wl = [r[4] for r in rows if r[4] and 2 < r[4] < 300]
    ar = []
    for s, _w, a, arc, _, _, _ in rows:
        if s and a and a > 0:
            ar.append((s / 100) ** 2 / a)
        elif arc:
            ar.append(arc)
    ar = [x for x in ar if 2 < x < 40]
    sp = [r[0] for r in rows if r[0] and r[0] > 100]
    ms = [r[1] for r in rows if r[1] and r[1] > 20]
    lf = [r[5] / r[0] for r in rows if r[5] and r[0] and r[0] > 100 and 0.2 < r[5] / r[0] < 2]
    ta = [r[6] / r[2] for r in rows if r[6] and r[2] and 0 < r[6] / r[2] < 0.6]
    pts = [
        (math.log(r[0] / 1000), math.log(r[1] / 1000))
        for r in rows
        if r[0] and r[1] and r[0] > 100 and r[1] > 20
    ]
    fit = None
    if len(pts) >= 6:
        mx = st.mean(p[0] for p in pts)
        my = st.mean(p[1] for p in pts)
        sxx = sum((p[0] - mx) ** 2 for p in pts)
        if sxx > 0:
            k = sum((p[0] - mx) * (p[1] - my) for p in pts) / sxx
            C = math.exp(my - k * mx)
            res = [p[1] - (my + k * (p[0] - mx)) for p in pts]
            s = (sum(r * r for r in res) / (len(pts) - 2)) ** 0.5
            fit = (round(C, 3), round(k, 2), round(math.exp(s), 2), len(pts))
    # electric drive class "NNNW" is the motor's nominal rating, not the flown input power
    pw = []
    for dc, w in c.execute(
        f"select drive_class, weight_g from models where type in ({','.join('?' * len(types))})",
        types,
    ).fetchall():
        hit = re.fullmatch(r"\s*(\d+)\s*W\s*", dc or "")
        if hit and w and w > 50:
            pw.append(int(hit.group(1)) / (w / 1000))
    out[m] = dict(
        w_per_kg=q(pw),
        n=len(rows),
        wl=q(wl),
        ar=q(ar),
        span=q(sp),
        mass=q(ms),
        len_span=q(lf),
        tail_area_ratio=q(ta),
        mass_fit=fit,
    )
json.dump(out, open(sys.argv[1], "w"), ensure_ascii=False, indent=1)


def f(t):
    return "–" if not t else f"{t[1]} [{t[0]}–{t[2]}] n={t[3]}"


print(
    f"{'mission':16} {'n':>3}  {'W/S g/dm2':24} {'AR':22} {'Spanne mm':26} {'Masse g':26} {'L/b':20} {'S_t/S':20} m=C·b^k (kg,m) ×σ"
)
for m, v in out.items():
    ft = v["mass_fit"]
    fs = f"C={ft[0]} k={ft[1]} ×{ft[2]} n={ft[3]}" if ft else "–"
    print(
        f"{m:16} {v['n']:>3}  {f(v['wl']):24} {f(v['ar']):22} {f(v['span']):26} {f(v['mass']):26} {f(v['len_span']):20} {f(v['tail_area_ratio']):20} {fs}"
    )
