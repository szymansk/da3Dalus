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

    def test_derived_xyz_matches_persisted_xsecs(self, client_and_db):
        """The derived absolute block must equal the PERSISTED cross-section
        positions (what the 3D viewer / ASB consume) — including dihedral.

        gh-958 review: the original hand-rolled LE walk diverged from the
        canonical geometry on any wing with dihedral (ignored root dihedral +
        off-by-one). Reading the persisted xsecs eliminates the divergence.
        """
        from app.models.aeroplanemodel import AeroplaneModel

        db = _make_session(client_and_db)
        plane = _plane_with_wing(db)
        node = db.query(AeroplaneModel).filter(AeroplaneModel.id == plane.id).first()
        wing_model = next(w for w in node.wings if w.name == "main_wing")

        res = copilot_tools.execute("get_wing_geometry", db, plane.id, wing="main_wing")
        ps = res["derived"]["per_station"]
        assert len(ps) == len(wing_model.x_secs)
        for st, xs in zip(ps, wing_model.x_secs, strict=True):
            for got, persisted in zip(st["xyz_le_mm"], xs.xyz_le, strict=True):
                assert got == pytest.approx(float(persisted) * 1000.0, abs=1e-2)
        # the fixture carries dihedral, so z must be non-trivial somewhere —
        # this is the case the old hand-walk got wrong.
        assert any(abs(st["xyz_le_mm"][2]) > 0.1 for st in ps), (
            "fixture should exercise dihedral (non-zero z) to cover the regression"
        )

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


_RECOMPUTE = "app.services.assumption_compute_service.recompute_assumptions"


class TestSetSegment:
    def _proposal(self, db, plane):
        from app.models.aeroplanemodel import AeroplaneModel
        from app.services.copilot_apply_service import get_or_open_proposal

        branch = get_or_open_proposal(db, plane.id)
        db.commit()
        node = db.query(AeroplaneModel).filter(AeroplaneModel.id == branch.head_id).first()
        return branch, node

    def test_relative_edit_applies_on_proposal(self, client_and_db):
        from unittest.mock import patch

        from app.schemas.copilot_edits import SetSegment
        from app.services.copilot_apply_service import apply_edits

        db = _make_session(client_and_db)
        plane = _plane_with_wing(db)
        branch, node = self._proposal(db, plane)

        with patch(_RECOMPUTE):
            res = apply_edits(
                db,
                str(node.uuid),
                [SetSegment(wing="main_wing", seg_index=0, incidence_deg=-2.5, sweep_mm=12.0)],
            )
        db.commit()

        assert res["applied"] == ["SetSegment"], res
        assert res["rejected"] == []
        geo = copilot_tools.execute("get_wing_geometry", db, branch.head_id, wing="main_wing")
        assert geo["editable"][0]["incidence_deg"] == pytest.approx(-2.5, abs=0.05)
        assert geo["editable"][0]["sweep_mm"] == pytest.approx(12.0, abs=0.05)

    def test_out_of_range_rejected_not_raised(self, client_and_db):
        from unittest.mock import patch

        from app.schemas.copilot_edits import SetSegment
        from app.services.copilot_apply_service import apply_edits

        db = _make_session(client_and_db)
        plane = _plane_with_wing(db)
        _, node = self._proposal(db, plane)

        with patch(_RECOMPUTE):
            res = apply_edits(
                db, str(node.uuid), [SetSegment(wing="main_wing", seg_index=999, length_mm=50.0)]
            )
        assert res["applied"] == []
        assert res["rejected"] and "out of range" in res["rejected"][0]["error"]

    def test_in_apply_design_edits_schema(self):
        from app.schemas.copilot_edits import edit_ops_array_schema

        schema = edit_ops_array_schema()
        blob = str(schema)
        assert "SetSegment" in blob and "dihedral_rel_deg" in blob
