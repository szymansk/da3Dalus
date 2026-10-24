"""Tests for the result types (ARCHITECTURE ch. 5, 8.2, 8.3, 8.4; scenarios Q3, Q15, Q23, Q26, Q31)."""

import pytest
from aero_kernel import schema
from aero_kernel.errors import ErrorCategory, format_world_assignment, parse_world_assignment
from aero_kernel.schema import (
    WARNING_CATALOGUE,
    ComputeResult,
    DefaultUsed,
    Interval,
    KernelError,
    KernelWarning,
    Provenance,
    QuantityResult,
    QuantityStatus,
    ReasonCode,
    WarningSeverity,
    dedupe_warnings,
)
from pydantic import JsonValue, ValidationError


def make_warning(**overrides: object) -> KernelWarning:
    """Build a valid practice warning, with fields overridden."""
    fields: dict[str, object] = {
        "severity": "practice",
        "code": "default_target_used",
        "message": "target taken from the canon default",
        "origin": "approach-speed-margin-target",
    }
    return KernelWarning.model_validate(fields | overrides)


class TestKernelWarning:
    def test_accepts_valid_warning(self) -> None:
        warning = make_warning()
        assert warning.severity is WarningSeverity.PRACTICE
        assert warning.origin == "approach-speed-margin-target"
        assert warning.world is None
        assert warning.detail == {}

    @pytest.mark.parametrize("field", ["code", "message"])
    def test_rejects_empty_text(self, field: str) -> None:
        with pytest.raises(ValidationError):
            make_warning(**{field: ""})

    def test_origin_is_optional_but_not_empty(self) -> None:
        assert make_warning(origin=None).origin is None
        with pytest.raises(ValidationError):
            make_warning(origin="")

    def test_rejects_uncatalogued_code(self) -> None:
        with pytest.raises(ValidationError, match="catalogue"):
            make_warning(code="invented_code")

    def test_rejects_severity_contradicting_the_table(self) -> None:
        with pytest.raises(ValidationError, match="severity"):
            make_warning(severity="defect")

    def test_of_derives_the_severity_from_the_catalogue(self) -> None:
        warning = KernelWarning.of(
            "precondition_violated", "x", origin="q", world="neutral-point=avl", detail={"a": 1}
        )
        assert warning.severity is WarningSeverity.DEFECT
        assert (warning.code, warning.message, warning.origin, warning.world, warning.detail) == (
            "precondition_violated",
            "x",
            "q",
            "neutral-point=avl",
            {"a": 1},
        )

    def test_of_rejects_an_unknown_code(self) -> None:
        with pytest.raises(ValueError, match="catalogue"):
            KernelWarning.of("invented_code", "x")

    def test_severity_is_required_in_the_constructor(self) -> None:
        with pytest.raises(ValidationError, match="severity"):
            KernelWarning.model_validate({"code": "mach_beyond_validity", "message": "x"})

    def test_a_matching_severity_is_accepted(self) -> None:
        warning = KernelWarning(
            severity=WarningSeverity.DEFECT, code="precondition_violated", message="x"
        )
        assert warning.severity is WarningSeverity.DEFECT

    def test_severity_is_set_so_exclude_unset_keeps_it(self) -> None:
        warning = KernelWarning.of("mach_beyond_validity", "x")
        assert warning.model_dump(exclude_unset=True)["severity"] == "defect"

    def test_severity_survives_a_json_round_trip(self) -> None:
        warning = KernelWarning.of("mach_beyond_validity", "x")
        assert KernelWarning.model_validate_json(warning.model_dump_json()) == warning

    def test_the_json_schema_does_not_mark_severity_nullable(self) -> None:
        schema = KernelWarning.model_json_schema()
        assert "severity" in schema["required"]
        assert "anyOf" not in schema["properties"]["severity"]

    def test_catalogue_holds_the_initial_codes(self) -> None:
        assert WARNING_CATALOGUE == {
            "conflicting_mass": WarningSeverity.PRACTICE,
            "default_target_used": WarningSeverity.PRACTICE,
            "deflection_without_flap": WarningSeverity.PRACTICE,
            "geometry_deflection_ignored": WarningSeverity.PRACTICE,
            "reference_wing_at_centreline": WarningSeverity.PRACTICE,
            "hinge_line_averaged": WarningSeverity.PRACTICE,
            "aileron_deflection_beyond_reference": WarningSeverity.PRACTICE,
            "control_surface_fit_range_unknown": WarningSeverity.PRACTICE,
            "fuselage_not_modelled": WarningSeverity.PRACTICE,
            "avl_mesh_not_converged": WarningSeverity.DEFECT,
            "avl_roll_rate_beyond_range": WarningSeverity.DEFECT,
            "avl_refinement_unchecked": WarningSeverity.DEFECT,
            "precondition_unchecked": WarningSeverity.PRACTICE,
            "precondition_violated": WarningSeverity.DEFECT,
            "postcondition_unchecked": WarningSeverity.PRACTICE,
            "postcondition_violated": WarningSeverity.DEFECT,
            "reynolds_outside_band": WarningSeverity.DEFECT,
            "reynolds_bubble_sensitive": WarningSeverity.PRACTICE,
            "mach_above_limit": WarningSeverity.PRACTICE,
            "mach_beyond_validity": WarningSeverity.DEFECT,
        }

    def test_carries_world_and_json_detail(self) -> None:
        warning = make_warning(world="neutral-point=avl", detail={"mass_kg": 2.5})
        assert warning.world == "neutral-point=avl"
        assert warning.detail == {"mass_kg": 2.5}

    def test_rejects_extra_field_and_is_frozen(self) -> None:
        with pytest.raises(ValidationError):
            make_warning(quantity="x")
        with pytest.raises(ValidationError):
            make_warning().code = "x"  # pyright: ignore[reportAttributeAccessIssue]  # frozen: assignment must fail


WORLDS = {"neutral-point=avl": 0.30, "neutral-point=textbook": 0.34}


class TestInterval:
    def test_accepts_min_max_matching_worlds(self) -> None:
        interval = Interval(min=0.30, max=0.34, worlds=WORLDS)
        assert interval.worlds == WORLDS

    def test_rejects_min_not_matching_worlds(self) -> None:
        with pytest.raises(ValidationError, match="min"):
            Interval(min=0.29, max=0.34, worlds=WORLDS)

    def test_rejects_max_not_matching_worlds(self) -> None:
        with pytest.raises(ValidationError, match="max"):
            Interval(min=0.30, max=0.40, worlds=WORLDS)

    def test_rejects_empty_worlds(self) -> None:
        with pytest.raises(ValidationError):
            Interval(min=0.0, max=0.0, worlds={})

    def test_single_world_is_a_zero_width_interval(self) -> None:
        interval = Interval(min=0.3, max=0.3, worlds={"neutral-point=avl": 0.3})
        assert interval.min == interval.max


def make_quantity(**overrides: object) -> QuantityResult:
    """Build a valid ``ok`` quantity with a value, with fields overridden."""
    fields: dict[str, object] = {
        "slug": "stall-speed",
        "unit": "m/s",
        "status": "ok",
        "value": 12.5,
        "tool": "aerobuildup",
        "application": "default",
    }
    return QuantityResult.model_validate(fields | overrides)


class TestQuantityResultOk:
    def test_ok_with_value(self) -> None:
        result = make_quantity()
        assert result.status is QuantityStatus.OK
        assert result.value == 12.5
        assert result.validated is False
        assert result.from_cache is False
        assert result.warnings == ()

    def test_ok_with_interval(self) -> None:
        result = make_quantity(value=None, interval=Interval(min=0.30, max=0.34, worlds=WORLDS))
        assert result.interval is not None

    def test_ok_rejects_value_and_interval_together(self) -> None:
        with pytest.raises(ValidationError, match="exactly one"):
            make_quantity(interval=Interval(min=0.30, max=0.34, worlds=WORLDS))

    def test_ok_rejects_neither_value_nor_interval(self) -> None:
        with pytest.raises(ValidationError, match="exactly one"):
            make_quantity(value=None)


def make_error() -> KernelError:
    """Build a valid ``missing_input`` error."""
    return KernelError(
        code="missing_input",
        category=ErrorCategory.INVALID_INPUT,
        quantity="stall-speed",
        message="aircraft-mass is missing",
        hint="Pass aircraft-mass.",
    )


class TestQuantityResultUnit:
    def test_ok_requires_a_unit(self) -> None:
        with pytest.raises(ValidationError, match="unit"):
            make_quantity(unit=None)

    def test_a_quantity_the_kernel_does_not_know_has_no_unit(self) -> None:
        error = make_error().model_copy(update={"quantity": "nonsense"})
        result = QuantityResult(
            slug="nonsense", unit=None, status=QuantityStatus.ERROR, error=error
        )
        assert result.unit is None

    def test_a_known_non_ok_quantity_keeps_its_unit(self) -> None:
        assert (
            make_quantity(
                status="error", value=None, tool=None, application=None, error=make_error()
            ).unit
            == "m/s"
        )

    def test_empty_unit_is_rejected(self) -> None:
        error = make_error().model_copy(update={"quantity": "x"})
        with pytest.raises(ValidationError, match="String should have at least 1 character"):
            QuantityResult(slug="x", unit="", status=QuantityStatus.ERROR, error=error)


class TestQuantityResultError:
    def test_error_with_error_and_no_value(self) -> None:
        result = make_quantity(status="error", value=None, error=make_error())
        assert result.error is not None
        assert result.error.code == "missing_input"

    def test_error_requires_error(self) -> None:
        with pytest.raises(ValidationError, match="error"):
            make_quantity(status="error", value=None)

    def test_error_rejects_value(self) -> None:
        with pytest.raises(ValidationError, match="value"):
            make_quantity(status="error", error=make_error())

    def test_error_rejects_interval(self) -> None:
        with pytest.raises(ValidationError, match="value"):
            make_quantity(
                status="error",
                value=None,
                interval=Interval(min=0.30, max=0.34, worlds=WORLDS),
                error=make_error(),
            )

    def test_ok_rejects_error(self) -> None:
        with pytest.raises(ValidationError, match="error"):
            make_quantity(error=make_error())


def make_reason(code: str) -> dict[str, str]:
    """Build the raw form of a reason."""
    return {"code": code, "message": "explained"}


class TestQuantityResultReason:
    @pytest.mark.parametrize(
        ("status", "code"),
        [
            ("not_applicable", "condition_not_met"),
            ("not_applicable", "not_given"),
            ("not_applicable", "depends_on_not_applicable"),
            ("skipped", "long_run_not_included"),
            ("skipped", "depends_on_skipped"),
        ],
    )
    def test_accepts_fitting_reason(self, status: str, code: str) -> None:
        result = make_quantity(status=status, value=None, reason=make_reason(code))
        assert result.reason is not None
        assert result.reason.code is ReasonCode(code)

    @pytest.mark.parametrize(
        ("status", "code"),
        [
            ("not_applicable", "long_run_not_included"),
            ("not_applicable", "depends_on_skipped"),
            ("skipped", "condition_not_met"),
            ("skipped", "not_given"),
            ("skipped", "depends_on_not_applicable"),
        ],
    )
    def test_rejects_reason_of_the_other_status(self, status: str, code: str) -> None:
        with pytest.raises(ValidationError, match="reason"):
            make_quantity(status=status, value=None, reason=make_reason(code))

    @pytest.mark.parametrize("status", ["not_applicable", "skipped"])
    def test_non_ok_status_requires_reason(self, status: str) -> None:
        with pytest.raises(ValidationError, match="reason"):
            make_quantity(status=status, value=None)

    def test_ok_rejects_reason(self) -> None:
        with pytest.raises(ValidationError, match="reason"):
            make_quantity(reason=make_reason("not_given"))

    def test_error_rejects_reason(self) -> None:
        with pytest.raises(ValidationError, match="reason"):
            make_quantity(
                status="error", value=None, error=make_error(), reason=make_reason("not_given")
            )

    def test_not_applicable_rejects_error(self) -> None:
        with pytest.raises(ValidationError, match="error"):
            make_quantity(
                status="not_applicable",
                value=None,
                error=make_error(),
                reason=make_reason("not_given"),
            )

    def test_rejects_empty_message(self) -> None:
        with pytest.raises(ValidationError):
            make_quantity(
                status="skipped", value=None, reason={"code": "depends_on_skipped", "message": ""}
            )


class TestQuantityResultInvariants:
    def test_validated_can_not_be_true(self) -> None:
        with pytest.raises(ValidationError):
            make_quantity(validated=True)

    def test_rejects_duplicate_warning_key(self) -> None:
        with pytest.raises(ValidationError, match="duplicate"):
            make_quantity(warnings=[make_warning(), make_warning()])

    def test_same_code_and_origin_in_different_worlds_is_kept(self) -> None:
        result = make_quantity(
            warnings=[make_warning(world="a=x"), make_warning(world="a=y")],
        )
        assert len(result.warnings) == 2

    def test_same_code_with_different_origin_is_kept(self) -> None:
        result = make_quantity(warnings=[make_warning(), make_warning(origin="other")])
        assert len(result.warnings) == 2


def make_provenance(**overrides: object) -> Provenance:
    """Build a valid provenance, with fields overridden."""
    fields: dict[str, object] = {
        "build_digest": "ab" * 32,
        "canon_model_hash": "cd" * 32,
        "tool_versions": {"aerosandbox": "4.2.9"},
        "solver_settings": {},
        "defaults_used": [
            {"slug": "gravity", "value": 9.80665, "unit": "m/s^2", "source": "ISO 80000-3"}
        ],
    }
    return Provenance.model_validate(fields | overrides)


class TestProvenance:
    def test_the_fields_are_exactly_these(self) -> None:
        assert sorted(Provenance.model_fields) == [
            "build_digest",
            "canon_model_hash",
            "defaults_used",
            "solver_settings",
            "tool_versions",
        ]

    @pytest.mark.parametrize("field", ["kernel_version", "accuracy", "canon_source_commit"])
    def test_removed_fields_are_rejected(self, field: str) -> None:
        with pytest.raises(ValidationError, match="extra_forbidden"):
            make_provenance(**{field: "x"})

    def test_accepts_valid_provenance_with_defaults_used(self) -> None:
        provenance = make_provenance()
        assert provenance.defaults_used == (
            DefaultUsed(slug="gravity", value=9.80665, unit="m/s^2", source="ISO 80000-3"),
        )

    @pytest.mark.parametrize("field", ["slug", "unit", "source"])
    def test_default_used_rejects_empty_text(self, field: str) -> None:
        entry = {"slug": "gravity", "value": 9.8, "unit": "m/s^2", "source": "ISO"} | {field: ""}
        with pytest.raises(ValidationError):
            make_provenance(defaults_used=[entry])

    @pytest.mark.parametrize("field", ["build_digest", "canon_model_hash"])
    def test_rejects_empty_identifier(self, field: str) -> None:
        with pytest.raises(ValidationError):
            make_provenance(**{field: ""})

    def test_canon_hash_is_none_without_a_model(self) -> None:
        assert make_provenance(canon_model_hash=None).canon_model_hash is None

    def test_build_digest_stays_required(self) -> None:
        with pytest.raises(ValidationError):
            make_provenance(build_digest=None)


def make_compute(**overrides: object) -> ComputeResult:
    """Build a valid compute result with one ok quantity, with fields overridden."""
    fields: dict[str, object] = {
        "quantities": [make_quantity()],
        "input_errors": [],
        "provenance": make_provenance(),
    }
    return ComputeResult.model_validate(fields | overrides)


class TestComputeResult:
    def test_accepts_quantities(self) -> None:
        assert len(make_compute().quantities) == 1

    def test_accepts_input_errors_with_no_quantities(self) -> None:
        result = make_compute(quantities=[], input_errors=[make_error()])
        assert result.input_errors[0].code == "missing_input"

    def test_rejects_input_errors_with_quantities(self) -> None:
        with pytest.raises(ValidationError, match="input_errors"):
            make_compute(input_errors=[make_error()])

    def test_rejects_non_invalid_input_error(self) -> None:
        timeout = KernelError(
            code="timeout", category=ErrorCategory.TIMEOUT, message="slow", hint="Retry."
        )
        with pytest.raises(ValidationError, match="invalid_input"):
            make_compute(quantities=[], input_errors=[timeout])

    def test_rejects_duplicate_slugs(self) -> None:
        with pytest.raises(ValidationError, match="slug"):
            make_compute(quantities=[make_quantity(), make_quantity()])

    def test_json_round_trip_with_every_status(self) -> None:
        interval = Interval(min=0.30, max=0.34, worlds=WORLDS)
        quantities = [
            make_quantity(slug="a", warnings=[make_warning(world="w=x", detail={"k": [1, "x"]})]),
            make_quantity(slug="b", value=None, interval=interval, tool="avl", application="x"),
            make_quantity(
                slug="c", status="not_applicable", value=None, reason=make_reason("not_given")
            ),
            make_quantity(
                slug="d", status="skipped", value=None, reason=make_reason("long_run_not_included")
            ),
            make_quantity(slug="stall-speed", status="error", value=None, error=make_error()),
        ]
        result = make_compute(quantities=quantities)
        restored = ComputeResult.model_validate_json(result.model_dump_json())
        assert restored == result
        assert {q.status for q in restored.quantities} == set(QuantityStatus)


class TestDedupeWarnings:
    def test_first_occurrence_wins_and_order_is_kept(self) -> None:
        first = make_warning()
        other = make_warning(origin="other")
        again = make_warning()
        result = dedupe_warnings([first, other, again])
        assert result == (first, other)
        assert result[0] is first

    def test_world_distinguishes_warnings(self) -> None:
        a, b = make_warning(world="w=x"), make_warning(world="w=y")
        assert dedupe_warnings([a, b]) == (a, b)

    def test_result_passes_the_quantity_invariant(self) -> None:
        deduped = dedupe_warnings([make_warning(), make_warning()])
        assert len(make_quantity(warnings=deduped).warnings) == 1

    def test_the_key_is_the_full_content(self) -> None:
        """Two devices with the same code, origin and world are two warnings (ch. 8.2)."""
        fields = {"code": "geometry_deflection_ignored", "origin": "airplane"}
        left = make_warning(**fields, detail={"device": "left", "deflection_deg": 5.0})
        right = make_warning(**fields, detail={"device": "right", "deflection_deg": 5.0})
        other_text = make_warning(**fields, message="other text", detail=left.detail)
        assert dedupe_warnings([left, right, other_text]) == (left, right, other_text)
        assert len(make_quantity(warnings=[left, right, other_text]).warnings) == 3

    def test_detail_key_order_does_not_matter(self) -> None:
        a = make_warning(detail={"x": 1.0, "y": 2.0})
        b = make_warning(detail={"y": 2.0, "x": 1.0})
        assert dedupe_warnings([a, b]) == (a,)
        with pytest.raises(ValidationError, match="duplicate"):
            make_quantity(warnings=[a, b])


class TestErrorQuantity:
    def test_rejects_error_quantity_differing_from_slug(self) -> None:
        with pytest.raises(ValidationError, match="slug"):
            make_quantity(slug="other", status="error", value=None, error=make_error())

    def test_accepts_error_without_quantity(self) -> None:
        error = KernelError(
            code="missing_input", category=ErrorCategory.INVALID_INPUT, message="m", hint="h"
        )
        assert make_quantity(status="error", value=None, error=error).error == error


class TestWorldAssignment:
    def test_format_sorts_by_slug(self) -> None:
        text = format_world_assignment({"roll-rate": "aerobuildup", "neutral-point": "avl"})
        assert text == "neutral-point=avl,roll-rate=aerobuildup"

    def test_parse_inverts_format(self) -> None:
        text = "neutral-point=textbook_pappas,roll-rate=aerobuildup"
        assert format_world_assignment(parse_world_assignment(text)) == text

    def test_single_pair(self) -> None:
        assert parse_world_assignment("neutral-point=avl") == {"neutral-point": "avl"}

    @pytest.mark.parametrize(
        ("text", "message"),
        [
            ("", "without '='"),
            ("avl", "without '='"),
            ("neutral-point=avl,", "without '='"),
            ("neutral-point=", "malformed pair"),
            ("=avl", "malformed pair"),
            ("neutral-point=avl, roll-rate=aerobuildup", "malformed pair"),
            ("Neutral-Point=avl", "malformed pair"),
            ("neutral_point=avl", "malformed pair"),
            ("neutral-point=Avl", "malformed pair"),
            ("neutral-point=a-b", "malformed pair"),
            ("a=b=c", "malformed pair"),
            ("-a=x", "malformed pair"),
            ("a-=x", "malformed pair"),
            ("a--b=x", "malformed pair"),
            ("a=_avl", "malformed pair"),
            ("a=avl_", "malformed pair"),
            ("a=a__b", "malformed pair"),
            ("roll-rate=aerobuildup,neutral-point=avl", "not sorted"),
            ("neutral-point=avl,neutral-point=avl", "repeats formula"),
        ],
    )
    def test_parse_rejects_malformed(self, text: str, message: str) -> None:
        with pytest.raises(ValueError, match=message):
            parse_world_assignment(text)

    def test_interval_rejects_malformed_second_world_key(self) -> None:
        with pytest.raises(ValidationError, match="malformed pair"):
            Interval(min=1.0, max=2.0, worlds={"a=x": 1.0, "a=Bad": 2.0})

    @pytest.mark.parametrize(("lo", "hi"), [(0.31, 0.34), (0.30, 0.33)])
    def test_interval_rejects_narrowed_bounds(self, lo: float, hi: float) -> None:
        with pytest.raises(ValidationError, match="smallest and largest"):
            Interval(min=lo, max=hi, worlds=WORLDS)

    @pytest.mark.parametrize(("lo", "hi"), [(0.30 - 1e-9, 0.34), (0.30, 0.34 + 1e-9)])
    def test_interval_bounds_must_match_exactly(self, lo: float, hi: float) -> None:
        with pytest.raises(ValidationError, match="smallest and largest"):
            Interval(min=lo, max=hi, worlds=WORLDS)

    def test_format_rejects_malformed_pair(self) -> None:
        with pytest.raises(ValueError, match="world"):
            format_world_assignment({"Bad": "avl"})

    def test_format_rejects_empty(self) -> None:
        with pytest.raises(ValueError, match="world"):
            format_world_assignment({})

    def test_interval_rejects_malformed_world_key(self) -> None:
        with pytest.raises(ValidationError, match="world"):
            Interval(min=0.3, max=0.3, worlds={"bad key": 0.3})

    def test_warning_rejects_malformed_world(self) -> None:
        with pytest.raises(ValidationError, match="world"):
            make_warning(world="avl")


NON_FINITE = [float("nan"), float("inf"), float("-inf")]


class TestFiniteFloats:
    @pytest.mark.parametrize("bad", NON_FINITE)
    def test_value_rejects_non_finite(self, bad: float) -> None:
        with pytest.raises(ValidationError):
            make_quantity(value=bad)

    @pytest.mark.parametrize("bad", NON_FINITE)
    @pytest.mark.parametrize("field", ["min", "max"])
    def test_interval_bound_rejects_non_finite(self, field: str, bad: float) -> None:
        base: dict[str, object] = {"min": 0.30, "max": 0.34, "worlds": WORLDS}
        fields = base | {field: bad}
        with pytest.raises(ValidationError):
            Interval.model_validate(fields)

    @pytest.mark.parametrize("bad", NON_FINITE)
    def test_interval_world_value_rejects_non_finite(self, bad: float) -> None:
        with pytest.raises(ValidationError):
            Interval.model_validate({"min": 0.3, "max": 0.3, "worlds": {"a=x": bad}})

    @pytest.mark.parametrize("bad", NON_FINITE)
    def test_default_used_rejects_non_finite(self, bad: float) -> None:
        with pytest.raises(ValidationError):
            DefaultUsed(slug="gravity", value=bad, unit="m/s^2", source="ISO")


def test_all_pins_the_public_names() -> None:
    assert sorted(schema.__all__) == sorted(
        [
            "AircraftInput",
            "AirplaneGeometry",
            "ComputeRequest",
            "ComputeResult",
            "DefaultUsed",
            "Interval",
            "KernelError",
            "KernelWarning",
            "Polar",
            "Provenance",
            "QuantityResult",
            "QuantityStatus",
            "Reason",
            "ReasonCode",
            "WARNING_CATALOGUE",
            "WarningSeverity",
            "dedupe_warnings",
        ]
    )
    for name in schema.__all__:
        assert hasattr(schema, name)


class TestMinorInvariants:
    def test_interval_worlds_must_assign_the_same_formulas(self) -> None:
        with pytest.raises(ValidationError, match="formulas"):
            Interval(min=1.0, max=2.0, worlds={"a=x": 1.0, "b=y": 2.0})

    def test_interval_accepts_multi_formula_product(self) -> None:
        worlds = {"a=x,b=y": 1.0, "a=x,b=z": 2.0, "a=w,b=y": 3.0}
        assert Interval(min=1.0, max=3.0, worlds=worlds).max == 3.0

    @pytest.mark.parametrize("status", ["not_applicable", "skipped", "error"])
    def test_from_cache_requires_ok(self, status: str) -> None:
        extra: dict[str, object] = {
            "not_applicable": {"reason": make_reason("not_given")},
            "skipped": {"reason": make_reason("depends_on_skipped")},
            "error": {"error": make_error()},
        }[status]  # pyright: ignore[reportAssignmentType]  # literal mapping of raw fields
        with pytest.raises(ValidationError, match="from_cache"):
            make_quantity(status=status, value=None, from_cache=True, **extra)

    def test_from_cache_ok_is_accepted(self) -> None:
        assert make_quantity(from_cache=True).from_cache is True

    @pytest.mark.parametrize("field", ["slug", "unit"])
    def test_quantity_rejects_empty_slug_and_unit(self, field: str) -> None:
        with pytest.raises(ValidationError):
            make_quantity(**{field: ""})


class TestSurvivingMutants:
    def test_dedupe_keeps_different_codes_with_same_origin_and_world(self) -> None:
        a = make_warning()
        b = make_warning(code="conflicting_mass")
        assert dedupe_warnings([a, b]) == (a, b)
        assert len(make_quantity(warnings=[a, b]).warnings) == 2

    @pytest.mark.parametrize("status", ["not_applicable", "skipped"])
    def test_non_ok_status_rejects_value_and_interval(self, status: str) -> None:
        reason = make_reason("not_given" if status == "not_applicable" else "depends_on_skipped")
        interval = Interval(min=0.30, max=0.34, worlds=WORLDS)
        with pytest.raises(ValidationError, match="value or interval"):
            make_quantity(status=status, reason=reason)
        with pytest.raises(ValidationError, match="value or interval"):
            make_quantity(status=status, value=None, interval=interval, reason=reason)

    def test_skipped_rejects_error(self) -> None:
        with pytest.raises(ValidationError, match="must not carry an error"):
            make_quantity(
                status="skipped",
                value=None,
                error=make_error(),
                reason=make_reason("depends_on_skipped"),
            )

    @pytest.mark.parametrize("bad", [{"a": 1}, [1.0], "abc"])
    def test_value_rejects_non_float(self, bad: object) -> None:
        with pytest.raises(ValidationError):
            make_quantity(value=bad)

    def test_mixed_input_errors_are_rejected(self) -> None:
        timeout = KernelError(
            code="timeout", category=ErrorCategory.TIMEOUT, message="slow", hint="Retry."
        )
        with pytest.raises(ValidationError, match="invalid_input"):
            make_compute(quantities=[], input_errors=[make_error(), timeout])


class TestRulings:
    @pytest.mark.parametrize("bad", [True, False, "12.5"])
    def test_value_rejects_bool_and_numeric_string(self, bad: object) -> None:
        with pytest.raises(ValidationError):
            make_quantity(value=bad)

    def test_value_accepts_int(self) -> None:
        assert make_quantity(value=3).value == 3

    @pytest.mark.parametrize("bad", [True, "1.0"])
    def test_interval_numbers_are_strict(self, bad: object) -> None:
        # 1.0 is what ``bad`` would coerce to, so only strictness can reject it.
        with pytest.raises(ValidationError):
            Interval.model_validate({"min": bad, "max": 1.0, "worlds": {"a=x": 1.0}})
        with pytest.raises(ValidationError):
            Interval.model_validate({"min": 1.0, "max": bad, "worlds": {"a=x": 1.0}})
        with pytest.raises(ValidationError):
            Interval.model_validate({"min": 1.0, "max": 1.0, "worlds": {"a=x": bad}})

    def test_interval_rejects_nan_in_a_later_world(self) -> None:
        # min() and max() skip a NaN that is not first, so only the field rule rejects it.
        with pytest.raises(ValidationError):
            Interval.model_validate(
                {"min": 1.0, "max": 1.0, "worlds": {"a=y": 1.0, "a=z": float("nan")}}
            )

    @pytest.mark.parametrize("bad", [True, "9.8"])
    def test_default_used_value_is_strict(self, bad: object) -> None:
        with pytest.raises(ValidationError):
            DefaultUsed.model_validate({"slug": "g", "value": bad, "unit": "u", "source": "s"})

    @pytest.mark.parametrize("empty", [None, ""])
    @pytest.mark.parametrize("field", ["tool", "application"])
    def test_ok_requires_tool_and_application(self, field: str, empty: str | None) -> None:
        with pytest.raises(ValidationError, match=field):
            make_quantity(**{field: empty})

    def test_non_ok_needs_no_tool(self) -> None:
        result = make_quantity(
            status="skipped",
            value=None,
            tool=None,
            application=None,
            reason=make_reason("depends_on_skipped"),
        )
        assert result.tool is None

    def test_tool_versions_must_be_non_empty(self) -> None:
        with pytest.raises(ValidationError):
            make_provenance(tool_versions={"avl": ""})

    def test_tool_versions_may_be_empty(self) -> None:
        assert make_provenance(tool_versions={}).tool_versions == {}

    @pytest.mark.parametrize("text", ["a1-b2=x1_y2", "neutral-point=avl2"])
    def test_digits_are_allowed_after_the_first_letter(self, text: str) -> None:
        assert parse_world_assignment(text)

    @pytest.mark.parametrize("text", ["1a=x", "a=1x", "1=x", "a=_x"])
    def test_first_character_must_be_a_letter(self, text: str) -> None:
        with pytest.raises(ValueError, match="malformed pair"):
            parse_world_assignment(text)


def test_tool_versions_keys_must_be_non_empty() -> None:
    with pytest.raises(ValidationError):
        make_provenance(tool_versions={"": "1.0"})


@pytest.mark.parametrize("bad", NON_FINITE)
@pytest.mark.parametrize("shape", ["top", "dict", "list"])
class TestNonFiniteJsonFields:
    @staticmethod
    def nested(bad: float, shape: str) -> dict[str, JsonValue]:
        shapes: dict[str, dict[str, JsonValue]] = {
            "top": {"x": bad},
            "dict": {"outer": {"x": bad}},
            "list": {"outer": [1.0, {"x": [bad]}]},
        }
        return shapes[shape]

    def test_warning_detail_rejects(self, bad: float, shape: str) -> None:
        with pytest.raises(ValidationError, match="finite"):
            make_warning(detail=self.nested(bad, shape))

    def test_solver_settings_reject(self, bad: float, shape: str) -> None:
        with pytest.raises(ValidationError, match="finite"):
            make_provenance(solver_settings=self.nested(bad, shape))


def test_finite_json_passes_in_warning_detail_and_solver_settings() -> None:
    value = {"f": 1.5, "i": 2, "b": True, "n": None, "s": "t", "l": [0.0, {"k": -3.0}]}
    assert make_warning(detail=value).detail == value
    assert make_provenance(solver_settings=value).solver_settings == value
