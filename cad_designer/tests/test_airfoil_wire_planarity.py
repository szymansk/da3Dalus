"""The airfoil section wire is a plane curve in every section plane (gh-1493).

The wire built by the ``airfoil`` CadQuery plugin must lie in its section
plane for every orientation of that plane. A wire that leaves the plane by
more than its edge tolerance gives a loft without end caps on some platforms
(x86-64 Linux), i.e. an open shell instead of a solid.
"""

from pathlib import Path

import numpy as np
import pytest

pytestmark = [pytest.mark.requires_cadquery]

REPO_ROOT = Path(__file__).resolve().parents[2]
AIRFOIL = str(REPO_ROOT / "components" / "airfoils" / "naca0010.dat")
CHORD_MM = 200.0

# OCCT's Precision::Confusion() is 1e-7 mm and is the tolerance of the wire's
# edges. The wire has to be planar well inside that; 1e-9 mm leaves two orders
# of magnitude of margin and is far above double-precision noise (~1e-13 mm
# at these coordinates).
PLANARITY_TOL_MM = 1e-9

# (dihedral, incidence) in degrees. Dihedral is what takes the section plane
# out of axis alignment; the pure-incidence and flat cases guard the planes
# that were already exact.
SECTION_ROTATIONS = [
    (0.0, 0.0),
    (0.0, 3.0),
    (10.0, 0.0),
    (10.0, 3.0),
    (5.0, -5.0),
    (10.0, 8.0),
    (-7.5, 2.0),
]


def _section_plane(dihedral: float, incidence: float, origin=(0.0, 0.0, 0.0)):
    import cadquery as cq

    plane = cq.Workplane("XZ").plane.rotated((dihedral, 0, -incidence))
    plane.origin = cq.Vector(*origin)
    return plane


def _airfoil_wire(plane, **kwargs):
    import cadquery as cq

    import cad_designer.cq_plugins  # noqa: F401 — registers the plugin

    return cq.Workplane(inPlane=plane).airfoil(AIRFOIL, CHORD_MM, **kwargs).val()


def _sample_wire(wire, samples_per_edge: int = 400) -> np.ndarray:
    from OCP.BRepAdaptor import BRepAdaptor_Curve

    points = []
    for edge in wire.Edges():
        curve = BRepAdaptor_Curve(edge.wrapped)
        for u in np.linspace(curve.FirstParameter(), curve.LastParameter(), samples_per_edge):
            p = curve.Value(u)
            points.append((p.X(), p.Y(), p.Z()))
    return np.array(points)


def _max_distance_from_plane(wire, plane) -> float:
    origin = np.array(plane.origin.toTuple())
    normal = np.array(plane.zDir.toTuple())
    return float(np.max(np.abs((_sample_wire(wire) - origin) @ normal)))


@pytest.mark.parametrize("dihedral,incidence", SECTION_ROTATIONS)
def test_airfoil_wire_lies_in_its_section_plane(dihedral, incidence):
    plane = _section_plane(dihedral, incidence)

    wire = _airfoil_wire(plane)

    deviation = _max_distance_from_plane(wire, plane)
    assert deviation <= PLANARITY_TOL_MM, (
        f"airfoil wire leaves its section plane by {deviation:.3e} mm "
        f"(dihedral={dihedral}, incidence={incidence})"
    )


@pytest.mark.parametrize("dihedral,incidence", SECTION_ROTATIONS)
def test_occt_finds_a_plane_through_the_airfoil_wire(dihedral, incidence):
    """This is the check the loft uses to decide whether it can cap its ends."""
    from OCP.BRepLib import BRepLib_FindSurface

    wire = _airfoil_wire(_section_plane(dihedral, incidence))

    finder = BRepLib_FindSurface(wire.wrapped, -1, True)  # default tolerance, planes only

    assert finder.Found()


@pytest.mark.parametrize("kwargs", [{}, {"offset": 0.42}, {"number_interpolation_points": 101}])
def test_airfoil_wire_is_the_same_curve_in_every_section_plane(kwargs):
    """The section is one fixed plane curve, moved rigidly into its plane.

    Expressed in the local coordinates of its plane, the wire in a rotated and
    shifted plane is the wire of the axis-aligned plane.
    """
    reference_plane = _section_plane(0.0, 0.0)
    rotated_plane = _section_plane(10.0, 3.0, origin=(25.0, 50.0, 100.0))

    reference = _airfoil_wire(reference_plane, **kwargs)
    rotated = _airfoil_wire(rotated_plane, **kwargs)

    def local(wire, plane):
        from cadquery import Vector

        return np.array([plane.toLocalCoords(Vector(*p)).toTuple() for p in _sample_wire(wire, 100)])

    np.testing.assert_allclose(
        local(rotated, rotated_plane), local(reference, reference_plane), atol=1e-9
    )
    assert rotated.IsClosed()
    assert rotated.Length() == pytest.approx(reference.Length(), abs=1e-9)


def test_loft_over_twisted_dihedral_sections_is_a_closed_solid():
    """A loft over two sections with twist and dihedral has both end caps.

    Before gh-1493 this loft had two faces: the skin and the trailing edge,
    no caps.
    """
    import cadquery as cq
    from OCP.BRepCheck import BRepCheck_Analyzer

    import cad_designer.cq_plugins  # noqa: F401 — registers the plugin

    loft = (
        cq.Workplane("XZ")
        .wing_root_segment(
            root_airfoil=AIRFOIL,
            root_chord=200.0,
            tip_chord=150.0,
            length=500.0,
            sweep=20.0,
            root_incidence=3.0,
            tip_incidence=-5.0,
            root_dihedral=10.0,
            connected=False,
        )
        .vals()[-1]  # the plugin stacks [tip plane, tip wire, solid]
    )

    assert loft.ShapeType() == "Solid"
    assert len(loft.Faces()) == 4  # skin, blunt trailing edge, root cap, tip cap
    assert BRepCheck_Analyzer(loft.wrapped).IsValid()
    assert loft.Volume() > 0
