"""Builders of the fixture canon and the stub formulas for the engine tests (ARCHITECTURE ch. 6)."""

from collections.abc import Callable, Coroutine, Mapping
from typing import Any

# ``Any`` is the raw-JSON boundary: hand-written model dicts that the canon model validates.
from aero_kernel.build import Build
from aero_kernel.canon.model import CanonModel
from aero_kernel.context import Context, Inputs, Solvers
from aero_kernel.geometry import AirplaneGeometry
from aero_kernel.graph import CanonGraph
from aero_kernel.registry import Registry
from aero_kernel.runtime import SolverRuntime
from aero_kernel.schema import AircraftInput, ComputeRequest
from aero_kernel.solvers.atmosphere import AtmosphereAdapter
from aero_kernel.solvers.geometry import GeometryAdapter
from aero_kernel.tests.graph_builders import formula, model_of, quantity
from aero_kernel.tests.wing_builders import main_wing_document

Impl = Callable[[Inputs, Context], Coroutine[object, object, Mapping[str, object]]]

# For the engine tests whose stub formulas use no solver; the runtime never starts a thread or a pool.
NO_SOLVERS = Solvers(
    atmosphere=AtmosphereAdapter(SolverRuntime()), geometry=GeometryAdapter(SolverRuntime())
)


def num(x: Inputs, name: str) -> float:
    """The number bound to a parameter."""
    value = x[name]
    assert isinstance(value, float)
    return value


DEFAULTS: dict[str, dict[str, Any]] = {
    "air-density": {
        "value": 1.225,
        "unit": "kg/m^3",
        "source": "us standard atmosphere",
        "regime": "RC and UAV, sea level",
    },
    "margin-target": {
        "value": 1.3,
        "unit": "1",
        "source": "test margin",
        "regime": "RC and UAV, test value",
    },
}


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
        "components": quantity("input", type="components"),
        "air-density": quantity("input", unit="kg/m^3", positive=True),
        "margin-target": quantity("target"),
        "density-q": quantity("output"),
        "margin-q": quantity("output"),
        "both-q": quantity("output"),
        "density-again-q": quantity("output"),
        "long-density-q": quantity("output"),
        "optional-density-q": quantity("output"),
        "fail-density-q": quantity("output"),
        "gravity-only-q": quantity("output"),
        "after-margin-q": quantity("output"),
        "density-when-q": quantity("output"),
        "density-after-roll-q": quantity("output"),
        "density-pending-q": quantity("output"),
        "density-needs-t-q": quantity("output"),
        "density-after-long-q": quantity("output"),
        "margin-and-after-q": quantity("output"),
        "density-after-margin-q": quantity("output"),
        "mass-airplane-q": quantity("output"),
        "two-uncarried-q": quantity("output"),
        "three-uncarried-q": quantity("output"),
        "target-u": quantity("target"),
        "two-givens-q": quantity("output"),
        "pending-curve-q": quantity("output"),
        "three-q": quantity("output"),
        "tail-twin-a": quantity("output"),
        "tail-twin-b": quantity("output"),
        "curve-twin-a": quantity("output"),
        "curve-twin-b": quantity("output"),
        "pending-given-q": quantity("output"),
        "two-na-q": quantity("output"),
        "twice-na-q": quantity("output"),
        "polar-q": quantity("derived", type="polar"),
        "polar-scalar-q": quantity("output"),
        "polar-read-q": quantity("output"),
        "na-when-q": quantity("output"),
        "long-after-long-q": quantity("output"),
        "long-needs-t-q": quantity("output"),
        "long-after-roll-q": quantity("output"),
        "when-after-weight-q": quantity("output"),
        "err-missing-q": quantity("output"),
        "after-both-q": quantity("output"),
        "unexposed-q": quantity("output"),
        "curve-read-q": quantity("output"),
        "needs-components-q": quantity("output"),
        "long-after-weight-q": quantity("output"),
        "na-twin-a": quantity("output"),
        "na-twin-b": quantity("output"),
        "long-twin-a": quantity("output"),
        "long-twin-b": quantity("output"),
        "dep-twin-a": quantity("output"),
        "dep-twin-b": quantity("output"),
        "airplane-cfg": quantity("derived", type="airplane"),
        "cfg-span-q": quantity("output", unit="m"),
    }
    scaled = formula({"m": "aircraft-mass"}, {"r": "scaled-q"})
    scaled["inputs"]["k"] = None
    scaled["applications"][0]["bind"]["k"] = {"const": 3.0, "source": "test constant"}
    unexposed = formula({"m": "aircraft-mass"}, {"r": "unexposed-q"})
    unexposed["outputs"]["u"] = None
    unexposed["applications"][0]["produce"]["u"] = None
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
        "curve-reader": formula({"c": "curve-q"}, {"r": "curve-read-q"}),
        "needs-components": formula(
            {"m": "aircraft-mass", "c": "components"}, {"r": "needs-components-q"}
        ),
        "long-after-weight": formula({"w": "weight"}, {"r": "long-after-weight-q"}, cost="minutes"),
        "na-twin": formula({"p": "roll-q"}, {"a": "na-twin-a", "b": "na-twin-b"}),
        "long-twin": formula(
            {"m": "aircraft-mass"}, {"a": "long-twin-a", "b": "long-twin-b"}, cost="minutes"
        ),
        "dep-twin": formula({"w": "weight"}, {"a": "dep-twin-a", "b": "dep-twin-b"}),
        "polar-twin": formula({"m": "aircraft-mass"}, {"pol": "polar-q", "s": "polar-scalar-q"}),
        "polar-reader": formula({"pol": "polar-q"}, {"r": "polar-read-q"}),
        "na-when": formula({"p": "roll-q"}, {"r": "na-when-q"}, when="has_aileron"),
        "long-after-long": formula({"l": "long-q"}, {"r": "long-after-long-q"}, cost="minutes"),
        "long-needs-t": formula(
            {"m": "aircraft-mass", "t": "target-t"}, {"r": "long-needs-t-q"}, cost="minutes"
        ),
        "long-after-roll": formula({"p": "roll-q"}, {"r": "long-after-roll-q"}, cost="minutes"),
        "when-after-weight": formula(
            {"w": "weight"}, {"r": "when-after-weight-q"}, when="has_aileron"
        ),
        "err-missing": formula({"w": "weight", "t": "target-t"}, {"r": "err-missing-q"}),
        "after-both": formula({"a": "twin-a", "b": "twin-b"}, {"r": "after-both-q"}),
        "unexposed": unexposed,
        "three-inputs": formula(
            {"m": "aircraft-mass", "g": "gravity", "t": "target-t"}, {"r": "three-q"}
        ),
        "tail-twin": formula(
            {"m": "aircraft-mass"},
            {"a": "tail-twin-a", "b": "tail-twin-b"},
            when="has_horizontal_tail",
        ),
        "curve-twin": formula({"c": "curve-q"}, {"a": "curve-twin-a", "b": "curve-twin-b"}),
        "pending-given": formula(
            {"m": "aircraft-mass", "t": "target-t"},
            {"r": "pending-given-q"},
            when="has_horizontal_tail",
            given=["calc:target-t"],
        ),
        "two-na": formula({"p": "roll-q", "q": "na-when-q"}, {"r": "two-na-q"}),
        "twice-na": formula({"p": "roll-q", "q": "roll-q"}, {"r": "twice-na-q"}),
        "pending-curve": formula(
            {"c": "curve-q"}, {"r": "pending-curve-q"}, when="has_horizontal_tail"
        ),
        "two-givens": formula(
            {"m": "aircraft-mass", "t": "target-t", "u": "target-u"},
            {"r": "two-givens-q"},
            given=["calc:target-t", "calc:target-u"],
        ),
        "two-uncarried": formula({"c": "curve-q", "p": "polar-q"}, {"r": "two-uncarried-q"}),
        "three-uncarried": formula(
            {"c": "curve-q", "p": "polar-q", "k": "components"}, {"r": "three-uncarried-q"}
        ),
        "density-user": formula({"rho": "air-density"}, {"r": "density-q"}),
        "margin-user": formula({"k": "margin-target"}, {"r": "margin-q"}),
        "both-user": formula({"rho": "air-density", "k": "margin-target"}, {"r": "both-q"}),
        "density-again": formula({"rho": "air-density"}, {"r": "density-again-q"}),
        "long-density": formula({"rho": "air-density"}, {"r": "long-density-q"}, cost="minutes"),
        "optional-density": formula(
            {"m": "aircraft-mass", "rho": "air-density"},
            {"r": "optional-density-q"},
            optional=["rho"],
        ),
        "fail-density": formula({"w": "weight", "rho": "air-density"}, {"r": "fail-density-q"}),
        "gravity-only": formula({"g": "gravity"}, {"r": "gravity-only-q"}),
        "after-margin": formula({"q": "margin-q"}, {"r": "after-margin-q"}),
        "density-when": formula(
            {"rho": "air-density"}, {"r": "density-when-q"}, when="has_aileron"
        ),
        "density-after-roll": formula(
            {"rho": "air-density", "p": "roll-q"}, {"r": "density-after-roll-q"}
        ),
        "density-pending": formula(
            {"rho": "air-density"}, {"r": "density-pending-q"}, when="has_horizontal_tail"
        ),
        "density-needs-t": formula(
            {"rho": "air-density", "t": "target-t"}, {"r": "density-needs-t-q"}
        ),
        "density-after-long": formula(
            {"rho": "air-density", "l": "long-q"}, {"r": "density-after-long-q"}
        ),
        "margin-and-after": formula(
            {"q": "margin-q", "k": "margin-target"}, {"r": "margin-and-after-q"}
        ),
        "density-after-margin": formula(
            {"q": "margin-q", "rho": "air-density"}, {"r": "density-after-margin-q"}
        ),
        "mass-airplane": formula({"m": "aircraft-mass", "a": "airplane"}, {"r": "mass-airplane-q"}),
        "configure": formula({"a": "airplane"}, {"c": "airplane-cfg"}),
        "cfg-span": formula({"a": "airplane-cfg"}, {"s": "cfg-span-q"}),
        "curve-producer": formula({"m": "aircraft-mass"}, {"c": "curve-q"}),
    }
    return model_of(quantities, formulas, defaults=DEFAULTS)


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


async def _pair(x: Inputs, ctx: Context) -> Mapping[str, object]:
    return {"a": 1.0, "b": 2.0}


async def _one(x: Inputs, ctx: Context) -> Mapping[str, object]:
    return {"r": 1.0}


async def _polar_twin(x: Inputs, ctx: Context) -> Mapping[str, object]:
    return {"pol": "not a value v1 carries", "s": 5.0}


async def _unexposed(x: Inputs, ctx: Context) -> Mapping[str, object]:
    return {"r": 1.0, "u": 99.0}


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
    "curve-reader": _one,
    "needs-components": _one,
    "long-after-weight": _one,
    "na-twin": _pair,
    "long-twin": _pair,
    "dep-twin": _pair,
    "polar-twin": _polar_twin,
    "polar-reader": _one,
    "na-when": _one,
    "long-after-long": _one,
    "long-needs-t": _one,
    "long-after-roll": _one,
    "when-after-weight": _one,
    "err-missing": _one,
    "after-both": _one,
    "unexposed": _unexposed,
    "three-inputs": _one,
    "tail-twin": _pair,
    "curve-twin": _pair,
    "pending-given": _one,
    "two-na": _one,
    "twice-na": _one,
    "pending-curve": _one,
    "two-givens": _one,
    "two-uncarried": _one,
    "three-uncarried": _one,
    "density-user": _one,
    "margin-user": _one,
    "both-user": _one,
    "density-again": _one,
    "long-density": _one,
    "optional-density": _one,
    "fail-density": _one,
    "gravity-only": _one,
    "after-margin": _one,
    "density-when": _one,
    "density-after-roll": _one,
    "density-pending": _one,
    "density-needs-t": _one,
    "density-after-long": _one,
    "margin-and-after": _one,
    "density-after-margin": _one,
    "mass-airplane": _one,
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
    values: Mapping[str, float] | None = None,
    wings: dict[str, Any] | None = None,
    geometry_mass_kg: float | None = None,
) -> AircraftInput:
    """A wingless aircraft of mass 2 kg and gravity 9.81 m/s^2, with the given values and wings."""
    document: dict[str, Any] = {"name": "t"}
    if geometry_mass_kg is not None:
        document["total_mass_kg"] = geometry_mass_kg
    document["wings"] = {"Main": main_wing_document()} if wings is None else wings
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
    return {
        "Main": {
            "name": "Main",
            "symmetric": True,
            "surface_type": "main_wing",
            "x_secs": sections,
        }
    }


def deflected_wing() -> dict[str, Any]:
    """A wing whose device carries a non-zero deflection, which the kernel ignores and reports."""
    wings = aileron_wing()
    wings["Main"]["x_secs"][0]["trailing_edge_device"]["deflection_deg"] = 5.0
    return wings


def two_deflected_wing() -> dict[str, Any]:
    """A wing with a deflected device on each of its first two ribs."""
    sections = [
        {
            "xyz_le": [0.0, y, 0.0],
            "chord": 0.2,
            "twist": 0.0,
            "airfoil": "naca2412",
            **(
                {"trailing_edge_device": {"role": "aileron", "deflection_deg": 5.0 + y}}
                if y < 1.0
                else {}
            ),
        }
        for y in (0.0, 0.5, 1.0)
    ]
    return {
        "Main": {
            "name": "Main",
            "symmetric": True,
            "surface_type": "main_wing",
            "x_secs": sections,
        }
    }
