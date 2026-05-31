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

    metric: str  # e.g. "max_LD", "CD0", "CLmax"
    value: float
    source: str  # short citation


@dataclass(frozen=True)
class ReferencePolar:
    """A digitized external reference drag polar (CL vs CD) for overlay."""

    label: str
    source: str
    CL: list[float]
    CD: list[float]
    note: str = ""


@dataclass(frozen=True)
class AircraftConfig:
    key: str
    name: str
    vsp_filename: str
    velocity_mps: float
    altitude_m: float
    category: str  # "anchored" (has real data) | "tool_vs_tool"
    topology: str  # short description for the dashboard
    anchors: list[Anchor] = field(default_factory=list)
    notes: str = ""
    # VSPAERO mirror flag: 0 = geometry already full (our .vsp3 files).
    symmetry: int = 0
    # Optional digitized external reference polar (overlaid on drag-polar chart).
    reference_polar: ReferencePolar | None = None
    # Qualitative interpretation of this aircraft's comparison (dashboard prose).
    verdict: str = ""

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
        velocity_mps=29.17,  # 105 km/h
        altitude_m=1500.0,
        category="anchored",
        topology="High-AR Standard-Class sailplane",
        anchors=[
            Anchor("max_LD", 38.3, "Akaflieg flight polar (POH)"),
            Anchor("max_LD_vspaero_ref", 26.0, "Luka, OpenVSP groups (VSPAERO VLM)"),
        ],
        notes="Strongest external anchor; community VSPAERO reference exists.",
        verdict=(
            "Best result of the set. AeroBuildup — the app's default method — "
            "reproduces the glider's real measured glide ratio almost exactly "
            "(~39 vs Akaflieg's 38.3). The two VLMs agree on lift-curve slope to "
            "within ~2 %; VSPAERO sits lower on L/D only because it is run "
            "wings-only (no fuselage). Verdict: the analysis core is trustworthy "
            "for a clean, high-aspect-ratio sailplane."
        ),
    ),
    AircraftConfig(
        key="cessna172",
        name="Cessna 172",
        vsp_filename="cessna172.vsp3",
        velocity_mps=50.0,  # ~cruise
        altitude_m=0.0,
        category="anchored",
        topology="Conventional GA, strut-braced high wing",
        anchors=[
            Anchor("CD0", 0.0376, "WT lab report (academic)"),
            Anchor("max_LD", 10.5, "flight test, M=0.32"),
            Anchor("CLmax", 1.5, "WT / POH stall speed"),
        ],
        notes="Multiple wind-tunnel reports; classic validation case.",
        verdict=(
            "Lift slopes line up, but every tool predicts a higher L/D than flight "
            "test (~10.5). The reasons are instructive. The .vsp3 does model the "
            "struts and gear fairings (as fuselage-type bodies), but VSPAERO is run "
            "wings-only, so it ignores the fuselage, struts and gear entirely. "
            "AeroBuildup does count them, yet still comes out optimistic because "
            "the propeller, spinner and cooling drag aren't modelled at all, and a "
            "streamlined-body buildup underestimates the bluff-body and "
            "interference drag of exposed struts and fixed gear. Verdict: lift is "
            "right; absolute drag is optimistic — chiefly missing propulsion drag "
            "and under-modelled interference, not missing geometry."
        ),
    ),
    AircraftConfig(
        key="spitfire",
        name="Supermarine Spitfire",
        vsp_filename="spitfire.vsp3",
        velocity_mps=102.0,  # ~M=0.3 sea level
        altitude_m=0.0,
        category="tool_vs_tool",
        topology="Elliptical planform (e → 1 test)",
        anchors=[
            Anchor("CLmax", 1.36, "Shenstone / RAeS (qualitative)"),
        ],
        notes="Elliptical wing: do both tools recover near-unity span efficiency?",
        verdict=(
            "This model is the one that exposed the critical bug (#788): the ASB "
            "converter took its reference area from the tailplane instead of the "
            "wing, inflating every coefficient ~8×. With that corrected, the two "
            "VLMs agree on lift slope to ~3 %. VSPAERO's induced-drag solve is "
            "still unreliable on this thin elliptical wing (it reports a "
            "non-physical span efficiency, flagged), while AeroSandbox recovers a "
            "sensible near-elliptical e. Verdict: a tool-vs-tool diagnostic that "
            "earned its keep by catching a real defect."
        ),
    ),
    AircraftConfig(
        key="stratos_ul",
        name="Ligeti Stratos",
        vsp_filename="Stratos_UL_2025-11-29T11_54_22.123Z.vsp3",
        velocity_mps=50.0,  # 180 km/h cruise
        altitude_m=0.0,
        category="anchored",
        topology="Closed-tandem / joined-tip Boxwing",
        anchors=[
            Anchor("max_LD", 20.0, "Ligeti open-source spec sheet"),
            Anchor("CLmax", 1.45, "from published Vs 58-61 km/h"),
        ],
        notes="Boxwing topology stress-test; joined tips. Original 1985 prototype.",
        verdict=(
            "The unconventional-topology stress test. The VLMs handle the "
            "joined-tip box wing and show a span efficiency above 1.0 — which is "
            "physically correct here: a box wing beats the equivalent monoplane's "
            "induced-drag limit. AeroBuildup, however, fails outright (all-NaN) on "
            "the imported fuselage (#790). Verdict: the vortex-lattice path copes "
            "with exotic geometry; the component-buildup path needs a fuselage "
            "guard before it can touch box wings."
        ),
    ),
    AircraftConfig(
        key="falcon_v2",
        name="Titan Dynamics Falcon V2",
        vsp_filename="tdfalconv2.vsp3",
        velocity_mps=15.0,  # ~cruise (45-65 km/h = 12.5-18 m/s)
        altitude_m=0.0,
        category="anchored",
        topology="3D-printed RC/UAV; cambered wing (NACA 4411→3411), 4° washout, V-tail",
        anchors=[
            Anchor("CLmax", 1.42, "Titan Dynamics manual (CFD)"),
            Anchor("max_LD", 12.0, "Titan CFD drag plot, AUW 3 kg, full aircraft"),
        ],
        notes=(
            "Real 3D-printed RC model — exact app target audience. Anchors are "
            "Titan Dynamics' own CFD (not WT/flight). CFD drag is full-aircraft "
            "(incl. fuselage), so only AeroBuildup compares on total C_D; C_Di, "
            "C_Lα, AoA are the clean comparisons. Known airfoils (NACA 4411 root) "
            "make this the test for the importer camber fidelity (#791)."
        ),
        # Digitized from the AUW = 3 kg total-drag plot (manual p.7):
        # W = 29.43 N, S = 0.4514 m², ρ = 1.225. CL = W/(qS), CD = D/(qS).
        reference_polar=ReferencePolar(
            label="Titan CFD (3 kg, full aircraft)",
            source="Titan Dynamics manual rev 1.1, p.7 (digitized ±)",
            CL=[1.064, 0.739, 0.543, 0.416, 0.328, 0.266, 0.185],
            CD=[0.0904, 0.0616, 0.0489, 0.0424, 0.0391, 0.0380, 0.0364],
            note="full-aircraft total C_D incl. fuselage parasite — compares to "
            "AeroBuildup, not wings-only VSPAERO",
        ),
        verdict=(
            "The most relevant case for the app's audience: a real 3D-printed "
            "RC/UAV checked against the manufacturer's own CFD. CLmax (1.42) is "
            "reproduced and lift slopes agree to ~4 %, and camber fidelity is good "
            "here (small C_L0 offset — so #791 is geometry-specific, not "
            "universal). As with the Cessna, our tools predict a higher L/D than "
            "the real airframe, because the CFD captures the antenna/payload-bay "
            "parasite drag our idealised model omits. Verdict: strong agreement on "
            "the aerodynamics that depend on the wing shape; absolute drag stays "
            "optimistic."
        ),
    ),
]

# Overall qualitative conclusion across all aircraft (dashboard executive summary).
EXECUTIVE_SUMMARY = (
    "Across five aircraft spanning sailplane, GA, elliptical, box-wing and RC/UAV "
    "configurations, the picture is consistent. **AeroSandbox AeroBuildup — the "
    "app's default analysis — reproduces measured glide performance closely where "
    "clean flight or wind-tunnel data exists** (within ~2 % of a real glider's "
    "polar), and the two independent vortex-lattice solvers (AeroSandbox and "
    "VSPAERO) **agree on lift-curve slope to within ~2–4 %** once reference areas "
    "match. Lift and lift-slope are therefore trustworthy. **Absolute drag and L/D "
    "are optimistic** for draggy real airframes — because the analysis doesn't "
    "fully capture every real drag source: propulsion (propeller, spinner, "
    "cooling) is not modelled, bluff-body and interference drag of struts and gear "
    "is under-estimated, surface finish is ignored, and the wings-only VSPAERO "
    "pass leaves out the fuselage and struts entirely. It's a modelling-scope "
    "limitation, not a solver error. The exercise also paid for itself by "
    "surfacing "
    "**five real app defects**, one critical: the analysis converter was taking "
    "its reference area from the wrong wing (#788), silently producing ~8× wrong "
    "coefficients whenever the tail imported before the wing. Net: the analysis "
    "core is sound for the aerodynamics that matter most, with a short, concrete "
    "list of import/geometry-handling fixes to harden it."
)


def by_key(key: str) -> AircraftConfig:
    for cfg in AIRCRAFT:
        if cfg.key == key:
            return cfg
    raise KeyError(f"unknown aircraft key: {key}")
