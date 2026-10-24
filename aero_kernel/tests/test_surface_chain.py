"""The oriented section chain (one rule for the planform values and the AVL mesh)."""

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
