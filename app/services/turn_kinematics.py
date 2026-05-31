"""gh-806: steady coordinated level-turn kinematics.

Pure functions, no I/O. Convention: right turn (phi > 0); mirror lateral signs for
a left turn. Body rates are DIMENSIONAL (rad/s) — AeroBuildup / the AVL pipeline
non-dimensionalize internally. v1 uses theta=0 (p=0); the alpha_deg hook lets a later
refinement recompute with the solved angle of attack.
"""

from __future__ import annotations

import math
from dataclasses import dataclass

_G = 9.81


@dataclass(frozen=True)
class TurnKinematics:
    n: float          # load factor = 1/cos(phi)
    psi_dot: float    # heading rate (rad/s)
    p: float          # body roll rate (rad/s)
    q: float          # body pitch rate (rad/s)
    r: float          # body yaw rate (rad/s)
    cl_factor: float  # CL_turn / CL_1g == n


def turn_kinematics(bank_deg: float, velocity: float, alpha_deg: float = 0.0) -> TurnKinematics:
    """Body-axis kinematics of a steady coordinated level turn at bank ``bank_deg``."""
    phi = math.radians(bank_deg)
    theta = math.radians(alpha_deg)
    cos_phi = math.cos(phi)
    n = 1.0 / cos_phi if abs(cos_phi) > 1e-9 else float("inf")
    v = max(float(velocity), 1e-6)
    psi_dot = _G * math.tan(phi) / v
    p = -psi_dot * math.sin(theta)
    q = psi_dot * math.cos(theta) * math.sin(phi)
    r = psi_dot * math.cos(theta) * cos_phi
    return TurnKinematics(n=n, psi_dot=psi_dot, p=p, q=q, r=r, cl_factor=n)
