"""Regime warnings of the solver adapter base (ch. 8.2, ADR 0028)."""

import math

import pytest
from aero_kernel.schema import KernelWarning, WarningSeverity
from aero_kernel.solvers.base import regime

SPEED_OF_SOUND = 340.0
NU = 1.5e-5


def detail_number(warning: KernelWarning, key: str) -> float:
    value = warning.detail[key]
    assert isinstance(value, float)
    return value


def codes(warnings: list[KernelWarning]) -> list[str]:
    return [warning.code for warning in warnings]


def test_inside_the_band_gives_no_warning() -> None:
    # Re = 20 * 0.3 / 1.5e-5 = 4e5, M = 20 / 340
    assert regime([0.3], 20.0, SPEED_OF_SOUND, NU) == []


def test_below_the_band_is_a_defect() -> None:
    # Re = 5 * 0.1 / 1.5e-5 = 33333 is inside; 2 * 0.1 / 1.5e-5 = 13333 is outside
    (warning,) = regime([0.1], 2.0, SPEED_OF_SOUND, NU)
    assert warning.code == "reynolds_outside_band"
    assert warning.severity is WarningSeverity.DEFECT
    assert math.isclose(detail_number(warning, "re_min"), 2.0 * 0.1 / NU)


def test_above_the_band_is_a_defect() -> None:
    # Re = 30 * 0.6 / 1.5e-5 = 1.2e6
    assert codes(regime([0.6], 30.0, SPEED_OF_SOUND, NU)) == ["reynolds_outside_band"]


def test_bubble_sensitive_between_the_band_start_and_70000() -> None:
    # Re = 6 * 0.1 / 1.5e-5 = 40000
    (warning,) = regime([0.1], 6.0, SPEED_OF_SOUND, NU)
    assert warning.code == "reynolds_bubble_sensitive"
    assert warning.severity is WarningSeverity.PRACTICE


@pytest.mark.parametrize(
    ("re_value", "expected"),
    [
        (29_999.0, ["reynolds_outside_band"]),
        (30_000.0, ["reynolds_bubble_sensitive"]),
        (69_999.0, ["reynolds_bubble_sensitive"]),
        (70_000.0, []),
        (1_000_000.0, []),
        (1_000_001.0, ["reynolds_outside_band"]),
    ],
)
def test_band_edges(re_value: float, expected: list[str]) -> None:
    chord = 1.0
    assert codes(regime([chord], re_value * NU / chord, 1e9, NU)) == expected


def test_several_chords_give_one_warning_per_code() -> None:
    # root 0.3 m (Re 4e5, fine), tip 0.06 m (Re 8e4 at 20 m/s is fine); tip 0.02 m: Re 26667
    warnings = regime([0.3, 0.1, 0.02], 20.0, SPEED_OF_SOUND, NU)
    assert codes(warnings) == ["reynolds_outside_band"]
    warning = warnings[0]
    assert math.isclose(detail_number(warning, "re_min"), 20.0 * 0.02 / NU)
    assert math.isclose(detail_number(warning, "re_max"), 20.0 * 0.3 / NU)


def test_straddling_chords_warn_outside_and_bubble() -> None:
    # Re of 0.02 m: 26667 (outside); of 0.04 m: 53333 (bubble)
    assert codes(regime([0.02, 0.04], 20.0, SPEED_OF_SOUND, NU)) == [
        "reynolds_outside_band",
        "reynolds_bubble_sensitive",
    ]


@pytest.mark.parametrize(
    ("mach", "expected"),
    [
        (0.3, []),
        (0.31, ["mach_above_limit"]),
        (0.6, ["mach_above_limit"]),
        (0.61, ["mach_beyond_validity"]),
    ],
)
def test_mach_bands(mach: float, expected: list[str]) -> None:
    # Re kept in band: chord 1 m, nu chosen so that Re = 5e5
    v = mach * SPEED_OF_SOUND
    assert codes(regime([1.0], v, SPEED_OF_SOUND, v / 5e5)) == expected


def test_mach_detail_and_severity() -> None:
    v = 0.7 * SPEED_OF_SOUND
    (warning,) = regime([1.0], v, SPEED_OF_SOUND, v / 5e5)
    assert warning.severity is WarningSeverity.DEFECT
    assert math.isclose(detail_number(warning, "mach"), 0.7)


@pytest.mark.parametrize(
    "kwargs",
    [
        {"chords_m": []},
        {"chords_m": [0.0]},
        {"v_ms": -1.0},
        {"speed_of_sound_ms": 0.0},
        {"kinematic_viscosity_m2s": 0.0},
    ],
)
def test_rejects_non_physical_arguments(kwargs: dict[str, object]) -> None:
    arguments: dict[str, object] = {
        "chords_m": [0.3],
        "v_ms": 20.0,
        "speed_of_sound_ms": SPEED_OF_SOUND,
        "kinematic_viscosity_m2s": NU,
    }
    arguments.update(kwargs)
    with pytest.raises(ValueError, match="must be"):
        regime(**arguments)  # pyright: ignore[reportArgumentType]  # parametrised bad values
