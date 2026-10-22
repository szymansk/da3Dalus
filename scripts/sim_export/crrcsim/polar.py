"""Polar post-processing for the CRRCSim export (pure numpy, no solver imports).

CRRCSim's lift and drag model (larcsim.cpp):
  CL_wing  = CL_0 + CL_a (alpha - Alpha_0), clipped at CL_max / CL_min and dropped by CL_drop
  CD       = (CD_prof + CD_CLsq (CL - CL_CD0)^2) (V / U_ref)^Uexp_CD
             + (|CL| + 2 |Cl_w|)^2 S_ref / (B_ref^2 pi span_eff) + stall term
so the polar is split into an induced part with the *declared* span efficiency and a profile
parabola in CL.
"""

from __future__ import annotations

from dataclasses import dataclass

import numpy as np

# slope threshold of the negative-side stall knee, as a fraction of the pre-stall lift slope
KNEE_SLOPE_FRACTION = 0.25
# plateau window behind the first C_L peak [deg] used for CL_drop / CD_stall
PLATEAU_FROM_DEG = 5.0
PLATEAU_TO_DEG = 13.0
# profile-drag fit range: from alpha_fit_lo to this fraction of CL_max (linear range, no stall)
FIT_CL_FRACTION_OF_MAX = 0.9


class PolarError(RuntimeError):
    """The polar does not have the shape the CRRCSim model needs (never papered over)."""


@dataclass(frozen=True)
class StallData:
    alpha_peak_deg: float
    cl_max: float
    cl_min: float
    alpha_knee_neg_deg: float
    cl_plateau: float
    cd_plateau: float
    cd_at_peak: float

    @property
    def cl_drop(self) -> float:
        return self.cl_max - self.cl_plateau

    @property
    def cd_stall(self) -> float:
        return self.cd_plateau - self.cd_at_peak


@dataclass(frozen=True)
class ProfileFit:
    cd_prof: float
    cd_clsq: float
    cl_cd0: float
    residual_rms: float


def first_peak_index(cl: np.ndarray) -> int:
    """Index of the first local C_L maximum when sweeping alpha upward from zero lift (the global
    maximum can sit on a lower post-stall plateau, and the negative side can have its own bumps)."""
    start = max(int(np.argmin(np.abs(cl))), 1)
    for k in range(start, len(cl) - 1):
        if cl[k] >= cl[k - 1] and cl[k] > cl[k + 1]:
            return k
    raise PolarError("no C_L peak in the alpha sweep: extend the sweep beyond stall")


def negative_knee_index(alpha: np.ndarray, cl: np.ndarray) -> int:
    """Index of the negative stall knee: sweeping downward from alpha = alpha(CL=0), the first
    point where the lift slope falls below KNEE_SLOPE_FRACTION of the linear slope near zero lift."""
    i0 = int(np.argmin(np.abs(cl)))
    lin = np.polyfit(alpha[max(i0 - 2, 0) : i0 + 3], cl[max(i0 - 2, 0) : i0 + 3], 1)[0]
    for k in range(i0 - 1, 0, -1):
        slope = (cl[k + 1] - cl[k]) / (alpha[k + 1] - alpha[k])
        if slope < KNEE_SLOPE_FRACTION * lin:
            return k + 1
    raise PolarError("no negative stall knee in the alpha sweep: extend the sweep to lower alpha")


def stall_data(alpha: np.ndarray, cl: np.ndarray, cd: np.ndarray) -> StallData:
    alpha, cl, cd = (np.asarray(x, dtype=float) for x in (alpha, cl, cd))
    ip = first_peak_index(cl)
    ik = negative_knee_index(alpha, cl)
    ap = alpha[ip]
    window = (alpha >= ap + PLATEAU_FROM_DEG) & (alpha <= ap + PLATEAU_TO_DEG)
    if window.sum() < 3:
        raise PolarError(
            f"post-stall window [{ap + PLATEAU_FROM_DEG}, {ap + PLATEAU_TO_DEG}] deg not covered"
        )
    return StallData(
        alpha_peak_deg=float(ap),
        cl_max=float(cl[ip]),
        cl_min=float(cl[ik]),
        alpha_knee_neg_deg=float(alpha[ik]),
        cl_plateau=float(cl[window].mean()),
        cd_plateau=float(cd[window].mean()),
        cd_at_peak=float(cd[ip]),
    )


def induced_cd(cl: np.ndarray, aspect_ratio: float, span_eff: float) -> np.ndarray:
    return np.asarray(cl) ** 2 / (np.pi * aspect_ratio * span_eff)


def fit_profile_drag(
    alpha: np.ndarray,
    cl: np.ndarray,
    cd: np.ndarray,
    aspect_ratio: float,
    span_eff: float,
    cl_lo: float,
    cl_hi: float,
    alpha_max: float,
) -> ProfileFit:
    """Least-squares CD_prof + CD_CLsq (CL - CL_CD0)^2 on (CD - induced) over the pre-stall branch
    (alpha <= alpha_max) with cl in [cl_lo, cl_hi]."""
    alpha, cl, cd = (np.asarray(x, dtype=float) for x in (alpha, cl, cd))
    sel = (cl >= cl_lo) & (cl <= cl_hi) & (alpha <= alpha_max)
    if sel.sum() < 5:
        raise PolarError(f"only {int(sel.sum())} polar points in CL [{cl_lo:.2f}, {cl_hi:.2f}]")
    x = cl[sel]
    y = cd[sel] - induced_cd(x, aspect_ratio, span_eff)
    c2, c1, c0 = np.polyfit(x, y, 2)
    if c2 <= 0:
        raise PolarError(
            f"profile drag is not convex in CL (curvature {c2:.4g}): the CRRCSim form does not fit"
        )
    cl_cd0 = -c1 / (2 * c2)
    cd_prof = c0 - c1**2 / (4 * c2)
    if cd_prof <= 0:
        raise PolarError(
            f"fitted CD_prof {cd_prof:.4g} <= 0 (induced part too large for this span_eff)"
        )
    rms = float(np.sqrt(np.mean((np.polyval([c2, c1, c0], x) - y) ** 2)))
    return ProfileFit(float(cd_prof), float(c2), float(cl_cd0), rms)


def reynolds_exponent(speeds: np.ndarray, cd_values: np.ndarray) -> float:
    """Slope of ln(profile CD at fixed C_L) over ln(V): CRRCSim's `Uexp_CD`."""
    if np.any(np.asarray(cd_values) <= 0):
        raise PolarError("non-positive profile CD in the Reynolds scan")
    return float(np.polyfit(np.log(speeds), np.log(cd_values), 1)[0])


def alpha_at_cl(alpha: np.ndarray, cl: np.ndarray, cl_target: float) -> float:
    """Alpha [deg] where the pre-stall branch reaches cl_target (linear interpolation)."""
    ip = first_peak_index(np.asarray(cl, dtype=float))
    a, c = np.asarray(alpha)[: ip + 1], np.asarray(cl)[: ip + 1]
    if not (c.min() <= cl_target <= c.max()):
        raise PolarError(
            f"CL {cl_target:.3f} outside the pre-stall branch [{c.min():.3f}, {c.max():.3f}]"
        )
    return float(np.interp(cl_target, c, a))
