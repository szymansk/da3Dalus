"""Expert View slice 2 (gh-1282): a stored aeroplane converted to the kernel's input.

Fast tier: the conversion is pure data, no solver runs.
"""

from __future__ import annotations

import uuid
from datetime import datetime, timezone

import pytest
from sqlalchemy.orm import Session

from app.core.exceptions import NotFoundError, ValidationError
from app.models.aeroplanemodel import (
    DesignAssumptionModel,
    FuselageModel,
    FuselageXSecSuperEllipseModel,
    WingModel,
    WingXSecDetailModel,
    WingXSecModel,
    WingXSecSpareModel,
)
from app.services.canon_aeroplane_input import (
    geometry_document,
    input_path,
    kernel_input,
    stored_aircraft_input,
)
from app.tests.conftest import seed_integration_aeroplane


@pytest.fixture
def session(client_and_db) -> Session:
    _, session_factory = client_and_db
    with session_factory() as db:
        yield db


def assume_mass(
    db: Session, aeroplane_id: int, estimate: float, calculated: float | None, active: str
) -> None:
    db.add(
        DesignAssumptionModel(
            aeroplane_id=aeroplane_id,
            parameter_name="mass",
            estimate_value=estimate,
            calculated_value=calculated,
            active_source=active,
            updated_at=datetime.now(timezone.utc),
        )
    )
    db.commit()


def add_fuselage(db: Session, aeroplane_id: int) -> None:
    body = FuselageModel(name="Rumpf", aeroplane_id=aeroplane_id)
    canopy = FuselageModel(
        name="Haube", aeroplane_id=aeroplane_id, role="canopy", attached_to="Rumpf"
    )
    db.add_all([body, canopy])
    db.flush()
    for target, z in ((body, 0.0), (canopy, 0.03)):
        for index, x in enumerate((0.0, 0.3)):
            db.add(
                FuselageXSecSuperEllipseModel(
                    fuselage_id=target.id,
                    xyz=[x, 0.0, z],
                    a=0.03,
                    b=0.04,
                    n=2.0,
                    contour=[[0.0, -0.04], [0.03, 0.0], [0.0, 0.04]],
                    sort_index=index,
                )
            )
    db.commit()


class TestInputPath:
    def test_a_map_key_is_quoted_and_an_index_is_bracketed(self):
        assert (
            input_path(("airplane", "wings", "Main Wing", "x_secs", 2, "chord"))
            == 'airplane.wings["Main Wing"].x_secs[2].chord'
        )

    def test_a_key_is_json_escaped(self):
        assert input_path(("airplane", "fuselages", 'a"b', "x_secs")) == (
            'airplane.fuselages["a\\"b"].x_secs'
        )

    def test_a_field_named_like_a_map_below_a_key_is_a_field(self):
        assert input_path(("airplane", "wings", "wings", "name")) == (
            'airplane.wings["wings"].name'
        )


class TestStoredAircraftInput:
    def test_the_geometry_of_a_stored_aeroplane_is_converted(self, session):
        plane = seed_integration_aeroplane(session)
        add_fuselage(session, plane.id)
        aircraft = stored_aircraft_input(session, plane.uuid, {})
        geometry = aircraft.airplane
        assert geometry.name == "integration-test-plane"
        assert geometry.xyz_ref == (0.15, 0.0, 0.0)
        assert geometry.total_mass_kg == 1.5
        assert {name: w.surface_type for name, w in geometry.wings.items()} == {
            "main_wing": "main_wing",
            "horizontal_tail": "horizontal_tail",
            "vertical_tail": "vertical_tail",
        }
        main = geometry.wings["main_wing"]
        assert [x.chord for x in main.x_secs] == [0.2, 0.15]
        assert main.x_secs[0].twist == 2.0
        assert main.x_secs[1].xyz_le == (0.0, 0.5, 0.0)
        device = main.x_secs[0].trailing_edge_device
        assert device is not None
        assert device.role == "aileron"
        assert device.rel_chord_root == 0.75
        assert geometry.wings["vertical_tail"].symmetric is False
        body, canopy = geometry.fuselages["Rumpf"], geometry.fuselages["Haube"]
        assert [x.xyz for x in body.x_secs] == [(0.0, 0.0, 0.0), (0.3, 0.0, 0.0)]
        assert body.x_secs[0].contour == ((0.0, -0.04), (0.03, 0.0), (0.0, 0.04))
        assert (canopy.role, canopy.attached_to) == ("canopy", "Rumpf")

    def test_an_airfoil_file_becomes_its_inline_contour(self, session):
        plane = seed_integration_aeroplane(session)
        x_sec = stored_aircraft_input(session, plane.uuid, {}).airplane.wings["main_wing"].x_secs[0]
        coordinates = x_sec.airfoil.coordinates
        assert len(coordinates) > 20
        assert coordinates[0][0] == pytest.approx(1.0, abs=1e-3)

    def test_an_airfoil_without_a_file_is_passed_on_for_the_kernel_to_judge(self, session):
        # no naca0012.dat in components/airfoils: the kernel reads the NACA designation itself
        plane = seed_integration_aeroplane(session)
        wing = stored_aircraft_input(session, plane.uuid, {}).airplane.wings["horizontal_tail"]
        assert wing.x_secs[0].airfoil == "naca0012"

    def test_spars_are_given_in_metres(self, session):
        plane = seed_integration_aeroplane(session)
        root = (
            session.query(WingXSecModel)
            .join(WingModel)
            .filter(WingModel.name == "main_wing", WingXSecModel.sort_index == 0)
            .one()
        )
        detail = session.query(WingXSecDetailModel).filter_by(wing_xsec_id=root.id).one()
        session.add(
            WingXSecSpareModel(
                wing_xsec_detail_id=detail.id,
                sort_index=0,
                spare_support_dimension_width=4.0,
                spare_support_dimension_height=6.0,
                spare_position_factor=0.25,
                spare_start=10.0,
                spare_vector=[0.0, 1.0, 0.0],
            )
        )
        session.commit()
        aircraft = stored_aircraft_input(session, plane.uuid, {})
        (spar,) = aircraft.airplane.wings["main_wing"].x_secs[0].spare_list
        assert spar.spare_support_dimension_width == pytest.approx(0.004)
        assert spar.spare_support_dimension_height == pytest.approx(0.006)
        assert spar.spare_start == pytest.approx(0.010)
        assert spar.spare_vector == (0.0, 1.0, 0.0)

    @pytest.mark.parametrize(("active", "expected"), [("ESTIMATE", 1.2), ("CALCULATED", 1.4)])
    def test_the_mass_is_the_design_assumption_with_its_active_source(
        self, session, active, expected
    ):
        plane = seed_integration_aeroplane(session)
        assume_mass(session, plane.id, estimate=1.2, calculated=1.4, active=active)
        aircraft = stored_aircraft_input(session, plane.uuid, {})
        assert aircraft.values == {"aircraft-mass": expected}

    def test_the_callers_values_replace_the_aircrafts_own(self, session):
        plane = seed_integration_aeroplane(session)
        assume_mass(session, plane.id, estimate=1.2, calculated=None, active="CALCULATED")
        aircraft = stored_aircraft_input(
            session, plane.uuid, {"aircraft-mass": 2.0, "flap-deflection-landing": 30.0}
        )
        assert aircraft.values == {"aircraft-mass": 2.0, "flap-deflection-landing": 30.0}

    def test_without_the_mass_assumption_no_mass_is_passed(self, session):
        # total_mass_kg is a consistency check of the kernel, never the mass (ADR 0020)
        plane = seed_integration_aeroplane(session)
        aircraft = stored_aircraft_input(session, plane.uuid, {})
        assert "aircraft-mass" not in aircraft.values

    def test_an_unknown_aeroplane_is_not_found(self, session):
        with pytest.raises(NotFoundError):
            stored_aircraft_input(session, uuid.uuid4(), {})


class TestConversionErrors:
    def test_a_stored_wing_the_document_refuses_is_named_by_its_path(self, session):
        plane = seed_integration_aeroplane(session)
        tip = (
            session.query(WingXSecModel)
            .join(WingModel)
            .filter(WingModel.name == "horizontal_tail", WingXSecModel.sort_index == 1)
            .one()
        )
        session.delete(tip)
        session.commit()
        with pytest.raises(ValidationError) as caught:
            stored_aircraft_input(session, plane.uuid, {})
        (error,) = caught.value.details["input_errors"]
        assert error["input_path"] == 'airplane.wings["horizontal_tail"].x_secs'
        assert error["code"] == "invalid_input"
        assert 'airplane.wings["horizontal_tail"].x_secs' in caught.value.message

    def test_a_document_item_of_the_wrong_type_is_named_by_its_path(self, session):
        plane = seed_integration_aeroplane(session)
        document = geometry_document(plane, session)
        document["wings"]["main_wing"]["x_secs"][1]["chord"] = "wide"
        with pytest.raises(ValidationError) as caught:
            kernel_input(document, {})
        paths = [e["input_path"] for e in caught.value.details["input_errors"]]
        assert paths == ['airplane.wings["main_wing"].x_secs[1].chord']

    def test_an_item_the_format_does_not_know_is_named_by_its_path(self, session):
        plane = seed_integration_aeroplane(session)
        document = geometry_document(plane, session)
        document["fuselages"] = {"F": {"name": "F", "x_secs": [], "colour": "red"}}
        with pytest.raises(ValidationError) as caught:
            kernel_input(document, {})
        paths = [e["input_path"] for e in caught.value.details["input_errors"]]
        assert paths == ['airplane.fuselages["F"].colour']
