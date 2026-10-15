"""Registry: the traceability check against a canon model (ARCHITECTURE ch. 8.12, tests Q1, Q11)."""

import importlib.util
import textwrap
from collections.abc import Callable, Mapping
from pathlib import Path

import pytest
from aero_kernel.canon.model import CanonModel
from aero_kernel.registry import (
    DEFAULT_REGISTRY,
    CheckResult,
    Registry,
    RegistryFinding,
    check_registry,
    interface_fingerprint,
)

HELD = CheckResult(state="held", message="ok")


def pre(x: Mapping[str, float]) -> CheckResult:
    return HELD


def post(x: Mapping[str, float], y: Mapping[str, float]) -> CheckResult:
    return HELD


async def impl(x: Mapping[str, float], ctx: object) -> dict[str, float]:
    return {}


def fingerprint_of(model: CanonModel, slug: str) -> str:
    formula = model.formula(slug)
    assert formula is not None
    return interface_fingerprint(formula)


def codes(findings: tuple[RegistryFinding, ...]) -> list[tuple[str, str, str | None]]:
    return [(f.code, f.slug, f.check_id) for f in findings]


def test_an_empty_registry_has_no_findings(flight_canon: CanonModel) -> None:
    """A model formula without implementation is not_implemented at runtime (Q1), no finding."""
    assert check_registry(Registry(), flight_canon) == ()


def test_a_matching_registry_has_no_findings(flight_canon: CanonModel) -> None:
    registry = Registry()
    registry.formula("stall-speed", interface=fingerprint_of(flight_canon, "stall-speed"))(impl)
    registry.precondition("stall-speed", "rho_at_evaluation_altitude")(pre)
    registry.postcondition("stall-speed", "optimum_at_first_cl_peak")(post)
    registry.postcondition("butterfly-approach", "optimum_at_first_cl_peak")(post)
    registry.relation("stall-speed")(post)
    assert check_registry(registry, flight_canon) == ()


def test_a_slug_the_model_does_not_have_is_unknown(flight_canon: CanonModel) -> None:
    registry = Registry()
    fake = "sha256:" + "1" * 64
    registry.formula("no-such-formula", interface=fake)(impl)
    registry.relation("no-such-relation")(post)
    registry.precondition("no-such-check", "a")(pre)
    findings = check_registry(registry, flight_canon)
    assert codes(findings) == [
        ("unknown_formula", "calc:no-such-check", None),
        ("unknown_formula", "calc:no-such-formula", None),
        ("unknown_formula", "calc:no-such-relation", None),
    ]
    assert all(f.message for f in findings)


def test_a_namespace_the_model_does_not_have_is_unknown(flight_canon: CanonModel) -> None:
    registry = Registry()
    registry.relation("other:stall-speed")(post)
    assert codes(check_registry(registry, flight_canon)) == [
        ("unknown_formula", "other:stall-speed", None)
    ]


def _unknown_precondition(r: Registry) -> None:
    r.precondition("stall-speed", "no-such-check")(pre)


def _postcondition_id_used_as_precondition(r: Registry) -> None:
    r.precondition("stall-speed", "optimum_at_first_cl_peak")(pre)


def _precondition_id_used_as_postcondition(r: Registry) -> None:
    r.postcondition("stall-speed", "rho_at_evaluation_altitude")(post)


@pytest.mark.parametrize(
    ("register", "check_id"),
    [
        (_unknown_precondition, "no-such-check"),
        (_postcondition_id_used_as_precondition, "optimum_at_first_cl_peak"),
        (_precondition_id_used_as_postcondition, "rho_at_evaluation_altitude"),
    ],
)
def test_a_check_the_formula_does_not_have_on_that_side_is_unknown(
    flight_canon: CanonModel, register: Callable[[Registry], None], check_id: str
) -> None:
    registry = Registry()
    register(registry)
    findings = check_registry(registry, flight_canon)
    assert codes(findings) == [("unknown_check", "calc:stall-speed", check_id)]
    assert check_id in findings[0].message


def test_a_changed_interface_is_a_stale_implementation(flight_canon: CanonModel) -> None:
    registry = Registry()
    registry.formula("stall-speed", interface=fingerprint_of(flight_canon, "neutral-point"))(impl)
    findings = check_registry(registry, flight_canon)
    assert codes(findings) == [("stale_implementation", "calc:stall-speed", None)]


def test_findings_are_frozen_and_closed() -> None:
    finding = RegistryFinding(code="unknown_formula", slug="calc:a", message="m")
    assert finding.check_id is None
    with pytest.raises(ValueError, match="frozen"):
        finding.slug = "b"
    with pytest.raises(ValueError, match="validation error"):
        RegistryFinding(code="other", slug="a", message="m")  # pyright: ignore[reportArgumentType]  # malformed on purpose


SAMPLES = {
    "requests_clean": 'ctx.embedded("stall-speed.clean")',
    "requests_qualified": 'ctx.embedded("calc:stall-speed.clean")',
    "requests_nothing": "pass",
    "requests_something_else": """
        ctx.embedded("stall-speed.landing")
        ctx.embedded(1)
        ctx.embedded("not a reference")
        ctx.other("stall-speed.clean")
    """,
}


def _sample_function(tmp_path: Path, name: str) -> Callable[..., object]:
    """Import a module of its own whose ``formula`` coroutine contains the sample's calls.

    The check scans the whole module, so each sample needs a module to itself.
    """
    body = textwrap.indent(textwrap.dedent(SAMPLES[name]).strip(), "    ")
    path = tmp_path / f"{name}.py"
    path.write_text(f"async def formula(x, ctx):\n{body}\n    return {{}}\n", encoding="utf-8")
    spec = importlib.util.spec_from_file_location(name, path)
    assert spec is not None
    assert spec.loader is not None
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module.formula


def _embedder_registry(model: CanonModel, func: Callable[..., object]) -> Registry:
    registry = Registry()
    registry.formula(
        "max-mass-level-flight", interface=fingerprint_of(model, "max-mass-level-flight")
    )(func)  # pyright: ignore[reportArgumentType]  # the samples are coroutine functions
    return registry


def test_an_implemented_embedder_needs_a_relation_of_every_embedded_formula(
    flight_canon: CanonModel,
    tmp_path: Path,
) -> None:
    registry = _embedder_registry(flight_canon, _sample_function(tmp_path, "requests_clean"))
    findings = check_registry(registry, flight_canon)
    assert codes(findings) == [("missing_relation", "calc:max-mass-level-flight", None)]
    assert "calc:stall-speed" in findings[0].message
    registry.relation("stall-speed")(post)
    assert check_registry(registry, flight_canon) == ()


@pytest.mark.parametrize("sample", ["requests_clean", "requests_qualified"])
def test_the_embedder_may_request_an_item_bare_or_qualified(
    flight_canon: CanonModel, tmp_path: Path, sample: str
) -> None:
    registry = _embedder_registry(flight_canon, _sample_function(tmp_path, sample))
    registry.relation("stall-speed")(post)
    assert check_registry(registry, flight_canon) == ()


@pytest.mark.parametrize("sample", ["requests_nothing", "requests_something_else"])
def test_an_embedder_that_does_not_request_its_item_is_a_finding(
    flight_canon: CanonModel, tmp_path: Path, sample: str
) -> None:
    registry = _embedder_registry(flight_canon, _sample_function(tmp_path, sample))
    registry.relation("stall-speed")(post)
    findings = check_registry(registry, flight_canon)
    assert codes(findings) == [("embedded_item_not_requested", "calc:max-mass-level-flight", None)]
    assert "calc:stall-speed.clean" in findings[0].message


def test_an_embedder_without_readable_source_is_a_finding(flight_canon: CanonModel) -> None:
    namespace: dict[str, object] = {}
    exec("async def f(x, ctx):\n    return {}\n", namespace)  # a function with no source file
    registry = _embedder_registry(flight_canon, namespace["f"])  # pyright: ignore[reportArgumentType]
    registry.relation("stall-speed")(post)
    findings = check_registry(registry, flight_canon)
    assert codes(findings) == [("embedded_item_not_requested", "calc:max-mass-level-flight", None)]
    assert "source" in findings[0].message


def test_findings_are_sorted_and_collected_from_every_rule(flight_canon: CanonModel) -> None:
    registry = Registry()
    registry.precondition("stall-speed", "zzz")(pre)
    registry.precondition("stall-speed", "aaa")(pre)
    registry.relation("a-unknown")(post)
    findings = check_registry(registry, flight_canon)
    assert codes(findings) == [
        ("unknown_formula", "calc:a-unknown", None),
        ("unknown_check", "calc:stall-speed", "aaa"),
        ("unknown_check", "calc:stall-speed", "zzz"),
    ]


def test_the_default_registry_is_consistent_with_the_fixture_model(
    flight_canon: CanonModel,
) -> None:
    """The CI traceability test; it runs against the packaged model once that exists."""
    assert check_registry(DEFAULT_REGISTRY, flight_canon) == ()
