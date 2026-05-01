"""NeuralFoil-based CDCL (profile drag polar) computation for AVL sections."""

from __future__ import annotations

import logging
from functools import lru_cache

import aerosandbox as asb
import numpy as np

from app.avl.geometry import AvlCdcl
from app.schemas.aeroanalysisschema import CdclConfig

logger = logging.getLogger(__name__)


def compute_reynolds_number(velocity: float, chord: float, altitude: float) -> float:
    """Compute Reynolds number from flight conditions and section chord."""
    atm = asb.Atmosphere(altitude=altitude)
    return velocity * chord / atm.kinematic_viscosity()


@lru_cache(maxsize=128)
def _get_polar_data(
    airfoil_name: str,
    re: float,
    mach: float,
    alpha_start: float,
    alpha_end: float,
    alpha_step: float,
    model_size: str,
    n_crit: float,
) -> tuple:
    """Cached NeuralFoil polar — keyed on hashable primitives only."""
    airfoil = asb.Airfoil(name=airfoil_name)
    alphas = np.arange(alpha_start, alpha_end + alpha_step / 2, alpha_step)
    aero = airfoil.get_aero_from_neuralfoil(
        alpha=alphas,
        Re=re,
        mach=mach,
        model_size=model_size,
        n_crit=n_crit,
    )
    CLs = np.atleast_1d(aero["CL"])
    CDs = np.atleast_1d(aero["CD"])
    return tuple(alphas.tolist()), tuple(CLs.tolist()), tuple(CDs.tolist())


class NeuralFoilCdclService:
    """Compute per-section CDCL via NeuralFoil 3-point fitting."""

    def compute_cdcl(
        self, airfoil: asb.Airfoil, re: float, mach: float, config: CdclConfig
    ) -> AvlCdcl:
        """Fit a 3-point drag polar (negative stall, drag bucket, positive stall)."""
        _, cl_list, cd_list = _get_polar_data(
            airfoil_name=airfoil.name,
            re=re,
            mach=mach,
            alpha_start=config.alpha_start_deg,
            alpha_end=config.alpha_end_deg,
            alpha_step=config.alpha_step_deg,
            model_size=config.model_size,
            n_crit=config.n_crit,
        )
        CLs = np.array(cl_list)
        CDs = np.array(cd_list)

        # Point 2 (drag bucket): minimum CD
        idx_cd_min = int(np.argmin(CDs))
        cl_0, cd_0 = float(CLs[idx_cd_min]), float(CDs[idx_cd_min])

        # Point 3 (positive stall): maximum CL
        idx_cl_max = int(np.argmax(CLs))
        cl_max, cd_max = float(CLs[idx_cl_max]), float(CDs[idx_cl_max])

        # Point 1 (negative stall): minimum CL
        idx_cl_min = int(np.argmin(CLs))
        cl_min, cd_min = float(CLs[idx_cl_min]), float(CDs[idx_cl_min])

        return AvlCdcl(
            cl_min=cl_min, cd_min=cd_min, cl_0=cl_0, cd_0=cd_0, cl_max=cl_max, cd_max=cd_max
        )
