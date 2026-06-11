"""gh-958: copilot geometry tools — get_wing_geometry hybrid read + the
relative/absolute geometry edit-ops.

The wing-representation spike settled the surface: a HYBRID read (editable
relative per-segment fields + a derived ABSOLUTE block) plus relative + absolute
writes, framed by op descriptions. These tests drive that against the real
in-memory DB (no mocks of the geometry path).
"""

from __future__ import annotations

import json
from pathlib import Path

import pytest

from app.schemas.wing import Wing as WingConfigurationSchema
from app.services import copilot_tools
from app.services.aeroplane_service import create_aeroplane
from app.services.wing_service import put_wing_as_wingconfig

_FIXTURE = Path(__file__).parent / "fixtures" / "wingconfig_from_prompt.json"
_WC = json.loads(_FIXTURE.read_text()) if _FIXTURE.exists() else None


def _make_session(client_and_db):
    _, SessionLocal = client_and_db
    return SessionLocal()


def _plane_with_wing(db):
    if _WC is None:
        pytest.skip("wingconfig fixture missing")
    plane = create_aeroplane(db, "geom-tool-plane")
    db.commit()
    db.refresh(plane)
    put_wing_as_wingconfig(
        db,
        str(plane.uuid),
        "main_wing",
        WingConfigurationSchema.model_validate(_WC),
        scale=0.001,
    )
    db.commit()
    db.refresh(plane)
    return plane


class TestGetWingGeometry:
    def test_returns_editable_and_derived_blocks(self, client_and_db):
        db = _make_session(client_and_db)
        plane = _plane_with_wing(db)

        res = copilot_tools.execute("get_wing_geometry", db, plane.id, wing="main_wing")
        assert "error" not in res, res
        assert "editable" in res and "derived" in res

        seg = res["editable"][0]
        for k in (
            "index",
            "chord_tip_mm",
            "length_mm",
            "sweep_mm",
            "dihedral_rel_deg",
            "incidence_deg",
        ):
            assert k in seg, f"missing editable field {k}"

        derived = res["derived"]
        assert "per_station" in derived and "wing_level" in derived
        st = derived["per_station"][0]
        for k in ("xyz_le_mm", "chord_mm", "accumulated_dihedral_deg", "te_x_mm"):
            assert k in st, f"missing derived field {k}"

    def test_te_x_equals_le_x_plus_chord(self, client_and_db):
        db = _make_session(client_and_db)
        plane = _plane_with_wing(db)
        res = copilot_tools.execute("get_wing_geometry", db, plane.id, wing="main_wing")
        for stn in res["derived"]["per_station"]:
            assert stn["te_x_mm"] == pytest.approx(stn["xyz_le_mm"][0] + stn["chord_mm"], abs=1e-3)

    def test_unknown_wing_returns_error(self, client_and_db):
        db = _make_session(client_and_db)
        plane = _plane_with_wing(db)
        res = copilot_tools.execute("get_wing_geometry", db, plane.id, wing="does_not_exist")
        assert "error" in res

    def test_registered_and_in_schemas(self):
        assert "get_wing_geometry" in copilot_tools.TOOL_REGISTRY
        names = [s["function"]["name"] for s in copilot_tools.list_schemas()]
        assert "get_wing_geometry" in names
