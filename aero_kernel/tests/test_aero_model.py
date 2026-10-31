"""The AeroBuildup model function, its key and the worker's cache of it (ch. 8.4, 8.8, #1336).

Fast tier: AeroSandbox and CasADi are faked; the real function is pinned in the aero tier.
"""

import math
from types import SimpleNamespace
from typing import Any

import pytest
from aero_kernel.solvers import aero_model as module
from aero_kernel.solvers.aero_model import (
    MAX_MODELS_PER_WORKER,
    MODEL_INPUTS,
    MODEL_OUTPUTS,
    AeroModel,
    ModelCache,
    aero_model,
    build_aero_model,
    install_model_cache,
    installed_model_cache,
    model_key,
)
from aero_kernel.solvers.air import AirState, FixedAtmosphere
from aero_kernel.tests.solver_builders import AIR, airplane

VERSIONS = {"aerosandbox": "4.2.9", "neuralfoil": "0.3.2"}


def key_of(**changes: Any) -> str:
    arguments: dict[str, Any] = {
        "roll_deg": 0.0,
        "model_size": "xlarge",
        "tool_versions": VERSIONS,
    } | changes
    plane = arguments.pop("airplane", airplane())
    return model_key(plane, **arguments)


@pytest.fixture
def no_cache(monkeypatch: pytest.MonkeyPatch) -> None:
    """Restore the process's (absent) cache after a test that installs one."""
    monkeypatch.setattr(module._INSTALLED, "cache", None)  # pyright: ignore[reportPrivateUsage]  # the process-local holder under test


class TestKey:
    def test_the_same_airplane_has_the_same_key(self) -> None:
        first, second = key_of(), key_of()
        assert first == second
        assert first.startswith("sha256:")

    @pytest.mark.parametrize(
        "change",
        [
            {"airplane": airplane(chords=(0.2, 0.11))},
            {"airplane": airplane(device=("flap", 10.0), hinge=0.7)},
            {"roll_deg": 5.0},
            {"model_size": "large"},
            {"tool_versions": VERSIONS | {"neuralfoil": "0.3.3"}},
        ],
    )
    def test_whatever_changes_the_converted_airplane_or_its_model_changes_the_key(
        self, change: dict[str, Any]
    ) -> None:
        assert key_of(**change) != key_of()

    def test_exact_values_not_rounded(self) -> None:
        assert key_of(roll_deg=5.0) != key_of(roll_deg=5.0 + 1e-12)

    def test_a_negative_zero_command_is_the_airplane_without_one(self) -> None:
        """``to_asb_airplane`` builds no roll surface for -0.0 either."""
        assert key_of(roll_deg=-0.0) == key_of(roll_deg=0.0)

    def test_a_non_finite_unread_field_does_not_fail_the_key(self) -> None:
        plane = airplane().model_copy(update={"total_mass_kg": math.nan})
        assert key_of(airplane=plane) != key_of()


class TestModelCache:
    def test_a_miss_builds_and_a_hit_reuses(self) -> None:
        cache, built = ModelCache(2), list[int]()

        def build() -> AeroModel:
            built.append(1)
            return AeroModel(len(built))

        first, held_first = cache.get("A", build)
        again, held_again = cache.get("A", build)
        assert (held_first, held_again) == (False, True)
        assert again is first
        assert len(built) == 1

    def test_the_least_recently_used_function_is_dropped(self) -> None:
        cache = ModelCache(2)
        for key in ("A", "B", "A", "C"):
            cache.get(key, lambda: AeroModel(None))
        assert cache.keys() == ("A", "C")

    def test_a_failed_build_keeps_nothing(self) -> None:
        cache = ModelCache(1)

        def broken() -> AeroModel:
            msg = "no model"
            raise ValueError(msg)

        with pytest.raises(ValueError, match="no model"):
            cache.get("A", broken)
        assert cache.keys() == ()

    def test_the_bound_must_be_positive(self) -> None:
        with pytest.raises(ValueError, match="max_models"):
            ModelCache(0)

    def test_the_default_bound_is_two(self) -> None:
        assert MAX_MODELS_PER_WORKER == 2


class TestInstalledCache:
    def test_the_parent_process_has_none(self) -> None:
        assert installed_model_cache() is None

    @pytest.mark.usefixtures("no_cache")
    def test_installing_is_idempotent_for_the_same_bound(self) -> None:
        install_model_cache(2)
        first = installed_model_cache()
        install_model_cache(2)
        assert installed_model_cache() is first
        install_model_cache(3)
        replaced = installed_model_cache()
        assert replaced is not first
        assert replaced is not None
        assert replaced.max_models == 3

    @pytest.mark.usefixtures("no_cache")
    def test_with_a_cache_the_function_is_built_once_per_key(
        self, monkeypatch: pytest.MonkeyPatch
    ) -> None:
        built: list[object] = []

        def build(asb_airplane: object, model_size: str) -> AeroModel:
            built.append(asb_airplane)
            return AeroModel(model_size)

        monkeypatch.setattr(module, "build_aero_model", build)
        install_model_cache(2)
        first, note_first = aero_model("A", "plane", "xlarge")
        again, note_again = aero_model("A", "plane", "xlarge")
        assert again is first
        assert built == ["plane"]
        assert "built" in note_first
        assert "reused" in note_again

    def test_without_a_cache_or_a_key_the_function_is_built_per_call(
        self, monkeypatch: pytest.MonkeyPatch
    ) -> None:
        built: list[object] = []

        def build(asb_airplane: object, model_size: str) -> AeroModel:
            built.append(asb_airplane)
            return AeroModel(model_size)

        monkeypatch.setattr(module, "build_aero_model", build)
        aero_model("A", "plane", "xlarge")
        aero_model(None, "plane", "xlarge")
        assert len(built) == 2


class FakeSymbol:
    """A stand-in for ``casadi.MX``: records its name, supports the atmosphere's arithmetic."""

    def __init__(self, name: str) -> None:
        self.name = name

    def __pow__(self, exponent: float) -> tuple[str, str, float]:
        return ("pow", self.name, exponent)


class FakeCasadi:
    """Records the function the builder makes and answers it with the inputs it was called with."""

    def __init__(self) -> None:
        self.functions: list[tuple[Any, ...]] = []
        self.MX = SimpleNamespace(sym=FakeSymbol)

    def Function(self, *spec: Any) -> Any:  # noqa: N802  # CasADi's own name
        self.functions.append(spec)

        def call(*arguments: Any) -> tuple[Any, ...]:
            return tuple((name, arguments) for name in MODEL_OUTPUTS)

        return call


class FakeAsb:
    """Records the operating point AeroBuildup is built on."""

    def __init__(self) -> None:
        self.points: list[dict[str, Any]] = []
        self.runs: list[tuple[object, str]] = []

    def OperatingPoint(self, **kwargs: Any) -> dict[str, Any]:  # noqa: N802  # AeroSandbox's own name
        self.points.append(kwargs)
        return kwargs

    def AeroBuildup(  # noqa: N802  # AeroSandbox's own name
        self, airplane: object, op_point: object, model_size: str
    ) -> SimpleNamespace:
        self.runs.append((airplane, model_size))
        return SimpleNamespace(run=lambda: {name: f"expr-{name}" for name in MODEL_OUTPUTS})


def test_the_function_is_aerobuildup_over_symbolic_inputs(monkeypatch: pytest.MonkeyPatch) -> None:
    fake_asb, fake_casadi = FakeAsb(), FakeCasadi()
    monkeypatch.setattr(module, "load_aerosandbox", lambda: fake_asb)
    monkeypatch.setattr(module, "load_casadi", lambda: fake_casadi)
    model = build_aero_model("plane", "xlarge")
    (point,) = fake_asb.points
    assert fake_asb.runs == [("plane", "xlarge")]
    for name in ("p", "q", "r"):
        assert point[name].name == name
    assert (point["velocity"].name, point["alpha"].name) == ("v", "alpha")
    atmosphere = point["atmosphere"]
    assert atmosphere.density().name == "density"
    assert atmosphere.dynamic_viscosity().name == "dynamic_viscosity"
    assert atmosphere.speed_of_sound().name == "speed_of_sound"
    ((name, inputs, outputs, input_names, output_names),) = fake_casadi.functions
    assert name == "aero_model"
    assert [s.name for s in inputs] == list(MODEL_INPUTS) == input_names
    assert outputs == [f"expr-{n}" for n in MODEL_OUTPUTS]
    assert output_names == list(MODEL_OUTPUTS)
    values = model(8.0, 3.0, AIR, p=0.1, r=0.2)
    assert list(values) == list(MODEL_OUTPUTS)
    expected = (8.0, 3.0, 0.1, 0.0, 0.2, AIR.density, AIR.dynamic_viscosity, AIR.speed_of_sound)
    assert values["L"] == ("L", expected)


def test_the_symbolic_atmosphere_derives_the_state_as_the_fixed_one() -> None:
    """Same formulas, bit for bit, so the function's air is the air a fixed run sees."""
    air = AirState(density=1.1, dynamic_viscosity=1.8e-5, speed_of_sound=338.0)
    fixed = FixedAtmosphere(air)
    symbolic = module._SymbolicAtmosphere(  # pyright: ignore[reportPrivateUsage]  # the duck-typed atmosphere under test
        air.density, air.dynamic_viscosity, air.speed_of_sound
    )
    for method in (
        "density",
        "dynamic_viscosity",
        "speed_of_sound",
        "ratio_of_specific_heats",
        "temperature",
        "pressure",
    ):
        assert getattr(symbolic, method)() == getattr(fixed, method)()
