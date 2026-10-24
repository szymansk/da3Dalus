"""The oriented section chain (one rule for the planform values and the AVL mesh)."""

from typing import Any

import pytest
from aero_kernel.errors import ErrorCategory, FormulaError
from aero_kernel.geometry import Wing
from aero_kernel.surface_chain import oriented_chain


def surface(
    rows: list[tuple[float, float, float, float, float]], *, symmetric: bool, surface_type: str
) -> Wing:
    """A surface from (x_le, y, z, chord, twist) rows in the stored order."""
    return Wing.model_validate(
        {
            "name": "S",
            "symmetric": symmetric,
            "surface_type": surface_type,
            "x_secs": [
                {"xyz_le": [x, y, z], "chord": c, "twist": t, "airfoil": "naca0012"}
                for x, y, z, c, t in rows
            ],
        }
    )


def test_a_one_sided_wing_stored_entirely_on_negative_y_keeps_its_y_and_order() -> None:
    wing = surface(
        [(0.0, -0.6, 0.0, 0.2, 0.0), (0.1, -0.3, 0.0, 0.15, 1.0), (0.2, -0.1, 0.0, 0.1, 2.0)],
        symmetric=False,
        surface_type="main_wing",
    )
    chain = oriented_chain(wing, 1)
    assert [p.y for p in chain] == [-0.6, -0.3, -0.1]
    assert [p.x for p in chain] == [0.0, 0.1, 0.2]


def test_a_mirrored_fin_with_all_z_negative_keeps_y_zero() -> None:
    """The mirroring of a surface stored on -y concerns y only; a fin is not mirrored by its z."""
    fin = surface(
        [(0.5, 0.0, -0.15, 0.1, 0.0), (0.52, 0.0, -0.1, 0.08, 0.0), (0.53, 0.0, -0.05, 0.05, 0.0)],
        symmetric=True,
        surface_type="vertical_tail",
    )
    chain = oriented_chain(fin, 2)
    assert [p.y for p in chain] == [0.0, 0.0, 0.0]
    assert [p.z for p in chain] == [-0.15, -0.1, -0.05]


def test_a_fin_chain_that_folds_back_names_z() -> None:
    fin = surface(
        [(0.5, 0.0, 0.0, 0.1, 0.0), (0.5, 0.0, 0.1, 0.08, 0.0), (0.5, 0.0, 0.05, 0.05, 0.0)],
        symmetric=False,
        surface_type="vertical_tail",
    )
    with pytest.raises(FormulaError, match="fold back in z") as raised:
        oriented_chain(fin, 2)
    assert raised.value.category is ErrorCategory.UNSUPPORTED_CONFIGURATION


def test_a_wing_chain_that_folds_back_names_y() -> None:
    wing = surface(
        [(0.0, 0.0, 0.0, 0.2, 0.0), (0.0, 0.4, 0.0, 0.15, 0.0), (0.0, 0.2, 0.0, 0.1, 0.0)],
        symmetric=True,
        surface_type="main_wing",
    )
    with pytest.raises(FormulaError, match="fold back in y"):
        oriented_chain(wing, 1)


def test_a_ventral_fin_comes_out_with_z_ascending_and_the_other_fields_paired() -> None:
    """Stored from the root downwards; the chain is reversed as a whole, so x, chord and twist stay
    with their z."""
    fin = surface(
        [(0.50, 0.0, 0.0, 0.10, 0.0), (0.52, 0.0, -0.05, 0.08, 1.0), (0.54, 0.0, -0.10, 0.05, 2.0)],
        symmetric=False,
        surface_type="vertical_tail",
    )
    chain = oriented_chain(fin, 2)
    assert [p.z for p in chain] == [-0.10, -0.05, 0.0]
    assert [p.x for p in chain] == [0.54, 0.52, 0.50]
    assert [p.chord for p in chain] == [0.05, 0.08, 0.10]
    assert [p.twist for p in chain] == [2.0, 1.0, 0.0]


def device_surface(
    ys: list[float], device_at: int, root: float, tip: float, *, symmetric: bool = True
) -> Wing:
    """A rectangular chord-0.2 surface at the given y stations with an aileron on rib ``device_at``."""
    sections: list[dict[str, Any]] = [
        {"xyz_le": [0.0, y, 0.0], "chord": 0.2, "twist": 0.0, "airfoil": "naca0012"} for y in ys
    ]
    sections[device_at]["trailing_edge_device"] = {
        "name": "ail",
        "role": "aileron",
        "rel_chord_root": root,
        "rel_chord_tip": tip,
    }
    return Wing.model_validate(
        {"name": "S", "symmetric": symmetric, "surface_type": "main_wing", "x_secs": sections}
    )


def hinges(wing: Wing) -> list[tuple[float, float] | None]:
    """(hinge at the start, hinge at the end) of the device of each chain point's segment."""
    return [
        None if p.device is None else (p.device.hinge_start, p.device.hinge_end)  # pyright: ignore[reportReturnType]
        for p in oriented_chain(wing, 1)
    ]


def test_the_device_of_a_root_first_chain_keeps_its_hinges() -> None:
    wing = device_surface([0.0, 0.2, 0.4], 1, 0.78, 0.80)
    assert hinges(wing) == [None, (0.78, 0.80), None]


def test_a_tip_first_chain_has_the_device_on_its_own_segment_with_the_hinges_swapped() -> None:
    """Stored 0.4, 0.2, 0.0 with the device on rib 1: the segment 0.2 -> 0.0 with hinge 0.78 at 0.2
    and 0.80 at 0.0; oriented from the root, the start of the segment (y = 0) has 0.80."""
    wing = device_surface([0.4, 0.2, 0.0], 1, 0.78, 0.80)
    chain = oriented_chain(wing, 1)
    assert [p.y for p in chain] == [0.0, 0.2, 0.4]
    assert hinges(wing) == [(0.80, 0.78), None, None]


def test_a_surface_stored_on_minus_y_is_mirrored_with_its_devices() -> None:
    wing = device_surface([0.0, -0.2, -0.4], 1, 0.78, 0.80)
    chain = oriented_chain(wing, 1)
    assert [p.y for p in chain] == [0.0, 0.2, 0.4]
    assert hinges(wing) == [None, (0.78, 0.80), None]


def test_a_missing_tip_hinge_takes_the_root_hinge() -> None:
    """Format ch. 6: a device without a tip hinge has the root's along the whole segment."""
    wing = device_surface([0.0, 0.2, 0.4], 1, 0.78, 0.80)
    sections = [section.model_dump(exclude_none=True) for section in wing.x_secs]
    del sections[1]["trailing_edge_device"]["rel_chord_tip"]
    rebuilt = Wing.model_validate({**wing.model_dump(exclude_none=True), "x_secs": sections})
    assert hinges(rebuilt) == [None, (0.78, 0.78), None]
