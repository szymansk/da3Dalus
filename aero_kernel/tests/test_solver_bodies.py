"""The bodies the solvers see: a canopy merged into the body it sits on (#1355, slice 2)."""

import math
from typing import Any

import numpy as np
from aero_kernel.geometry import AirplaneGeometry, Fuselage, FuselageXSecSuperEllipse
from aero_kernel.solver_bodies import merged_bodies, outline_perimeter, solver_bodies, wetted_area
from aero_kernel.superellipse import quadrant_area_fraction
from aero_kernel.tests.np_builders import CONVENTIONAL, airplane_with


def section(
    x: float,
    a: float,
    b: float,
    n: float = 2.0,
    n_lower: float | None = None,
    y: float = 0.0,
    z: float = 0.0,
    contour: list[list[float]] | None = None,
) -> dict[str, Any]:
    document: dict[str, Any] = {"xyz": [x, y, z], "a": a, "b": b, "n": n}
    if n_lower is not None:
        document["n_lower"] = n_lower
    if contour is not None:
        document["contour"] = contour
    return document


def body(
    sections: list[dict[str, Any]], role: str = "fuselage", attached_to: str | None = None
) -> dict[str, Any]:
    return {"x_secs": sections, "role": role, "attached_to": attached_to}


def airplane(**bodies: dict[str, Any]) -> AirplaneGeometry:
    dumped = airplane_with(*CONVENTIONAL).model_dump(mode="json")
    dumped["fuselages"] = {name: {"name": name, **found} for name, found in bodies.items()}
    return AirplaneGeometry.model_validate(dumped)


def area(found: FuselageXSecSuperEllipse) -> float:
    lower = found.n if found.n_lower is None else found.n_lower
    return (
        2.0 * found.a * found.b * (quadrant_area_fraction(found.n) + quadrant_area_fraction(lower))
    )


def fuselage_box() -> dict[str, Any]:
    """A long body of half-width 0.05 and half-height 0.04 from x = 0 to 1, ellipses."""
    return body([section(0.0, 0.05, 0.04), section(0.5, 0.05, 0.04), section(1.0, 0.05, 0.04)])


def canopy(
    x: tuple[float, ...] = (0.3, 0.4, 0.6),
    a: float = 0.03,
    b: float = 0.03,
    z: float = 0.04,
    n: float = 2.0,
    y: float = 0.0,
    attached_to: str = "Rumpf",
) -> dict[str, Any]:
    return body([section(x_i, a, b, n=n, y=y, z=z) for x_i in x], "canopy", attached_to)


def merged(**bodies: dict[str, Any]) -> Fuselage:
    (found,) = solver_bodies(airplane(**bodies))
    return found


def test_an_airplane_without_canopies_hands_its_bodies_over_unchanged() -> None:
    plane = airplane(Rumpf=fuselage_box(), Gondel=body([section(0.0, 0.01, 0.01)] * 2, "nacelle"))
    result = merged_bodies(plane)
    assert result.bodies == tuple((plane.fuselages or {}).values())
    assert result.merges == ()


def test_a_nacelle_attached_to_the_fuselage_stays_a_body_of_its_own() -> None:
    nacelle = body([section(0.2, 0.01, 0.01, z=0.05), section(0.4, 0.01, 0.01, z=0.05)])
    nacelle.update(role="nacelle", attached_to="Rumpf")
    plane = airplane(Rumpf=fuselage_box(), Gondel=nacelle)
    assert [b.name for b in solver_bodies(plane)] == ["Rumpf", "Gondel"]
    assert merged_bodies(plane).merges == ()


def test_the_canopy_is_no_body_of_its_own_and_the_order_is_kept() -> None:
    pod = body([section(0.0, 0.01, 0.01, y=0.3), section(0.2, 0.01, 0.01, y=0.3)], "pod")
    plane = airplane(Haube=canopy(), Rumpf=fuselage_box(), Pod=pod)
    assert [b.name for b in solver_bodies(plane)] == ["Rumpf", "Pod"]


def test_the_stations_are_the_union_with_exact_duplicates_collapsed() -> None:
    """0.3 and 0.6 are inserted; 0.4 too; the parent's 0.5 stays; nothing at 0.3 duplicated."""
    found = merged(Rumpf=fuselage_box(), Haube=canopy(x=(0.3, 0.5, 0.6)))
    assert [s.xyz[0] for s in found.x_secs] == [0.0, 0.3, 0.5, 0.6, 1.0]


def test_the_parent_sections_away_from_the_canopy_are_copied_verbatim() -> None:
    document = fuselage_box()
    contour = [[0.05, 0.0], [0.0, 0.04], [-0.05, 0.0], [0.0, -0.04]]
    document["x_secs"][0] = section(0.0, 0.05, 0.04, n=2.5, n_lower=3.0, contour=contour)
    plane = airplane(Rumpf=document, Haube=canopy())
    original = (plane.fuselages or {})["Rumpf"].x_secs
    found = merged(Rumpf=document, Haube=canopy())
    assert found.x_secs[0] == original[0]
    assert found.x_secs[-1] == original[-1]


def test_the_envelope_spans_from_the_parent_bottom_to_the_canopy_top() -> None:
    found = merged(Rumpf=fuselage_box(), Haube=canopy())
    station = next(s for s in found.x_secs if s.xyz[0] == 0.4)
    bottom, top = -0.04, 0.04 + 0.03
    assert math.isclose(station.xyz[2], (top + bottom) / 2.0, rel_tol=1e-12)
    assert math.isclose(station.b, (top - bottom) / 2.0, rel_tol=1e-12)
    assert math.isclose(station.a, 0.05, rel_tol=1e-6)
    assert station.contour is None


def _union_area(sections: list[FuselageXSecSuperEllipse], points: int = 200001) -> float:
    """An independent fine-grid area of the envelope max(w_i) (no gap in these cases)."""
    bottom = min(s.xyz[2] - s.b for s in sections)
    top = max(s.xyz[2] + s.b for s in sections)
    z = np.linspace(bottom, top, points)
    width = np.zeros_like(z)
    for s in sections:
        t = np.abs((z - s.xyz[2]) / s.b)
        width = np.maximum(width, np.where(t < 1.0, s.a * np.sqrt(np.clip(1 - t * t, 0, 1)), 0.0))
    return float(2.0 * np.sum((width[1:] + width[:-1]) * np.diff(z)) / 2.0)


def test_the_refit_keeps_the_area_of_the_envelope_with_its_notch() -> None:
    """The canopy's ellipse rises out of the parent's: the waist between them is a real notch."""
    found = merged(Rumpf=fuselage_box(), Haube=canopy())
    station = next(s for s in found.x_secs if s.xyz[0] == 0.4)
    parts = [
        FuselageXSecSuperEllipse.model_validate(section(0.4, 0.05, 0.04)),
        FuselageXSecSuperEllipse.model_validate(section(0.4, 0.03, 0.03, z=0.04)),
    ]
    assert math.isclose(area(station), _union_area(parts), rel_tol=5e-5)
    assert station.n != station.n_lower


def test_a_canopy_floating_above_the_parent_has_its_gap_filled() -> None:
    """Rectangles (n = 400): parent 0.10 x 0.08, canopy 0.06 x 0.04 starting 0.01 above it."""
    rectangle = 400.0
    parent = body([section(x, 0.05, 0.04, n=rectangle) for x in (0.0, 1.0)])
    floating = canopy(x=(0.3, 0.6), a=0.03, b=0.02, z=0.07, n=rectangle)
    found = merged(Rumpf=parent, Haube=floating)
    station = found.x_secs[1]
    box = 4.0 * quadrant_area_fraction(rectangle)
    expected = box * 0.05 * 0.04 + box * 0.03 * 0.02 + 2.0 * 0.03 * 0.01
    assert math.isclose(area(station), expected, rel_tol=2e-3)


def test_several_canopies_on_one_parent_fold_into_one_envelope() -> None:
    plane = airplane(
        Rumpf=fuselage_box(),
        Vorne=canopy(x=(0.2, 0.45)),
        Hinten=canopy(x=(0.4, 0.7), b=0.05),
    )
    result = merged_bodies(plane)
    (found,) = result.bodies
    assert [m.canopy for m in result.merges] == ["Vorne", "Hinten"]
    assert all(m.canopies_on_parent == ("Vorne", "Hinten") for m in result.merges)
    station = next(s for s in found.x_secs if s.xyz[0] == 0.4)
    assert math.isclose(station.b, (0.04 + 0.05 + 0.04) / 2.0, rel_tol=1e-12)


def test_a_degenerate_canopy_station_keeps_the_parent_section() -> None:
    """The canopy's first section has b = 0 (its nose line): nothing shows, nothing inserted."""
    nose = canopy(x=(0.3, 0.4, 0.6))
    nose["x_secs"][0]["b"] = 0.0
    found = merged(Rumpf=fuselage_box(), Haube=nose)
    assert [s.xyz[0] for s in found.x_secs] == [0.0, 0.4, 0.5, 0.6, 1.0]


def test_a_degenerate_canopy_at_a_parent_station_copies_that_section() -> None:
    nose = canopy(x=(0.5, 0.6))
    nose["x_secs"][0]["a"] = 0.0
    plane = airplane(Rumpf=fuselage_box(), Haube=nose)
    found = merged(Rumpf=fuselage_box(), Haube=nose)
    assert found.x_secs[1] == (plane.fuselages or {})["Rumpf"].x_secs[1]


def test_a_canopy_hidden_inside_its_parent_changes_nothing() -> None:
    plane = airplane(Rumpf=fuselage_box(), Haube=canopy(a=0.01, b=0.01, z=0.0))
    result = merged_bodies(plane)
    assert result.bodies[0].x_secs == (plane.fuselages or {})["Rumpf"].x_secs
    assert result.merges[0].merged_stations == 0
    assert result.merges[0].wetted_area_added == 0.0


def test_the_merge_reports_stations_areas_and_deviations() -> None:
    plane = airplane(Rumpf=fuselage_box(), Haube=canopy())
    (merge,) = merged_bodies(plane).merges
    assert (merge.canopy, merge.parent, merge.canopies_on_parent) == ("Haube", "Rumpf", ("Haube",))
    assert merge.merged_stations == 4  # 0.3, 0.4, the parent's 0.5 and 0.6
    haube = (plane.fuselages or {})["Haube"].x_secs
    assert math.isclose(merge.canopy_wetted_area, wetted_area(haube), rel_tol=1e-12)
    assert 0.0 < merge.wetted_area_added < merge.canopy_wetted_area
    assert merge.area_deviation < 1e-9
    assert 0.0 < merge.perimeter_deviation < 0.1
    assert merge.clamped_exponents == 0
    assert merge.off_centre == 0.0


def test_an_off_centre_canopy_counts_with_its_offset_and_is_reported() -> None:
    found_plane = airplane(Rumpf=fuselage_box(), Haube=canopy(a=0.03, y=0.03))
    result = merged_bodies(found_plane)
    station = next(s for s in result.bodies[0].x_secs if s.xyz[0] == 0.4)
    assert math.isclose(station.a, 0.06, rel_tol=1e-6)
    assert station.xyz[1] == 0.0
    assert result.merges[0].off_centre == 0.03


def test_a_rectangular_envelope_beyond_the_bracket_is_clamped_and_counted() -> None:
    square = 5000.0
    parent = body([section(x, 0.05, 0.04, n=square) for x in (0.0, 1.0)])
    lid = canopy(x=(0.3, 0.6), a=0.05, b=0.02, z=0.06, n=square)
    (merge,) = merged_bodies(airplane(Rumpf=parent, Haube=lid)).merges
    assert merge.clamped_exponents > 0
    assert merge.area_deviation > 0.0


def test_the_perimeter_of_a_circle_and_a_diamond() -> None:
    circle = FuselageXSecSuperEllipse.model_validate(section(0.0, 0.1, 0.1))
    diamond = FuselageXSecSuperEllipse.model_validate(section(0.0, 0.3, 0.4, n=1.0))
    point = FuselageXSecSuperEllipse.model_validate(section(0.0, 0.0, 0.0))
    assert math.isclose(outline_perimeter(circle), 2.0 * math.pi * 0.1, rel_tol=1e-6)
    assert math.isclose(outline_perimeter(diamond), 4.0 * 0.5, rel_tol=1e-9)
    assert outline_perimeter(point) == 0.0


def test_the_wetted_area_of_a_cylinder_is_perimeter_times_length() -> None:
    sections = [FuselageXSecSuperEllipse.model_validate(section(x, 0.1, 0.1)) for x in (0.0, 2.0)]
    assert math.isclose(wetted_area(sections), 2.0 * math.pi * 0.1 * 2.0, rel_tol=1e-6)
