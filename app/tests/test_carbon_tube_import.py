"""Tests for gh-1081: carbon-fibre tube stock ingest.

TDD (Iron Law): these tests are written FIRST and drive the implementation.

Coverage:
- validate_spar_tube_record: required fields, physical-bounds guard,
  conical geometry-incomplete flag, role_use filter
- import_snapshot extended to accept 'spar_tube' component_type
- The committed data/cots/carbon_tubes.json snapshot is valid + idempotent
"""

from __future__ import annotations

import json
from pathlib import Path

import pytest
from sqlalchemy import create_engine
from sqlalchemy.orm import Session, sessionmaker
from sqlalchemy.pool import StaticPool

from app.db.base import Base
from app.models.component import ComponentModel
from app.services.cots_import import ImportResult, import_snapshot
from app.services.carbon_tube_import import validate_spar_tube_record

# ---------------------------------------------------------------------------
# In-memory DB fixture
# ---------------------------------------------------------------------------


@pytest.fixture()
def session() -> Session:
    engine = create_engine(
        "sqlite://",
        connect_args={"check_same_thread": False},
        poolclass=StaticPool,
    )
    Base.metadata.create_all(bind=engine)
    SM = sessionmaker(bind=engine, autocommit=False, autoflush=False, class_=Session)
    db = SM()
    yield db
    db.close()


# ---------------------------------------------------------------------------
# Minimal valid tube record (geometry-complete, spar role)
# ---------------------------------------------------------------------------

TUBE_RECORD = {
    "manufacturer": "R&G",
    "name": "R&G CFK Rohr 8/6 1000mm",
    "component_type": "spar_tube",
    "source_url": "https://www.r-g.de/artikel/100232",
    "source_version": "R&G web catalogue 2024-11",
    "specs": {
        "outer_d_mm": 8.0,
        "inner_d_mm": 6.0,
        "wall_mm": 1.0,
        "length_mm": [1000],
        "fiber_orientation": "0/90",
        "vf_percent": 55,
        "role_use": "spar",
        "geometry_complete": True,
        "density_kg_m3": 1550.0,
        "allowable_bending_stress_mpa": 250.0,
        "youngs_modulus_gpa": 50.0,
        "sigma_allow_sf": 2.5,
        "sigma_allow_basis": "R&G datasheet R_m=625 MPa, SF=2.5",
        "e_basis": "R&G datasheet, woven 0/90 laminate",
        "torsion_suitable": True,
    },
}

PUSHROD_RECORD = {
    "manufacturer": "DPP",
    "name": "DPP Pultruded Rod 2mm",
    "component_type": "spar_tube",
    "source_url": "https://example.com/dpp",
    "source_version": "DPP 2024",
    "specs": {
        "outer_d_mm": 2.0,
        "inner_d_mm": 0.0,
        "wall_mm": None,
        "length_mm": [330],
        "fiber_orientation": "UD-axial",
        "vf_percent": 60,
        "role_use": "pushrod",
        "geometry_complete": True,
        "density_kg_m3": 1580.0,
        "allowable_bending_stress_mpa": 500.0,
        "youngs_modulus_gpa": 125.0,
        "sigma_allow_sf": 2.0,
        "sigma_allow_basis": "DPP datasheet estimate",
        "e_basis": "DPP datasheet",
        "torsion_suitable": False,
    },
}

CONICAL_RECORD = {
    "manufacturer": "R&G",
    "name": "R&G CFK Konus 5-10mm",
    "component_type": "spar_tube",
    "source_url": "https://www.r-g.de/artikel/100240",
    "source_version": "R&G web catalogue 2024-11",
    "specs": {
        "outer_d_mm": None,  # conical — geometry varies along length
        "inner_d_mm": None,
        "wall_mm": None,
        "length_mm": [1000],
        "fiber_orientation": "0/90",
        "vf_percent": 55,
        "role_use": "boom",
        "geometry_complete": False,  # conical → cannot compute I/σ
        "density_kg_m3": 1550.0,
        "allowable_bending_stress_mpa": None,  # not sizing-usable
        "youngs_modulus_gpa": None,
        "sigma_allow_sf": None,
        "sigma_allow_basis": "geometry-incomplete: conical, no uniform wall",
        "e_basis": None,
        "torsion_suitable": None,
    },
}


# ---------------------------------------------------------------------------
# validate_spar_tube_record
# ---------------------------------------------------------------------------


class TestValidateSparTubeRecord:
    def test_valid_tube_returns_none(self):
        assert validate_spar_tube_record(TUBE_RECORD) is None

    def test_valid_conical_incomplete_returns_none(self):
        """Conical tubes are valid records — just geometry_complete=False."""
        assert validate_spar_tube_record(CONICAL_RECORD) is None

    def test_missing_fiber_orientation_is_error(self):
        bad = {**TUBE_RECORD, "specs": {**TUBE_RECORD["specs"], "fiber_orientation": None}}
        err = validate_spar_tube_record(bad)
        assert err is not None
        assert "fiber_orientation" in err

    def test_missing_role_use_is_error(self):
        bad = {**TUBE_RECORD, "specs": {**TUBE_RECORD["specs"], "role_use": None}}
        err = validate_spar_tube_record(bad)
        assert err is not None
        assert "role_use" in err

    def test_invalid_role_use_is_error(self):
        bad = {**TUBE_RECORD, "specs": {**TUBE_RECORD["specs"], "role_use": "turbine_blade"}}
        err = validate_spar_tube_record(bad)
        assert err is not None
        assert "role_use" in err

    def test_sigma_allow_above_upper_bound_is_error(self):
        """Physical-bounds guard: σ_allow > 1500 MPa is outside valid range."""
        bad = {
            **TUBE_RECORD,
            "specs": {**TUBE_RECORD["specs"], "allowable_bending_stress_mpa": 2000.0},
        }
        err = validate_spar_tube_record(bad)
        assert err is not None
        assert "allowable_bending_stress_mpa" in err

    def test_sigma_allow_below_lower_bound_is_error(self):
        bad = {
            **TUBE_RECORD,
            "specs": {**TUBE_RECORD["specs"], "allowable_bending_stress_mpa": 5.0},
        }
        err = validate_spar_tube_record(bad)
        assert err is not None
        assert "allowable_bending_stress_mpa" in err

    def test_e_above_upper_bound_is_error(self):
        """E > 250 GPa is outside valid CF range."""
        bad = {**TUBE_RECORD, "specs": {**TUBE_RECORD["specs"], "youngs_modulus_gpa": 300.0}}
        err = validate_spar_tube_record(bad)
        assert err is not None
        assert "youngs_modulus_gpa" in err

    def test_density_above_upper_bound_is_error(self):
        bad = {**TUBE_RECORD, "specs": {**TUBE_RECORD["specs"], "density_kg_m3": 3500.0}}
        err = validate_spar_tube_record(bad)
        assert err is not None
        assert "density_kg_m3" in err

    def test_density_below_lower_bound_is_error(self):
        bad = {**TUBE_RECORD, "specs": {**TUBE_RECORD["specs"], "density_kg_m3": 50.0}}
        err = validate_spar_tube_record(bad)
        assert err is not None
        assert "density_kg_m3" in err

    def test_geometry_complete_false_allows_none_dimensions(self):
        """geometry_complete=False → outer_d_mm/inner_d_mm/wall_mm may all be None."""
        assert validate_spar_tube_record(CONICAL_RECORD) is None

    def test_geometry_complete_true_requires_outer_d(self):
        """geometry_complete=True + outer_d_mm=None is an error."""
        bad = {
            **TUBE_RECORD,
            "specs": {**TUBE_RECORD["specs"], "geometry_complete": True, "outer_d_mm": None},
        }
        err = validate_spar_tube_record(bad)
        assert err is not None
        assert "outer_d_mm" in err

    def test_sigma_allow_none_allowed_for_geometry_incomplete(self):
        """Conical records may have σ_allow=None — not sizing-usable."""
        assert validate_spar_tube_record(CONICAL_RECORD) is None

    def test_missing_sigma_allow_basis_is_error_for_complete_geometry(self):
        """Provenance required for geometry-complete spar tubes."""
        bad = {**TUBE_RECORD, "specs": {**TUBE_RECORD["specs"], "sigma_allow_basis": None}}
        err = validate_spar_tube_record(bad)
        assert err is not None
        assert "sigma_allow_basis" in err


# ---------------------------------------------------------------------------
# import_snapshot accepts spar_tube component_type
# ---------------------------------------------------------------------------


class TestImportSnapshotAcceptsSparTube:
    def test_spar_tube_imported(self, session):
        result = import_snapshot(session, [TUBE_RECORD])
        session.commit()

        assert result.imported == 1
        assert result.errors == []
        row = session.query(ComponentModel).filter_by(name="R&G CFK Rohr 8/6 1000mm").first()
        assert row is not None
        assert row.component_type == "spar_tube"
        assert row.specs["outer_d_mm"] == 8.0
        assert row.specs["fiber_orientation"] == "0/90"
        assert row.specs["role_use"] == "spar"
        assert row.specs["geometry_complete"] is True
        assert row.specs["sigma_allow_basis"] is not None

    def test_conical_tube_imported_as_geometry_incomplete(self, session):
        result = import_snapshot(session, [CONICAL_RECORD])
        session.commit()

        assert result.imported == 1
        assert result.errors == []
        row = session.query(ComponentModel).filter_by(name="R&G CFK Konus 5-10mm").first()
        assert row is not None
        assert row.specs["geometry_complete"] is False
        # cots_import omits None values from specs; absent key behaves as None
        assert row.specs.get("allowable_bending_stress_mpa") is None

    def test_pushrod_imported_with_pushrod_role(self, session):
        result = import_snapshot(session, [PUSHROD_RECORD])
        session.commit()

        assert result.imported == 1
        assert result.errors == []
        row = session.query(ComponentModel).filter_by(name="DPP Pultruded Rod 2mm").first()
        assert row.specs["role_use"] == "pushrod"

    def test_idempotent_upsert_no_duplicates(self, session):
        import_snapshot(session, [TUBE_RECORD])
        session.commit()
        result2 = import_snapshot(session, [TUBE_RECORD])
        session.commit()

        assert result2.skipped == 1
        assert result2.imported == 0
        assert session.query(ComponentModel).count() == 1

    def test_spar_only_query_excludes_pushrods_and_booms(self, session):
        """role_use filter: spar-snapping (#1080) must see only role_use='spar'."""
        import_snapshot(session, [TUBE_RECORD, PUSHROD_RECORD, CONICAL_RECORD])
        session.commit()

        spar_only = (
            session.query(ComponentModel).filter(ComponentModel.component_type == "spar_tube").all()
        )
        spar_roles = [r.specs.get("role_use") for r in spar_only]
        spar_eligible = [r for r in spar_only if r.specs.get("role_use") == "spar"]
        # tube is spar; pushrod and conical boom are not
        assert len(spar_eligible) == 1
        assert "pushrod" in spar_roles
        assert "boom" in spar_roles


# ---------------------------------------------------------------------------
# Committed carbon_tubes.json snapshot guard
# ---------------------------------------------------------------------------


class TestCommittedCarbonTubesSnapshot:
    def _load(self) -> list[dict]:
        repo_root = Path(__file__).resolve().parents[2]
        path = repo_root / "data" / "cots" / "carbon_tubes.json"
        return json.loads(path.read_text(encoding="utf-8"))

    def test_snapshot_exists_and_has_records(self):
        records = self._load()
        assert len(records) >= 5, "Expected at least 5 tubes in the snapshot"

    def test_all_records_pass_validation(self):
        records = self._load()
        for rec in records:
            assert rec.get("component_type") == "spar_tube", f"Wrong type: {rec.get('name')}"
            err = validate_spar_tube_record(rec)
            assert err is None, f"{rec.get('name')}: {err}"

    def test_snapshot_imports_cleanly(self, session):
        records = self._load()
        result = import_snapshot(session, records)
        session.commit()
        assert result.imported == len(records)
        assert not result.errors

    def test_snapshot_is_idempotent(self, session):
        records = self._load()
        import_snapshot(session, records)
        session.commit()
        result2 = import_snapshot(session, records)
        session.commit()
        assert result2.imported == 0
        assert result2.skipped == len(records)
        assert not result2.errors

    def test_at_least_one_spar_eligible_tube(self, session):
        """At least one tube in the snapshot must be spar-eligible (role_use='spar')."""
        records = self._load()
        import_snapshot(session, records)
        session.commit()
        spar_eligible = (
            session.query(ComponentModel).filter(ComponentModel.component_type == "spar_tube").all()
        )
        assert any(r.specs.get("role_use") == "spar" for r in spar_eligible)

    def test_cfrp_densities_in_valid_range(self):
        """All CFRP tube densities must be in [1400, 2000] kg/m³ (Sadraey Table 10.6)."""
        records = self._load()
        for rec in records:
            d = rec["specs"].get("density_kg_m3")
            if d is not None:
                assert 1400 <= d <= 2000, (
                    f"{rec['name']}: density {d} kg/m³ out of CFRP range [1400, 2000]"
                )

    def test_sigma_allow_lte_half_rm_where_stated(self):
        """Where sigma_allow_sf is stated, verify σ_allow ≤ R_m / SF (no SF < 1.5)."""
        records = self._load()
        for rec in records:
            sf = rec["specs"].get("sigma_allow_sf")
            if sf is not None:
                assert sf >= 1.5, f"{rec['name']}: SF={sf} < 1.5 is unconservative"
