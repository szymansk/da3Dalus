"""Summarise fleet_results.csv per mission and flag what the canon should look at (2026-10-03)."""

import csv
import pathlib
import statistics as st

HERE = pathlib.Path(__file__).parent
rows = list(csv.DictReader(open(HERE / "fleet_results.csv")))
ok = [r for r in rows if r["status"] == "ok"]


def f(r, k):
    try:
        return float(r[k])
    except (KeyError, ValueError):
        return None


print(f"{len(ok)}/{len(rows)} ok")
for r in rows:
    if r["status"] != "ok":
        print("  ", r["id"], r["status"])

print("\nmission         n   V_S   L/D   sink  SM_target  SM[min..max]  NP spread  AB-NP minus geo  roll AB/AVL")
for m in dict.fromkeys(r["mission"] for r in ok):
    g = [r for r in ok if r["mission"] == m]

    def med(k, g=g):
        v = [f(r, k) for r in g if f(r, k) is not None]
        return st.median(v) if v else float("nan")
    spread = st.median([f(r, "NP_max") - f(r, "NP_min") for r in g])
    ab = st.median([f(r, "NP_AeroBuildup") - f(r, "NP_max") for r in g])
    rr = [f(r, "roll_AB") / f(r, "roll_AVL") for r in g if f(r, "roll_AVL")]
    print(f"{m:14s} {len(g):2d} {med('V_S'):5.2f} {med('LD_max'):5.1f} {med('sink_min'):6.3f} {med('SM_target'):6.1f}"
          f"    {med('SM_min'):5.1f}..{med('SM_max'):5.1f}   {spread:5.1f}      {ab:+6.1f}"
          f"        {st.median(rr) if rr else float('nan'):.2f}")

print("\nFlags")
for r in ok:
    fl = []
    if f(r, "SM_min") < 0:
        fl.append(f"SM_min {r['SM_min']} < 0 (instabil in einer Welt)")
    if f(r, "NP_max") - f(r, "NP_min") > 8:
        fl.append(f"NP-Streuung {f(r, 'NP_max') - f(r, 'NP_min'):.1f} % MAC")
    if f(r, "Cnb") is not None and f(r, "Cnb") <= 0:
        fl.append(f"Cnb {r['Cnb']} <= 0")
    if f(r, "E_spiral") is not None and f(r, "E_spiral") < 0:  # canon: positive = spiral stable
        fl.append(f"Spirale instabil (AB, E {r['E_spiral']})")
    if f(r, "roll_AVL") and abs(f(r, "roll_AB") / f(r, "roll_AVL") - 1) > 0.5:
        fl.append(f"Rollrate AB/AVL {f(r, 'roll_AB') / f(r, 'roll_AVL'):.2f}")
    if fl:
        print(f"  {r['id']}: " + "; ".join(fl))

print("\nNP worlds: which is the forward edge, AeroBuildup offset by layout")
for lay, sel in (("Nurfluegel", lambda r: r["leitwerk"].startswith("nf_")), ("mit Leitwerk", lambda r: not r["leitwerk"].startswith("nf_"))):
    g = [r for r in ok if sel(r)]
    fwd = {}
    for r in g:
        k = min(("NP_Lehrbuch", "NP_Pappas", "NP_AVL"), key=lambda k: f(r, k))
        fwd[k] = fwd.get(k, 0) + 1
    off = sorted(f(r, "NP_AeroBuildup") - f(r, "NP_AVL") for r in g)
    print(f"  {lay:12s} n={len(g)}  vorderer Rand: {fwd}  AB-AVL [% MAC]: min {off[0]:+.1f} median {st.median(off):+.1f} max {off[-1]:+.1f}")
sp = [f(r, "E_spiral") for r in ok]
print(f"\nSpiral (AB): stabil {sum(e > 0 for e in sp)}, instabil {sum(e < 0 for e in sp)} von {len(sp)}")
rr = sorted(f(r, "roll_AB") / f(r, "roll_AVL") for r in ok if f(r, "roll_AVL"))
print(f"Rollrate AB/AVL: n={len(rr)} min {rr[0]:.2f} median {st.median(rr):.2f} max {rr[-1]:.2f}")
