"""Registry of the benchmark reference aircraft.

Reference quantities (S_ref, b_ref, c_ref) and atmosphere (rho, Mach,
Re) are NOT hardcoded — they are derived at runtime from the imported
ASB airplane + ISA atmosphere so that the VSPAERO and ASB sides use
byte-identical references (eliminating reference-area as a comparison
variable). Only the things that can't be derived live here: the flight
speed/altitude, and the real-world anchor values from literature.
"""
from __future__ import annotations

from dataclasses import dataclass, field
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parents[2]
VSP_DIR = REPO_ROOT / "components" / "aircraft" / "vsp"
RESULTS_DIR = Path(__file__).parent / "results"


@dataclass(frozen=True)
class Anchor:
    """A single real-world reference value (wind tunnel / flight test)."""
    metric: str          # e.g. "max_LD", "CD0", "CLmax"
    value: float
    source: str          # short citation


@dataclass(frozen=True)
class AircraftConfig:
    key: str
    name: str
    vsp_filename: str
    velocity_mps: float
    altitude_m: float
    category: str            # "anchored" (has real data) | "tool_vs_tool"
    topology: str            # short description for the dashboard
    anchors: list[Anchor] = field(default_factory=list)
    notes: str = ""
    # VSPAERO mirror flag: 0 = geometry already full (our .vsp3 files).
    symmetry: int = 0

    @property
    def vsp_path(self) -> Path:
        return VSP_DIR / self.vsp_filename

    @property
    def result_dir(self) -> Path:
        return RESULTS_DIR / self.key


AIRCRAFT: list[AircraftConfig] = [
    AircraftConfig(
        key="dg101g",
        name="Glaser-Dirks DG-101G",
        vsp_filename="dg101g.vsp3",
        velocity_mps=29.17,          # 105 km/h
        altitude_m=1500.0,
        category="anchored",
        topology="High-AR Standard-Class sailplane",
        anchors=[
            Anchor("max_LD", 38.3, "Akaflieg flight polar (POH)"),
            Anchor("max_LD_vspaero_ref", 26.0, "Luka, OpenVSP groups (VSPAERO VLM)"),
        ],
        notes="Strongest external anchor; community VSPAERO reference exists.",
    ),
    AircraftConfig(
        key="cessna172",
        name="Cessna 172",
        vsp_filename="cessna172.vsp3",
        velocity_mps=50.0,           # ~cruise
        altitude_m=0.0,
        category="anchored",
        topology="Conventional GA, strut-braced high wing",
        anchors=[
            Anchor("CD0", 0.0376, "WT lab report (academic)"),
            Anchor("max_LD", 10.5, "flight test, M=0.32"),
            Anchor("CLmax", 1.5, "WT / POH stall speed"),
        ],
        notes="Multiple wind-tunnel reports; classic validation case.",
    ),
    AircraftConfig(
        key="spitfire",
        name="Supermarine Spitfire",
        vsp_filename="spitfire.vsp3",
        velocity_mps=102.0,          # ~M=0.3 sea level
        altitude_m=0.0,
        category="tool_vs_tool",
        topology="Elliptical planform (e → 1 test)",
        anchors=[
            Anchor("CLmax", 1.36, "Shenstone / RAeS (qualitative)"),
        ],
        notes="Elliptical wing: do both tools recover near-unity span efficiency?",
    ),
    AircraftConfig(
        key="stratos_ul",
        name="Ligeti Stratos",
        vsp_filename="Stratos_UL_2025-11-29T11_54_22.123Z.vsp3",
        velocity_mps=50.0,           # 180 km/h cruise
        altitude_m=0.0,
        category="anchored",
        topology="Closed-tandem / joined-tip Boxwing",
        anchors=[
            Anchor("max_LD", 20.0, "Ligeti open-source spec sheet"),
            Anchor("CLmax", 1.45, "from published Vs 58-61 km/h"),
        ],
        notes="Boxwing topology stress-test; joined tips. Original 1985 prototype.",
    ),
]


def by_key(key: str) -> AircraftConfig:
    for cfg in AIRCRAFT:
        if cfg.key == key:
            return cfg
    raise KeyError(f"unknown aircraft key: {key}")
