"""The spar section in the geometry model, and the reachability guard of the capacity module."""

import re
from pathlib import Path
from typing import Any

import pytest
from aero_kernel.geometry import (
    CappedSection,
    RectangularSection,
    RodSection,
    SpareDetail,
    TubeSection,
)
from aero_kernel.tests.spar_builders import CAPPED, RECTANGULAR, ROD, TUBE, spar
from pydantic import ValidationError

KERNEL = Path(__file__).resolve().parent.parent


@pytest.mark.parametrize(
    ("section", "model"),
    [
        (ROD, RodSection),
        (TUBE, TubeSection),
        (RECTANGULAR, RectangularSection),
        (CAPPED, CappedSection),
    ],
)
def test_the_shape_tag_selects_the_section_model(section: dict[str, Any], model: type) -> None:
    assert type(SpareDetail.model_validate(spar(section=section)).section) is model


def test_a_spar_without_section_or_material_parses_as_before() -> None:
    parsed = SpareDetail.model_validate(spar())
    assert (parsed.section, parsed.material) == (None, None)


def test_the_dimensions_are_kept_in_metres_unscaled() -> None:
    parsed = SpareDetail.model_validate(spar(section=TUBE, material="carbon_tube"))
    assert parsed.section == TubeSection(shape="tube", outer_diameter=0.016, wall_thickness=0.001)
    assert parsed.material == "carbon_tube"


def test_an_unknown_shape_is_refused() -> None:
    with pytest.raises(ValidationError, match="shape"):
        SpareDetail.model_validate(spar(section={"shape": "hexagon", "width": 0.01}))


def test_a_section_without_its_tag_is_refused() -> None:
    with pytest.raises(ValidationError, match="shape"):
        SpareDetail.model_validate(spar(section={"diameter": 0.01}))


def test_a_dimension_of_another_shape_is_refused() -> None:
    with pytest.raises(ValidationError, match="width"):
        SpareDetail.model_validate(spar(section=ROD | {"width": 0.01}))


def test_a_missing_dimension_is_refused() -> None:
    with pytest.raises(ValidationError, match="wall_thickness"):
        SpareDetail.model_validate(spar(section={"shape": "tube", "outer_diameter": 0.016}))


def test_a_dimension_must_be_a_number_not_a_string() -> None:
    with pytest.raises(ValidationError, match="diameter"):
        SpareDetail.model_validate(spar(section={"shape": "rod", "diameter": "0.01"}))


def test_no_strength_or_safety_factor_field_exists_in_the_document() -> None:
    for name in ("strength", "safety_factor", "bending_strength_pa", "knockdown"):
        with pytest.raises(ValidationError, match=name):
            SpareDetail.model_validate(spar(**{name: 1.0}))


def test_spar_capacity_reachability() -> None:
    """ADR 0021, rule 2: the capacity module stays unreachable until gh-1429 wires its reader.

    When gh-1429 imports it from a formula, this test and the ``UNREACHABLE(gh-1429)`` markers go.
    """
    importers = [
        path.relative_to(KERNEL).as_posix()
        for path in KERNEL.rglob("*.py")
        if "tests" not in path.parts
        and path.name != "spar_capacity.py"
        and re.search(r"\bspar_capacity\b", path.read_text(encoding="utf-8"))
    ]
    assert importers == []
    marked = (KERNEL / "spar_capacity.py").read_text(encoding="utf-8")
    assert "UNREACHABLE(gh-1429)" in marked
