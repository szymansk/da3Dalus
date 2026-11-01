"""Regime warnings of the solver adapter base, per surface and per device (ch. 8.2, ADR 0028, #1342)."""

import math

import pytest
from aero_kernel.geometry import Wing
from aero_kernel.schema import KernelWarning, WarningSeverity
from aero_kernel.solvers.regime import SurfaceSections, regime_by_surface
from aero_kernel.tests.planform_stand_in import canon_bands
from pydantic import ValidationError

SPEED_OF_SOUND = 340.0
NU = 1.5e-5
BUBBLE = "reynolds_bubble_sensitive"
OUTSIDE = "reynolds_outside_band"
AT_DEVICE = "reynolds_outside_band_at_device"


def detail_number(warning: KernelWarning, key: str) -> float:
    value = warning.detail[key]
    assert isinstance(value, (int, float))
    return float(value)


def codes(warnings: list[KernelWarning]) -> list[str]:
    return [warning.code for warning in warnings]


def surface(
    chords: tuple[float, ...],
    spans: tuple[float, ...] | None = None,
    c_mac: float | None = None,
    devices: tuple[str | None, ...] | None = None,
) -> SurfaceSections:
    """A surface of the given chords, 0.1 m apart unless given; the MAC is the root chord unless given."""
    count = len(chords) - 1
    return SurfaceSections(
        chords_m=chords,
        spans_m=spans or (0.1,) * count,
        c_mac_m=c_mac or chords[0],
        devices=devices or (None,) * count,
    )


def at(re_mac: float, *chords_re: float) -> SurfaceSections:
    """A surface whose MAC and station chords give these Reynolds numbers at V = nu (chord = Re)."""
    return surface(tuple(chords_re), c_mac=re_mac)


def regime(
    sections: SurfaceSections, v: float = 20.0, a: float = SPEED_OF_SOUND
) -> list[KernelWarning]:
    return regime_by_surface({"Main": sections}, v, a, NU, canon_bands())


def test_inside_the_band_gives_no_warning() -> None:
    assert regime(at(4e5, 4e5, 3e5), v=NU) == []


@pytest.mark.parametrize(
    ("re_mac", "expected", "severity"),
    [
        (20_000.0, OUTSIDE, WarningSeverity.WARNING),
        (29_999.0, OUTSIDE, WarningSeverity.WARNING),
        (30_000.0, BUBBLE, WarningSeverity.NOTICE),
        (69_999.0, BUBBLE, WarningSeverity.NOTICE),
        (70_000.0, None, None),
        (1_000_000.0, None, None),
        (1_000_001.0, "reynolds_above_band", WarningSeverity.NOTICE),
    ],
)
def test_the_surface_is_judged_by_the_reynolds_number_at_its_mac(
    re_mac: float, expected: str | None, severity: WarningSeverity | None
) -> None:
    """The stations stay inside the band (2e5), so only the MAC decides."""
    warnings = regime(at(re_mac, 2e5, 2e5), v=NU)
    assert codes(warnings) == ([] if expected is None else [expected])
    if severity is not None:
        assert warnings[0].severity is severity
        assert math.isclose(detail_number(warnings[0], "re_mac"), re_mac)
        assert warnings[0].detail["wing"] == "Main"


def test_a_tip_station_below_the_band_does_not_make_the_surface_warn() -> None:
    """A rounded tip: 10 mm at the last station (Re 13 333 at 20 m/s), MAC Re 4e5: no warning; the
    lowest station shows only where a surface does warn."""
    assert regime(surface((0.3, 0.3, 0.01), c_mac=0.3)) == []


def test_the_detail_says_where_and_how_much() -> None:
    """Chords 0.03 m and 0.01 m over 0.1 m at 10 m/s: Re 20 000 and 6 667, MAC 0.0217 m (Re 14 444).
    Everything lies below 3e4: the whole area and span share; the lowest station is x_secs[1]."""
    sections = surface((0.03, 0.01), c_mac=0.0216667)
    (warning,) = regime(sections, v=10.0)
    assert warning.code == OUTSIDE
    assert warning.detail["re_min_station"] == 1
    assert math.isclose(detail_number(warning, "re_min"), 10.0 * 0.01 / NU)
    assert math.isclose(detail_number(warning, "area_share_below_band"), 1.0)
    assert math.isclose(detail_number(warning, "area_share_below_bubble"), 1.0)
    assert math.isclose(detail_number(warning, "span_share_below_band"), 1.0)
    assert math.isclose(detail_number(warning, "c_mac_m"), 0.0216667)
    assert "x_secs[1]" in warning.message


def test_the_shares_follow_the_linear_chord_of_a_section() -> None:
    """At 1 m/s the band edge 3e4 is chord 0.45 m and the bubble edge 7e4 is 1.05 m. A section from
    1.2 m to 0.3 m over 1 m: chord below 0.45 m on the outer 1/6 of its span (area 1/6 (0.3 + 0.45)/2
    of 0.75), below 1.05 m on the outer 5/6 (area 5/6 (0.3 + 1.05)/2)."""
    (warning,) = regime_by_surface(
        {"Main": surface((1.2, 0.3), spans=(1.0,), c_mac=0.5)},
        1.0,
        SPEED_OF_SOUND,
        NU,
        canon_bands(),
    )
    assert warning.code == BUBBLE  # MAC Re 33 333
    assert math.isclose(detail_number(warning, "span_share_below_band"), 1.0 / 6.0)
    assert math.isclose(detail_number(warning, "area_share_below_band"), (0.75 / 12.0) / 0.75)
    assert math.isclose(
        detail_number(warning, "area_share_below_bubble"), (5.0 / 6.0 * 1.35 / 2.0) / 0.75
    )


def test_the_area_weighs_the_sections() -> None:
    """At 20 m/s the band edge is chord 0.0225 m. A 0.1 m section of chord 0.02 m lies wholly below
    it; the next one, 0.4 m from 0.02 m to 0.2 m, only on its first (0.0225 - 0.02) / 0.18 of span."""
    (warning,) = regime(surface((0.02, 0.02, 0.2), spans=(0.1, 0.4), c_mac=0.02))
    assert warning.code == OUTSIDE
    fraction = 0.0025 / 0.18
    below = 0.1 * 0.02 + 0.4 * fraction * (0.02 + 0.0225) / 2.0
    total = 0.1 * 0.02 + 0.4 * 0.11
    assert math.isclose(detail_number(warning, "area_share_below_band"), below / total)
    assert math.isclose(
        detail_number(warning, "span_share_below_band"), (0.1 + 0.4 * fraction) / 0.5
    )


def test_a_device_with_a_station_below_the_band_warns_and_names_itself() -> None:
    """The surface is fine at its MAC (Re 4e5); the elevator on the outer section reaches a station
    of chord 0.02 m (Re 26 667 at 20 m/s): a warning at the device, with its span share."""
    sections = surface((0.3, 0.3, 0.02), c_mac=0.3, devices=(None, "elevator"))
    (warning,) = regime(sections)
    assert (warning.code, warning.severity) == (AT_DEVICE, WarningSeverity.WARNING)
    assert warning.detail["device"] == "elevator"
    assert warning.detail["device_re_min_station"] == 2
    assert math.isclose(detail_number(warning, "device_re_min"), 20.0 * 0.02 / NU)
    # chord below 0.0225 m (Re 3e4) on (0.0225 - 0.02) / 0.28 of the device's section
    assert math.isclose(
        detail_number(warning, "device_span_share_below_band"), 0.0025 / 0.28, rel_tol=1e-9
    )
    assert math.isclose(detail_number(warning, "re_mac"), 20.0 * 0.3 / NU)
    assert "'elevator'" in warning.message


def test_a_device_inside_the_band_and_a_station_outside_it_do_not_warn() -> None:
    sections = surface((0.3, 0.3, 0.02), c_mac=0.3, devices=("aileron", None))
    assert regime(sections) == []


def test_the_device_and_the_surface_warn_independently() -> None:
    sections = surface((0.02, 0.02, 0.02), c_mac=0.02, devices=("rudder", "rudder"))
    assert codes(regime(sections)) == [OUTSIDE, AT_DEVICE]


def test_one_warning_per_surface_and_per_device() -> None:
    """Two surfaces and two devices below the band; Mach is raised once (120 m/s, M 0.35)."""
    tail = surface((0.002, 0.002, 0.002), c_mac=0.002, devices=("left", "right"))
    warnings = regime_by_surface(
        {"Main": surface((0.05, 0.05)), "Tail": tail}, 120.0, 340.0, NU, canon_bands()
    )
    assert [(w.code, w.detail.get("wing"), w.detail.get("device")) for w in warnings] == [
        (OUTSIDE, "Tail", None),
        (AT_DEVICE, "Tail", "left"),
        (AT_DEVICE, "Tail", "right"),
        ("mach_above_limit", None, None),
    ]
    assert set(warnings[-1].detail) == {"mach"}


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
    """Re kept inside the band by the viscosity: chord 1 m, Re 5e5."""
    v = mach * SPEED_OF_SOUND
    found = regime_by_surface(
        {"Main": surface((1.0, 1.0))}, v, SPEED_OF_SOUND, v / 5e5, canon_bands()
    )
    assert codes(found) == expected


def test_beyond_mach_0_6_is_an_error() -> None:
    v = 0.7 * SPEED_OF_SOUND
    (warning,) = regime_by_surface(
        {"Main": surface((1.0, 1.0))}, v, SPEED_OF_SOUND, v / 5e5, canon_bands()
    )
    assert warning.severity is WarningSeverity.ERROR
    assert math.isclose(detail_number(warning, "mach"), 0.7)


def test_mach_uses_the_given_speed_of_sound() -> None:
    """100 m/s is Mach 0.29 at 340 m/s but Mach 0.33 at 300 m/s."""
    sections = {"Main": surface((1.0, 1.0))}
    assert regime_by_surface(sections, 100.0, 340.0, 100.0 / 5e5, canon_bands()) == []
    (warning,) = regime_by_surface(sections, 100.0, 300.0, 100.0 / 5e5, canon_bands())
    assert warning.code == "mach_above_limit"


def test_zero_airspeed_puts_everything_below_the_band() -> None:
    (warning,) = regime(surface((0.3, 0.3)), v=0.0)
    assert warning.code == OUTSIDE
    assert math.isclose(detail_number(warning, "area_share_below_band"), 1.0)


@pytest.mark.parametrize(
    "kwargs",
    [
        {"v_ms": -1.0},
        {"speed_of_sound_ms": 0.0},
        {"kinematic_viscosity_m2s": 0.0},
        *(
            {name: value}
            for name in ("v_ms", "speed_of_sound_ms", "kinematic_viscosity_m2s")
            for value in (math.nan, math.inf, -math.inf)
        ),
    ],
)
def test_rejects_non_physical_flow(kwargs: dict[str, float]) -> None:
    arguments: dict[str, float] = {
        "v_ms": 20.0,
        "speed_of_sound_ms": SPEED_OF_SOUND,
        "kinematic_viscosity_m2s": NU,
    }
    arguments.update(kwargs)
    with pytest.raises(ValueError, match="must be"):
        regime_by_surface({"Main": surface((0.3, 0.3))}, bands=canon_bands(), **arguments)


@pytest.mark.parametrize(
    "fields",
    [
        {"chords_m": (0.3,), "spans_m": (), "devices": ()},
        {"chords_m": (0.3, 0.0)},
        {"chords_m": (0.3, math.nan)},
        {"spans_m": (-0.1,)},
        {"spans_m": (0.0,)},
        {"spans_m": (0.1, 0.1)},
        {"devices": (None, None)},
        {"c_mac_m": 0.0},
        {"c_mac_m": math.inf},
    ],
)
def test_the_sections_must_describe_a_surface(fields: dict[str, object]) -> None:
    valid: dict[str, object] = {
        "chords_m": (0.3, 0.2),
        "spans_m": (0.1,),
        "c_mac_m": 0.25,
        "devices": (None,),
    }
    with pytest.raises(ValidationError):
        SurfaceSections.model_validate(valid | fields)


def wing(points: list[tuple[float, float, float]], devices: list[str | None]) -> Wing:
    """A wing of these leading edges, chord 0.1 m, a named elevator where given."""
    sections: list[dict[str, object]] = []
    for point, device in zip(points, [*devices, None], strict=True):
        section: dict[str, object] = {
            "xyz_le": list(point),
            "chord": 0.1,
            "twist": 0.0,
            "airfoil": "naca0012",
        }
        if device is not None:
            section["trailing_edge_device"] = {"name": device, "role": "elevator"}
        sections.append(section)
    return Wing.model_validate({"name": "W", "x_secs": sections})


def test_the_sections_of_a_wing_span_in_y() -> None:
    sections = SurfaceSections.of(wing([(0.0, 0.0, 0.0), (0.1, 0.3, 0.0)], ["elevator"]), 0.1)
    assert sections.chords_m == (0.1, 0.1)
    assert len(sections.spans_m) == 1
    assert math.isclose(sections.spans_m[0], math.hypot(0.3, 0.0))
    assert sections.devices == ("elevator",)
    assert sections.c_mac_m == 0.1


def test_the_sections_of_a_fin_span_in_z_and_a_dihedral_panel_in_both() -> None:
    fin = SurfaceSections.of(wing([(0.0, 0.0, 0.0), (0.1, 0.0, 0.2)], [None]), 0.1)
    assert math.isclose(fin.spans_m[0], 0.2)
    panel = SurfaceSections.of(wing([(0.0, 0.0, 0.0), (0.0, 0.3, 0.4)], [None]), 0.1)
    assert math.isclose(panel.spans_m[0], 0.5)


def test_an_unnamed_device_is_named_by_the_rib_it_starts_on() -> None:
    document = Wing.model_validate(
        {
            "name": "W",
            "x_secs": [
                {"xyz_le": [0.0, y, 0.0], "chord": 0.1, "twist": 0.0, "airfoil": "naca0012"}
                | ({"trailing_edge_device": {"role": "aileron"}} if y == 0.2 else {})
                for y in (0.0, 0.2, 0.4)
            ],
        }
    )
    assert SurfaceSections.of(document, 0.1).devices == (None, "device 1")


def test_the_bands_are_the_canon_rule_and_an_override_moves_them() -> None:
    """ADR 0028's edges come from the rule reynolds-mach-regime, never from a literal in the code."""
    from aero_kernel.build import shipped_build
    from aero_kernel.rules import Rules
    from aero_kernel.solvers.regime import REGIME_RULE, RegimeBands

    assert (
        RegimeBands(
            re_band_min=3e4, re_bubble_max=7e4, re_band_max=1e6, mach_limit=0.3, mach_validity=0.6
        )
        == canon_bands()
    )
    rules = Rules(shipped_build().model, {f"{REGIME_RULE}.re_band_min": 2e4})
    lowered = RegimeBands.of(rules)
    assert lowered.re_band_min == 2e4
    (used,) = [u for u in rules.used() if u.parameter == "re_band_min"]
    assert used.overridden
    # Re 25 000 at the MAC: below the canon's band, inside the lowered one (bubble-sensitive)
    sections = {"Main": at(25_000.0, 2e5, 2e5)}
    assert codes(regime_by_surface(sections, NU, SPEED_OF_SOUND, NU, canon_bands())) == [OUTSIDE]
    assert codes(regime_by_surface(sections, NU, SPEED_OF_SOUND, NU, lowered)) == [BUBBLE]
