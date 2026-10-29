"""The cache key follows the tool of the world a node ran in (ARCHITECTURE ch. 8.4; #1221)."""

from typing import Any

import pytest
from aero_kernel import config as config_module
from aero_kernel.cache import cache_key
from aero_kernel.context import Solvers
from aero_kernel.runtime import SolverRuntime
from aero_kernel.solvers import avl as avl_module
from aero_kernel.solvers import opti as opti_module
from aero_kernel.solvers.avl import AvlAdapter
from aero_kernel.tests.formula_builders import OPT_SETTINGS, solvers_with
from aero_kernel.tests.graph_builders import formula, model_of, quantity

TAXONOMY: dict[str, Any] = {
    "tools": [{"id": "OPT", "name": "O"}, {"id": "AVL", "name": "AVL"}],
    "worlds": [{"id": "aerobuildup", "tool": "OPT"}, {"id": "avl", "tool": "AVL"}],
}


class VersionedAvl(AvlAdapter):
    def __init__(self, version: str) -> None:
        super().__init__(SolverRuntime())
        self.version = version

    def tool_versions(self) -> dict[str, str]:
        return {"avl-binary": self.version}


def node_key(solvers: Solvers, world: str, **inputs: float) -> str:
    """The key of the roll-rate-like node in ``world``, built as the facade will build it."""
    model = model_of(
        {"aircraft-mass": quantity("input", unit="kg"), "rate-q": quantity("derived")},
        {
            "rate": formula(
                {"m": "aircraft-mass"},
                {"o": "rate-q"},
                tool="OPT",
                uncertainty="interval",
                worlds=["aerobuildup", "avl"],
            )
        },
        taxonomy=TAXONOMY,
    )
    tool = model.tool_of("calc:rate", world)
    return cache_key(
        formula="calc:rate",
        application="default",
        world=f"rate={world}",
        inputs={"m": 2.0, **inputs},
        build_digest="sha256:aa",
        tool_versions=solvers.tool_versions_of(tool),
        solver_settings=solvers.settings_of(tool),
        rule_overrides={},
    )


def test_a_changed_avl_setting_misses_the_cache_in_the_avl_world(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    solvers = solvers_with()
    before = node_key(solvers, "avl")
    assert node_key(solvers, "avl") == before
    monkeypatch.setattr(avl_module, "N_SPAN", avl_module.N_SPAN + 1)
    assert node_key(solvers, "avl") != before


def test_a_changed_avl_setting_keeps_the_aerobuildup_world_cached(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    solvers = solvers_with()
    before = node_key(solvers, "aerobuildup")
    monkeypatch.setattr(avl_module, "N_SPAN", avl_module.N_SPAN + 1)
    assert node_key(solvers, "aerobuildup") == before


def test_a_new_avl_binary_misses_the_cache_in_the_avl_world() -> None:
    old = node_key(solvers_with(avl=VersionedAvl("1.0")), "avl")
    new = node_key(solvers_with(avl=VersionedAvl("1.1")), "avl")
    assert old != new
    assert old == node_key(solvers_with(avl=VersionedAvl("1.0")), "avl")


def test_a_new_avl_binary_keeps_the_aerobuildup_world_cached() -> None:
    old = node_key(solvers_with(avl=VersionedAvl("1.0")), "aerobuildup")
    assert old == node_key(solvers_with(avl=VersionedAvl("1.1")), "aerobuildup")


@pytest.mark.parametrize(
    "constant",
    [
        "ALPHA_MIN_DEG",
        "ALPHA_MAX_DEG",
        "ALPHA_STEP_DEG",
        "BRACKET_CL",
        "V_MIN_MS",
        "V_MAX_MACH",
        "MAX_ITERATIONS",
        "EFFECTIVENESS_EXPONENT",
    ],
)
def test_a_changed_optimisation_setting_misses_the_cache_in_the_aerobuildup_world(
    monkeypatch: pytest.MonkeyPatch, constant: str
) -> None:
    solvers = solvers_with()
    before = node_key(solvers, "aerobuildup")
    monkeypatch.setattr(opti_module, constant, getattr(opti_module, constant) + 0.5)
    assert node_key(solvers, "aerobuildup") != before


@pytest.mark.parametrize(
    "constant",
    [
        "CHORD_SPACING",
        "SLIVER_STEPS",
        "CLAF_PER_THICKNESS",
        "AVL_MAX_RUN_S",
        "MESH_DECIMALS",
    ],
)
def test_a_changed_avl_constant_misses_the_cache_in_the_avl_world(
    monkeypatch: pytest.MonkeyPatch, constant: str
) -> None:
    solvers = solvers_with()
    before = node_key(solvers, "avl")
    monkeypatch.setattr(avl_module, constant, getattr(avl_module, constant) + 1)
    assert node_key(solvers, "avl") != before


def test_the_optimisation_constants_are_part_of_the_solver_settings() -> None:
    settings = solvers_with().settings_of("OPT")
    assert settings == OPT_SETTINGS


def _with_config_value(monkeypatch: pytest.MonkeyPatch, name: str) -> None:
    """Make the shipped configuration state a different value for ``name``."""
    shipped = config_module.config()
    entry = getattr(shipped, name)
    changed = shipped.model_copy(update={name: entry.model_copy(update={"value": entry.value * 2})})
    monkeypatch.setattr(avl_module, "config", lambda: changed)
    monkeypatch.setattr(opti_module, "config", lambda: changed)


@pytest.mark.parametrize(
    "name",
    [
        "avl_refinement_tolerance_mac",
        "avl_roll_refinement_tolerance",
        "avl_roll_branch_tolerance",
        "avl_roll_print_floor",
        "avl_roll_moment_tolerance",
        "avl_control_echo_tolerance",
        "avl_cl_tolerance",
    ],
)
def test_a_changed_avl_config_value_misses_the_cache_in_the_avl_world(
    monkeypatch: pytest.MonkeyPatch, name: str
) -> None:
    solvers = solvers_with()
    before = node_key(solvers, "avl")
    _with_config_value(monkeypatch, name)
    assert node_key(solvers, "avl") != before


@pytest.mark.parametrize(
    "name",
    [
        "opt_probe_tolerance",
        "opt_peak_tolerance",
        "opt_zero_span",
        "opt_active_bound_fraction",
        "opt_alpha_margin_deg",
        "opt_hinge_floor",
        "opt_flap_rib_gap",
        "opt_fuselage_area_tolerance",
    ],
)
def test_a_changed_optimisation_config_value_misses_the_cache_in_the_aerobuildup_world(
    monkeypatch: pytest.MonkeyPatch, name: str
) -> None:
    solvers = solvers_with()
    before = node_key(solvers, "aerobuildup")
    _with_config_value(monkeypatch, name)
    assert node_key(solvers, "aerobuildup") != before


@pytest.mark.parametrize(
    "override",
    ["avl-roll-rate-validity.max_roll_rate_coefficient", "hinge-line-continuity.join_tolerance"],
)
def test_an_overridden_rule_parameter_misses_the_cache_in_the_avl_world(override: str) -> None:
    """A rule parameter the caller overrides shapes the AVL result, so it is part of the key."""
    solvers = solvers_with()
    solvers.rules.begin()
    before = node_key(solvers, "avl")
    solvers.rules.begin({override: 0.5})
    assert node_key(solvers, "avl") != before
