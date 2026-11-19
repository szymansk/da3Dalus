"""gh-1428: section and material of a spar, stored in mm, delivered in metres to the kernel.

Fast tier. DB -> document (format v3) -> kernel input, the components contract v3 (materials),
the snapshot of published strengths and its validator.
"""

from __future__ import annotations

import copy
import json
from pathlib import Path

import jsonschema
import pytest
from pydantic import ValidationError as PydanticValidationError
from sqlalchemy.orm import Session

from app import schemas
from app.core.exceptions import ValidationError
from app.models.aeroplanemodel import (
    WingModel,
    WingXSecDetailModel,
    WingXSecModel,
    WingXSecSpareModel,
)
from app.models.component import ComponentModel
from app.services.aeroplane_clone_service import clone_aeroplane_subgraph
from app.services.canon_aeroplane_input import (
    components_document,
    geometry_document,
    materials_table,
    spar_material_names,
    stored_aircraft_input,
)
from app.services.structural_material_import import validate_structural_material_record
from app.services.wing_service import _convert_spare_to_meters, _convert_spare_to_mm
from app.tests.conftest import seed_integration_aeroplane

REPO = Path(__file__).resolve().parents[2]
SNAPSHOT = REPO / "data" / "cots" / "structural_materials.json"
SCHEMA = REPO / "docs" / "geometry-format" / "airplane-geometry.schema.json"

TUBE_MM = {"shape": "tube", "outer_diameter": 16.0, "wall_thickness": 1.0}


@pytest.fixture
def session(client_and_db) -> Session:
    _, session_factory = client_and_db
    with session_factory() as db:
        yield db


def add_spar(db: Session, section: dict | None, material: str | None) -> None:
    """A spar with the given section (mm) on the root segment of the integration plane's wing."""
    root = (
        db.query(WingXSecModel)
        .join(WingModel)
        .filter(WingModel.name == "main_wing", WingXSecModel.sort_index == 0)
        .one()
    )
    detail = db.query(WingXSecDetailModel).filter_by(wing_xsec_id=root.id).one()
    db.add(
        WingXSecSpareModel(
            wing_xsec_detail_id=detail.id,
            sort_index=0,
            spare_support_dimension_width=6.0,
            spare_support_dimension_height=16.0,
            spare_position_factor=0.25,
            spare_start=0.0,
            spare_vector=[0.0, 1.0, 0.0],
            section=section,
            material=material,
        )
    )
    db.commit()


def add_material(db: Session, name: str, specs: dict, manufacturer: str | None = "M") -> None:
    db.add(
        ComponentModel(name=name, manufacturer=manufacturer, component_type="material", specs=specs)
    )
    db.commit()


class TestSectionSchema:
    @pytest.mark.parametrize(
        "section",
        [
            {"shape": "rod", "diameter": 0.01},
            {"shape": "tube", "outer_diameter": 0.016, "wall_thickness": 0.001},
            {"shape": "rectangular", "width": 0.006, "height": 0.016},
            {"shape": "capped", "width": 0.01, "height": 0.012, "flange_thickness": 0.001},
        ],
    )
    def test_every_shape_converts_to_mm_and_back(self, section):
        spar = schemas.SpareDetailSchema(
            spare_support_dimension_width=0.01,
            spare_support_dimension_height=0.01,
            section=section,
            material="x",
        )
        in_mm = _convert_spare_to_mm(spar)
        for key, value in section.items():
            if key != "shape":
                assert getattr(in_mm.section, key) == pytest.approx(value * 1000.0)
        assert in_mm.section.shape == section["shape"]
        assert _convert_spare_to_meters(in_mm).section == spar.section
        assert in_mm.material == "x"

    def test_a_spar_without_a_section_stays_valid(self):
        spar = schemas.SpareDetailSchema(
            spare_support_dimension_width=0.01, spare_support_dimension_height=0.01
        )
        assert spar.section is None and spar.material is None
        assert _convert_spare_to_mm(spar).section is None
        assert _convert_spare_to_meters(spar).section is None

    @pytest.mark.parametrize(
        "section",
        [
            {"shape": "rod", "diameter": 0.0},
            {"shape": "tube", "outer_diameter": 0.016, "wall_thickness": 0.008},
            {"shape": "capped", "width": 0.01, "height": 0.012, "flange_thickness": 0.006},
            {"shape": "oval", "diameter": 0.01},
            {"shape": "rod", "diameter": 0.01, "extra": 1.0},
        ],
    )
    def test_an_inadmissible_section_is_refused(self, section):
        with pytest.raises(PydanticValidationError):
            schemas.SpareDetailSchema(
                spare_support_dimension_width=0.01,
                spare_support_dimension_height=0.01,
                section=section,
            )


class TestDocument:
    def test_the_document_carries_section_in_metres_and_the_material_name(self, session):
        plane = seed_integration_aeroplane(session)
        add_spar(session, TUBE_MM, "Carbon tube")
        document = geometry_document(plane, session)
        (spar,) = document["wings"]["main_wing"]["x_secs"][0]["spare_list"]
        assert spar["section"] == {
            "shape": "tube",
            "outer_diameter": pytest.approx(0.016),
            "wall_thickness": pytest.approx(0.001),
        }
        assert spar["material"] == "Carbon tube"

    def test_the_document_validates_against_the_published_json_schema(self, session):
        plane = seed_integration_aeroplane(session)
        add_spar(session, TUBE_MM, "Carbon tube")
        document = geometry_document(plane, session)
        schema = json.loads(SCHEMA.read_text(encoding="utf-8"))
        spar = document["wings"]["main_wing"]["x_secs"][0]["spare_list"][0]
        spar_schema = {"$ref": "#/$defs/SpareDetail", "$defs": schema["$defs"]}
        jsonschema.validate(spar, spar_schema)

    def test_a_spar_without_section_has_neither_key(self, session):
        plane = seed_integration_aeroplane(session)
        add_spar(session, None, None)
        (spar,) = geometry_document(plane, session)["wings"]["main_wing"]["x_secs"][0]["spare_list"]
        assert "section" not in spar and "material" not in spar

    def test_the_round_trip_db_document_db_keeps_section_and_material(self, session):
        plane = seed_integration_aeroplane(session)
        add_spar(session, TUBE_MM, "Carbon tube")
        document = geometry_document(plane, session)
        spar = document["wings"]["main_wing"]["x_secs"][0]["spare_list"][0]
        # import path: the document's metre schema converts to mm for storage
        stored = _convert_spare_to_mm(schemas.SpareDetailSchema.model_validate(spar))
        row = WingXSecSpareModel(sort_index=1, **stored.model_dump())
        assert row.section == TUBE_MM
        assert row.material == "Carbon tube"

    def test_the_kernel_parses_the_section_and_the_material(self, session):
        plane = seed_integration_aeroplane(session)
        add_spar(session, TUBE_MM, "Carbon tube")
        aircraft = stored_aircraft_input(session, plane.uuid, {})
        (spar,) = aircraft.airplane.wings["main_wing"].x_secs[0].spare_list
        assert spar.section.outer_diameter == pytest.approx(0.016)
        assert spar.material == "Carbon tube"


class TestClone:
    def test_a_cloned_aeroplane_keeps_the_section_and_the_material(self, session):
        plane = seed_integration_aeroplane(session)
        add_spar(session, TUBE_MM, "Carbon tube")
        copy_ = clone_aeroplane_subgraph(
            session, plane, immutable=True, branch_id=None, predecessor_id=plane.id, root_id=None
        )
        session.commit()
        rows = (
            session.query(WingXSecSpareModel)
            .filter(WingXSecSpareModel.material == "Carbon tube")
            .all()
        )
        assert len(rows) == 2
        assert all(r.section == TUBE_MM for r in rows)
        assert copy_ is not None


class TestMaterialsTable:
    def test_the_published_strength_goes_in_pascal_with_source_and_basis(self, session):
        add_material(
            session,
            "Birch",
            {
                "bending_strength_mpa": 114.0,
                "bending_strength_basis": "mean",
                "bending_strength_source": "Wood Handbook Table 5-3a",
                "allowable_bending_stress_mpa": 30.0,
            },
        )
        table = materials_table(session, ["Birch"])
        assert table["Birch"] == {
            "name": "Birch",
            "bending_strength_pa": pytest.approx(114.0e6),
            "source": "Wood Handbook Table 5-3a [mean]",
        }

    def test_the_allowable_is_never_passed_as_a_strength(self, session):
        add_material(session, "Pine", {"allowable_bending_stress_mpa": 39.0, "density_kg_m3": 500})
        assert materials_table(session, ["Pine"]) == {"Pine": {"name": "Pine"}}

    def test_a_source_without_basis_is_passed_as_written(self, session):
        add_material(
            session, "X", {"bending_strength_mpa": 10.0, "bending_strength_source": "a data sheet"}
        )
        assert materials_table(session, ["X"])["X"]["source"] == "a data sheet"

    def test_an_unknown_material_is_left_out(self, session):
        assert materials_table(session, ["Nothing"]) == {}

    def test_an_ambiguous_name_is_refused(self, session):
        add_material(session, "Twin", {"bending_strength_mpa": 10.0}, manufacturer="A")
        add_material(session, "Twin", {"bending_strength_mpa": 20.0}, manufacturer="B")
        with pytest.raises(ValidationError):
            materials_table(session, ["Twin"])

    def test_only_materials_a_spar_names_are_pushed(self, session):
        plane = seed_integration_aeroplane(session)
        add_material(session, "Carbon tube", {"bending_strength_mpa": 1370.0})
        add_material(session, "Unused", {"bending_strength_mpa": 5.0})
        add_spar(session, TUBE_MM, "Carbon tube")
        document = geometry_document(plane, session)
        assert spar_material_names(document) == ["Carbon tube"]
        components = components_document(session, document)
        assert components["schema_version"] == 3
        assert list(components["materials"]) == ["Carbon tube"]

    def test_without_a_named_material_no_components_are_pushed(self, session):
        plane = seed_integration_aeroplane(session)
        add_spar(session, TUBE_MM, None)
        assert components_document(session, geometry_document(plane, session)) is None

    def test_the_kernel_receives_the_materials(self, session):
        plane = seed_integration_aeroplane(session)
        add_material(
            session,
            "Carbon tube",
            {"bending_strength_mpa": 1370.0, "bending_strength_source": "sheet"},
        )
        add_spar(session, TUBE_MM, "Carbon tube")
        aircraft = stored_aircraft_input(session, plane.uuid, {})
        material = aircraft.components.materials["Carbon tube"]
        assert material.bending_strength_pa == pytest.approx(1.37e9)
        assert material.source == "sheet"

    def test_a_material_without_strength_reaches_the_kernel_without_one(self, session):
        plane = seed_integration_aeroplane(session)
        add_material(session, "Pine", {"allowable_bending_stress_mpa": 39.0})
        add_spar(session, TUBE_MM, "Pine")
        material = stored_aircraft_input(session, plane.uuid, {}).components.materials["Pine"]
        assert material.bending_strength_pa is None


class TestSnapshot:
    def records(self) -> list[dict]:
        return json.loads(SNAPSHOT.read_text(encoding="utf-8"))

    def test_every_committed_record_is_valid(self):
        records = self.records()
        assert records
        assert [validate_structural_material_record(r) for r in records] == [None] * len(records)

    def test_every_strength_cites_a_source_and_a_basis(self):
        for record in self.records():
            specs = record["specs"]
            assert specs["bending_strength_source"] and specs["bending_strength_basis"]
            assert "allowable_bending_stress_mpa" not in specs

    def test_the_wood_values_are_the_handbook_values_in_mpa(self):
        by_name = {r["name"]: r["specs"]["bending_strength_mpa"] for r in self.records()}
        assert by_name["Birch, yellow (Betula alleghaniensis)"] == 114.0
        assert by_name["Obeche (Triplochiton scleroxylon)"] == 51.0
        assert by_name["Balsa (Ochroma pyramidale)"] == 21.6

    def test_names_are_unique(self):
        names = [r["name"] for r in self.records()]
        assert len(names) == len(set(names))

    def test_the_snapshot_imports_and_reimport_is_idempotent(self, session):
        from app.services.cots_import import import_snapshot

        records = self.records()
        assert import_snapshot(session, records).imported == len(records)
        session.commit()
        assert import_snapshot(session, records).skipped == len(records)

    @pytest.mark.parametrize(
        ("change", "message"),
        [
            ({"bending_strength_mpa": "114"}, "must be a number"),
            ({"bending_strength_mpa": 0.5}, "typo-guard"),
            ({"bending_strength_source": ""}, "bending_strength_source"),
            ({"bending_strength_basis": None}, "bending_strength_basis"),
            ({"allowable_bending_stress_mpa": 30.0}, "allowable"),
        ],
    )
    def test_a_bad_record_is_refused(self, change, message):
        record = copy.deepcopy(self.records()[0])
        record["specs"].update(change)
        assert message in validate_structural_material_record(record)

    def test_a_record_without_strength_is_fine_and_a_non_material_is_not(self):
        record = {"name": "n", "component_type": "material", "specs": {}}
        assert validate_structural_material_record(record) is None
        record["component_type"] = "servo"
        assert "must be 'material'" in validate_structural_material_record(record)


class TestUncitedProperties:
    def record(self, **specs) -> dict:
        return {"name": "n", "component_type": "material", "specs": specs}

    def test_a_property_without_a_source_is_refused(self):
        error = validate_structural_material_record(self.record(density_kg_m3=1500.0))
        assert "density_kg_m3" in error and "no source" in error

    def test_a_property_with_a_sibling_source_is_accepted(self):
        record = self.record(density_kg_m3=1500.0, density_kg_m3_source="data sheet, 'Density'")
        assert validate_structural_material_record(record) is None

    def test_the_committed_records_carry_no_uncited_property(self):
        for record in json.loads(SNAPSHOT.read_text(encoding="utf-8")):
            assert set(record["specs"]) == {
                "bending_strength_mpa",
                "bending_strength_basis",
                "bending_strength_source",
            }
