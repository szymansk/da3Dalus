"""Low-poly AC3D (.ac) model of BRYAN from bryan.airplane.json, with CRRCSim animation hinges.

Axes: geometry file x aft / y right / z up  ->  CRRCSim XML axes x fwd / y right / z down, origin at
the plan CG (the origin of the wheel and CG elements)  ->  AC3D axes, by the table in the CRRCSim
airplane documentation (section 6.1): AC3D (X, Y, Z) = (-y_xml, -z_xml, x_xml).

Control surfaces are separate objects (aileron_r, aileron_l, elevator, rudder) so that the XML
`<animations>` section can rotate them about their hinge lines; the rest of each surface stays in a
fixed object. Surfaces are open two-sided skins (no caps): enough for a flight-sim visual.
"""

from __future__ import annotations

import math
import pathlib
from dataclasses import dataclass, field

import numpy as np

K_FRONT, K_REAR = 5, 4  # airfoil stations ahead of / behind the hinge line, per side
N_ST = K_FRONT + K_REAR + 1  # stations per side
UP_H, LO_H = K_REAR, N_ST + K_FRONT - 1  # loop indices of the hinge on the upper / lower side
FUSELAGE_RING = 14  # points per fuselage section


@dataclass
class Mesh:
    name: str
    material: int
    verts: list[tuple[float, float, float]] = field(default_factory=list)  # AC3D axes
    faces: list[tuple[int, ...]] = field(default_factory=list)
    two_sided: bool = True

    def add_vertex(self, p: tuple[float, float, float]) -> int:
        self.verts.append(p)
        return len(self.verts) - 1

    def add_face(self, idx: list[int]) -> None:
        out = [
            i for k, i in enumerate(idx) if i != idx[k - 1]
        ]  # drop repeated corners (degenerate ends)
        if len(set(out)) >= 3:
            self.faces.append(tuple(out))


@dataclass(frozen=True)
class Hinge:
    """Animation spec in CRRCSim XML axes relative to the CG."""

    object_name: str
    mapping: str  # AILERON / ELEVATOR / RUDDER
    p1: tuple[float, float, float]
    p2: tuple[float, float, float]


MATERIALS = [
    ("fuselage", (0.9, 0.9, 0.9)),
    ("wing", (0.85, 0.15, 0.1)),
    ("canopy", (0.3, 0.4, 0.6)),
    ("surface", (0.95, 0.95, 0.95)),
]


def read_dat(path: pathlib.Path) -> tuple[np.ndarray, np.ndarray]:
    """Selig .dat -> (upper, lower) as arrays of (x, z), both ordered LE -> TE."""
    pts = []
    for line in path.read_text().splitlines()[1:]:
        parts = line.split()
        if len(parts) == 2:
            try:
                pts.append((float(parts[0]), float(parts[1])))
            except ValueError:
                continue
    arr = np.array(pts)
    le = int(np.argmin(arr[:, 0]))
    upper = arr[: le + 1][::-1]  # file runs TE -> upper -> LE -> lower -> TE
    lower = arr[le:]
    return upper, lower


def stations(h: float) -> np.ndarray:
    """Chordwise stations 0..1 with the hinge h as station number K_FRONT (cosine-bunched)."""
    front = h * (1 - np.cos(np.linspace(0, np.pi / 2, K_FRONT + 1)))
    rear = h + (1 - h) * np.sin(np.linspace(0, np.pi / 2, K_REAR + 1))
    return np.concatenate([front, rear[1:]])


def loop(
    upper: np.ndarray, lower: np.ndarray, h: float, x_le: tuple[float, float, float], chord: float,
    twist_deg: float, vertical: bool,
) -> list[tuple[float, float, float]]:  # fmt: skip
    """Closed outline TE(upper) -> LE -> TE(lower) in geometry axes. The hinge sits at loop index
    UP_H (upper) and LO_H (lower), the same for every section of a surface."""
    xs = stations(h)
    up = np.interp(xs, upper[:, 0], upper[:, 1])
    lo = np.interp(xs, lower[:, 0], lower[:, 1])
    pts2 = [(x, z) for x, z in zip(xs[::-1], up[::-1], strict=True)]
    pts2 += [(x, z) for x, z in zip(xs[1:], lo[1:], strict=True)]
    th = math.radians(twist_deg)
    out = []
    for x, z in pts2:
        px = chord * (x * math.cos(th) + z * math.sin(th))
        pz = chord * (-x * math.sin(th) + z * math.cos(th))
        if vertical:  # thickness along y for a vertical surface
            out.append((x_le[0] + px, x_le[1] + pz, x_le[2]))
        else:
            out.append((x_le[0] + px, x_le[1], x_le[2] + pz))
    return out


def to_ac(p: tuple[float, float, float], cg: list[float]) -> tuple[float, float, float]:
    """Geometry axes -> AC3D axes about the CG: (X, Y, Z) = (-y, up, forward)."""
    return (-p[1], p[2] - cg[2], cg[0] - p[0])


def to_xml(p: tuple[float, float, float], cg: list[float]) -> tuple[float, float, float]:
    """Geometry axes -> CRRCSim XML axes (x fwd, y right, z down) about the CG."""
    return (cg[0] - p[0], p[1], cg[2] - p[2])


def _skin(mesh: Mesh, a: list[int], b: list[int], lo: int, hi: int) -> None:
    for k in range(lo, hi):
        mesh.add_face([a[k], a[k + 1], b[k + 1], b[k]])


MIN_DY = 0.012  # drop sections closer than this (y-z plane) unless they bound a control surface


def thin_sections(secs: list[dict]) -> list[dict]:
    on = [bool((s.get("control_surface") or {}).get("hinge_point", 0) >= 0.3) for s in secs]
    kept = [0]
    for i in range(1, len(secs) - 1):
        a, b = secs[kept[-1]]["xyz_le"], secs[i]["xyz_le"]
        far = ((a[1] - b[1]) ** 2 + (a[2] - b[2]) ** 2) ** 0.5 >= MIN_DY
        edge = on[i] != on[i - 1] or on[i] != on[i + 1]
        if far or edge:
            kept.append(i)
    last = len(secs) - 1
    a, b = secs[kept[-1]]["xyz_le"], secs[last]["xyz_le"]
    if (
        len(kept) > 1
        and not on[kept[-1]]
        and not on[kept[-2]]  # keep the rib that ends a control surface
        and ((a[1] - b[1]) ** 2 + (a[2] - b[2]) ** 2) ** 0.5 < MIN_DY
    ):
        kept.pop()
    return [secs[i] for i in [*kept, last]]


def surface_meshes(
    name: str,
    w: dict,
    airfoils: dict[str, tuple[np.ndarray, np.ndarray]],
    cg: list[float],
    control: str | None,
    material: int,
) -> tuple[list[Mesh], list[Hinge]]:
    """Fixed mesh(es) plus control-surface mesh(es) of one geometry surface (mirrored if symmetric)."""
    secs = thin_sections(w["x_secs"])
    ctrl = [s.get("control_surface") for s in secs]
    on = [bool(c and c["hinge_point"] >= 0.3) for c in ctrl]
    h_default = next((c["hinge_point"] for c, o in zip(ctrl, on, strict=True) if o), 0.75)
    sides = [1.0, -1.0] if w["symmetric"] else [1.0]
    dy = abs(secs[-1]["xyz_le"][1] - secs[0]["xyz_le"][1])
    dz = abs(secs[-1]["xyz_le"][2] - secs[0]["xyz_le"][2])
    vertical = dz > dy
    meshes: dict[str, Mesh] = {}
    cache: dict[tuple, list[int]] = {}
    hinge_pts: dict[str, list[tuple[float, float, float]]] = {}

    def mesh(key: str, mat: int) -> Mesh:
        return meshes.setdefault(key, Mesh(key, mat))

    for sgn in sides:
        tag = "r" if sgn > 0 else "l"
        loops, idx = [], []
        for j, (s, o, c) in enumerate(zip(secs, on, ctrl, strict=True)):
            # hinge fraction per rib; the first rib past a control carries the previous rib's hinge
            # (the control on rib i covers the segment i -> i+1)
            if o:
                h = c["hinge_point"]
            elif j > 0 and on[j - 1]:
                h = ctrl[j - 1]["hinge_point"]
            else:
                h = h_default
            up, lo = airfoils[s["airfoil"]]
            le = (s["xyz_le"][0], sgn * s["xyz_le"][1], s["xyz_le"][2])
            loops.append(loop(up, lo, h, le, s["chord"], s["twist"], vertical))
        fixed = mesh(name, material)
        for i in range(len(secs) - 1):
            moving = on[i]  # the control on rib i covers the segment i -> i+1
            ncol = len(loops[i])
            # fixed part: front of the hinge on both sides = polyline indices around the leading edge
            f_lo, f_hi = UP_H, LO_H
            target_front = fixed
            if moving:
                key = _ctrl_key(control, tag, w["symmetric"])
                target_rear = mesh(key, 3)
            else:
                target_rear = fixed
            for tgt, lo_i, hi_i in (
                (target_front, f_lo, f_hi),
                (target_rear, 0, f_lo),
                (target_rear, f_hi, ncol - 1),
            ):
                ia = _ring(tgt, cache, tag, i, lo_i, loops[i], cg)
                ib = _ring(tgt, cache, tag, i + 1, lo_i, loops[i + 1], cg)
                _skin(tgt, ia, ib, lo_i, hi_i)
            if moving:
                for j in (i, i + 1):
                    p = loops[j][UP_H]
                    q = loops[j][LO_H]
                    mid = tuple((a + b) / 2 for a, b in zip(p, q, strict=True))
                    hinge_pts.setdefault(_ctrl_key(control, tag, w["symmetric"]), []).append(mid)  # type: ignore[arg-type]
    hinges = _hinges(control, hinge_pts, cg, w["symmetric"], vertical)
    return list(meshes.values()), hinges


def _ring(
    tgt: Mesh, cache: dict, tag: str, sec: int, start: int, pts: list, cg: list[float]
) -> list[int]:
    """Vertex indices of a section loop in `tgt` (shared between the two spans that meet there)."""
    key = (id(tgt), tag, sec, start)
    if key not in cache:
        cache[key] = [tgt.add_vertex(to_ac(p, cg)) for p in pts]
    return cache[key]


def _ctrl_key(control: str | None, tag: str, symmetric: bool) -> str:
    if control == "aileron":
        return f"aileron_{tag}"
    return str(control)


def _hinges(
    control: str | None, pts: dict[str, list[tuple[float, float, float]]], cg: list[float],
    symmetric: bool, vertical: bool,
) -> list[Hinge]:  # fmt: skip
    out: list[Hinge] = []
    if control == "aileron":
        for key, p in pts.items():
            xs = [to_xml(q, cg) for q in p]
            root = min(xs, key=lambda q: abs(q[1]))
            tip = max(xs, key=lambda q: abs(q[1]))
            # right (y>0): axis tip -> root = -y;  left: tip -> root = +y  (positive stick = roll right)
            out.append(Hinge(key, "AILERON", tip, root))
    elif control == "elevator" and pts:
        xs = [to_xml(q, cg) for p in pts.values() for q in p]
        right = max(xs, key=lambda q: q[1])
        left = min(xs, key=lambda q: q[1])
        out.append(
            Hinge("elevator", "ELEVATOR", left, right)
        )  # axis +y: +stick = trailing edge down
    elif control == "rudder" and pts:
        xs = [to_xml(q, cg) for p in pts.values() for q in p]
        top = min(xs, key=lambda q: q[2])
        bottom = max(xs, key=lambda q: q[2])
        out.append(
            Hinge("rudder", "RUDDER", top, bottom)
        )  # axis +z (down): +stick = trailing edge left
    return out


def superellipse_ring(
    a: float, b: float, n: float, m: int = FUSELAGE_RING
) -> list[tuple[float, float]]:
    out = []
    for k in range(m):
        t = 2 * math.pi * k / m
        c, s = math.cos(t), math.sin(t)
        e = 2.0 / max(n, 0.5)
        out.append((a * math.copysign(abs(c) ** e, c), b * math.copysign(abs(s) ** e, s)))
    return out


def fuselage_mesh(name: str, f: dict, cg: list[float], material: int) -> Mesh:
    m = Mesh(name, material)
    rings = []
    for s in f["x_secs"]:
        x, y, z = s["xyz"]
        ring = [(x, y + dy, z + dz) for dy, dz in superellipse_ring(s["a"], s["b"], s["n"])]
        rings.append([m.add_vertex(to_ac(p, cg)) for p in ring])
    for r0, r1 in zip(rings[:-1], rings[1:], strict=True):
        for k in range(len(r0)):
            k2 = (k + 1) % len(r0)
            m.add_face([r0[k], r0[k2], r1[k2], r1[k]])
    return m


def build_model(
    geo: dict, airfoils: dict[str, tuple[np.ndarray, np.ndarray]]
) -> tuple[list[Mesh], list[Hinge]]:
    cg = geo["xyz_ref"]
    meshes: list[Mesh] = []
    hinges: list[Hinge] = []
    plan = {
        "Tragflaeche": ("wing", "aileron", 1),
        "Hoehenleitwerk": ("htail", "elevator", 3),
        "Seitenleitwerk": ("fin", "rudder", 3),
    }
    for gname, (obj, control, mat) in plan.items():
        ms, hs = surface_meshes(obj, geo["wings"][gname], airfoils, cg, control, mat)
        meshes += ms
        hinges += hs
    meshes.append(fuselage_mesh("fuselage", geo["fuselages"]["Rumpf"], cg, 0))
    meshes.append(fuselage_mesh("canopy", geo["fuselages"]["Haube"], cg, 2))
    return meshes, hinges


def render_ac(meshes: list[Mesh]) -> str:
    lines = ["AC3Db"]
    for name, (r, g, b) in MATERIALS:
        lines.append(
            f'MATERIAL "{name}" rgb {r} {g} {b}  amb 0.2 0.2 0.2  emis 0 0 0  spec 0.5 0.5 0.5  shi 10  trans 0'
        )
    lines += ["OBJECT world", f"kids {len(meshes)}"]
    for m in meshes:
        lines += ["OBJECT poly", f'name "{m.name}"', "loc 0 0 0", f"numvert {len(m.verts)}"]
        lines += [f"{x:.5f} {y:.5f} {z:.5f}" for x, y, z in m.verts]
        lines.append(f"numsurf {len(m.faces)}")
        flag = "0x30" if m.two_sided else "0x10"
        for f in m.faces:
            lines += [f"SURF {flag}", f"mat {m.material}", f"refs {len(f)}"]
            lines += [f"{i} 0 0" for i in f]
        lines.append("kids 0")
    return "\n".join(lines) + "\n"


def parse_ac(text: str) -> dict[str, list[tuple[float, float, float]]]:
    """Minimal reader (used by the tests): object name -> vertices."""
    objs: dict[str, list[tuple[float, float, float]]] = {}
    it = iter(text.splitlines())
    if next(it) != "AC3Db":
        raise ValueError("not an AC3D file")
    name = None
    for line in it:
        if line.startswith("name "):
            name = line.split('"')[1]
        elif line.startswith("numvert "):
            n = int(line.split()[1])
            objs[name] = [tuple(float(v) for v in next(it).split()) for _ in range(n)]  # type: ignore[index, misc]
    return objs


def animations_xml(hinges: list[Hinge], throws: dict[str, float]) -> str:
    """<animations> block: gain 1 at full stick, max_angle = throw in rad."""
    out = ["  <animations>"]
    for h in hinges:
        ang = math.radians(throws[h.mapping])
        out += [
            '    <animation type="ControlSurface">',
            f'      <object name="{h.object_name}" max_angle="{ang:.4f}" />',
            f'      <control mapping="{h.mapping}" gain="1.0" />',
            f'      <hinge x="{h.p1[0]:.5f}" y="{h.p1[1]:.5f}" z="{h.p1[2]:.5f}" />',
            f'      <hinge x="{h.p2[0]:.5f}" y="{h.p2[1]:.5f}" z="{h.p2[2]:.5f}" />',
            "    </animation>",
        ]
    out.append("  </animations>")
    return "\n".join(out)
