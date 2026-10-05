"""BRYAN: adverse yaw at a FIXED roll rate, minimised over both ailerons (maintainer's
proposal, 2026-10-01). At equal roll performance the yaw from the roll itself (lift vectors
tilting) is fixed; what the ailerons can change is only their own contribution.

AVL, same model as bryan_aileron_differential.py (inviscid; original airfoil files).
Right aileron up by delta_up (prescribed), left aileron set by AVL so that the rolling
moment is zero at the fixed pb/2V ("d2 rm 0"); alpha trimmed to C_L = W/(qS).
"""

import runpy
import pathlib
import re
import subprocess
from avl_binary import avl_path

ns = runpy.run_path(
    str(pathlib.Path(__file__).parent / "bryan_aileron_differential.py"), run_name="lib"
)
geom, work, atm, m, g, plane = ns["geom"], ns["work"], ns["atm"], ns["m"], ns["g"], ns["plane"]


def run(CL, phat, d_up):
    cmds = [
        "oper",
        f"a c {CL}",
        f"r r {phat}",
        f"d1 d1 {-d_up}",
        "d2 rm 0",
        "b b 0",
        "y y 0",
        "x",
        "",
        "quit",
    ]
    out = subprocess.run(
        [avl_path(), str(geom)],
        input="\n".join(cmds) + "\n",
        capture_output=True,
        text=True,
        cwd=work,
        timeout=60,
    ).stdout

    def get(k):
        f = re.findall(rf"\b{re.escape(k)}\s*=\s*(-?[\d.]+(?:E[-+]?\d+)?)", out)
        if not f:
            raise RuntimeError(out[-2000:])
        return float(f[-1])

    return dict(Cn=get("Cntot"), Cl=get("Cltot"), d_down=get("ail_L"), alpha=get("Alpha"))


V = 1.3 * 5.29
CL = m * g / (0.5 * float(atm.density()) * V**2 * plane.s_ref)
for phat in (0.276, 0.15):
    print(f"\n=== Anflug {V:.2f} m/s, C_L = {CL:.3f}, Rollrate pb/2V = {phat} fest ===")
    for d_up in (0, 5, 10, 15, 20, 25):
        r = run(CL, phat, d_up)
        ratio = f"1:{d_up / r['d_down']:.2f}" if r["d_down"] > 1e-6 else "—"
        print(
            f"  auf {d_up:4.1f} deg   ab {r['d_down']:6.2f} deg   ({ratio:>7})   Cn = {r['Cn']:+.5f}   Cl = {r['Cl']:+.1e}"
        )
