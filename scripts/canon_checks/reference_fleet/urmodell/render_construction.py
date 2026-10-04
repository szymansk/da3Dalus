"""Urmodell fleet in the app's construction view (2026-10-04).

Python port of frontend/components/workbench/WingOutlineViewer.tsx (trace builders, colours, line widths,
Plotly layout), rendered to PNG with kaleido: station airfoils + camber, 3 interpolated profiles per
segment, LE/TE edges per segment, TED outline + hinge line, spars (vertical lines, cross-sections,
upper/lower spanwise lines, dashed edges; centre on the camber line as the viewer's fallback without
spare_origin), symmetric mirror, superellipse fuselage. Units: metres, as the viewer.
  python3 render_construction.py  ->  renders_construction/<id>.png
"""

import json
import math
import multiprocessing as mp
import pathlib

import numpy as np

HERE = pathlib.Path(__file__).parent
OUT = HERE / "renders_construction"

C_AIRFOIL, C_CAMBER, C_TED, C_SPAR, C_FUS = "#FF8400", "#7A7B78", "#30A46C", "#6E56CF", "#3B82F6"
BG, GRID = "#17171A", "#2E2E2E"


def airfoil(path):
    pts = []
    for line in (HERE / "fleet" / path[2:]).read_text().splitlines():
        try:
            a, b = (float(v) for v in line.split()[:2])
        except ValueError:
            continue
        if a <= 1.5:
            pts.append((a, b))
    pts = np.array(pts)
    i0 = int(np.argmin(pts[:, 0]))
    up, lo = pts[: i0 + 1][::-1], pts[i0:]
    xg = np.linspace(0, 1, 61)
    yu, yl = np.interp(xg, up[:, 0], up[:, 1]), np.interp(xg, lo[:, 0], lo[:, 1])
    if np.mean(yu - yl) < 0:
        yu, yl = yl, yu
    return {"x": pts[:, 0], "y": pts[:, 1], "xg": xg, "upper": yu, "lower": yl, "camber": (yu + yl) / 2}


def transform(px, py, chord, twist, le, dih):
    """transformProfile(): twist about LE in XZ, then dihedral rotation in YZ."""
    px, py = np.asarray(px, float) * chord, np.asarray(py, float) * chord
    t = math.radians(twist or 0)
    rx = px * math.cos(t) + py * math.sin(t)
    rz = -px * math.sin(t) + py * math.cos(t)
    return le[0] + rx, le[1] - rz * math.sin(dih), le[2] + rz * math.cos(dih)


def line(x, y, z, color, width, dash=None):
    import plotly.graph_objects as go
    return go.Scatter3d(x=list(np.atleast_1d(x)), y=list(np.atleast_1d(y)), z=list(np.atleast_1d(z)), mode="lines",
                        line=dict(color=color, width=width, **({"dash": dash} if dash else {})),
                        showlegend=False, hoverinfo="skip")


def dihedrals(xs):
    out = []
    for i in range(len(xs)):
        a, b = (xs[i], xs[i + 1]) if i < len(xs) - 1 else (xs[i - 1], xs[i])
        out.append(math.atan2(b["xyz_le"][2] - a["xyz_le"][2], b["xyz_le"][1] - a["xyz_le"][1]))
    return out


def lerp_st(a, b, t, da, db):
    return dict(xyz_le=[u + (v - u) * t for u, v in zip(a["xyz_le"], b["xyz_le"], strict=True)],
                chord=a["chord"] + (b["chord"] - a["chord"]) * t, twist=a["twist"] + (b["twist"] - a["twist"]) * t,
                dih=da + (db - da) * t)


def lerp_af(fa, fb, t):
    return {k: fa[k] * (1 - t) + fb[k] * t for k in ("upper", "lower", "camber")} | {"xg": fa["xg"]}


def at(af, key, x):
    return float(np.interp(x, af["xg"], af[key]))


def wing_traces(w):
    xs = w["x_secs"]
    afs = [airfoil(x["airfoil"]) for x in xs]
    dh = dihedrals(xs)
    tr = []
    for x, af, d in zip(xs, afs, dh, strict=True):                       # stations
        tr.append(line(*transform(af["x"], af["y"], x["chord"], x["twist"], x["xyz_le"], d), C_AIRFOIL, 2))
        tr.append(line(*transform(af["xg"], af["camber"], x["chord"], x["twist"], x["xyz_le"], d), C_CAMBER, 1, "dot"))
    for i in range(len(xs) - 1):                                          # interpolated + edges
        for k in (1, 2, 3):
            t = k / 4
            s = lerp_st(xs[i], xs[i + 1], t, dh[i], dh[i + 1])
            f = lerp_af(afs[i], afs[i + 1], t)
            px = np.r_[f["xg"][::-1], f["xg"][1:]]
            py = np.r_[f["upper"][::-1], f["lower"][1:]]
            tr.append(line(*transform(px, py, s["chord"], s["twist"], s["xyz_le"], s["dih"]), C_AIRFOIL, 1))
        a, b = xs[i], xs[i + 1]
        tr.append(line([a["xyz_le"][0], b["xyz_le"][0]], [a["xyz_le"][1], b["xyz_le"][1]],
                       [a["xyz_le"][2], b["xyz_le"][2]], C_AIRFOIL, 2))
        t1 = transform([1], [0], a["chord"], a["twist"], a["xyz_le"], dh[i])
        t2 = transform([1], [0], b["chord"], b["twist"], b["xyz_le"], dh[i + 1])
        tr.append(line([t1[0][0], t2[0][0]], [t1[1][0], t2[1][0]], [t1[2][0], t2[2][0]], C_AIRFOIL, 2))
    for i, x in enumerate(xs):                                            # TEDs (mixer = one outline)
        cs = x.get("control_surfaces")
        if not cs:
            continue
        j = min(i + 1, len(xs) - 1)
        r = cs[0]["hinge_point"]
        h1 = transform([r], [0], x["chord"], x["twist"], x["xyz_le"], dh[i])
        h2 = transform([r], [0], xs[j]["chord"], xs[j]["twist"], xs[j]["xyz_le"], dh[j])
        e1 = transform([1], [0], x["chord"], x["twist"], x["xyz_le"], dh[i])
        e2 = transform([1], [0], xs[j]["chord"], xs[j]["twist"], xs[j]["xyz_le"], dh[j])
        tr.append(line([h1[0][0], h2[0][0]], [h1[1][0], h2[1][0]], [h1[2][0], h2[2][0]], C_TED, 3))
        tr.append(line([h1[0][0], e1[0][0], e2[0][0], h2[0][0], h1[0][0]], [h1[1][0], e1[1][0], e2[1][0], h2[1][0], h1[1][0]],
                       [h1[2][0], e1[2][0], e2[2][0], h2[2][0], h1[2][0]], C_TED, 1.5))
    for i in range(len(xs) - 1):                                          # spars
        for sp in xs[i].get("spare_list", []):
            p, wd = sp["spare_position_factor"], sp["spare_support_dimension_width"]
            st = [lerp_st(xs[i], xs[i + 1], t, dh[i], dh[i + 1]) for t in (0, 1)]
            fa = [lerp_af(afs[i], afs[i + 1], t) for t in (0, 1)]
            cen = []
            for s, f in zip(st, fa, strict=True):
                top = transform([p], [at(f, "upper", p)], s["chord"], s["twist"], s["xyz_le"], s["dih"])
                bot = transform([p], [at(f, "lower", p)], s["chord"], s["twist"], s["xyz_le"], s["dih"])
                tr.append(line([top[0][0], bot[0][0]], [top[1][0], bot[1][0]], [top[2][0], bot[2][0]], C_SPAR, 2))
                c = transform([p], [at(f, "camber", p)], s["chord"], s["twist"], s["xyz_le"], s["dih"])
                cen.append((c[0][0], c[1][0], c[2][0], s["twist"]))
                th = np.linspace(0, 2 * math.pi, 17)
                tr.append(line(c[0][0] + wd / 2 * np.cos(th) * math.cos(math.radians(s["twist"])),
                               np.full(17, c[1][0]), c[2][0] + wd / 2 * np.sin(th), C_SPAR, 1.5))
            for key in ("upper", "lower"):
                q = [transform([p], [at(f, key, p)], s["chord"], s["twist"], s["xyz_le"], s["dih"]) for s, f in zip(st, fa, strict=True)]
                tr.append(line([q[0][0][0], q[1][0][0]], [q[0][1][0], q[1][1][0]], [q[0][2][0], q[1][2][0]], C_SPAR, 1.5))
            for dc, dv in ((0, wd / 2), (0, -wd / 2), (wd / 2, 0), (-wd / 2, 0)):
                (x1, y1, z1, t1), (x2, y2, z2, t2) = cen
                tr.append(line([x1 + dc * math.cos(math.radians(t1)), x2 + dc * math.cos(math.radians(t2))], [y1, y2],
                               [z1 + dv, z2 + dv], C_SPAR, 1, "dash"))
    if w["symmetric"]:
        tr += [t.update(y=[-v for v in t.y]) or t for t in [type(t)(t) for t in tr]]
    return tr


def fuselage_traces(f):
    xs = f["x_secs"]
    tr = [line([x["xyz"][0] for x in xs], [x["xyz"][1] for x in xs], [x["xyz"][2] for x in xs], C_FUS, 1.5, "dash")]

    def pt(x, th):
        c, s = math.cos(th), math.sin(th)
        return (x["xyz"][1] + x["a"] * math.copysign(abs(c) ** (2 / x["n"]), c),
                x["xyz"][2] + x["b"] * math.copysign(abs(s) ** (2 / x["n"]), s))
    for x in xs:
        ths = np.linspace(0, 2 * math.pi, 33)
        yz = [pt(x, t) for t in ths]
        tr.append(line([x["xyz"][0]] * 33, [p[0] for p in yz], [p[1] for p in yz], C_FUS, 1.5))
    for th in (0, math.pi / 2, math.pi, 3 * math.pi / 2):
        yz = [pt(x, th + 1e-10) for x in xs]
        tr.append(line([x["xyz"][0] for x in xs], [p[0] for p in yz], [p[1] for p in yz], C_FUS, 1.5))
    return tr


def render(path):
    import plotly.graph_objects as go
    d = json.loads(path.read_text())
    traces = [t for w in d["wings"].values() for t in wing_traces(w)]
    traces += [t for f in d["fuselages"].values() for t in fuselage_traces(f)]
    ax = dict(showgrid=True, gridcolor=GRID, zerolinecolor="#3A3A3A", color="#7A7B78", title="",
              showticklabels=False, showbackground=False)
    fig = go.Figure(traces)
    fig.update_layout(paper_bgcolor=BG, plot_bgcolor=BG, showlegend=False, margin=dict(l=0, r=0, t=0, b=0),
                      scene=dict(xaxis=ax, yaxis=ax, zaxis=ax, aspectmode="data", bgcolor=BG,
                                 camera=dict(eye=dict(x=-1.95, y=-1.35, z=1.3), up=dict(x=0, y=0, z=1),
                                             projection=dict(type="orthographic"))))
    fig.write_image(OUT / f"{d['name']}.png", width=900, height=640, scale=1)
    return d["name"]


if __name__ == "__main__":
    OUT.mkdir(exist_ok=True)
    files = sorted((HERE / "fleet").glob("*.airplane.json"))
    with mp.get_context("spawn").Pool(4) as pool:
        for n in pool.imap_unordered(render, files):
            print(n, flush=True)
