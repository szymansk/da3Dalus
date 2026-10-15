"""Registry: the traceability check against a canon model (ARCHITECTURE ch. 8.12, tests Q1, Q11)."""

from collections.abc import Callable, Mapping

import pytest
from aero_kernel.canon.model import CanonModel
from aero_kernel.registry import (
    DEFAULT_REGISTRY,
    CheckResult,
    Registry,
    RegistryFinding,
    TraceabilityReport,
    interface_fingerprint,
)

HELD = CheckResult(state="held", message="ok")
ALL_FORMULAS = [
    "calc:airplane-configuration",
    "calc:butterfly-approach",
    "calc:max-mass-level-flight",
    "calc:neutral-point",
    "calc:roll-rate-cruise",
    "calc:speed-from-stall-margin",
    "calc:stall-speed",
]


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


def codes(report: TraceabilityReport) -> list[tuple[str, str, str | None]]:
    return [(f.kind, f.slug, f.check_id) for f in report.findings]


def test_an_empty_registry_is_ok_and_every_model_formula_is_not_implemented(
    flight_canon: CanonModel,
) -> None:
    """A model formula without implementation is not_implemented (Q1), no finding."""
    report = Registry().check_traceability(flight_canon)
    assert report.findings == ()
    assert report.ok
    assert report.not_implemented == tuple(ALL_FORMULAS)


def test_a_matching_registry_is_ok_and_lists_the_rest_as_not_implemented(
    flight_canon: CanonModel,
) -> None:
    registry = Registry()
    registry.formula("stall-speed", interface=fingerprint_of(flight_canon, "stall-speed"))(impl)
    registry.precondition("stall-speed", "rho_at_evaluation_altitude")(pre)
    registry.postcondition("stall-speed", "optimum_at_first_cl_peak")(post)
    registry.postcondition("butterfly-approach", "optimum_at_first_cl_peak")(post)
    report = registry.check_traceability(flight_canon)
    assert report.ok
    assert report.not_implemented == tuple(f for f in ALL_FORMULAS if f != "calc:stall-speed")


def test_a_slug_the_model_does_not_have_is_unknown(flight_canon: CanonModel) -> None:
    registry = Registry()
    registry.formula("no-such-formula", interface="sha256:" + "1" * 64)(impl)
    registry.precondition("no-such-check", "a")(pre)
    registry.postcondition("other:stall-speed", "a")(post)
    report = registry.check_traceability(flight_canon)
    assert codes(report) == [
        ("unknown_formula", "calc:no-such-check", None),
        ("unknown_formula", "calc:no-such-formula", None),
        ("unknown_formula", "other:stall-speed", None),
    ]
    assert not report.ok
    assert all(f.message for f in report.findings)
    assert report.not_implemented == tuple(ALL_FORMULAS)


def _unknown_precondition(r: Registry) -> None:
    r.precondition("stall-speed", "no-such-check")(pre)


def _unknown_postcondition(r: Registry) -> None:
    r.postcondition("stall-speed", "no-such-check")(post)


@pytest.mark.parametrize("register", [_unknown_precondition, _unknown_postcondition])
def test_a_check_id_the_formula_does_not_have_is_unknown(
    flight_canon: CanonModel, register: Callable[[Registry], None]
) -> None:
    registry = Registry()
    register(registry)
    report = registry.check_traceability(flight_canon)
    assert codes(report) == [("unknown_check", "calc:stall-speed", "no-such-check")]
    assert "no-such-check" in report.findings[0].message


def _postcondition_id_used_as_precondition(r: Registry) -> None:
    r.precondition("stall-speed", "optimum_at_first_cl_peak")(pre)


def _precondition_id_used_as_postcondition(r: Registry) -> None:
    r.postcondition("stall-speed", "rho_at_evaluation_altitude")(post)


@pytest.mark.parametrize(
    ("register", "check_id"),
    [
        (_postcondition_id_used_as_precondition, "optimum_at_first_cl_peak"),
        (_precondition_id_used_as_postcondition, "rho_at_evaluation_altitude"),
    ],
)
def test_a_check_registered_on_the_wrong_side_is_a_kind_mismatch(
    flight_canon: CanonModel, register: Callable[[Registry], None], check_id: str
) -> None:
    registry = Registry()
    register(registry)
    report = registry.check_traceability(flight_canon)
    assert codes(report) == [("check_kind_mismatch", "calc:stall-speed", check_id)]
    assert "precondition" in report.findings[0].message
    assert "postcondition" in report.findings[0].message


def test_a_changed_interface_is_a_stale_implementation(flight_canon: CanonModel) -> None:
    registry = Registry()
    registry.formula("stall-speed", interface=fingerprint_of(flight_canon, "neutral-point"))(impl)
    report = registry.check_traceability(flight_canon)
    assert codes(report) == [("stale_implementation", "calc:stall-speed", None)]
    assert "calc:stall-speed" not in report.not_implemented


def test_findings_are_sorted_by_slug_then_kind_then_check_id(flight_canon: CanonModel) -> None:
    registry = Registry()
    registry.precondition("stall-speed", "zzz")(pre)
    registry.precondition("stall-speed", "aaa")(pre)
    registry.precondition("stall-speed", "optimum_at_first_cl_peak")(pre)
    registry.postcondition("a-unknown", "x")(post)
    assert codes(registry.check_traceability(flight_canon)) == [
        ("unknown_formula", "calc:a-unknown", None),
        ("check_kind_mismatch", "calc:stall-speed", "optimum_at_first_cl_peak"),
        ("unknown_check", "calc:stall-speed", "aaa"),
        ("unknown_check", "calc:stall-speed", "zzz"),
    ]


def test_findings_and_report_are_frozen_and_closed() -> None:
    finding = RegistryFinding(kind="unknown_formula", slug="calc:a", message="m")
    assert finding.check_id is None
    with pytest.raises(ValueError, match="frozen"):
        finding.slug = "b"
    with pytest.raises(ValueError, match="validation error"):
        RegistryFinding(kind="other", slug="a", message="m")  # pyright: ignore[reportArgumentType]  # malformed on purpose
    report = TraceabilityReport(findings=(finding,), not_implemented=())
    assert not report.ok
    with pytest.raises(ValueError, match="frozen"):
        report.findings = ()


def test_the_default_registry_is_consistent_with_the_fixture_model(
    flight_canon: CanonModel,
) -> None:
    """The CI traceability test; it runs against the packaged model once that exists."""
    assert DEFAULT_REGISTRY.check_traceability(flight_canon).ok
