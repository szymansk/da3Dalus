"""Admissibility of the propeller table (rules ``components-propeller-table-shape`` and ``-ordered``)."""

import math
from collections.abc import Callable
from typing import Any

from aero_kernel.components import Components
from aero_kernel.errors import KernelError
from aero_kernel.schema import AircraftInput
from aero_kernel.tests.components_builders import complete_components_with_table
from aero_kernel.tests.wing_builders import airplane_document
from aero_kernel.validate import validate_aircraft

Blocks = list[dict[str, Any]]
TABLE = "components.propeller.table"


def findings(components: Components) -> tuple[KernelError, ...]:
    aircraft = AircraftInput.model_validate(
        {
            "airplane": airplane_document(),
            "components": components.model_dump(),
            "values": {"aircraft-mass": 0.151},
        }
    )
    return validate_aircraft(aircraft).errors


def with_table(mutate: Callable[[Blocks], None]) -> Components:
    """The complete document with the APC table, changed by ``mutate(blocks)``."""
    document: dict[str, Any] = complete_components_with_table().model_dump()
    blocks: Blocks = [dict(block) for block in document["propeller"]["table"]["blocks"]]
    mutate(blocks)
    document["propeller"]["table"]["blocks"] = blocks
    return Components.model_validate(document)


def test_the_published_table_is_admissible() -> None:
    assert findings(complete_components_with_table()) == ()


def test_a_table_without_blocks_is_malformed() -> None:
    (error,) = findings(with_table(lambda blocks: blocks.clear()))
    assert (error.code, error.input_path) == ("malformed_table", f"{TABLE}.blocks")


def test_a_block_whose_lists_differ_in_length_is_malformed() -> None:
    def shorten(blocks: Blocks) -> None:
        blocks[2]["cp"] = blocks[2]["cp"][:-1]

    (error,) = findings(with_table(shorten))
    assert (error.code, error.input_path) == ("malformed_table", f"{TABLE}.blocks[2]")


def test_a_block_with_one_point_is_malformed() -> None:
    def one_point(blocks: Blocks) -> None:
        for key in ("j", "ct", "cp"):
            blocks[0][key] = blocks[0][key][:1]

    (error,) = findings(with_table(one_point))
    assert error.code == "malformed_table"


def test_rpm_must_be_strictly_increasing() -> None:
    def repeat(blocks: Blocks) -> None:
        blocks[3]["rpm"] = blocks[2]["rpm"]

    (error,) = findings(with_table(repeat))
    assert (error.code, error.input_path) == ("table_not_increasing", f"{TABLE}.blocks.rpm[3]")


def test_the_first_rpm_must_be_positive() -> None:
    def zero(blocks: Blocks) -> None:
        blocks[0]["rpm"] = 0.0

    (error,) = findings(with_table(zero))
    assert error.input_path == f"{TABLE}.blocks.rpm[0]"


def test_j_must_be_strictly_increasing_and_not_negative() -> None:
    def break_axis(blocks: Blocks) -> None:
        j = list(blocks[1]["j"])
        j[4] = j[3]
        j[0] = -0.1
        blocks[1]["j"] = j

    first, second = findings(with_table(break_axis))
    assert first.input_path == f"{TABLE}.blocks[1].j[0]"
    assert second.input_path == f"{TABLE}.blocks[1].j[4]"
    assert {first.code, second.code} == {"table_not_increasing"}


def test_a_non_finite_coefficient_is_reported_at_its_index() -> None:
    def poison(blocks: Blocks) -> None:
        ct = list(blocks[5]["ct"])
        ct[2] = math.nan
        blocks[5]["ct"] = ct

    (error,) = findings(with_table(poison))
    assert error.code == "non_finite_number"
    assert error.input_path == f"{TABLE}.blocks[5].ct[2]"
