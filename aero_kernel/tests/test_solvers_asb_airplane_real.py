"""The geometry conversion against the real AeroSandbox (the fast tier uses a fake)."""

import pytest
from aero_kernel.solvers.asb_airplane import to_asb_airplane
from aero_kernel.tests.test_solvers_asb_airplane import CONTOUR, geometry

pytestmark = pytest.mark.aero


def test_the_real_airplane_has_the_wings_sections_and_airfoils_of_the_document() -> None:
    airplane = to_asb_airplane(geometry())
    assert airplane.name == "t"
    assert [w.name for w in airplane.wings] == ["Main", "Fin"]
    assert [w.symmetric for w in airplane.wings] == [True, False]
    main = airplane.wings[0]
    assert [list(s.xyz_le) for s in main.xsecs] == [
        [0.0, 0.0, 0.0],
        [0.02, 0.4, 0.01],
        [0.04, 0.8, 0.02],
    ]
    assert [s.chord for s in main.xsecs] == [0.2, 0.1, 0.05]
    assert [s.twist for s in main.xsecs] == [0.0, -1.5, 0.0]
    assert main.xsecs[0].airfoil.name == "naca2412"
    assert main.xsecs[1].airfoil.coordinates.tolist() == CONTOUR
