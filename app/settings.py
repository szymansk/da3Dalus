from functools import lru_cache
from typing import Any

from pydantic import Field
from pydantic_settings import BaseSettings, SettingsConfigDict


# ---------------------------------------------------------------------------
# Low-Re airfoil scoring — mission-weighting defaults (gh-821)
# ---------------------------------------------------------------------------
# Each entry describes one mission preset. The coefficients are hobbyist
# heuristics from the RC-aircraft-designer skill; they live here so they
# can be tuned without rerunning the NeuralFoil backfill.
#
# Fields per entry:
#   thickness_min_pct / thickness_max_pct  — preferred t/c band (% chord)
#   cl_max_weight    — importance of high CL_max for this mission (0..1 scale)
#   preferred_families — list of family labels that score bonus
_DEFAULT_MISSION_WEIGHTS: dict[str, dict[str, Any]] = {
    "trainer": {
        "thickness_min_pct": 11.0,
        "thickness_max_pct": 14.0,
        "cl_max_weight": 0.7,
        "preferred_families": ["flat_bottom", "semi_symmetric"],
    },
    "sport": {
        "thickness_min_pct": 9.0,
        "thickness_max_pct": 13.0,
        "cl_max_weight": 0.55,
        "preferred_families": ["semi_symmetric", "cambered"],
    },
    "aerobatic": {
        "thickness_min_pct": 8.0,
        "thickness_max_pct": 12.0,
        "cl_max_weight": 0.4,
        "preferred_families": ["symmetric"],
    },
    "glider": {
        "thickness_min_pct": 10.0,
        "thickness_max_pct": 14.0,
        "cl_max_weight": 0.5,
        "preferred_families": ["cambered", "semi_symmetric"],
    },
    "flying_wing": {
        "thickness_min_pct": 8.0,
        "thickness_max_pct": 13.0,
        "cl_max_weight": 0.5,
        "preferred_families": ["reflexed", "symmetric"],
    },
}

# Absolute Re grid for the low-Re backfill (13 log-spaced points).
# Dense below 250k where the laminar-separation bubble governs; coarser above.
_DEFAULT_LOW_RE_GRID: list[int] = [
    40_000,
    50_000,
    60_000,
    75_000,
    90_000,
    110_000,
    130_000,
    160_000,
    200_000,
    250_000,
    350_000,
    500_000,
    750_000,
]


class Settings(BaseSettings):
    # extra="ignore" so developer-local variables in .env (GITHUB_TOKEN, etc.)
    # do not break application startup or test collection.
    model_config = SettingsConfigDict(env_file=".env", extra="ignore")

    base_url: str = "http://localhost:8000"
    openai_api_key: str = "sk*"
    version: str = "0.1.0"

    # -----------------------------------------------------------------------
    # Low-Re airfoil scoring (gh-821)
    # -----------------------------------------------------------------------
    # Absolute Re grid — 13 points, dense below 250k.
    # NOTE: the per-request NeuralFoil endpoint (endpoints/airfoils.py:111)
    # uses model_size="large" by default (interactive, fast). The backfill
    # uses "xxxlarge" for maximum accuracy (CD error ~2% vs ~8% for large).
    # These are intentionally different defaults — do NOT collapse them.
    low_re_grid: list[int] = Field(default_factory=lambda: list(_DEFAULT_LOW_RE_GRID))
    low_re_neuralfoil_model_size: str = "xxxlarge"
    low_re_n_crit: float = 9.0
    # Gate: only metrics where analysis_confidence >= gate are accepted.
    low_re_confidence_gate: float = 0.90
    # Flag threshold: any item with min_analysis_confidence < flag → caveat.
    low_re_low_confidence_flag: float = 0.85
    # Relative drag-rise CD(CL_target)/cd0 at which Match→0  (gh-825 scoring).
    low_re_score_r_poor: float = 2.5
    # Drag-bucket width that earns full tolerance credit in Match formula (gh-825).
    low_re_bucket_tolerance_ref: float = 0.6
    # CL_max margin (cl_max − cl_target) at which the high-CL Match component
    # reaches 1.0.  Below 0 → score 0 (stall risk).  (gh-825 glide-point fix)
    low_re_score_cl_max_safety_band: float = 0.30
    # Mission-weight coefficient table keyed by mission preset name.
    low_re_mission_weights: dict[str, dict[str, Any]] = Field(
        default_factory=lambda: dict(_DEFAULT_MISSION_WEIGHTS)
    )


settings = Settings()


@lru_cache()
def get_settings() -> Settings:
    return Settings()
