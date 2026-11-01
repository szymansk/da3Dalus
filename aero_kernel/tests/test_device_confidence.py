"""NeuralFoil's confidence over the span of a control device, weighted by area (#1342, M1)."""

import math

import pytest
from aero_kernel.solvers.opti import DeviceConfidence, SectionConfidence
from pydantic import ValidationError


def section(area: float, span: float, confidence: float, y: float = 0.1) -> SectionConfidence:
    return SectionConfidence(area_m2=area, span_m=span, confidence=confidence, at_m=(0.0, y, 0.0))


def flap(*sections: SectionConfidence) -> DeviceConfidence:
    return DeviceConfidence(wing="Main", device="flap", sections=sections)


def test_the_mean_is_weighted_by_area() -> None:
    """20 % of the area at 0.4, the rest at 0.95: 0.84, the issue's declared limit of a mean."""
    device = flap(section(0.2, 0.1, 0.4), section(0.8, 0.4, 0.95))
    assert math.isclose(device.mean_confidence(), 0.2 * 0.4 + 0.8 * 0.95)


def test_the_span_share_below_a_floor_and_the_lowest_section() -> None:
    device = flap(section(0.2, 0.1, 0.4, y=0.5), section(0.8, 0.4, 0.95, y=0.2))
    assert math.isclose(device.span_share_below(0.85), 0.1 / 0.5)
    assert device.lowest().at_m == (0.0, 0.5, 0.0)
    assert device.span_share_below(0.3) == 0.0


def test_a_device_needs_a_section_with_area() -> None:
    with pytest.raises(ValidationError):
        flap()
    with pytest.raises(ValidationError):
        flap(section(0.0, 0.0, 0.9))


def test_the_span_of_a_device_is_its_segments_on_either_half() -> None:
    """A flap on the first two panels of a wing stored on the negative side: |y| 0 to 0.6 m."""
    from aero_kernel.geometry import AirplaneGeometry
    from aero_kernel.solvers.devices import flap_segments
    from aero_kernel.solvers.opti import device_spans

    device = {"name": "Klappe", "role": "flap", "deflection_deg": 20.0, "rel_chord_root": 0.75}
    sections = [
        {"xyz_le": [0.0, -0.3 * i, 0.0], "chord": 0.2, "twist": 0.0, "airfoil": "naca2412"}
        | ({"trailing_edge_device": device} if i < 2 else {})
        for i in range(4)
    ]
    plane = AirplaneGeometry.model_validate(
        {
            "name": "t",
            "wings": {"Main": {"name": "Main", "surface_type": "main_wing", "x_secs": sections}},
        }
    )
    (span,) = device_spans(plane, flap_segments(plane))
    assert (span.wing, span.device) == ("Main", "Klappe")
    assert span.intervals == ((0.0, 0.3), (0.3, 0.6))
    assert span.holds(-0.45)
    assert span.holds(0.3)
    assert not span.holds(0.61)


def test_a_mean_above_the_floor_declares_nothing_however_low_one_section() -> None:
    """Decision 3 (#1342): the mean decides, the lowest section is information. 10 % of the area at
    0.4 and the rest at 0.95 is a mean of 0.895, above 0.85."""
    from aero_kernel.formulas.flap_validity import warn_flap_validity
    from aero_kernel.solvers.opti import DeflectionDiagnostics
    from aero_kernel.tests.formula_builders import StubAtmosphere, context_with
    from aero_kernel.tests.solver_builders import airplane

    def diagnostics(*sections: SectionConfidence) -> DeflectionDiagnostics:
        return DeflectionDiagnostics(
            min_confidence=0.4,
            min_confidence_wing="Main",
            max_effective_alpha_deg=10.0,
            max_effective_alpha_wing="Main",
            devices=(flap(*sections),),
        )

    flapped = airplane(device=("flap", 20.0), hinge=0.8)
    context = context_with(StubAtmosphere({}))
    warn_flap_validity(
        context, flapped, diagnostics(section(0.1, 0.1, 0.4), section(0.9, 0.4, 0.95))
    )
    assert context.warnings == ()
    warn_flap_validity(
        context, flapped, diagnostics(section(0.3, 0.1, 0.4), section(0.7, 0.4, 0.95))
    )
    (low,) = context.warnings
    assert low.code == "flap_confidence_low"
    assert math.isclose(float(low.detail["mean_confidence"]), 0.785)  # pyright: ignore[reportArgumentType]
    assert math.isclose(float(low.detail["span_share_below_threshold"]), 0.2)  # pyright: ignore[reportArgumentType]
    assert low.detail["min_confidence"] == 0.4


class _Wing:
    """A converted, unmirrored wing of two sections (three cross-sections at y 0, 0.1, 0.2 m)."""

    symmetric = False

    def __init__(self) -> None:
        from types import SimpleNamespace

        self.xsecs = [
            SimpleNamespace(chord=c, xyz_le=[0.0, y, 0.0])
            for c, y in ((0.3, 0.0), (0.1, 0.1), (0.1, 0.2))
        ]

    def area(self, **_: object) -> list[float]:
        return [0.02, 0.01]

    def span(self, **_: object) -> list[float]:
        return [0.1, 0.1]


def _calls(*pairs: tuple[int, float]) -> list[object]:
    from aero_kernel.solvers.opti import _Seen  # pyright: ignore[reportPrivateUsage]

    return [_Seen(wing="Main", xsec=i, confidence=c, effective_alpha=0.0) for i, c in pairs]


def test_a_section_is_the_chord_blend_of_its_two_ends() -> None:
    """Section 0: chords 0.3 and 0.1 at confidence 0.9 and 0.5 blend to 0.8."""
    from aero_kernel.solvers.opti import _wing_sections  # pyright: ignore[reportPrivateUsage]

    found = _wing_sections("Main", _Wing(), _calls((0, 0.9), (1, 0.5), (1, 0.7), (2, 0.7)))  # pyright: ignore[reportArgumentType]
    assert [round(s.confidence, 12) for s in found] == [0.8, 0.7]
    assert [s.area_m2 for s in found] == [0.02, 0.01]
    assert all(
        math.isclose(a, b, abs_tol=1e-12)
        for a, b in zip(found[0].at_m, (0.0, 0.05, 0.0), strict=True)
    )


def test_calls_out_of_order_are_a_defect_of_ours() -> None:
    from aero_kernel.solvers.opti import _wing_sections  # pyright: ignore[reportPrivateUsage]

    calls = _calls((0, 0.9), (2, 0.5), (1, 0.7), (2, 0.7))
    with pytest.raises(RuntimeError, match="out of order"):
        _wing_sections("Main", _Wing(), calls)  # pyright: ignore[reportArgumentType]


def test_a_device_without_a_section_on_its_span_is_a_defect_of_ours() -> None:
    from types import SimpleNamespace

    from aero_kernel.solvers import opti as opti_module

    plane = SimpleNamespace(wings=[_Wing()])
    calls = _calls((0, 0.9), (1, 0.5), (1, 0.7), (2, 0.7))
    away = opti_module.DeviceSpan(wing="Main", device="flap", intervals=((0.5, 0.6),))
    with pytest.raises(RuntimeError, match="no section"):
        opti_module._device_confidence(plane, ["Main"], calls, [away])  # pyright: ignore[reportPrivateUsage, reportArgumentType]
