"""Tests for gh-1009 COTS re-import idempotency with the new ESC schema.

Verifies that the updated dpower.json AVICON/Antares ESC records carry the
new bec_voltage_* toggles, cells_nixx_*, and bec_current_a fields, and that
re-import is idempotent.
"""

from __future__ import annotations

import pytest
from sqlalchemy import create_engine
from sqlalchemy.orm import Session, sessionmaker
from sqlalchemy.pool import StaticPool

from app.db.base import Base
from app.models.component import ComponentModel
from app.services.cots_import import ImportResult, import_snapshot


# ──────────────────────────────────────────────────────────────────────────────
# In-memory DB fixture
# ──────────────────────────────────────────────────────────────────────────────


@pytest.fixture()
def session() -> Session:
    """Fresh in-memory SQLite session per test."""
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


# ──────────────────────────────────────────────────────────────────────────────
# Updated AVICON/Antares test records (post-gh1009 shape)
# ──────────────────────────────────────────────────────────────────────────────

AVICON_20A = {
    "manufacturer": "D-Power",
    "name": "AVICON 20A",
    "component_type": "esc",
    "mass_g": 25,
    "bbox_x_mm": 60,
    "bbox_y_mm": 25,
    "bbox_z_mm": 10,
    "model_ref": "dpower/avicon-20a",
    "source_url": "https://www.d-power-modellbau.com/avicon-regler",
    "source_version": "Avicon manual",
    "specs": {
        "continuous_current_a": 20.0,
        "max_current_a": 30.0,
        "cells_lipo_min": 2,
        "cells_lipo_max": 4,
        "cells_nixx_min": 5,
        "cells_nixx_max": 12,
        "bec_voltage_5v": True,
        "bec_voltage_6v": True,
        "bec_current_a": 4,
        "art_no": "DPAC020",
    },
}

ANTARES_85A_OPTO = {
    "manufacturer": "D-Power",
    "name": "Antares 85A OPTO",
    "component_type": "esc",
    "mass_g": 74,
    "bbox_x_mm": 35,
    "bbox_y_mm": 30,
    "bbox_z_mm": 12,
    "model_ref": "dpower/antares-85a-opto",
    "source_url": "https://www.d-power-modellbau.com/antares-regler",
    "source_version": "Antares manual",
    "specs": {
        "continuous_current_a": 85.0,
        "max_current_a": 100.0,
        "cells_lipo_min": 2,
        "cells_lipo_max": 6,
        "protocol": "oneshot",
        "art_no": "DPAN085O",
    },
}

ANTARES_45A_SBEC = {
    "manufacturer": "D-Power",
    "name": "Antares 45A SBEC 5A",
    "component_type": "esc",
    "mass_g": 37,
    "bbox_x_mm": 31,
    "bbox_y_mm": 27,
    "bbox_z_mm": 9,
    "model_ref": "dpower/antares-45a-sbec-5a",
    "source_url": "https://www.d-power-modellbau.com/antares-regler",
    "source_version": "Antares manual",
    "specs": {
        "continuous_current_a": 45.0,
        "max_current_a": 60.0,
        "cells_lipo_min": 2,
        "cells_lipo_max": 6,
        "bec_voltage_5v": True,
        "bec_voltage_5_5v": True,
        "bec_voltage_6v": True,
        "bec_current_a": 5,
        "art_no": "DPAN045S",
    },
}

AVICON_PRO_65A_HV = {
    "manufacturer": "D-Power",
    "name": "AVICON PRO 65A HV",
    "component_type": "esc",
    "mass_g": 55,
    "bbox_x_mm": None,
    "bbox_y_mm": None,
    "bbox_z_mm": None,
    "model_ref": "dpower/avicon-pro-65a-hv",
    "source_url": "https://www.d-power-modellbau.com/avicon-regler",
    "source_version": "Avicon PRO manual",
    "specs": {
        "continuous_current_a": 65.0,
        "max_current_a": 80.0,
        "cells_lipo_min": 3,
        "cells_lipo_max": 14,
        "bec_voltage_5v": True,
        "bec_current_a": 8,
        "art_no": "DPAC065P",
    },
}


class TestCotsEscGh1009:
    def test_avicon_20a_import_sets_bec_voltage_toggles(self, session):
        """AVICON 20A import must store bec_voltage_5v, bec_voltage_6v, bec_current_a,
        cells_nixx_min, cells_nixx_max in specs."""
        result = import_snapshot(session, [AVICON_20A])
        session.commit()

        assert result.imported == 1
        assert result.errors == []

        row = session.query(ComponentModel).filter_by(name="AVICON 20A").first()
        assert row is not None
        assert row.specs.get("bec_voltage_5v") is True
        assert row.specs.get("bec_voltage_6v") is True
        assert row.specs.get("bec_current_a") == 4
        assert row.specs.get("cells_nixx_min") == 5
        assert row.specs.get("cells_nixx_max") == 12

    def test_avicon_20a_reimport_is_idempotent(self, session):
        """Importing AVICON 20A twice: second run must report updated=0, skipped=1."""
        import_snapshot(session, [AVICON_20A])
        session.commit()

        result = import_snapshot(session, [AVICON_20A])
        session.commit()

        assert result.imported == 0
        assert result.updated == 0
        assert result.skipped == 1

    def test_avicon_opto_no_bec_toggles(self, session):
        """Antares 85A OPTO has no BEC — none of the bec_voltage_* keys must be True."""
        result = import_snapshot(session, [ANTARES_85A_OPTO])
        session.commit()

        assert result.imported == 1
        row = session.query(ComponentModel).filter_by(name="Antares 85A OPTO").first()
        assert row is not None
        specs = row.specs
        bec_voltage_keys = [k for k in specs if k.startswith("bec_voltage_")]
        assert all(not specs[k] for k in bec_voltage_keys), (
            f"Expected no true bec_voltage_* keys; got {bec_voltage_keys}"
        )
        assert "bec_current_a" not in specs

    def test_antares_sbec_multi_voltage(self, session):
        """Antares 45A SBEC: bec_voltage_5v, bec_voltage_5_5v, bec_voltage_6v all True,
        bec_current_a=5."""
        result = import_snapshot(session, [ANTARES_45A_SBEC])
        session.commit()

        assert result.imported == 1
        row = session.query(ComponentModel).filter_by(name="Antares 45A SBEC 5A").first()
        assert row.specs.get("bec_voltage_5v") is True
        assert row.specs.get("bec_voltage_5_5v") is True
        assert row.specs.get("bec_voltage_6v") is True
        assert row.specs.get("bec_current_a") == 5

    def test_avicon_pro_hv_only_5v(self, session):
        """AVICON PRO 65A HV: only bec_voltage_5v=True (5V / 8A BEC)."""
        result = import_snapshot(session, [AVICON_PRO_65A_HV])
        session.commit()

        assert result.imported == 1
        row = session.query(ComponentModel).filter_by(name="AVICON PRO 65A HV").first()
        assert row.specs.get("bec_voltage_5v") is True
        assert row.specs.get("bec_voltage_6v") is not True
        assert row.specs.get("bec_current_a") == 8

    def test_esc_record_bbox_preserved(self, session):
        """AVICON 20A: bbox_x_mm=60, bbox_y_mm=25, bbox_z_mm=10 must be set on the row."""
        import_snapshot(session, [AVICON_20A])
        session.commit()

        row = session.query(ComponentModel).filter_by(name="AVICON 20A").first()
        assert row.bbox_x_mm == 60
        assert row.bbox_y_mm == 25
        assert row.bbox_z_mm == 10
