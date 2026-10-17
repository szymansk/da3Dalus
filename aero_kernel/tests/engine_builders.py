"""Builders of the fixture canon and the stub formulas for the engine tests (ARCHITECTURE ch. 6)."""

from collections.abc import Callable, Coroutine, Mapping
from typing import Any

# ``Any`` is the raw-JSON boundary: hand-written model dicts that the canon model validates.
from aero_kernel.build import Build
from aero_kernel.canon.model import CanonModel
from aero_kernel.context import Context, Inputs
from aero_kernel.geometry import AirplaneGeometry
from aero_kernel.graph import CanonGraph
from aero_kernel.registry import Registry
from aero_kernel.schema import AircraftInput, ComputeRequest
from aero_kernel.tests.graph_builders import formula, model_of, quantity

Impl = Callable[[Inputs, Context], Coroutine[object, object, Mapping[str, object]]]


def num(x: Inputs, name: str) -> float:
    """The number bound to a parameter."""
    value = x[name]
    assert isinstance(value, float)
    return value


def fixture_model() -> CanonModel:
    """A small canon model that exercises every engine path."""
    quantities: dict[str, dict[str, Any]] = {
        "airplane": quantity("input", type="airplane"),
        "aircraft-mass": quantity("input", unit="kg", positive=True),
        "gravity": quantity("input", unit="m/s^2"),
        "weight": quantity("output", unit="N"),
        "double-weight": quantity("output", unit="N"),
        "independent-q": quantity("output", unit="kg"),
        "twin-a": quantity("derived"),
        "twin-b": quantity("derived"),
        "after-a": quantity("output"),
        "after-b": quantity("output"),
        "roll-q": quantity("output", unit="deg/s"),
        "after-roll-q": quantity("output"),
        "tail-q": quantity("output"),
        "long-q": quantity("output"),
        "after-long-q": quantity("output"),
        "mix-q": quantity("output"),
        "mix-na-q": quantity("output"),
        "mix-skip-q": quantity("output"),
        "span-q": quantity("output", unit="m"),
        "opt-q": quantity("output"),
        "unimpl-q": quantity("output"),
        "scaled-q": quantity("output"),
        "given-q": quantity("output"),
        "target-t": quantity("target"),
        "curve-q": quantity("output", type="curve"),
        "airplane-cfg": quantity("derived", type="airplane"),
        "cfg-span-q": quantity("output", unit="m"),
    }
    scaled = formula({"m": "aircraft-mass"}, {"r": "scaled-q"})
    scaled["inputs"]["k"] = None
    scaled["applications"][0]["bind"]["k"] = {"const": 3.0, "source": "test constant"}
    formulas: dict[str, dict[str, Any]] = {
        "weight": formula({"m": "aircraft-mass", "g": "gravity"}, {"w": "weight"}),
        "double": formula({"w": "weight"}, {"d": "double-weight"}),
        "independent": formula({"m": "aircraft-mass"}, {"r": "independent-q"}),
        "twin": formula({"m": "aircraft-mass"}, {"a": "twin-a", "b": "twin-b"}),
        "after-twin-a": formula({"a": "twin-a"}, {"r": "after-a"}),
        "after-twin-b": formula({"b": "twin-b"}, {"r": "after-b"}),
        "roll": formula({"m": "aircraft-mass"}, {"p": "roll-q"}, when="has_aileron"),
        "after-roll": formula({"p": "roll-q"}, {"r": "after-roll-q"}),
        "tail": formula({"m": "aircraft-mass"}, {"t": "tail-q"}, when="has_horizontal_tail"),
        "long-run": formula({"m": "aircraft-mass"}, {"r": "long-q"}, cost="minutes"),
        "after-long": formula({"l": "long-q"}, {"r": "after-long-q"}),
        "mix": formula({"w": "weight", "p": "roll-q"}, {"r": "mix-q"}),
        "mix-na": formula({"p": "roll-q", "m": "aircraft-mass"}, {"r": "mix-na-q"}),
        "mix-skip": formula({"p": "roll-q", "l": "long-q"}, {"r": "mix-skip-q"}),
        "wing-span": formula({"airplane": "airplane"}, {"s": "span-q"}),
        "optional-g": formula(
            {"m": "aircraft-mass", "g": "gravity"}, {"r": "opt-q"}, optional=["g"]
        ),
        "unimplemented": formula({"m": "aircraft-mass"}, {"r": "unimpl-q"}),
        "scaled": scaled,
        "given-only": formula(
            {"m": "aircraft-mass", "t": "target-t"}, {"r": "given-q"}, given=["calc:target-t"]
        ),
        "configure": formula({"a": "airplane"}, {"c": "airplane-cfg"}),
        "cfg-span": formula({"a": "airplane-cfg"}, {"s": "cfg-span-q"}),
        "curve-producer": formula({"m": "aircraft-mass"}, {"c": "curve-q"}),
    }
    return model_of(quantities, formulas)


async def _weight(x: Inputs, ctx: Context) -> Mapping[str, object]:
    return {"w": num(x, "m") * num(x, "g")}


async def _double(x: Inputs, ctx: Context) -> Mapping[str, object]:
    return {"d": 2 * num(x, "w")}


async def _mass(x: Inputs, ctx: Context) -> Mapping[str, object]:
    return {"r": num(x, "m")}


async def _twin(x: Inputs, ctx: Context) -> Mapping[str, object]:
    return {"a": num(x, "m"), "b": 2 * num(x, "m")}


async def _after_a(x: Inputs, ctx: Context) -> Mapping[str, object]:
    return {"r": num(x, "a") + 1}


async def _after_b(x: Inputs, ctx: Context) -> Mapping[str, object]:
    return {"r": num(x, "b") + 1}


async def _roll(x: Inputs, ctx: Context) -> Mapping[str, object]:
    return {"p": 10.0}


async def _after_roll(x: Inputs, ctx: Context) -> Mapping[str, object]:
    return {"r": num(x, "p") + 1}


async def _long(x: Inputs, ctx: Context) -> Mapping[str, object]:
    return {"r": 99.0}


async def _after_long(x: Inputs, ctx: Context) -> Mapping[str, object]:
    return {"r": num(x, "l") + 1}


async def _mix(x: Inputs, ctx: Context) -> Mapping[str, object]:
    return {"r": num(x, "w") + num(x, "p")}


async def _mix_na(x: Inputs, ctx: Context) -> Mapping[str, object]:
    return {"r": num(x, "p") + num(x, "m")}


async def _mix_skip(x: Inputs, ctx: Context) -> Mapping[str, object]:
    return {"r": num(x, "p") + num(x, "l")}


async def _tail(x: Inputs, ctx: Context) -> Mapping[str, object]:
    return {"t": 1.0}


async def _span(x: Inputs, ctx: Context) -> Mapping[str, object]:
    return {"s": 1.5}


async def _optional_g(x: Inputs, ctx: Context) -> Mapping[str, object]:
    return {"r": num(x, "m") if x["g"] is None else num(x, "m") * num(x, "g")}


async def _scaled(x: Inputs, ctx: Context) -> Mapping[str, object]:
    return {"r": num(x, "m") * num(x, "k")}


async def _given(x: Inputs, ctx: Context) -> Mapping[str, object]:
    return {"r": num(x, "m") + num(x, "t")}


async def _configure(x: Inputs, ctx: Context) -> Mapping[str, object]:
    return {"c": x["a"]}


async def _cfg_span(x: Inputs, ctx: Context) -> Mapping[str, object]:
    assert isinstance(x["a"], AirplaneGeometry)
    return {"s": 2.5}


async def _curve(x: Inputs, ctx: Context) -> Mapping[str, object]:
    return {"c": 1.0}


STANDARD: Mapping[str, Impl] = {
    "weight": _weight,
    "double": _double,
    "independent": _mass,
    "twin": _twin,
    "after-twin-a": _after_a,
    "after-twin-b": _after_b,
    "roll": _roll,
    "after-roll": _after_roll,
    "tail": _tail,
    "long-run": _long,
    "after-long": _after_long,
    "mix": _mix,
    "mix-na": _mix_na,
    "mix-skip": _mix_skip,
    "wing-span": _span,
    "optional-g": _optional_g,
    "scaled": _scaled,
    "given-only": _given,
    "configure": _configure,
    "cfg-span": _cfg_span,
    "curve-producer": _curve,
}


def registry_with(
    overrides: Mapping[str, Impl] | None = None, *, drop: tuple[str, ...] = ()
) -> Registry:
    """A registry of the standard stubs, some replaced or left out."""
    registry = Registry()
    implementations = {**STANDARD, **(overrides or {})}
    for slug, implementation in implementations.items():
        if slug not in drop:
            registry.formula(slug)(implementation)
    return registry


def make_build(registry: Registry | None = None, model: CanonModel | None = None) -> Build:
    """A fixture build over the fixture model, without touching the shipped model."""
    used_model = model or fixture_model()
    used_registry = registry or registry_with()
    return Build(
        model=used_model,
        graph=CanonGraph(used_model),
        digest="sha256:" + "ab" * 32,
        registry=used_registry,
        report=used_registry.check_traceability(used_model),
    )


def aircraft(
    values: Mapping[str, float] | None = None, wings: dict[str, Any] | None = None
) -> AircraftInput:
    """A wingless aircraft of mass 2 kg and gravity 9.81 m/s^2, with the given values and wings."""
    document: dict[str, Any] = {"name": "t"}
    if wings is not None:
        document["wings"] = wings
    given = {"aircraft-mass": 2.0, "gravity": 9.81, **(values or {})}
    return AircraftInput.model_validate({"airplane": document, "values": given})


def request(*slugs: str, long_runs: bool = False) -> ComputeRequest:
    """A request for the given quantities."""
    return ComputeRequest(quantities=slugs, include_long_runs=long_runs)


def aileron_wing() -> dict[str, Any]:
    """A wing with an aileron, so ``has_aileron`` holds."""
    sections = [
        {
            "xyz_le": [0.0, 0.0, 0.0],
            "chord": 0.2,
            "twist": 0.0,
            "airfoil": "naca2412",
            "trailing_edge_device": {"role": "aileron"},
        },
        {"xyz_le": [0.0, 0.5, 0.0], "chord": 0.2, "twist": 0.0, "airfoil": "naca2412"},
    ]
    return {"Main": {"name": "Main", "symmetric": True, "x_secs": sections}}
