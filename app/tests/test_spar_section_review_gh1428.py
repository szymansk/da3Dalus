"""gh-1428 review round: omitted-keeps semantics, the rebuild paths, the powertrain errors, unknown material."""

from __future__ import annotations

import asyncio
import logging
from pathlib import Path

import pytest
from aero_kernel import compute
from aero_kernel.errors import FormulaError
from aero_kernel.schema import ComputeRequest
from aero_kernel.spar_capacity import bending_capacity
from sqlalchemy.orm import Session

from app.models.aeroplanemodel import AeroplaneModel, WingXSecSpareModel
from app.schemas.wing import Wing as WingConfigurationSchema
from app.services import wing_service
from app.services.canon_aeroplane_input import stored_aircraft_input
from app.tests.conftest import seed_integration_aeroplane
from app.tests.test_spar_and_ted_crud import _seed_wing
from app.tests.test_spar_section_gh1428 import TUBE_MM, add_material, add_spar

AIRFOIL = str(
    (Path(__file__).resolve().parents[2] / "components" / "airfoils" / "mh32.dat").resolve()
)
SPARS_URL = "/aeroplanes/{aid}/wings/w/cross_sections/0/spars"


@pytest.fixture
def session(client_and_db) -> Session:
    _, session_factory = client_and_db
    with session_factory() as db:
        yield db


def spar_body(**extra) -> dict:
    return {
        "spare_support_dimension_width": 0.006,
        "spare_support_dimension_height": 0.016,
        "spare_position_factor": 0.3,
        "spare_start": 0.0,
        "spare_mode": "standard",
        "spare_vector": [0, 1, 0],
        "spare_origin": [0, 0, 0],
        **extra,
    }


class TestPutKeepsWhenOmitted:
    """A spar edit that does not send section/material (the spar editor) keeps them."""

    @pytest.fixture
    def plane(self, client_and_db):
        client, session_factory = client_and_db
        with session_factory() as db:
            aid = _seed_wing(client, "keep", db=db)
        url = SPARS_URL.format(aid=aid) + "/0"
        section = {"shape": "rod", "diameter": 0.01}
        assert client.put(url, json=spar_body(section=section, material="m")).status_code == 200
        return client, url, aid

    def stored(self, client, aid) -> dict:
        return client.get(SPARS_URL.format(aid=aid)).json()[0]

    def test_omitted_keys_keep_section_and_material(self, plane):
        client, url, aid = plane
        edited = spar_body(spare_position_factor=0.5)
        assert client.put(url, json=edited).status_code == 200
        first = self.stored(client, aid)
        assert first["spare_position_factor"] == pytest.approx(0.5)
        assert first["section"] == {"shape": "rod", "diameter": pytest.approx(0.01)}
        assert first["material"] == "m"

    def test_explicit_null_clears_both(self, plane):
        client, url, aid = plane
        assert client.put(url, json=spar_body(section=None, material=None)).status_code == 200
        first = self.stored(client, aid)
        assert first["section"] is None and first["material"] is None

    def test_null_clears_only_the_key_that_is_sent(self, plane):
        client, url, aid = plane
        assert client.put(url, json=spar_body(material=None)).status_code == 200
        first = self.stored(client, aid)
        assert first["material"] is None
        assert first["section"]["shape"] == "rod"

    def test_a_new_value_replaces(self, plane):
        client, url, aid = plane
        section = {"shape": "tube", "outer_diameter": 0.016, "wall_thickness": 0.001}
        assert client.put(url, json=spar_body(section=section, material="n")).status_code == 200
        first = self.stored(client, aid)
        assert first["section"]["shape"] == "tube"
        assert first["material"] == "n"


def wing_config(spar_count: int) -> WingConfigurationSchema:
    spars = [
        {
            "spare_support_dimension_width": 5.0,
            "spare_support_dimension_height": 5.0,
            "spare_position_factor": 0.2 + 0.15 * i,
            "spare_start": 0.0,
            "spare_mode": "standard",
            "spare_vector": [0, 1, 0],
            "spare_origin": [0, 0, 0],
        }
        for i in range(spar_count)
    ]
    return WingConfigurationSchema.model_validate(
        {
            "segments": [
                {
                    "root_airfoil": {"airfoil": AIRFOIL, "chord": 150.0, "incidence": 0},
                    "tip_airfoil": {"airfoil": AIRFOIL, "chord": 120.0, "incidence": 0},
                    "length": 500.0,
                    "sweep": 10.0,
                    "number_interpolation_points": 101,
                    "spare_list": spars,
                }
            ],
            "nose_pnt": [0, 0, 0],
            "surface_type": "main_wing",
        }
    )


class TestRebuildFromWingConfig:
    """put_wing_as_wingconfig carries section and material over to the spars that still exist."""

    @pytest.fixture
    def plane(self, client_and_db):
        client, session_factory = client_and_db
        resp = client.post("/aeroplanes", params={"name": "rebuild"})
        aid = resp.json()["id"]
        with session_factory() as db:
            wing_service.put_wing_as_wingconfig(db, aid, "w", wing_config(2))
            db.commit()
            plane = db.query(AeroplaneModel).filter(AeroplaneModel.uuid == aid).one()
            spares = plane.wings[0].x_secs[0].detail.spares
            spares[0].section, spares[0].material = TUBE_MM, "first"
            spares[1].section, spares[1].material = {"shape": "rod", "diameter": 8.0}, "second"
            db.commit()
        return session_factory, aid

    def put(self, session_factory, aid, count: int) -> list[WingXSecSpareModel]:
        with session_factory() as db:
            wing_service.put_wing_as_wingconfig(db, aid, "w", wing_config(count))
            db.commit()
            db.expire_all()
            plane = db.query(AeroplaneModel).filter(AeroplaneModel.uuid == aid).one()
            assert len(plane.wings) == 1, [w.name for w in plane.wings]
            spares = list(plane.wings[0].x_secs[0].detail.spares)
            return [(s.section, s.material) for s in spares]

    def test_an_unchanged_layout_keeps_both(self, plane):
        session_factory, aid = plane
        got = self.put(session_factory, aid, 2)
        assert got == [(TUBE_MM, "first"), ({"shape": "rod", "diameter": 8.0}, "second")]

    def test_a_removed_spar_drops_only_its_own_and_is_logged(self, plane, caplog):
        session_factory, aid = plane
        with caplog.at_level(logging.WARNING, logger="app.services.wing_service"):
            got = self.put(session_factory, aid, 1)
        assert got == [(TUBE_MM, "first")]
        assert "spar 1 of cross-section 0 no longer exists" in caplog.text

    def test_an_added_spar_gets_none(self, plane):
        session_factory, aid = plane
        got = self.put(session_factory, aid, 3)
        assert got[:2] == [(TUBE_MM, "first"), ({"shape": "rod", "diameter": 8.0}, "second")]
        assert got[2] == (None, None)

    def test_a_wing_without_stored_sections_stays_without(self, client_and_db):
        client, session_factory = client_and_db
        aid = client.post("/aeroplanes", params={"name": "plain"}).json()["id"]
        with session_factory() as db:
            wing_service.put_wing_as_wingconfig(db, aid, "w", wing_config(1))
            wing_service.put_wing_as_wingconfig(db, aid, "w", wing_config(1))
            db.commit()
            plane = db.query(AeroplaneModel).filter(AeroplaneModel.uuid == aid).one()
            (spar,) = plane.wings[0].x_secs[0].detail.spares
            assert spar.section is None and spar.material is None


class TestSparInsertReplacesSections:
    def test_the_replaced_spars_take_their_section_and_material_with_them(self, session):
        from types import SimpleNamespace

        from app.services import spar_insert_service
        from cad_designer.airplane.geometry.spar_cad_insertion import spar_piece_to_spare
        from cad_designer.airplane.geometry.spar_solver import SparPiece, SparRole

        plane = seed_integration_aeroplane(session)
        add_spar(session, TUBE_MM, "Carbon tube")
        session.expire_all()
        wing = next(w for w in plane.wings if w.name == "main_wing")
        piece = SparPiece(
            role=SparRole.FRONT,
            spare_origin=(0.0, 0.0, 0.0),
            spare_vector=(0.0, 1.0, 0.0),
            outer_d=10.0,
            inner_d=8.0,
            shape="tube",
            governing_y=10.0,
            utilisation=0.5,
            length=100.0,
        )
        planned = SimpleNamespace(
            piece=piece, spare=spar_piece_to_spare(piece), segment_index=0, spar_index=0
        )
        spar_insert_service._persist_spares(session, plane.uuid, wing, [planned])
        session.flush()
        spares = wing.x_secs[0].detail.spares
        assert len(spares) == 1
        assert spares[0].section is None and spares[0].material is None


@pytest.mark.parametrize("slug", ["propeller-diameter", "motor-max-power", "battery-voltage"])
def test_a_spar_material_does_not_change_the_powertrain_error(session, slug):
    plane = seed_integration_aeroplane(session)
    add_material(session, "Carbon tube", {"bending_strength_mpa": 1370.0})
    results = {}
    for label in ("without", "with"):
        if label == "with":
            add_spar(session, TUBE_MM, "Carbon tube")
            session.expire_all()
        aircraft = stored_aircraft_input(session, plane.uuid, {})
        assert (aircraft.components is not None) == (label == "with")
        result = asyncio.run(compute(aircraft, ComputeRequest(quantities=(slug,))))
        (results[label],) = result.quantities
    without, with_ = (results[k].error for k in ("without", "with"))
    assert without is not None and with_ is not None
    assert (with_.code, with_.category, with_.input_path) == (
        without.code,
        without.category,
        without.input_path,
    )
    assert with_.hint == without.hint
    assert "Push the fitted motor, battery and propeller" in with_.hint


def test_a_spar_naming_an_unknown_material_reaches_the_caller_declared(session):
    plane = seed_integration_aeroplane(session)
    add_spar(session, TUBE_MM, "No such material")
    aircraft = stored_aircraft_input(session, plane.uuid, {})
    wing = aircraft.airplane.wings["main_wing"]
    with pytest.raises(FormulaError) as raised:
        bending_capacity(wing, 0.05, aircraft.components.materials)
    assert raised.value.code == "spar_material_unknown"
    assert "No such material" in raised.value.message
