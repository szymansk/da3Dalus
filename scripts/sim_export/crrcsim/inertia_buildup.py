"""Mass moments of inertia by component build-up (Sadraey, Aircraft Design: A Systems Engineering
Approach, section 11.7, eqs. 11.27-11.29): I = sum(I_c + m d^2) about the build-up CG.

Pure geometry/arithmetic. Positions are given in geometry axes (x aft, y right, z up) and converted to
CRRCSim body axes (x forward, y right, z down) here. Component self-inertia is neglected for point
masses (small items, a few mm); the fuselage is a uniform rod and carries I_c = m L^2 / 12.
"""

from __future__ import annotations

from dataclasses import dataclass

import numpy as np


@dataclass(frozen=True)
class PointMass:
    name: str
    mass_kg: float
    x: float  # geometry axes [m]
    y: float
    z: float
    source: str


@dataclass(frozen=True)
class Rod:
    """Uniform rod along geometry x from x0 to x1 at lateral offset 0 and height z."""

    name: str
    mass_kg: float
    x0: float
    x1: float
    z: float
    source: str


@dataclass(frozen=True)
class Buildup:
    ixx: float
    iyy: float
    izz: float
    ixz: float
    mass_kg: float
    cg_geometry: tuple[float, float, float]  # build-up CG in geometry axes [m]


def strip_masses(
    name: str, xsecs, total_mass: float, mirrored: bool, source: str
) -> list[PointMass]:
    """Distribute total_mass over the planform strips proportional to strip area (point mass at the
    mid-chord of each strip); mirrored wings get both halves."""
    strips = []
    for a, b in zip(xsecs[:-1], xsecs[1:], strict=True):
        dy, dz = b.xyz_le[1] - a.xyz_le[1], b.xyz_le[2] - a.xyz_le[2]
        area = 0.5 * (a.chord + b.chord) * float(np.hypot(dy, dz))
        x = 0.5 * ((a.xyz_le[0] + 0.5 * a.chord) + (b.xyz_le[0] + 0.5 * b.chord))
        y = 0.5 * (a.xyz_le[1] + b.xyz_le[1])
        z = 0.5 * (a.xyz_le[2] + b.xyz_le[2])
        strips.append((area, x, y, z))
        if mirrored:
            strips.append((area, x, -y, z))
    total_area = sum(s[0] for s in strips)
    return [
        PointMass(f"{name} strip", total_mass * s[0] / total_area, s[1], s[2], s[3], source)
        for s in strips
    ]


def buildup(points: list[PointMass], rods: list[Rod]) -> Buildup:
    items = [(p.mass_kg, p.x, p.y, p.z, 0.0) for p in points]
    items += [
        (r.mass_kg, 0.5 * (r.x0 + r.x1), 0.0, r.z, r.mass_kg * (r.x1 - r.x0) ** 2 / 12)
        for r in rods
    ]
    m = np.array([i[0] for i in items])
    pos = np.array([[i[1], i[2], i[3]] for i in items])
    cg = (m[:, None] * pos).sum(axis=0) / m.sum()
    d = pos - cg
    # CRRCSim body axes: x forward = -x_geo, z down = -z_geo; squares/products of x,z keep sign rules
    x, y, z = -d[:, 0], d[:, 1], -d[:, 2]
    rod_iyy = np.array([i[4] for i in items])
    ixx = float((m * (y**2 + z**2)).sum())
    iyy = float((m * (x**2 + z**2)).sum() + rod_iyy.sum())
    izz = float((m * (x**2 + y**2)).sum() + rod_iyy.sum())
    ixz = float((m * x * z).sum())
    return Buildup(ixx, iyy, izz, ixz, float(m.sum()), (float(cg[0]), float(cg[1]), float(cg[2])))
