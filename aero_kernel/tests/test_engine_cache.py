"""The node cache in the engine (ARCHITECTURE ch. 8.4, #1332), on the fixture canon with stubs.

Every test injects a fresh ``DedupedCache`` into ``evaluate``, counts the calls of the stub
formulas, and compares a hit with the computed value bit for bit (``struct``), never with a
tolerance.
"""

import asyncio
import struct
from collections import Counter
from collections.abc import Mapping

import pytest
from aero_kernel.build import Build
from aero_kernel.cache import DedupedCache, Entry, MemoryCache
from aero_kernel.context import Context, Inputs, Solvers
from aero_kernel.engine import evaluate
from aero_kernel.errors import ErrorCategory, FormulaError
from aero_kernel.graph import CanonGraph
from aero_kernel.registry import Registry
from aero_kernel.runtime import SolverRuntime
from aero_kernel.schema import (
    AircraftInput,
    ComputeRequest,
    ComputeResult,
    Polar,
    QuantityResult,
    QuantityStatus,
)
from aero_kernel.solvers.avl import AvlAdapter
from aero_kernel.tests.engine_builders import (
    A_POLAR,
    NO_SOLVERS,
    Impl,
    aircraft,
    make_build,
    num,
    registry_with,
)
from aero_kernel.tests.formula_builders import StubAtmosphere, solvers_with
from aero_kernel.tests.graph_builders import formula, model_of, quantity
from aero_kernel.tests.test_engine_worlds import Probe
from aero_kernel.tests.test_engine_worlds import fixture_model as worlds_model
from aero_kernel.tests.wing_builders import airplane_document, main_wing_document
from pydantic import JsonValue

pytestmark = [pytest.mark.asyncio, pytest.mark.usefixtures("pending_horizontal_tail")]

# A threshold no validation rule reads, so only the node that reads it declares it.
RULE, PARAMETER = "flap-model-validity", "max_flap_deflection"
# A threshold the fixture canon holds (its geometry rules), so the caller may override it.
OVERRIDABLE = "main-wing-spanwise-extent.max_inclination"


class RecordingCache(MemoryCache):
    """A memory cache that remembers the keys it was asked to store."""

    def __init__(self, max_entries: int = 64) -> None:
        super().__init__(max_entries=max_entries)
        self.stored: list[str] = []

    def put(self, key: str, entry: Entry) -> None:
        self.stored.append(key)
        super().put(key, entry)


class Counted:
    """Stub formulas that count their calls by formula slug."""

    def __init__(self) -> None:
        self.calls: Counter[str] = Counter()

    def __call__(self, slug: str, impl: Impl) -> Impl:
        async def counted(x: Inputs, ctx: Context) -> Mapping[str, object]:
            self.calls[slug] += 1
            return await impl(x, ctx)

        return counted


async def _weight(x: Inputs, ctx: Context) -> Mapping[str, object]:
    return {"w": num(x, "m") * num(x, "g")}


async def _double(x: Inputs, ctx: Context) -> Mapping[str, object]:
    return {"d": 2 * num(x, "w")}


async def _gravity_only(x: Inputs, ctx: Context) -> Mapping[str, object]:
    return {"r": -0.0 * num(x, "g")}  # -0.0: the sign must survive the round trip


async def _reads_rule(x: Inputs, ctx: Context) -> Mapping[str, object]:
    return {"r": ctx.solvers.rules.value(RULE, PARAMETER) + num(x, "m")}


async def _reads_overridable(x: Inputs, ctx: Context) -> Mapping[str, object]:
    rule, _, parameter = OVERRIDABLE.partition(".")
    return {"r": ctx.solvers.rules.value(rule, parameter) + num(x, "m")}


async def _fails(x: Inputs, ctx: Context) -> Mapping[str, object]:
    raise FormulaError(
        ErrorCategory.NOT_CONVERGED, "not_converged", "no convergence", "try another input"
    )


async def _polar(x: Inputs, ctx: Context) -> Mapping[str, object]:
    return {"pol": A_POLAR, "s": 5.0}


def counted_build(counter: Counted, **extra: Impl) -> Build:
    """The fixture build with counting stubs for the formulas the cache tests use."""
    stubs: dict[str, Impl] = {
        "weight": _weight,
        "double": _double,
        "gravity-only": _gravity_only,
        "independent": _reads_rule,
        "polar-twin": _polar,
        **extra,
    }
    return make_build(registry_with({slug: counter(slug, impl) for slug, impl in stubs.items()}))


async def run(
    build: Build,
    store: MemoryCache | None,
    *slugs: str,
    the_aircraft: AircraftInput | None = None,
    solvers: Solvers = NO_SOLVERS,
    budget: float | None = None,
) -> ComputeResult:
    """One call; ``store`` ``None`` is the stateless path."""
    return await evaluate(
        build,
        the_aircraft or aircraft(),
        ComputeRequest(quantities=slugs, time_budget_s=budget),
        solvers=solvers,
        cache=None if store is None else DedupedCache(store),
    )


def with_override(value: float) -> AircraftInput:
    """The fixture aircraft with the caller's override of the overridable threshold."""
    plain = aircraft()
    return AircraftInput(
        airplane=plain.airplane,
        values=plain.values,
        rule_overrides={OVERRIDABLE: value},
    )


def by_slug(result: ComputeResult) -> dict[str, QuantityResult]:
    return {q.slug: q for q in result.quantities}


def bits(value: float | None) -> bytes:
    assert value is not None
    return struct.pack("<d", value)


async def test_a_second_identical_call_serves_every_node_from_the_cache() -> None:
    counter = Counted()
    build, store = counted_build(counter), RecordingCache()
    slugs = ("double-weight", "gravity-only-q")
    first = by_slug(await run(build, store, *slugs))
    second = by_slug(await run(build, store, *slugs))
    assert counter.calls == {"weight": 1, "double": 1, "gravity-only": 1}
    for slug in slugs:
        assert not first[slug].from_cache
        assert second[slug].from_cache
        assert bits(second[slug].value) == bits(first[slug].value)
    assert repr(second["gravity-only-q"].value) == "-0.0"


async def test_a_hit_reports_the_time_measured_when_it_was_computed() -> None:
    counter = Counted()
    build, store = counted_build(counter), RecordingCache()
    first = by_slug(await run(build, store, "double-weight"))["double-weight"]
    second = by_slug(await run(build, store, "double-weight"))["double-weight"]
    assert first.timing is not None
    assert second.timing is not None
    assert second.timing.model_dump_json() == first.timing.model_dump_json()


async def test_the_stateless_path_never_serves_from_a_cache() -> None:
    counter = Counted()
    build = counted_build(counter)
    for _ in range(2):
        quantity = by_slug(await run(build, None, "double-weight"))["double-weight"]
        assert not quantity.from_cache
    assert counter.calls == {"weight": 2, "double": 2}


async def test_a_changed_input_expires_exactly_its_subtree() -> None:
    counter = Counted()
    build, store = counted_build(counter), RecordingCache()
    slugs = ("double-weight", "gravity-only-q")
    await run(build, store, *slugs)
    changed = aircraft({"aircraft-mass": 3.0})
    second = by_slug(await run(build, store, *slugs, the_aircraft=changed))
    assert counter.calls == {"weight": 2, "double": 2, "gravity-only": 1}
    assert not second["double-weight"].from_cache
    assert second["gravity-only-q"].from_cache


async def test_a_downstream_node_whose_inputs_did_not_change_value_still_hits() -> None:
    """A1: the key holds the direct input values, so an unchanged value keeps the node cached."""
    counter = Counted()

    async def mass_free_weight(x: Inputs, ctx: Context) -> Mapping[str, object]:
        return {"w": num(x, "g")}

    build, store = counted_build(counter, weight=mass_free_weight), RecordingCache()
    await run(build, store, "double-weight")
    second = by_slug(
        await run(build, store, "double-weight", the_aircraft=aircraft({"aircraft-mass": 3.0}))
    )
    assert counter.calls == {"weight": 2, "double": 1}
    assert second["double-weight"].from_cache


@pytest.mark.parametrize(
    ("slug", "status"),
    [
        ("roll-q", QuantityStatus.NOT_APPLICABLE),
        ("long-q", QuantityStatus.SKIPPED),
        ("unimpl-q", QuantityStatus.ERROR),
        ("err-missing-q", QuantityStatus.ERROR),
    ],
)
async def test_a_node_without_a_value_is_never_stored(slug: str, status: QuantityStatus) -> None:
    store = RecordingCache()
    build = make_build()
    quantity = by_slug(await run(build, store, slug))[slug]
    assert quantity.status is status
    assert not quantity.from_cache
    produced = {"err-missing-q": 1}.get(slug, 0)  # only its predecessor weight is ok and stored
    assert len(store.stored) == produced


async def test_a_failed_computation_is_not_stored_and_runs_again() -> None:
    counter = Counted()
    build, store = counted_build(counter, independent=_fails), RecordingCache()
    for _ in range(2):
        quantity = by_slug(await run(build, store, "independent-q"))["independent-q"]
        assert quantity.error is not None
        assert quantity.error.code == "not_converged"
        assert not quantity.from_cache
    assert counter.calls["independent"] == 2
    assert store.stored == []


async def test_a_node_open_when_the_budget_expired_is_not_stored() -> None:
    counter = Counted()

    async def slow_double(x: Inputs, ctx: Context) -> Mapping[str, object]:
        await asyncio.sleep(0.2)
        return {"d": 2 * num(x, "w")}

    build, store = counted_build(counter, double=slow_double), RecordingCache()
    timed_out = by_slug(await run(build, store, "double-weight", budget=0.05))["double-weight"]
    assert timed_out.error is not None
    assert timed_out.error.code == "timeout"
    assert len(store.stored) == 1  # weight finished in time
    again = by_slug(await run(build, store, "double-weight"))["double-weight"]
    assert again.status is QuantityStatus.OK
    assert not again.from_cache
    assert counter.calls == {"weight": 1, "double": 2}


async def test_an_overridden_threshold_changes_the_key() -> None:
    counter = Counted()
    build, store = counted_build(counter, independent=_reads_overridable), RecordingCache()
    plain = by_slug(await run(build, store, "independent-q"))["independent-q"]
    overridden = with_override(60.0)
    changed = by_slug(await run(build, store, "independent-q", the_aircraft=overridden))
    assert not changed["independent-q"].from_cache
    assert bits(changed["independent-q"].value) != bits(plain.value)
    assert counter.calls["independent"] == 2


async def test_a_call_without_overrides_after_one_with_gets_no_stale_hit() -> None:
    counter = Counted()
    build, store = counted_build(counter, independent=_reads_overridable), RecordingCache()
    overridden = with_override(60.0)
    first = by_slug(await run(build, store, "independent-q", the_aircraft=overridden))
    plain = by_slug(await run(build, store, "independent-q"))["independent-q"]
    assert not plain.from_cache
    assert bits(plain.value) != bits(first["independent-q"].value)
    assert counter.calls["independent"] == 2


async def test_a_hit_declares_the_thresholds_its_node_read() -> None:
    counter = Counted()
    build, store = counted_build(counter), RecordingCache()
    first = await run(build, store, "independent-q")
    second = await run(build, store, "independent-q")
    assert by_slug(second)["independent-q"].from_cache
    read = [(r.rule, r.parameter) for r in second.provenance.rules_used]
    assert (RULE, PARAMETER) in read
    assert second.provenance.rules_used == first.provenance.rules_used


async def test_a_polar_output_comes_back_as_an_equal_fresh_polar() -> None:
    counter = Counted()
    seen: list[Polar] = []

    async def reader(x: Inputs, ctx: Context) -> Mapping[str, object]:
        polar = x["pol"]
        assert isinstance(polar, Polar)
        seen.append(polar)
        return {"r": float(len(seen))}

    build, store = counted_build(counter), RecordingCache()
    await run(build, store, "polar-scalar-q")
    reading = counted_build(counter, **{"polar-reader": reader})
    result = by_slug(await run(reading, store, "polar-scalar-q", "polar-read-q"))
    assert result["polar-scalar-q"].from_cache
    assert counter.calls["polar-twin"] == 1
    (polar,) = seen
    assert polar == A_POLAR
    assert polar is not A_POLAR


async def test_an_airplane_output_is_not_cached_and_says_why(
    caplog: pytest.LogCaptureFixture,
) -> None:
    """The configured airplane cannot round-trip (mm fields parse to metres): declared, not stored."""
    counter = Counted()

    async def configure(x: Inputs, ctx: Context) -> Mapping[str, object]:
        return {"c": x["a"]}

    build, store = counted_build(counter, configure=configure), RecordingCache()
    with caplog.at_level("DEBUG", logger="aero_kernel.engine"):
        first = by_slug(await run(build, store, "cfg-span-q"))["cfg-span-q"]
        second = by_slug(await run(build, store, "cfg-span-q"))["cfg-span-q"]
    assert (first.status, second.status) == (QuantityStatus.OK, QuantityStatus.OK)
    assert counter.calls["configure"] == 2
    assert second.from_cache  # its own node reads an unchanged configured airplane
    assert any("produces a value of type airplane" in r.getMessage() for r in caplog.records)


async def test_a_quantity_is_from_cache_only_if_its_own_node_hit() -> None:
    counter = Counted()
    build, store = counted_build(counter), RecordingCache()
    await run(build, store, "weight")
    result = by_slug(await run(build, store, "weight", "double-weight"))
    assert result["weight"].from_cache
    assert not result["double-weight"].from_cache


class VersionedAvl(AvlAdapter):
    """An AVL adapter that reports a given binary version and is never run."""

    def __init__(self, version: str, nspan: int = 7) -> None:
        super().__init__(SolverRuntime())
        self.version = version
        self.nspan = nspan

    def tool_versions(self) -> dict[str, str]:
        return {"avl-binary": self.version}

    def settings(self) -> dict[str, JsonValue]:
        return {"avl_nspan": self.nspan}


def two_tool_build(counter: Counted) -> Build:
    """A formula whose world ``alpha`` runs on ATM and ``beta`` on AVL (#1221)."""
    model = model_of(
        {"aircraft-mass": quantity("input", unit="kg"), "np-q": quantity("derived")},
        {
            "np": formula(
                {"m": "aircraft-mass"},
                {"o": "np-q"},
                tool="AVL",
                uncertainty="interval",
                worlds=["alpha", "beta"],
            )
        },
        taxonomy={
            "tools": [{"id": "ATM", "name": "ATM"}, {"id": "AVL", "name": "AVL"}],
            "worlds": [{"id": "alpha", "tool": "ATM"}, {"id": "beta", "tool": "AVL"}],
        },
    )

    async def np(x: Inputs, ctx: Context) -> Mapping[str, object]:
        assert ctx.world is not None
        counter.calls[ctx.world] += 1
        return {"o": num(x, "m") + (1.0 if ctx.world == "alpha" else 2.0)}

    registry = Registry()
    registry.formula("np")(np)
    return Build(
        model=model,
        graph=CanonGraph(model),
        digest="sha256:" + "ab" * 32,
        registry=registry,
        report=registry.check_traceability(model),
    )


async def test_a_new_tool_version_expires_only_the_world_of_that_tool() -> None:
    counter = Counted()
    build, store = two_tool_build(counter), RecordingCache()
    the_aircraft = AircraftInput.model_validate(
        {"airplane": airplane_document(), "values": {"aircraft-mass": 2.0}}
    )
    atmosphere = StubAtmosphere({}, {"aerosandbox": "1.2.3"})

    async def interval_with(avl_version: str) -> QuantityResult:
        solvers = solvers_with(atmosphere=atmosphere, avl=VersionedAvl(avl_version))
        result = await run(build, store, "np-q", the_aircraft=the_aircraft, solvers=solvers)
        return by_slug(result)["np-q"]

    first = await interval_with("1.0")
    again = await interval_with("1.0")
    upgraded = await interval_with("1.1")
    assert counter.calls == {"alpha": 1, "beta": 2}
    assert (first.from_cache, again.from_cache, upgraded.from_cache) == (False, True, False)
    assert upgraded.interval is not None
    assert first.interval is not None
    assert upgraded.interval.model_dump_json() == first.interval.model_dump_json()


async def test_a_non_finite_number_in_an_unread_geometry_field_does_not_break_the_key() -> None:
    """Validation skips unread fields (the spar pocket); the key spells NaN out instead of failing."""
    counter = Counted()

    async def span(x: Inputs, ctx: Context) -> Mapping[str, object]:
        counter.calls["wing-span"] += 1
        return {"s": 1.5}

    def with_spar(**extra: float) -> AircraftInput:
        wing = main_wing_document()
        spar = {"spare_support_dimension_width": 0.01, "spare_support_dimension_height": 0.01}
        wing["x_secs"][0]["spare_list"] = [{**spar, **extra}]
        return aircraft(wings={"Main": wing})

    build, store = counted_build(counter, **{"wing-span": span}), RecordingCache()
    with_nan = with_spar(spare_support_dimension_width=float("nan"))
    first = by_slug(await run(build, store, "span-q", the_aircraft=with_nan))["span-q"]
    second = by_slug(await run(build, store, "span-q", the_aircraft=with_nan))["span-q"]
    without = by_slug(await run(build, store, "span-q", the_aircraft=with_spar()))["span-q"]
    assert first.status is QuantityStatus.OK
    assert second.from_cache
    assert not without.from_cache  # NaN is not equated with a finite pocket width


def worlds_build(probe: Probe) -> Build:
    """The three-world fixture canon of the world tests (head -> unc -> down -> join <- side)."""
    model = worlds_model()
    registry = probe.registry()
    return Build(
        model=model,
        graph=CanonGraph(model),
        digest="sha256:" + "ab" * 32,
        registry=registry,
        report=registry.check_traceability(model),
    )


async def test_every_world_of_an_uncertain_node_has_its_own_cache_entry() -> None:
    """The world assignment is part of the node key: the worlds share one tool (APP), nothing else
    tells their entries apart, so a key without the world would serve the first world's value to all.

    Hand values (fixture of test_engine_worlds): alpha/beta/gamma return 10/20/30; ``down`` adds 1,
    ``side`` is 7, ``join`` = down + side = 10 + 1 + 7 = 18, 28 and 38.
    """
    probe = Probe()
    build = worlds_build(probe)
    cache = DedupedCache(MemoryCache(max_entries=64))
    the_aircraft = AircraftInput.model_validate(
        {"airplane": airplane_document(), "values": {"aircraft-mass": 2.0}}
    )
    expected_np = {"unc=alpha": 10.0, "unc=beta": 20.0, "unc=gamma": 30.0}
    expected_join = {"unc=alpha": 18.0, "unc=beta": 28.0, "unc=gamma": 38.0}
    for second_call in (False, True):
        result = await evaluate(
            build,
            the_aircraft,
            ComputeRequest(quantities=("np-q", "join-q")),
            solvers=NO_SOLVERS,
            cache=cache,
        )
        found = by_slug(result)
        assert found["np-q"].interval is not None
        assert found["join-q"].interval is not None
        assert found["np-q"].interval.worlds == expected_np
        assert found["join-q"].interval.worlds == expected_join
        assert found["np-q"].from_cache is second_call
        assert found["join-q"].from_cache is second_call
    # one run per world over both calls: three in total
    assert sorted(str(world) for name, world in probe.calls if name == "unc") == [
        "alpha",
        "beta",
        "gamma",
    ]


def changed_polar() -> Polar:
    """A_POLAR with every lift coefficient raised by 0.1 (0.1 -> 0.2, 0.2 -> 0.3)."""
    return Polar(alpha_deg=(0.0, 1.0), cl=(0.2, 0.3), cd=(0.01, 0.01))


async def test_a_changed_polar_a_node_reads_changes_its_key() -> None:
    """The reader's key holds the polar it reads: another polar must not be served the old value."""
    counter = Counted()

    async def twin(x: Inputs, ctx: Context) -> Mapping[str, object]:
        counter.calls["polar-twin"] += 1
        polar = A_POLAR if num(x, "m") == 2.0 else changed_polar()
        return {"pol": polar, "s": 5.0}

    async def reader(x: Inputs, ctx: Context) -> Mapping[str, object]:
        polar = x["pol"]
        assert isinstance(polar, Polar)
        return {"r": polar.cl[0]}

    build = counted_build(counter, **{"polar-twin": twin, "polar-reader": reader})
    store = RecordingCache()
    first = by_slug(await run(build, store, "polar-read-q"))["polar-read-q"]
    second = by_slug(
        await run(build, store, "polar-read-q", the_aircraft=aircraft({"aircraft-mass": 3.0}))
    )["polar-read-q"]
    assert first.value == 0.1  # cl[0] of A_POLAR
    assert second.value == 0.2  # cl[0] of the changed polar: 0.1 + 0.1
    assert not second.from_cache
    assert counter.calls["polar-reader"] == 2


async def test_a_hit_reports_the_tool_versions_and_settings_of_the_computed_call() -> None:
    counter = Counted()
    build, store = two_tool_build(counter), RecordingCache()
    the_aircraft = AircraftInput.model_validate(
        {"airplane": airplane_document(), "values": {"aircraft-mass": 2.0}}
    )
    atmosphere = StubAtmosphere({}, {"aerosandbox": "1.2.3"})
    solvers = solvers_with(atmosphere=atmosphere, avl=VersionedAvl("1.0"))
    first = await run(build, store, "np-q", the_aircraft=the_aircraft, solvers=solvers)
    second = await run(build, store, "np-q", the_aircraft=the_aircraft, solvers=solvers)
    assert not by_slug(first)["np-q"].from_cache
    assert by_slug(second)["np-q"].from_cache
    assert first.provenance.tool_versions == {"aerosandbox": "1.2.3", "avl-binary": "1.0"}
    assert first.provenance.solver_settings == {"avl_nspan": 7}
    assert second.provenance.model_dump_json() == first.provenance.model_dump_json()


async def test_a_changed_solver_setting_misses_the_cache_in_the_world_of_its_tool() -> None:
    """The settings of a tool are part of its worlds' node keys (7, 7, 8 spanwise strips)."""
    counter = Counted()
    build, store = two_tool_build(counter), RecordingCache()
    the_aircraft = AircraftInput.model_validate(
        {"airplane": airplane_document(), "values": {"aircraft-mass": 2.0}}
    )
    atmosphere = StubAtmosphere({}, {"aerosandbox": "1.2.3"})
    hits: list[bool] = []
    for nspan in (7, 7, 8):
        solvers = solvers_with(atmosphere=atmosphere, avl=VersionedAvl("1.0", nspan))
        result = await run(build, store, "np-q", the_aircraft=the_aircraft, solvers=solvers)
        hits.append(by_slug(result)["np-q"].from_cache)
    assert hits == [False, True, False]
    assert counter.calls == {"alpha": 1, "beta": 2}  # the ATM world is not touched by AVL settings
