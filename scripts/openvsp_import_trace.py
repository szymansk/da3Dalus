"""OpenVSP wing import phase-by-phase trace.

Dev tool for debugging mis-imports of OpenVSP ``.vsp3`` files. Loads
a VSP file, replays each phase of ``_handle_wing`` for every WING
geom, and writes a Markdown dashboard with per-phase tables. Compares
the augmenter's assumed u-mapping against VSP's actual surface
parameterization so u-mismatches (a known limitation of the gh-753
augmenter) are obvious at a glance.

Usage:
    poetry run python scripts/openvsp_import_trace.py <path.vsp3> [out.md]

If ``out.md`` is omitted, prints to stdout.
"""

from __future__ import annotations

import math
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

import openvsp as vsp

from app.converters.openvsp_wing_handler import (
    _CAP_PROBE_EPS,
    _CAP_PROBE_US,
    _DEDUP_EPS,
    _N_INTERP_PER_PAIR,
    _W_LE,
    _W_TE,
    _airfoil_placeholder,
    _apply_xform,
    _chord_from_le_te,
    _find_cap_safe_u_max,
    _read_geom_xform,
    _read_relative_flag,
    _read_section_parm,
    _sample_le_te_at,
    sweep_at_le,
)


def _h(text: str, level: int = 2) -> str:
    return f"{'#' * level} {text}\n\n"


def _table(headers: list[str], rows: list[list[str]]) -> str:
    out = "| " + " | ".join(headers) + " |\n"
    out += "| " + " | ".join("---" for _ in headers) + " |\n"
    for r in rows:
        out += "| " + " | ".join(r) + " |\n"
    return out + "\n"


def _fmt(x: float, prec: int = 3) -> str:
    return f"{x:.{prec}f}"


def _probe_anchor_u(gid: str, n_xsec: int) -> list[float]:
    """Probe VSP's actual u-position for each anchor by sampling
    CompPnt01 in a dense grid and finding where each anchor's
    spanwise (y) position aligns.

    Returns a list of u-values, one per xsec. Anchor i's u-position
    is where CompPnt01(u) matches the anchor's body-frame y stored
    on the wing's XSec_<i>.Span cumulative walk.

    VSP doesn't expose anchor-u directly — this is empirical.
    """
    # Sample 200 points along u
    samples = []
    for k in range(201):
        u = k / 200.0
        try:
            p = vsp.CompPnt01(gid, 0, u, _W_LE)
            samples.append((u, p.x(), p.y(), p.z()))
        except Exception:
            samples.append((u, 0.0, 0.0, 0.0))
    return samples


def _trace_wing_phases(gid: str, name: str) -> str:
    out = _h(f"WING `{name}` (gid={gid})", level=2)

    # ───────────────────────────── Phase 1: VSP raw parms
    out += _h("Phase 1 — VSP section parms", level=3)
    xsurf = vsp.GetXSecSurf(gid, 0)
    n_xsec = int(vsp.GetNumXSec(xsurf))
    n_sec = n_xsec - 1
    out += f"`n_xsec = {n_xsec}` ({n_sec} planform sections)\n\n"

    rows = []
    for i in range(1, n_sec + 1):
        row = [str(i)]
        for parm in (
            "Root_Chord",
            "Span",
            "Tip_Chord",
            "Sweep",
            "Sweep_Location",
            "Dihedral",
            "Twist",
        ):
            v = _read_section_parm(vsp, gid, i, parm)
            row.append(_fmt(v))
        rows.append(row)
    out += _table(
        [
            "Section",
            "Root_Chord",
            "Span",
            "Tip_Chord",
            "Sweep°",
            "Sweep_Loc",
            "Dihedral°",
            "Twist°",
        ],
        rows,
    )

    # XForm + relative flags
    out += _h("Phase 1b — XForm + flags", level=3)
    translation, rotation_deg = _read_geom_xform(vsp, gid)
    rel_dih = _read_relative_flag(vsp, gid, "RelativeDihedralFlag")
    rel_twist = _read_relative_flag(vsp, gid, "RelativeTwistFlag")
    out += _table(
        ["Parm", "Value"],
        [
            [
                "Translation (X,Y,Z)",
                f"({translation[0]:.3f}, {translation[1]:.3f}, {translation[2]:.3f})",
            ],
            [
                "Rotation (X,Y,Z)°",
                f"({rotation_deg[0]:.1f}, {rotation_deg[1]:.1f}, {rotation_deg[2]:.1f})",
            ],
            ["RelativeDihedralFlag", str(rel_dih)],
            ["RelativeTwistFlag", str(rel_twist)],
        ],
    )

    # ───────────────────────────── Phase 2: Anchor walk (body frame)
    out += _h("Phase 2 — Anchor walk (BODY frame, pre-XForm)", level=3)
    root_chord = _read_section_parm(vsp, gid, 1, "Root_Chord") or 1.0

    anchors = [{"xyz": [0.0, 0.0, 0.0], "chord": root_chord, "twist": 0.0, "i_sec": 0}]
    cum_x = cum_y = cum_z = 0.0
    cum_dih = cum_tw = 0.0
    prev_chord = root_chord

    for i in range(1, n_sec + 1):
        span = _read_section_parm(vsp, gid, i, "Span")
        tip_chord = _read_section_parm(vsp, gid, i, "Tip_Chord")
        sweep_xref = _read_section_parm(vsp, gid, i, "Sweep")
        sweep_loc = _read_section_parm(vsp, gid, i, "Sweep_Location")
        dih = _read_section_parm(vsp, gid, i, "Dihedral")
        tw = _read_section_parm(vsp, gid, i, "Twist")

        if span <= 0:
            continue
        if rel_dih:
            cum_dih += dih
        else:
            cum_dih = dih
        if rel_twist:
            cum_tw += tw
        else:
            cum_tw = tw

        le_sweep = sweep_at_le(
            sweep_xref_deg=sweep_xref,
            xref=sweep_loc,
            span=span,
            c_root=prev_chord,
            c_tip=tip_chord,
        )
        cum_x += span * math.tan(math.radians(le_sweep))
        cum_y += span * math.cos(math.radians(cum_dih))
        cum_z += span * math.sin(math.radians(cum_dih))

        anchors.append(
            {
                "xyz": [cum_x, cum_y, cum_z],
                "chord": tip_chord if tip_chord > 0 else prev_chord,
                "twist": cum_tw,
                "i_sec": i,
                "le_sweep": le_sweep,
                "cum_dih": cum_dih,
            }
        )
        prev_chord = tip_chord if tip_chord > 0 else prev_chord

    rows = []
    for j, a in enumerate(anchors):
        rows.append(
            [
                str(j),
                f"({_fmt(a['xyz'][0])}, {_fmt(a['xyz'][1])}, {_fmt(a['xyz'][2])})",
                _fmt(a["chord"]),
                _fmt(a["twist"], 1),
            ]
        )
    out += _table(
        ["Anchor #", "xyz (body)", "chord", "twist°"],
        rows,
    )

    # ───────────────────────────── Phase 3: After XForm
    out += _h("Phase 3 — Anchor xyz_le AFTER XForm (world frame)", level=3)
    rows = []
    world_anchors = []
    for j, a in enumerate(anchors):
        xyz_world = _apply_xform(a["xyz"], translation, rotation_deg)
        world_anchors.append(xyz_world)
        rows.append(
            [
                str(j),
                f"({_fmt(xyz_world[0])}, {_fmt(xyz_world[1])}, {_fmt(xyz_world[2])})",
                _fmt(a["chord"]),
                _fmt(a["twist"], 1),
            ]
        )
    out += _table(
        ["Anchor #", "xyz_le (world)", "chord", "twist°"],
        rows,
    )

    # ───────────────────────────── Phase 4: VSP's ACTUAL u-position for each anchor
    out += _h("Phase 4 — VSP's actual u-position per anchor (empirical probe)", level=3)
    out += "Compare augmenter's assumed `u = i/(n_anchors-1)` against VSP's real surface mapping.\n"
    out += "Mismatch → inserts land at wrong spanwise positions.\n\n"

    # Sample VSP surface at fine u-grid to find anchor positions
    samples = []
    for k in range(201):
        u = k / 200.0
        try:
            p_le = vsp.CompPnt01(gid, 0, u, _W_LE)
            samples.append((u, p_le.x(), p_le.y(), p_le.z()))
        except Exception:
            samples.append((u, 0.0, 0.0, 0.0))

    # For each anchor, find the u whose LE-y best matches the world-frame anchor y
    rows = []
    for j, a in enumerate(world_anchors):
        target_y = a[1]
        # Find closest sample
        best_u, best_d = 0.0, float("inf")
        for u_s, _x_s, y_s, _z_s in samples:
            d = abs(y_s - target_y)
            if d < best_d:
                best_d = d
                best_u = u_s
        u_naive = j / (len(world_anchors) - 1) if len(world_anchors) > 1 else 0.0
        rows.append(
            [
                str(j),
                _fmt(u_naive),
                _fmt(best_u),
                _fmt(best_u - u_naive, 3),
                _fmt(target_y),
            ]
        )
    out += _table(
        ["Anchor #", "u (augmenter naïve)", "u (VSP actual)", "Δu", "target y (world)"],
        rows,
    )

    # ───────────────────────────── Phase 5: u-probe table
    out += _h("Phase 5 — Cap-safe u probe (gh-758 _find_cap_safe_u_max)", level=3)
    u_max = _find_cap_safe_u_max(vsp, gid)
    out += f"`u_max = {u_max:.4f}` — inserts with u ≥ u_max are skipped (tip-cap region).\n\n"
    rows = []
    try:
        le_tip, _ = _sample_le_te_at(vsp, gid, 1.0)
    except Exception:
        le_tip = (0.0, 0.0, 0.0)
    for u_p in _CAP_PROBE_US:
        try:
            le_p, te_p = _sample_le_te_at(vsp, gid, u_p)
            d = math.sqrt(sum((le_tip[k] - le_p[k]) ** 2 for k in range(3)))
            distinct = "✓" if d > _CAP_PROBE_EPS else "✗"
            rows.append(
                [
                    _fmt(u_p),
                    f"({_fmt(le_p[0])}, {_fmt(le_p[1])}, {_fmt(le_p[2])})",
                    _fmt(d, 5),
                    distinct,
                ]
            )
        except Exception:
            rows.append([_fmt(u_p), "(raised)", "—", "—"])
    out += _table(["u probe", "LE @u", "dist to LE@1.0", "distinct?"], rows)

    # ───────────────────────────── Phase 6: Augmenter simulation
    out += _h("Phase 6 — Augmenter trace (per-insert outcome)", level=3)
    n_anchors = len(world_anchors)
    rows = []
    out_xsecs = []
    for j, xyz_world in enumerate(world_anchors):
        out_xsecs.append(
            {
                "xyz_le": xyz_world,
                "chord": anchors[j]["chord"],
                "twist": anchors[j]["twist"],
                "role": f"Anchor {j}",
            }
        )
        if j == n_anchors - 1:
            break
        # Naive u-mapping
        u_lo = j / (n_anchors - 1)
        u_hi = (j + 1) / (n_anchors - 1)
        step = (u_hi - u_lo) / (_N_INTERP_PER_PAIR + 1)
        twist_lo = anchors[j]["twist"]
        twist_hi = anchors[j + 1]["twist"]
        for k in range(1, _N_INTERP_PER_PAIR + 1):
            u = u_lo + k * step
            t = k / float(_N_INTERP_PER_PAIR + 1)
            twist_d = twist_lo + (twist_hi - twist_lo) * t
            if u > u_max:
                rows.append([f"{j}→{j + 1}", str(k), _fmt(u), "—", "—", "CAP-CLAMPED"])
                continue
            try:
                le, te = _sample_le_te_at(vsp, gid, u)
            except Exception:
                rows.append([f"{j}→{j + 1}", str(k), _fmt(u), "—", "—", "FAILED (raised)"])
                continue
            chord = _chord_from_le_te(le, te)
            if chord <= 0:
                rows.append(
                    [
                        f"{j}→{j + 1}",
                        str(k),
                        _fmt(u),
                        f"({_fmt(le[0])},{_fmt(le[1])},{_fmt(le[2])})",
                        _fmt(chord),
                        "FAILED (chord≤0)",
                    ]
                )
                continue
            prev_le = out_xsecs[-1]["xyz_le"]
            d = math.sqrt(sum((le[m] - prev_le[m]) ** 2 for m in range(3)))
            if d < _DEDUP_EPS:
                rows.append(
                    [
                        f"{j}→{j + 1}",
                        str(k),
                        _fmt(u),
                        f"({_fmt(le[0])},{_fmt(le[1])},{_fmt(le[2])})",
                        _fmt(chord),
                        "DEDUPED",
                    ]
                )
                continue
            out_xsecs.append(
                {
                    "xyz_le": list(le),
                    "chord": chord,
                    "twist": twist_d,
                    "role": f"Insert {j}→{j + 1} #{k}",
                }
            )
            rows.append(
                [
                    f"{j}→{j + 1}",
                    str(k),
                    _fmt(u),
                    f"({_fmt(le[0])},{_fmt(le[1])},{_fmt(le[2])})",
                    _fmt(chord),
                    "INSERTED",
                ]
            )
    out += _table(
        ["Pair", "k", "u", "LE @u (world)", "chord", "outcome"],
        rows,
    )

    # ───────────────────────────── Phase 7: Final xsec list (what gets persisted)
    out += _h("Phase 7 — Final xsec list (what the DB stores)", level=3)
    rows = []
    prev_le_w = None
    for s, xs in enumerate(out_xsecs):
        le = xs["xyz_le"]
        flag = ""
        if prev_le_w is not None:
            dy = le[1] - prev_le_w[1]
            if dy < -1e-3:
                flag = "⚠ y backwards"
            elif abs(dy) < 1e-3 and abs(le[0] - prev_le_w[0]) < 1e-3:
                flag = "⚠ near-duplicate"
        rows.append(
            [
                str(s),
                xs["role"],
                f"({_fmt(le[0])}, {_fmt(le[1])}, {_fmt(le[2])})",
                _fmt(xs["chord"]),
                _fmt(xs["twist"], 1),
                flag,
            ]
        )
        prev_le_w = le
    out += _table(["sort", "role", "xyz_le", "chord", "twist°", "flag"], rows)

    return out


def main():
    if len(sys.argv) < 2:
        print(__doc__)
        sys.exit(1)
    vsp_path = Path(sys.argv[1]).resolve()
    out_path = Path(sys.argv[2]).resolve() if len(sys.argv) > 2 else None

    vsp.ClearVSPModel()
    vsp.ReadVSPFile(str(vsp_path))

    md = f"# OpenVSP import trace — `{vsp_path.name}`\n\n"
    md += "_Generated by `scripts/openvsp_import_trace.py`_\n\n"

    for gid in vsp.FindGeoms():
        if vsp.GetGeomTypeName(gid) != "Wing":
            continue
        name = vsp.GetGeomName(gid)
        md += "---\n\n"
        md += _trace_wing_phases(gid, name)

    if out_path:
        out_path.write_text(md)
        print(f"Wrote {out_path}")
    else:
        print(md)


if __name__ == "__main__":
    main()
