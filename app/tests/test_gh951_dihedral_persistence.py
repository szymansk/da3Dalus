"""gh-951: a rib's dihedral (local-x rotation) must survive DB persistence.

Twist has always been stored explicitly per cross-section, so incidence
round-trips. Dihedral used to be reconstructed from the xyz_le geometry,
which cannot encode the *terminal* rib's own rotation (it moves no
outboard station) — so it was silently lost on save. It is now persisted
explicitly in the ``wing_xsecs.dihedral`` column. These tests exercise the
full ``put_wing_as_wingconfig`` -> ``get_wing_as_wingconfig`` path against a
real (in-memory) DB.
"""

from __future__ import annotations

import pytest

pytest.importorskip("aerosandbox")
pytest.importorskip("cadquery")

from app.schemas.wing import Airfoil, Segment, Wing  # noqa: E402
from app.services.aeroplane_service import create_aeroplane  # noqa: E402
from app.services.wing_service import (  # noqa: E402
    get_wing_as_wingconfig,
    put_wing_as_wingconfig,
)


def _make_session(client_and_db):
    _, SessionLocal = client_and_db
    return SessionLocal()


def _wing_with_dihedral(terminal_tip_dihedral: float) -> Wing:
    """A 2-segment wing carrying a dihedral on the terminal (outermost) rib."""

    def _af(dihedral: float, incidence: float = 0.0) -> Airfoil:
        return Airfoil(
            airfoil="naca0015",
            chord=200,
            dihedral_as_rotation_in_degrees=dihedral,
            incidence=incidence,
        )

    return Wing(
        nose_pnt=[0, 0, 0],
        symmetric=True,
        segments=[
            Segment(root_airfoil=_af(0), tip_airfoil=_af(5, incidence=1), length=300, sweep=0),
            Segment(
                root_airfoil=_af(5, incidence=1),
                tip_airfoil=_af(terminal_tip_dihedral, incidence=2),
                length=200,
                sweep=10,
            ),
        ],
    )


def _put_get(db, uuid: str, wing: Wing) -> dict:
    put_wing_as_wingconfig(db, uuid, "main_wing", wing, scale=0.001)
    db.commit()
    db.expire_all()
    return get_wing_as_wingconfig(db, uuid, "main_wing")


def test_terminal_rib_dihedral_persists(client_and_db):
    """A 30 deg rotation on the outermost rib survives save + reload (gh-951)."""
    db = _make_session(client_and_db)
    plane = create_aeroplane(db, "gh951-plane")
    db.commit()
    db.refresh(plane)

    out = _put_get(db, str(plane.uuid), _wing_with_dihedral(30.0))

    terminal = out["segments"][-1]["tip_airfoil"]["dihedral_as_rotation_in_degrees"]
    assert terminal == pytest.approx(30.0, abs=0.1)


def test_inboard_dihedral_and_incidence_still_persist(client_and_db):
    """The fix must not disturb inboard dihedral or any incidence."""
    db = _make_session(client_and_db)
    plane = create_aeroplane(db, "gh951-plane-2")
    db.commit()
    db.refresh(plane)

    out = _put_get(db, str(plane.uuid), _wing_with_dihedral(30.0))

    tip_dihedrals = [s["tip_airfoil"]["dihedral_as_rotation_in_degrees"] for s in out["segments"]]
    tip_incidences = [s["tip_airfoil"]["incidence"] for s in out["segments"]]
    assert tip_dihedrals[0] == pytest.approx(5.0, abs=0.1)
    assert tip_dihedrals[1] == pytest.approx(30.0, abs=0.1)
    assert tip_incidences == pytest.approx([1.0, 2.0], abs=0.05)


def test_round_trip_is_idempotent(client_and_db):
    """put(get(put(x))) leaves the dihedral unchanged — no drift on re-save."""
    db = _make_session(client_and_db)
    plane = create_aeroplane(db, "gh951-plane-3")
    db.commit()
    db.refresh(plane)
    uuid = str(plane.uuid)

    out1 = _put_get(db, uuid, _wing_with_dihedral(30.0))
    out2 = _put_get(db, uuid, Wing.model_validate(out1))

    d1 = [s["tip_airfoil"]["dihedral_as_rotation_in_degrees"] for s in out1["segments"]]
    d2 = [s["tip_airfoil"]["dihedral_as_rotation_in_degrees"] for s in out2["segments"]]
    assert d1 == pytest.approx(d2, abs=1e-6)
