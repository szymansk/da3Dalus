"""Cache ``Entry``: lossless, serialised, finite (ARCHITECTURE ch. 8.4)."""

import math
import struct

import pytest
from aero_kernel.cache import Entry
from aero_kernel.schema import KernelWarning, WarningSeverity
from pydantic import JsonValue, ValidationError


def _bits(value: float) -> bytes:
    return struct.pack("<d", value)


def _warning() -> KernelWarning:
    return KernelWarning(
        severity=WarningSeverity.DEFECT,
        code="precondition_violated",
        message="check failed",
        origin="stall-speed",
        world="neutral-point=avl",
        detail={"limit": 0.5},
    )


def test_entry_has_exactly_outputs_warnings_and_the_measured_time() -> None:
    assert set(Entry.model_fields) == {"outputs", "warnings", "own_s"}


def test_the_measured_time_survives_the_round_trip() -> None:
    entry = Entry(outputs={"v": 1.0}, warnings=(), own_s=12.5)
    back = Entry.from_json(entry.to_json())
    assert back.own_s is not None
    assert math.isclose(back.own_s, 12.5)


def test_an_entry_without_a_measured_time_says_so() -> None:
    assert Entry(outputs={"v": 1.0}, warnings=()).own_s is None


@pytest.mark.parametrize("bad", [-1.0, math.nan, math.inf])
def test_a_negative_or_non_finite_time_is_rejected(bad: float) -> None:
    with pytest.raises(ValidationError):
        Entry(outputs={"v": 1.0}, warnings=(), own_s=bad)


def test_extra_fields_are_rejected() -> None:
    with pytest.raises(ValidationError):
        Entry.model_validate({"outputs": {}, "warnings": [], "status": "error"})


def test_json_round_trip_rebuilds_an_equal_entry() -> None:
    entry = Entry(outputs={"v": 12.5, "curve": [[1.0, 2.0]], "name": "x"}, warnings=(_warning(),))
    assert Entry.from_json(entry.to_json()) == entry


def test_json_round_trip_is_lossless_for_floats() -> None:
    values = [-0.0, math.nextafter(1.0, 2.0), 0.1, 1e-300]
    entry = Entry(outputs={"v": list[JsonValue](values)}, warnings=())
    back = Entry.from_json(entry.to_json()).outputs["v"]
    assert isinstance(back, list)
    assert [_bits(float(v)) for v in back if isinstance(v, float)] == [_bits(v) for v in values]


@pytest.mark.parametrize("bad", [math.nan, math.inf, -math.inf])
def test_non_finite_output_is_rejected(bad: float) -> None:
    with pytest.raises(ValueError, match="must be finite"):
        Entry(outputs={"v": list[JsonValue]([bad])}, warnings=())
