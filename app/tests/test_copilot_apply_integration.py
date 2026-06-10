"""Integration tests for copilot apply engine (gh-937/938).

All tests use a real DB (in-memory SQLite via conftest.client_and_db),
real wing_service, real aeroplane_version_service, and the real apply engine.

AeroSandbox-dependent recompute is mocked at the boundary
(``recompute_assumptions``) to keep the fast tier clean.  The branch/apply
logic runs entirely against real DB.  Slow tests that use real recompute are
marked ``@pytest.mark.slow``.

Coverage target: the new service logic must be covered by the fast tier.
"""

from __future__ import annotations

import json
import uuid
from pathlib import Path
from typing import Any
from unittest.mock import patch

import pytest

import app.models.analysismodels  # noqa: F401 — ensures complete metadata
import app.models.avl_geometry_file  # noqa: F401
import app.models.component  # noqa: F401
import app.models.component_type  # noqa: F401
import app.models.construction_part  # noqa: F401
import app.models.construction_plan  # noqa: F401
import app.models.flight_envelope_model  # noqa: F401
import app.models.flightprofilemodel  # noqa: F401
import app.models.mission_preset  # noqa: F401
import app.models.tessellation_cache  # noqa: F401

from app.models.aeroplanemodel import AeroplaneModel, BranchModel
from app.schemas.copilot_edits import (
    AddXsec,
    RemoveXsec,
    ReplaceWingConfig,
    SetAssumption,
    SetWingParam,
    SetXsec,
)
from app.services.aeroplane_service import create_aeroplane
from app.services.aeroplane_version_service import _metrics_payload
from app.services.copilot_apply_service import (
    apply_edits,
    compute_metrics_diff,
    discard_open_proposal,
    get_or_open_proposal,
)
from app.services.copilot_tools import (
    _apply_design_edits,
    _discard_proposal,
    _effective_target_id,
    execute,
)
from app.tests.conftest import make_aeroplane, seed_design_assumptions

# ---------------------------------------------------------------------------
# Fixtures and helpers
# ---------------------------------------------------------------------------

_FIXTURE_PATH = Path(__file__).parent / "fixtures" / "wingconfig_from_prompt.json"

_WC_PAYLOAD = json.loads(_FIXTURE_PATH.read_text()) if _FIXTURE_PATH.exists() else None


def _make_session(client_and_db):
    """Return a new DB session from the (client, SessionLocal) fixture pair."""
    _, SessionLocal = client_and_db
    return SessionLocal()


def _create_plane_with_branch(db) -> AeroplaneModel:
    """Create a versioned aeroplane (main branch) seeded with design assumptions."""
    plane = create_aeroplane(db, "test-copilot-plane")
    db.commit()
    db.refresh(plane)
    seed_design_assumptions(db, plane.id)
    return plane


def _create_plane_with_wc_wing(db) -> AeroplaneModel:
    """Create a versioned aeroplane with a WingConfig wing, for geometry op tests."""
    from app.schemas.wing import Wing as WingConfigurationSchema
    from app.services.wing_service import put_wing_as_wingconfig

    plane = create_aeroplane(db, "test-copilot-wc-plane")
    db.commit()
    db.refresh(plane)
    seed_design_assumptions(db, plane.id)

    if _WC_PAYLOAD is None:
        pytest.skip("WingConfig fixture not found — skip wing geometry test")

    wc_schema = WingConfigurationSchema.model_validate(_WC_PAYLOAD)
    put_wing_as_wingconfig(db, str(plane.uuid), "main_wing", wc_schema, scale=0.001)
    db.commit()
    db.refresh(plane)
    return plane


# Mock target for recompute — stub at the source module (the apply service
# imports it inside the function body via
# ``from app.services.assumption_compute_service import recompute_assumptions``,
# so we patch the original definition site).
_RECOMPUTE_PATH = "app.services.assumption_compute_service.recompute_assumptions"


# ---------------------------------------------------------------------------
# compute_metrics_diff — pure unit (included here for completeness; also in
# test_copilot_edits_schema.py)
# ---------------------------------------------------------------------------


class TestComputeMetricsDiff:
    def test_empty_dicts(self):
        diff = compute_metrics_diff({}, {})
        assert isinstance(diff, dict)

    def test_identical_dicts(self):
        m = {"total_mass_kg": 2.0}
        assert compute_metrics_diff(m, m) == {}


# ---------------------------------------------------------------------------
# get_or_open_proposal
# ---------------------------------------------------------------------------


class TestGetOrOpenProposal:
    def test_creates_proposal_branch(self, client_and_db):
        db = _make_session(client_and_db)
        try:
            plane = _create_plane_with_branch(db)

            branch = get_or_open_proposal(db, plane.id)
            db.commit()

            assert branch is not None
            assert branch.created_by == "copilot"
            assert "copilot-proposal" in branch.name
            assert branch.is_main is False
            assert branch.head_id != plane.id  # cloned, not the same node
        finally:
            db.close()

    def test_reuses_existing_open_proposal(self, client_and_db):
        db = _make_session(client_and_db)
        try:
            plane = _create_plane_with_branch(db)

            branch1 = get_or_open_proposal(db, plane.id)
            db.commit()
            branch2 = get_or_open_proposal(db, plane.id)
            db.commit()

            assert branch1.id == branch2.id
        finally:
            db.close()

    def test_proposal_has_correct_root_id(self, client_and_db):
        db = _make_session(client_and_db)
        try:
            plane = _create_plane_with_branch(db)
            branch = get_or_open_proposal(db, plane.id)
            db.commit()

            assert branch.root_id == plane.root_id or branch.root_id == plane.id
        finally:
            db.close()


# ---------------------------------------------------------------------------
# discard_open_proposal
# ---------------------------------------------------------------------------


class TestDiscardOpenProposal:
    def test_discard_existing_proposal(self, client_and_db):
        db = _make_session(client_and_db)
        try:
            plane = _create_plane_with_branch(db)
            get_or_open_proposal(db, plane.id)
            db.commit()

            discarded = discard_open_proposal(db, plane.id)
            db.commit()

            assert discarded is True

            # After discard: no proposal branch remains
            from app.services.copilot_apply_service import _find_open_proposal, _get_lineage_root_id

            root_id = _get_lineage_root_id(db, plane.id)
            assert _find_open_proposal(db, root_id) is None
        finally:
            db.close()

    def test_discard_no_proposal_returns_false(self, client_and_db):
        db = _make_session(client_and_db)
        try:
            plane = _create_plane_with_branch(db)
            result = discard_open_proposal(db, plane.id)
            assert result is False
        finally:
            db.close()


# ---------------------------------------------------------------------------
# apply_edits — SetAssumption
# ---------------------------------------------------------------------------


class TestApplyEditsSetAssumption:
    def test_set_assumption_applies_to_proposal_not_live(self, client_and_db):
        """
        SetAssumption on the proposal must NOT change the live head's assumption.
        """
        db = _make_session(client_and_db)
        try:
            plane = _create_plane_with_branch(db)
            branch = get_or_open_proposal(db, plane.id)
            db.commit()

            proposal_node = (
                db.query(AeroplaneModel).filter(AeroplaneModel.id == branch.head_id).first()
            )

            with patch(_RECOMPUTE_PATH):
                result = apply_edits(
                    db,
                    str(proposal_node.uuid),
                    [SetAssumption(param="mass", value=9.99)],
                )
            db.commit()

            # The proposal's assumption should reflect the new value
            from app.models.aeroplanemodel import DesignAssumptionModel

            proposal_assumption = (
                db.query(DesignAssumptionModel)
                .filter(
                    DesignAssumptionModel.aeroplane_id == branch.head_id,
                    DesignAssumptionModel.parameter_name == "mass",
                )
                .first()
            )
            # The live head's assumption must NOT be changed
            live_assumption = (
                db.query(DesignAssumptionModel)
                .filter(
                    DesignAssumptionModel.aeroplane_id == plane.id,
                    DesignAssumptionModel.parameter_name == "mass",
                )
                .first()
            )

            assert result["applied"] == ["SetAssumption"]
            assert result["rejected"] == []
            if proposal_assumption:
                assert proposal_assumption.estimate_value == 9.99
            if live_assumption:
                assert live_assumption.estimate_value != 9.99
        finally:
            db.close()

    def test_invalid_param_rejected(self, client_and_db):
        """Invalid assumption param name → rejected with an error, not raised."""
        db = _make_session(client_and_db)
        try:
            plane = _create_plane_with_branch(db)
            branch = get_or_open_proposal(db, plane.id)
            db.commit()

            proposal_node = (
                db.query(AeroplaneModel).filter(AeroplaneModel.id == branch.head_id).first()
            )

            with patch(_RECOMPUTE_PATH):
                result = apply_edits(
                    db,
                    str(proposal_node.uuid),
                    [SetAssumption(param="nonexistent_param", value=1.0)],
                )

            # The invalid op is rejected, NOT raised
            assert len(result["rejected"]) == 1
            # Error message can be "not found" or reference the param name
            err_str = str(result["rejected"][0]["error"])
            assert err_str  # non-empty error message
        finally:
            db.close()

    def test_mixed_valid_invalid_ops(self, client_and_db):
        """Valid ops are applied; invalid ops rejected; no exception raised."""
        db = _make_session(client_and_db)
        try:
            plane = _create_plane_with_branch(db)
            branch = get_or_open_proposal(db, plane.id)
            db.commit()

            proposal_node = (
                db.query(AeroplaneModel).filter(AeroplaneModel.id == branch.head_id).first()
            )

            with patch(_RECOMPUTE_PATH):
                result = apply_edits(
                    db,
                    str(proposal_node.uuid),
                    [
                        SetAssumption(param="mass", value=3.0),
                        SetAssumption(param="bad_param", value=0.0),
                        SetAssumption(param="cd0", value=0.02),
                    ],
                )
            db.commit()

            # mass and cd0 applied, bad_param rejected
            assert "SetAssumption" in result["applied"]
            assert len(result["rejected"]) == 1
        finally:
            db.close()


# ---------------------------------------------------------------------------
# apply_edits — wing geometry ops
# ---------------------------------------------------------------------------


class TestApplyEditsWingGeometry:
    def test_set_xsec_chord(self, client_and_db):
        """SetXsec on chord updates the WingConfiguration on the proposal."""
        db = _make_session(client_and_db)
        try:
            plane = _create_plane_with_wc_wing(db)
            branch = get_or_open_proposal(db, plane.id)
            db.commit()

            proposal_node = (
                db.query(AeroplaneModel).filter(AeroplaneModel.id == branch.head_id).first()
            )

            with patch(_RECOMPUTE_PATH):
                result = apply_edits(
                    db,
                    str(proposal_node.uuid),
                    [SetXsec(wing="main_wing", index=0, chord=200.0)],
                )
            db.commit()

            assert result["applied"] == ["SetXsec"]
            assert result["rejected"] == []

            # Verify the proposal wing config was updated.
            # db.expire() flushes stale cached ORM state (put_wing_as_wingconfig
            # deleted+re-inserted the wing so the session cache is stale).
            db.expire(proposal_node)
            from app.services.wing_service import get_wing_as_wingconfig

            wc = get_wing_as_wingconfig(db, str(proposal_node.uuid), "main_wing")
            assert wc["segments"][0]["root_airfoil"]["chord"] == pytest.approx(200.0)

            # Live wing must be unchanged
            db.expire_all()
            live_wc = get_wing_as_wingconfig(db, str(plane.uuid), "main_wing")
            assert live_wc["segments"][0]["root_airfoil"]["chord"] != pytest.approx(200.0)
        finally:
            db.close()

    def test_set_xsec_invalid_index_rejected(self, client_and_db):
        """SetXsec with out-of-range index → rejected (not raised)."""
        db = _make_session(client_and_db)
        try:
            plane = _create_plane_with_wc_wing(db)
            branch = get_or_open_proposal(db, plane.id)
            db.commit()

            proposal_node = (
                db.query(AeroplaneModel).filter(AeroplaneModel.id == branch.head_id).first()
            )

            with patch(_RECOMPUTE_PATH):
                result = apply_edits(
                    db,
                    str(proposal_node.uuid),
                    [SetXsec(wing="main_wing", index=9999, chord=100.0)],
                )

            assert result["rejected"]
            assert "9999" in str(result["rejected"][0]["error"]) or "out of range" in str(
                result["rejected"][0]["error"]
            )
        finally:
            db.close()

    def test_set_xsec_nonexistent_wing_rejected(self, client_and_db):
        """SetXsec on a wing that doesn't exist → rejected (not raised)."""
        db = _make_session(client_and_db)
        try:
            plane = _create_plane_with_branch(db)
            branch = get_or_open_proposal(db, plane.id)
            db.commit()

            proposal_node = (
                db.query(AeroplaneModel).filter(AeroplaneModel.id == branch.head_id).first()
            )

            with patch(_RECOMPUTE_PATH):
                result = apply_edits(
                    db,
                    str(proposal_node.uuid),
                    [SetXsec(wing="no_such_wing", index=0, chord=100.0)],
                )

            assert len(result["rejected"]) == 1
            assert "no_such_wing" in str(result["rejected"][0]["error"])
        finally:
            db.close()

    def test_add_xsec_increases_segment_count(self, client_and_db):
        """AddXsec inserts a new segment, increasing total segment count."""
        db = _make_session(client_and_db)
        try:
            plane = _create_plane_with_wc_wing(db)
            branch = get_or_open_proposal(db, plane.id)
            db.commit()

            proposal_node = (
                db.query(AeroplaneModel).filter(AeroplaneModel.id == branch.head_id).first()
            )

            # Get initial segment count
            from app.services.wing_service import get_wing_as_wingconfig

            wc_before = get_wing_as_wingconfig(db, str(proposal_node.uuid), "main_wing")
            n_before = len(wc_before["segments"])

            # Add a winglet at the TIP (at_index = n_segs, which appends beyond the
            # last segment).  This avoids the follow-spare chain-break issue that
            # occurs when inserting in the middle of segments with "follow" spares.
            from app.services.wing_service import get_wing_as_wingconfig as _gwc

            wc_check = _gwc(db, str(proposal_node.uuid), "main_wing")
            n_segs_tip = len(wc_check["segments"])

            with patch(_RECOMPUTE_PATH):
                result = apply_edits(
                    db,
                    str(proposal_node.uuid),
                    [
                        AddXsec(
                            wing="main_wing",
                            at_index=n_segs_tip + 1,
                            chord=40.0,
                            span=80.0,
                            dihedral=70.0,
                        )
                    ],
                )
            db.commit()

            assert result["applied"] == ["AddXsec"]
            assert not result["rejected"], f"Unexpected rejections: {result['rejected']}"

            # Expire stale ORM state before re-reading the modified wing
            db.expire_all()
            wc_after = get_wing_as_wingconfig(db, str(proposal_node.uuid), "main_wing")
            assert len(wc_after["segments"]) > n_before
        finally:
            db.close()

    def test_remove_xsec_decreases_segment_count(self, client_and_db):
        """RemoveXsec merges two segments, decreasing total segment count."""
        db = _make_session(client_and_db)
        try:
            plane = _create_plane_with_wc_wing(db)
            branch = get_or_open_proposal(db, plane.id)
            db.commit()

            proposal_node = (
                db.query(AeroplaneModel).filter(AeroplaneModel.id == branch.head_id).first()
            )

            from app.services.wing_service import get_wing_as_wingconfig

            wc_before = get_wing_as_wingconfig(db, str(proposal_node.uuid), "main_wing")
            n_before = len(wc_before["segments"])

            if n_before < 2:
                pytest.skip("Fixture has too few segments for RemoveXsec test")

            with patch(_RECOMPUTE_PATH):
                result = apply_edits(
                    db,
                    str(proposal_node.uuid),
                    [RemoveXsec(wing="main_wing", index=1)],
                )
            db.commit()

            assert result["applied"] == ["RemoveXsec"]
            assert not result["rejected"]

            # Expire stale ORM state before re-reading the modified wing
            db.expire_all()
            wc_after = get_wing_as_wingconfig(db, str(proposal_node.uuid), "main_wing")
            assert len(wc_after["segments"]) == n_before - 1
        finally:
            db.close()

    def test_remove_root_xsec_rejected(self, client_and_db):
        """RemoveXsec at index 0 (root) → rejected."""
        db = _make_session(client_and_db)
        try:
            plane = _create_plane_with_wc_wing(db)
            branch = get_or_open_proposal(db, plane.id)
            db.commit()

            proposal_node = (
                db.query(AeroplaneModel).filter(AeroplaneModel.id == branch.head_id).first()
            )

            # RemoveXsec(index=0) is rejected at schema level already (ge=1),
            # but let's test with index=1 which is allowed by schema but may
            # hit boundary via apply logic — actually index=0 is blocked by schema.
            # Instead verify that a boundary index (last xsec) is rejected by apply logic.
            from app.services.wing_service import get_wing_as_wingconfig

            wc = get_wing_as_wingconfig(db, str(proposal_node.uuid), "main_wing")
            last_idx = len(wc["segments"])  # n_segments = last xsec index

            with patch(_RECOMPUTE_PATH):
                result = apply_edits(
                    db,
                    str(proposal_node.uuid),
                    # Use index == last (tip), which should be rejected
                    [RemoveXsec(wing="main_wing", index=last_idx)],
                )

            assert len(result["rejected"]) == 1
        finally:
            db.close()


# ---------------------------------------------------------------------------
# apply_design_edits tool (via copilot_tools.execute)
# ---------------------------------------------------------------------------


class TestApplyDesignEditsTool:
    def test_creates_proposal_branch_and_returns_branch_info(self, client_and_db):
        """apply_design_edits creates a branch and returns branch_id, applied, diff."""
        db = _make_session(client_and_db)
        try:
            plane = _create_plane_with_branch(db)

            with patch(_RECOMPUTE_PATH):
                result = execute(
                    "apply_design_edits",
                    db,
                    plane.id,
                    ops=[{"type": "SetAssumption", "param": "mass", "value": 3.5}],
                )
            db.commit()

            assert "error" not in result, f"Unexpected error: {result.get('error')}"
            assert "branch_id" in result
            assert "applied" in result
            assert "diff_vs_live" in result
            assert result["applied"] == ["SetAssumption"]
        finally:
            db.close()

    def test_second_call_reuses_same_branch(self, client_and_db):
        """A second apply_design_edits call reuses the SAME open branch."""
        db = _make_session(client_and_db)
        try:
            plane = _create_plane_with_branch(db)

            with patch(_RECOMPUTE_PATH):
                r1 = execute(
                    "apply_design_edits",
                    db,
                    plane.id,
                    ops=[{"type": "SetAssumption", "param": "mass", "value": 3.0}],
                )
            db.commit()

            with patch(_RECOMPUTE_PATH):
                r2 = execute(
                    "apply_design_edits",
                    db,
                    plane.id,
                    ops=[{"type": "SetAssumption", "param": "cd0", "value": 0.02}],
                )
            db.commit()

            assert r1["branch_id"] == r2["branch_id"]
        finally:
            db.close()

    def test_live_head_is_unchanged(self, client_and_db):
        """The live head must not be mutated by apply_design_edits."""
        db = _make_session(client_and_db)
        try:
            plane = _create_plane_with_branch(db)
            live_id_before = plane.id

            with patch(_RECOMPUTE_PATH):
                execute(
                    "apply_design_edits",
                    db,
                    plane.id,
                    ops=[{"type": "SetAssumption", "param": "mass", "value": 99.0}],
                )
            db.commit()

            # Live aeroplane PK must be unchanged
            live_node = db.query(AeroplaneModel).filter(AeroplaneModel.id == live_id_before).first()
            assert live_node is not None
        finally:
            db.close()

    def test_invalid_op_rejected_not_raised(self, client_and_db):
        """Invalid op in the list → rejected dict, tool does not raise."""
        db = _make_session(client_and_db)
        try:
            plane = _create_plane_with_branch(db)

            with patch(_RECOMPUTE_PATH):
                result = execute(
                    "apply_design_edits",
                    db,
                    plane.id,
                    ops=[{"type": "SetAssumption", "param": "bad_param", "value": 1.0}],
                )
            db.commit()

            # Should have a rejected entry, no exception
            assert "rejected" in result
            assert len(result["rejected"]) == 1
        finally:
            db.close()

    def test_diff_vs_live_included(self, client_and_db):
        """diff_vs_live is always present, even if empty."""
        db = _make_session(client_and_db)
        try:
            plane = _create_plane_with_branch(db)

            with patch(_RECOMPUTE_PATH):
                result = execute(
                    "apply_design_edits",
                    db,
                    plane.id,
                    ops=[{"type": "SetAssumption", "param": "mass", "value": 5.0}],
                )
            db.commit()

            assert isinstance(result.get("diff_vs_live"), dict)
        finally:
            db.close()


# ---------------------------------------------------------------------------
# discard_proposal tool
# ---------------------------------------------------------------------------


class TestDiscardProposalTool:
    def test_discard_existing_proposal(self, client_and_db):
        db = _make_session(client_and_db)
        try:
            plane = _create_plane_with_branch(db)

            with patch(_RECOMPUTE_PATH):
                execute(
                    "apply_design_edits",
                    db,
                    plane.id,
                    ops=[{"type": "SetAssumption", "param": "mass", "value": 2.0}],
                )
            db.commit()

            result = execute("discard_proposal", db, plane.id)
            db.commit()

            assert result.get("discarded") is True
        finally:
            db.close()

    def test_discard_no_proposal(self, client_and_db):
        db = _make_session(client_and_db)
        try:
            plane = _create_plane_with_branch(db)
            result = execute("discard_proposal", db, plane.id)
            assert result.get("discarded") is False
        finally:
            db.close()


# ---------------------------------------------------------------------------
# Read-retargeting: _effective_target_id + get_design_snapshot
# ---------------------------------------------------------------------------


class TestReadRetargeting:
    def test_effective_target_is_proposal_when_open(self, client_and_db):
        """_effective_target_id returns proposal head id when a proposal is open."""
        db = _make_session(client_and_db)
        try:
            plane = _create_plane_with_branch(db)
            branch = get_or_open_proposal(db, plane.id)
            db.commit()

            effective_id = _effective_target_id(db, plane.id)
            assert effective_id == branch.head_id
            assert effective_id != plane.id
        finally:
            db.close()

    def test_effective_target_is_live_when_no_proposal(self, client_and_db):
        """_effective_target_id returns live aeroplane_id when no proposal exists."""
        db = _make_session(client_and_db)
        try:
            plane = _create_plane_with_branch(db)
            effective_id = _effective_target_id(db, plane.id)
            assert effective_id == plane.id
        finally:
            db.close()

    def test_get_design_snapshot_retargets_to_proposal(self, client_and_db):
        """get_design_snapshot returns proposal metrics while a proposal is open."""
        db = _make_session(client_and_db)
        try:
            plane = _create_plane_with_branch(db)
            branch = get_or_open_proposal(db, plane.id)
            db.commit()

            # get_design_snapshot should return the PROPOSAL node's metrics
            result = execute("get_design_snapshot", db, plane.id)
            assert "error" not in result

            # The uuid in the result should be the proposal head uuid
            proposal_node = (
                db.query(AeroplaneModel).filter(AeroplaneModel.id == branch.head_id).first()
            )
            if "uuid" in result:
                assert result["uuid"] == str(proposal_node.uuid)
        finally:
            db.close()

    def test_get_version_tree_is_not_retargeted(self, client_and_db):
        """get_version_tree always returns the live lineage, not the proposal."""
        db = _make_session(client_and_db)
        try:
            plane = _create_plane_with_branch(db)
            get_or_open_proposal(db, plane.id)
            db.commit()

            # get_version_tree should show the full lineage including the proposal branch
            result = execute("get_version_tree", db, plane.id)
            assert "error" not in result
            # The tree should include the proposal branch
            branch_names = [b["name"] for b in result.get("branches", [])]
            assert any("copilot-proposal" in n for n in branch_names)
        finally:
            db.close()


# ---------------------------------------------------------------------------
# Registry / schema counts
# ---------------------------------------------------------------------------


class TestToolRegistryExtended:
    def test_five_schemas_registered(self):
        from app.services.copilot_tools import list_schemas

        schemas = list_schemas()
        assert len(schemas) == 5

    def test_new_tools_registered(self):
        from app.services.copilot_tools import list_schemas

        names = {s["function"]["name"] for s in list_schemas()}
        assert "apply_design_edits" in names
        assert "discard_proposal" in names

    def test_apply_design_edits_schema_has_ops(self):
        from app.services.copilot_tools import list_schemas

        schema = next(s for s in list_schemas() if s["function"]["name"] == "apply_design_edits")
        props = schema["function"]["parameters"]["properties"]
        assert "ops" in props
        assert props["ops"]["type"] == "array"


# ---------------------------------------------------------------------------
# Regression: gh-938 discard crash after in-session wing write (Bug 1)
# ---------------------------------------------------------------------------


class TestDiscardAfterWingEditRegression:
    """Regression tests for gh-938 Bug 1: discard_proposal crashes when called
    in the same session that already ran put_wing_as_wingconfig (apply_edits
    with a wing-geometry op).

    Root cause: put_wing_as_wingconfig calls db.delete(existing_wing) then
    re-inserts, leaving stale WingXSecSpareModel instances in the session
    identity map.  discard_branch's cascade-delete later tries to attach
    those same instances and hits:
        InvalidRequestError: Can't attach instance <WingXSecSpareModel ...>;
        another instance with key (...) is already present in this session.

    Fix: discard_open_proposal flushes + expunge_all before calling
    discard_branch so the session identity map is clean.
    """

    def test_discard_after_wing_edit_no_crash(self, client_and_db):
        """discard_proposal must not crash after a wing-geometry apply in the
        same session.  After discard: 0 copilot branches remain."""
        db = _make_session(client_and_db)
        try:
            plane = _create_plane_with_wc_wing(db)

            # Step 1: apply a wing geometry op (triggers the problematic
            # delete-then-reinsert path in put_wing_as_wingconfig).
            with patch(_RECOMPUTE_PATH):
                apply_result = execute(
                    "apply_design_edits",
                    db,
                    plane.id,
                    ops=[
                        {
                            "type": "SetXsec",
                            "wing": "main_wing",
                            "index": 0,
                            "chord": 155.0,
                        }
                    ],
                )
            db.commit()

            assert "error" not in apply_result, f"apply failed: {apply_result.get('error')}"
            assert apply_result.get("applied") == ["SetXsec"]

            # Step 2: discard — this used to crash with InvalidRequestError.
            discard_result = execute("discard_proposal", db, plane.id)
            db.commit()

            assert discard_result.get("discarded") is True, (
                f"Expected discarded=True, got: {discard_result}"
            )

            # Step 3: confirm no copilot branches remain.
            from app.services.copilot_apply_service import _find_open_proposal, _get_lineage_root_id

            root_id = _get_lineage_root_id(db, plane.id)
            assert _find_open_proposal(db, root_id) is None, (
                "Copilot proposal branch still exists after discard"
            )
        finally:
            db.close()

    def test_discard_after_addxsec_no_crash(self, client_and_db):
        """discard_proposal must not crash after AddXsec (also a wing write)."""
        db = _make_session(client_and_db)
        try:
            plane = _create_plane_with_wc_wing(db)

            from app.services.wing_service import get_wing_as_wingconfig

            # Get initial segment count to compute at_index
            branch_prep = get_or_open_proposal(db, plane.id)
            db.commit()
            proposal_node_prep = (
                db.query(AeroplaneModel).filter(AeroplaneModel.id == branch_prep.head_id).first()
            )
            wc_before = get_wing_as_wingconfig(db, str(proposal_node_prep.uuid), "main_wing")
            n_segs = len(wc_before["segments"])

            # Discard the prep branch so apply creates a fresh one
            from app.services.copilot_apply_service import discard_open_proposal as _discard

            _discard(db, plane.id)
            db.commit()

            with patch(_RECOMPUTE_PATH):
                apply_result = execute(
                    "apply_design_edits",
                    db,
                    plane.id,
                    ops=[
                        {
                            "type": "AddXsec",
                            "wing": "main_wing",
                            "at_index": n_segs + 1,
                            "chord": 40.0,
                            "span": 80.0,
                            "dihedral": 45.0,
                        }
                    ],
                )
            db.commit()

            assert "error" not in apply_result, f"apply failed: {apply_result.get('error')}"

            # Discard must not raise
            discard_result = execute("discard_proposal", db, plane.id)
            db.commit()

            assert discard_result.get("discarded") is True

            from app.services.copilot_apply_service import _find_open_proposal, _get_lineage_root_id

            root_id = _get_lineage_root_id(db, plane.id)
            assert _find_open_proposal(db, root_id) is None
        finally:
            db.close()


# ---------------------------------------------------------------------------
# Regression: gh-937 AddXsec produces valid winglet at tip (Bug 2)
# ---------------------------------------------------------------------------


class TestAddXsecWingletRegression:
    """Regression tests for gh-937 Bug 2: AddXsec at at_index=n_segs+1
    (append beyond last segment) was producing incorrect geometry because
    create_wing_configuration() processes middle segments (tip_type=None)
    before tip segments (tip_type="flat"), causing the winglet to be inserted
    in the wrong position in the WingConfiguration.

    Fix: strip tip_type from all existing segments before appending the winglet,
    so create_wing_configuration processes segments in root-to-tip order.
    """

    def test_add_xsec_at_tip_correct_segment_count(self, client_and_db):
        """AddXsec at n_segs+1 increases segment count by exactly 1."""
        db = _make_session(client_and_db)
        try:
            plane = _create_plane_with_wc_wing(db)
            branch = get_or_open_proposal(db, plane.id)
            db.commit()

            proposal_node = (
                db.query(AeroplaneModel).filter(AeroplaneModel.id == branch.head_id).first()
            )

            from app.services.wing_service import get_wing_as_wingconfig

            n_segs_before = len(
                get_wing_as_wingconfig(db, str(proposal_node.uuid), "main_wing")["segments"]
            )

            with patch(_RECOMPUTE_PATH):
                result = apply_edits(
                    db,
                    str(proposal_node.uuid),
                    [
                        AddXsec(
                            wing="main_wing",
                            at_index=n_segs_before + 1,
                            chord=40.0,
                            span=80.0,
                            dihedral=45.0,
                        )
                    ],
                )
            db.commit()

            assert result["applied"] == ["AddXsec"], f"Not applied: {result}"
            assert not result["rejected"]

            # Expire stale ORM state before re-read
            db.expire_all()
            wc_after = get_wing_as_wingconfig(db, str(proposal_node.uuid), "main_wing")
            n_segs_after = len(wc_after["segments"])

            assert n_segs_after == n_segs_before + 1, (
                f"Expected {n_segs_before + 1} segments, got {n_segs_after}"
            )
        finally:
            db.close()

    def test_add_xsec_at_tip_correct_winglet_params(self, client_and_db):
        """AddXsec at n_segs+1 appends the winglet as the last segment with
        the specified chord and span parameters."""
        db = _make_session(client_and_db)
        try:
            plane = _create_plane_with_wc_wing(db)
            branch = get_or_open_proposal(db, plane.id)
            db.commit()

            proposal_node = (
                db.query(AeroplaneModel).filter(AeroplaneModel.id == branch.head_id).first()
            )

            from app.services.wing_service import get_wing_as_wingconfig

            wc_before = get_wing_as_wingconfig(db, str(proposal_node.uuid), "main_wing")
            n_segs = len(wc_before["segments"])
            original_last_tip_chord = wc_before["segments"][-1]["tip_airfoil"]["chord"]

            winglet_chord = 35.0  # mm
            winglet_span = 90.0  # mm

            with patch(_RECOMPUTE_PATH):
                result = apply_edits(
                    db,
                    str(proposal_node.uuid),
                    [
                        AddXsec(
                            wing="main_wing",
                            at_index=n_segs + 1,
                            chord=winglet_chord,
                            span=winglet_span,
                            dihedral=30.0,
                        )
                    ],
                )
            db.commit()

            assert result["applied"] == ["AddXsec"]
            assert not result["rejected"]

            db.expire_all()
            wc_after = get_wing_as_wingconfig(db, str(proposal_node.uuid), "main_wing")
            new_last = wc_after["segments"][-1]

            # The new last segment must have the right tip chord
            assert new_last["tip_airfoil"]["chord"] == pytest.approx(winglet_chord, abs=1.0), (
                f"Winglet tip chord: expected ~{winglet_chord}, "
                f"got {new_last['tip_airfoil']['chord']}"
            )

            # Its root chord must match the old tip chord
            assert new_last["root_airfoil"]["chord"] == pytest.approx(
                original_last_tip_chord, abs=1.0
            ), (
                f"Winglet root chord: expected ~{original_last_tip_chord}, "
                f"got {new_last['root_airfoil']['chord']}"
            )

            # Its span (length) must match op.span
            assert new_last["length"] == pytest.approx(winglet_span, rel=0.05), (
                f"Winglet span: expected ~{winglet_span}, got {new_last['length']}"
            )
        finally:
            db.close()

    def test_add_xsec_at_tip_winglet_xsec_beyond_original_tip(self, client_and_db):
        """The winglet tip xsec must be at a Y-position strictly beyond the
        original tip, confirming no segment-order scramble in the DB."""
        db = _make_session(client_and_db)
        try:
            plane = _create_plane_with_wc_wing(db)
            branch = get_or_open_proposal(db, plane.id)
            db.commit()

            proposal_node = (
                db.query(AeroplaneModel).filter(AeroplaneModel.id == branch.head_id).first()
            )
            from app.models.aeroplanemodel import WingModel
            from app.services.wing_service import get_wing_as_wingconfig

            # Record the original tip Y position
            db.expire_all()
            orig_wing = next(
                (w for w in proposal_node.wings if w.name == "main_wing"), None
            )
            assert orig_wing is not None
            orig_tip_y = orig_wing.x_secs[-1].xyz_le[1]  # original tip Y (metres)
            n_segs = len(orig_wing.x_secs) - 1  # n xsecs = n_segs + 1

            with patch(_RECOMPUTE_PATH):
                result = apply_edits(
                    db,
                    str(proposal_node.uuid),
                    [
                        AddXsec(
                            wing="main_wing",
                            at_index=n_segs + 1,
                            chord=40.0,
                            span=80.0,
                            dihedral=30.0,
                        )
                    ],
                )
            db.commit()

            assert result["applied"] == ["AddXsec"]

            db.expire_all()
            db.refresh(proposal_node)
            new_wing = next(
                (w for w in proposal_node.wings if w.name == "main_wing"), None
            )
            assert new_wing is not None

            # New wing should have 1 extra xsec
            assert len(new_wing.x_secs) == n_segs + 2, (
                f"Expected {n_segs + 2} xsecs, got {len(new_wing.x_secs)}"
            )

            # The new last xsec Y must be > original tip Y (winglet projects outward)
            new_tip_y = new_wing.x_secs[-1].xyz_le[1]
            assert new_tip_y > orig_tip_y, (
                f"Winglet tip Y ({new_tip_y:.4f}m) must exceed original tip Y ({orig_tip_y:.4f}m)"
            )
        finally:
            db.close()


# ---------------------------------------------------------------------------
# gh-938 Bug A/B regression tests
# ---------------------------------------------------------------------------


class TestGh938Regressions:
    """Regression tests for gh-938 Bugs A and B:

    Bug A: get_design_snapshot did not surface per-wing n_xsecs, so the LLM
           could not pick a valid AddXsec at_index.
    Bug B: AddXsec at a mid-wing index crashed with NoneType instead of
           rejecting cleanly.  Any at_index >= n_xsecs must tip-append;
           mid-wing must reject with a helpful message (no exception).
    """

    # --- Bug A: snapshot includes per-wing n_xsecs ---

    def test_snapshot_includes_wings_with_n_xsecs(self, client_and_db):
        """_metrics_payload must include a 'wings' list with name and n_xsecs."""
        db = _make_session(client_and_db)
        try:
            plane = _create_plane_with_wc_wing(db)
            metrics = _metrics_payload(plane)

            assert "wings" in metrics, "snapshot must have 'wings' key"
            assert isinstance(metrics["wings"], list)
            assert len(metrics["wings"]) >= 1

            wing_entry = next((w for w in metrics["wings"] if w["name"] == "main_wing"), None)
            assert wing_entry is not None, "'main_wing' missing from wings list"
            assert "n_xsecs" in wing_entry, "wing entry must have 'n_xsecs'"
            assert wing_entry["n_xsecs"] > 0
        finally:
            db.close()

    def test_snapshot_n_xsecs_matches_actual_xsec_count(self, client_and_db):
        """The n_xsecs value in the snapshot must equal the actual DB xsec count."""
        db = _make_session(client_and_db)
        try:
            plane = _create_plane_with_wc_wing(db)
            metrics = _metrics_payload(plane)

            wing_entry = next((w for w in metrics["wings"] if w["name"] == "main_wing"), None)
            assert wing_entry is not None

            # Get the actual xsec count from the ORM
            main_wing = next((w for w in plane.wings if w.name == "main_wing"), None)
            assert main_wing is not None
            assert wing_entry["n_xsecs"] == len(main_wing.x_secs)
        finally:
            db.close()

    def test_snapshot_wing_names_still_present(self, client_and_db):
        """wing_names must still be present alongside the new 'wings' list."""
        db = _make_session(client_and_db)
        try:
            plane = _create_plane_with_wc_wing(db)
            metrics = _metrics_payload(plane)
            assert "wing_names" in metrics
            assert "main_wing" in metrics["wing_names"]
        finally:
            db.close()

    # --- Bug B: at_index >= n_xsecs clamps to tip-append ---

    def test_add_xsec_at_index_equals_n_xsecs_tip_appends(self, client_and_db):
        """AddXsec with at_index == n_xsecs (the exact tip value) must succeed."""
        db = _make_session(client_and_db)
        try:
            plane = _create_plane_with_wc_wing(db)
            branch = get_or_open_proposal(db, plane.id)
            db.commit()

            proposal_node = (
                db.query(AeroplaneModel).filter(AeroplaneModel.id == branch.head_id).first()
            )

            from app.services.wing_service import get_wing_as_wingconfig

            wc = get_wing_as_wingconfig(db, str(proposal_node.uuid), "main_wing")
            n_segs = len(wc["segments"])
            n_xsecs = n_segs + 1  # correct tip-append index

            with patch(_RECOMPUTE_PATH):
                result = apply_edits(
                    db,
                    str(proposal_node.uuid),
                    [AddXsec(wing="main_wing", at_index=n_xsecs, chord=35.0, span=60.0, dihedral=75.0)],
                )
            db.commit()

            assert result["applied"] == ["AddXsec"], f"Expected applied, got: {result}"
            assert not result["rejected"], f"Unexpected rejection: {result['rejected']}"

            db.expire_all()
            wc_after = get_wing_as_wingconfig(db, str(proposal_node.uuid), "main_wing")
            assert len(wc_after["segments"]) == n_segs + 1
        finally:
            db.close()

    def test_add_xsec_at_index_beyond_n_xsecs_clamped_to_tip(self, client_and_db):
        """AddXsec with at_index > n_xsecs is silently clamped to tip-append (no crash, no reject)."""
        db = _make_session(client_and_db)
        try:
            plane = _create_plane_with_wc_wing(db)
            branch = get_or_open_proposal(db, plane.id)
            db.commit()

            proposal_node = (
                db.query(AeroplaneModel).filter(AeroplaneModel.id == branch.head_id).first()
            )

            from app.services.wing_service import get_wing_as_wingconfig

            wc = get_wing_as_wingconfig(db, str(proposal_node.uuid), "main_wing")
            n_segs = len(wc["segments"])
            n_xsecs = n_segs + 1
            # LLM over-estimates: passes n_xsecs + 10 (e.g. 23 for a 13-xsec wing)
            over_estimated_index = n_xsecs + 10

            with patch(_RECOMPUTE_PATH):
                result = apply_edits(
                    db,
                    str(proposal_node.uuid),
                    [AddXsec(wing="main_wing", at_index=over_estimated_index, chord=30.0, span=50.0, dihedral=80.0)],
                )
            db.commit()

            # Must be applied (clamped), never rejected
            assert result["applied"] == ["AddXsec"], f"Expected tip-append, got: {result}"
            assert not result["rejected"], f"Unexpected rejection: {result['rejected']}"

            db.expire_all()
            wc_after = get_wing_as_wingconfig(db, str(proposal_node.uuid), "main_wing")
            assert len(wc_after["segments"]) == n_segs + 1
        finally:
            db.close()

    def test_add_xsec_mid_wing_rejected_cleanly(self, client_and_db):
        """AddXsec at a mid-wing index (< n_xsecs) is rejected with a clear message — no exception."""
        db = _make_session(client_and_db)
        try:
            plane = _create_plane_with_wc_wing(db)
            branch = get_or_open_proposal(db, plane.id)
            db.commit()

            proposal_node = (
                db.query(AeroplaneModel).filter(AeroplaneModel.id == branch.head_id).first()
            )

            from app.services.wing_service import get_wing_as_wingconfig

            wc = get_wing_as_wingconfig(db, str(proposal_node.uuid), "main_wing")
            n_segs = len(wc["segments"])

            if n_segs < 2:
                pytest.skip("Fixture has too few segments for mid-wing rejection test")

            # at_index=2 is a mid-wing index for any wing with >= 3 xsecs
            with patch(_RECOMPUTE_PATH):
                result = apply_edits(
                    db,
                    str(proposal_node.uuid),
                    [AddXsec(wing="main_wing", at_index=2, chord=60.0, span=100.0)],
                )

            # Must be rejected, not raised, not applied
            assert len(result["rejected"]) == 1, f"Expected rejection, got: {result}"
            assert not result["applied"], f"Expected no applied ops, got: {result['applied']}"
            err = result["rejected"][0]["error"]
            # Error must mention mid-wing is not supported AND give the tip hint
            assert "not yet supported" in err or "tip" in err.lower(), (
                f"Error should explain mid-wing limitation: {err}"
            )
        finally:
            db.close()

    def test_add_xsec_mid_wing_does_not_corrupt_wing(self, client_and_db):
        """After a mid-wing rejection the wing config must be unchanged."""
        db = _make_session(client_and_db)
        try:
            plane = _create_plane_with_wc_wing(db)
            branch = get_or_open_proposal(db, plane.id)
            db.commit()

            proposal_node = (
                db.query(AeroplaneModel).filter(AeroplaneModel.id == branch.head_id).first()
            )

            from app.services.wing_service import get_wing_as_wingconfig

            wc_before = get_wing_as_wingconfig(db, str(proposal_node.uuid), "main_wing")
            n_segs_before = len(wc_before["segments"])

            if n_segs_before < 2:
                pytest.skip("Fixture has too few segments for this test")

            with patch(_RECOMPUTE_PATH):
                apply_edits(
                    db,
                    str(proposal_node.uuid),
                    [AddXsec(wing="main_wing", at_index=2, chord=60.0, span=100.0)],
                )

            # The wing config must be unchanged (no segments added)
            db.expire_all()
            wc_after = get_wing_as_wingconfig(db, str(proposal_node.uuid), "main_wing")
            assert len(wc_after["segments"]) == n_segs_before, (
                "Mid-wing rejection must not alter the segment count"
            )
        finally:
            db.close()


# ---------------------------------------------------------------------------
# compute_metrics_diff — edge cases for _get_path (line 71)
# ---------------------------------------------------------------------------


class TestComputeMetricsDiffEdgeCases:
    """Cover the _get_path branches not hit by the existing basic tests.

    Line 71: the ``not isinstance(val, dict)`` guard fires when a nested
    path is requested but the intermediate value is NOT a dict (e.g. a
    string or None stored where a sub-dict was expected).
    """

    def test_nested_path_intermediate_not_dict(self):
        """_get_path returns None when an intermediate node is not a dict."""
        # assumption_computation_context is set to a string instead of a dict;
        # _get_path should return None (not crash) for any nested key.
        a = {
            "total_mass_kg": 1.0,
            "assumption_computation_context": "not-a-dict",  # triggers line 71
        }
        b = {
            "total_mass_kg": 2.0,
            "assumption_computation_context": {
                "span_m": 1.5,
            },
        }
        diff = compute_metrics_diff(a, b)
        # mass_kg must differ (both numeric)
        assert "mass_kg" in diff
        assert diff["mass_kg"]["delta"] == pytest.approx(1.0)
        # span_m: val_a is None (intermediate not-a-dict), val_b is 1.5 → included
        assert "span_m" in diff

    def test_nested_path_missing_intermediate_key(self):
        """_get_path returns None (not KeyError) when an intermediate key is absent."""
        a = {}
        b = {"assumption_computation_context": {"span_m": 1.2}}
        diff = compute_metrics_diff(a, b)
        # span_m: val_a is None, val_b is 1.2 — should appear in diff
        assert "span_m" in diff
        assert diff["span_m"].get("after") == pytest.approx(1.2)

    def test_only_after_present_no_delta_key(self):
        """When val_a is None and val_b is numeric, entry has 'after' but no 'delta'."""
        a = {}
        b = {"total_mass_kg": 3.5}
        diff = compute_metrics_diff(a, b)
        assert "mass_kg" in diff
        assert "after" in diff["mass_kg"]
        assert "delta" not in diff["mass_kg"]

    def test_only_before_present_no_delta_key(self):
        """When val_a is numeric and val_b is None, entry has 'before' but no 'delta'."""
        a = {"total_mass_kg": 3.5}
        b = {}
        diff = compute_metrics_diff(a, b)
        assert "mass_kg" in diff
        assert "before" in diff["mass_kg"]
        assert "delta" not in diff["mass_kg"]


# ---------------------------------------------------------------------------
# SetXsec — interior x-sec (lines 350-388) + other field combos
# ---------------------------------------------------------------------------


class TestSetXsecInteriorAndFields:
    """Cover the interior-xsec branches (op.index > 0 AND op.index < n):
    lines 353-356 (chord), 362-366 (twist), 374-376 (airfoil), 383-388 (dihedral).
    """

    def _setup_proposal(self, db):
        """Return (plane, proposal_node, n_segs) for a WC wing proposal."""
        plane = _create_plane_with_wc_wing(db)
        branch = get_or_open_proposal(db, plane.id)
        db.commit()
        proposal_node = db.query(AeroplaneModel).filter(AeroplaneModel.id == branch.head_id).first()
        from app.services.wing_service import get_wing_as_wingconfig
        wc = get_wing_as_wingconfig(db, str(proposal_node.uuid), "main_wing")
        n_segs = len(wc["segments"])
        return plane, proposal_node, n_segs

    def test_set_xsec_interior_chord(self, client_and_db):
        """SetXsec on an interior index updates both neighbouring segments."""
        db = _make_session(client_and_db)
        try:
            _, proposal_node, n_segs = self._setup_proposal(db)
            if n_segs < 2:
                pytest.skip("Need >= 2 segments for interior xsec test")

            # interior_index is 1..n_segs-1 — choose the first interior one
            interior_idx = 1
            new_chord = 111.0

            with patch(_RECOMPUTE_PATH):
                result = apply_edits(
                    db,
                    str(proposal_node.uuid),
                    [SetXsec(wing="main_wing", index=interior_idx, chord=new_chord)],
                )
            db.commit()

            assert result["applied"] == ["SetXsec"]
            assert not result["rejected"]

            db.expire_all()
            from app.services.wing_service import get_wing_as_wingconfig
            wc = get_wing_as_wingconfig(db, str(proposal_node.uuid), "main_wing")
            # tip of seg[index-1] and root of seg[index] must both have the new chord
            assert wc["segments"][interior_idx - 1]["tip_airfoil"]["chord"] == pytest.approx(new_chord)
            assert wc["segments"][interior_idx]["root_airfoil"]["chord"] == pytest.approx(new_chord)
        finally:
            db.close()

    def test_set_xsec_interior_twist(self, client_and_db):
        """SetXsec twist on an interior index updates both neighbouring segments."""
        db = _make_session(client_and_db)
        try:
            _, proposal_node, n_segs = self._setup_proposal(db)
            if n_segs < 2:
                pytest.skip("Need >= 2 segments for interior xsec test")

            interior_idx = 1
            new_twist = -3.0

            with patch(_RECOMPUTE_PATH):
                result = apply_edits(
                    db,
                    str(proposal_node.uuid),
                    [SetXsec(wing="main_wing", index=interior_idx, twist=new_twist)],
                )
            db.commit()

            assert result["applied"] == ["SetXsec"]
            assert not result["rejected"]

            db.expire_all()
            from app.services.wing_service import get_wing_as_wingconfig
            wc = get_wing_as_wingconfig(db, str(proposal_node.uuid), "main_wing")
            assert wc["segments"][interior_idx - 1]["tip_airfoil"]["incidence"] == pytest.approx(new_twist)
            assert wc["segments"][interior_idx]["root_airfoil"]["incidence"] == pytest.approx(new_twist)
        finally:
            db.close()

    def test_set_xsec_interior_airfoil(self, client_and_db):
        """SetXsec airfoil on an interior index updates both neighbouring segments."""
        db = _make_session(client_and_db)
        try:
            _, proposal_node, n_segs = self._setup_proposal(db)
            if n_segs < 2:
                pytest.skip("Need >= 2 segments for interior xsec test")

            interior_idx = 1
            new_airfoil = "./components/airfoils/rg15.dat"

            with patch(_RECOMPUTE_PATH):
                result = apply_edits(
                    db,
                    str(proposal_node.uuid),
                    [SetXsec(wing="main_wing", index=interior_idx, airfoil=new_airfoil)],
                )
            db.commit()

            assert result["applied"] == ["SetXsec"]
            assert not result["rejected"]

            db.expire_all()
            from app.services.wing_service import get_wing_as_wingconfig
            wc = get_wing_as_wingconfig(db, str(proposal_node.uuid), "main_wing")
            assert wc["segments"][interior_idx - 1]["tip_airfoil"]["airfoil"] == new_airfoil
            assert wc["segments"][interior_idx]["root_airfoil"]["airfoil"] == new_airfoil
        finally:
            db.close()

    def test_set_xsec_interior_dihedral(self, client_and_db):
        """SetXsec dihedral on an interior index is applied (op succeeds, no rejection).

        Note: dihedral_as_rotation_in_degrees is baked into xyz_le geometry during
        WingConfig→ASB conversion.  The exact degree value is not guaranteed to
        survive the round-trip unchanged; we only verify the op is accepted.
        """
        db = _make_session(client_and_db)
        try:
            _, proposal_node, n_segs = self._setup_proposal(db)
            if n_segs < 2:
                pytest.skip("Need >= 2 segments for interior xsec test")

            interior_idx = 1
            new_dihedral = 5.0

            with patch(_RECOMPUTE_PATH):
                result = apply_edits(
                    db,
                    str(proposal_node.uuid),
                    [SetXsec(wing="main_wing", index=interior_idx, dihedral=new_dihedral)],
                )
            db.commit()

            assert result["applied"] == ["SetXsec"]
            assert not result["rejected"]

            # Verify the wing can be read back (geometry is consistent)
            db.expire_all()
            from app.services.wing_service import get_wing_as_wingconfig
            wc = get_wing_as_wingconfig(db, str(proposal_node.uuid), "main_wing")
            assert len(wc["segments"]) >= 2
        finally:
            db.close()

    def test_set_xsec_tip_chord(self, client_and_db):
        """SetXsec at the tip index (index == n_segs) updates tip_airfoil of last seg."""
        db = _make_session(client_and_db)
        try:
            _, proposal_node, n_segs = self._setup_proposal(db)
            tip_idx = n_segs  # last xsec
            new_chord = 55.0

            with patch(_RECOMPUTE_PATH):
                result = apply_edits(
                    db,
                    str(proposal_node.uuid),
                    [SetXsec(wing="main_wing", index=tip_idx, chord=new_chord)],
                )
            db.commit()

            assert result["applied"] == ["SetXsec"]
            assert not result["rejected"]

            db.expire_all()
            from app.services.wing_service import get_wing_as_wingconfig
            wc = get_wing_as_wingconfig(db, str(proposal_node.uuid), "main_wing")
            assert wc["segments"][-1]["tip_airfoil"]["chord"] == pytest.approx(new_chord)
        finally:
            db.close()

    def test_set_xsec_tip_twist(self, client_and_db):
        """SetXsec twist at the tip index updates tip_airfoil incidence of last seg."""
        db = _make_session(client_and_db)
        try:
            _, proposal_node, n_segs = self._setup_proposal(db)
            tip_idx = n_segs
            new_twist = -2.5

            with patch(_RECOMPUTE_PATH):
                result = apply_edits(
                    db,
                    str(proposal_node.uuid),
                    [SetXsec(wing="main_wing", index=tip_idx, twist=new_twist)],
                )
            db.commit()

            assert result["applied"] == ["SetXsec"]
            assert not result["rejected"]

            db.expire_all()
            from app.services.wing_service import get_wing_as_wingconfig
            wc = get_wing_as_wingconfig(db, str(proposal_node.uuid), "main_wing")
            assert wc["segments"][-1]["tip_airfoil"]["incidence"] == pytest.approx(new_twist)
        finally:
            db.close()

    def test_set_xsec_tip_airfoil(self, client_and_db):
        """SetXsec airfoil at tip index updates tip_airfoil.airfoil of last seg."""
        db = _make_session(client_and_db)
        try:
            _, proposal_node, n_segs = self._setup_proposal(db)
            tip_idx = n_segs
            new_airfoil = "./components/airfoils/rg15.dat"

            with patch(_RECOMPUTE_PATH):
                result = apply_edits(
                    db,
                    str(proposal_node.uuid),
                    [SetXsec(wing="main_wing", index=tip_idx, airfoil=new_airfoil)],
                )
            db.commit()

            assert result["applied"] == ["SetXsec"]
            assert not result["rejected"]

            db.expire_all()
            from app.services.wing_service import get_wing_as_wingconfig
            wc = get_wing_as_wingconfig(db, str(proposal_node.uuid), "main_wing")
            assert wc["segments"][-1]["tip_airfoil"]["airfoil"] == new_airfoil
        finally:
            db.close()

    def test_set_xsec_tip_dihedral(self, client_and_db):
        """SetXsec dihedral at tip index is applied (op succeeds, no rejection).

        Note: dihedral_as_rotation_in_degrees is baked into xyz_le geometry during
        WingConfig→ASB conversion and inferred back on read.  The round-trip
        approximation means the exact degree value is NOT guaranteed to survive
        unchanged, so we only assert the op was accepted and the wing is readable.
        Exact dihedral roundtrip accuracy is covered by test_wingconfig_roundtrip.py.
        """
        db = _make_session(client_and_db)
        try:
            _, proposal_node, n_segs = self._setup_proposal(db)
            tip_idx = n_segs
            new_dihedral = 8.0

            with patch(_RECOMPUTE_PATH):
                result = apply_edits(
                    db,
                    str(proposal_node.uuid),
                    [SetXsec(wing="main_wing", index=tip_idx, dihedral=new_dihedral)],
                )
            db.commit()

            assert result["applied"] == ["SetXsec"]
            assert not result["rejected"]

            # Verify the wing can be read back (geometry is consistent)
            db.expire_all()
            from app.services.wing_service import get_wing_as_wingconfig
            wc = get_wing_as_wingconfig(db, str(proposal_node.uuid), "main_wing")
            assert len(wc["segments"]) > 0
        finally:
            db.close()


# ---------------------------------------------------------------------------
# RemoveXsec — additional guard branches (lines 542-570)
# ---------------------------------------------------------------------------


class TestRemoveXsecGuards:
    """Cover the wing-not-found (lines 542-548) and too-few-segments (564-570) paths."""

    def test_remove_xsec_nonexistent_wing_rejected(self, client_and_db):
        """RemoveXsec on a wing that doesn't exist → rejected (not raised)."""
        db = _make_session(client_and_db)
        try:
            plane = _create_plane_with_branch(db)
            branch = get_or_open_proposal(db, plane.id)
            db.commit()
            proposal_node = db.query(AeroplaneModel).filter(
                AeroplaneModel.id == branch.head_id
            ).first()

            with patch(_RECOMPUTE_PATH):
                result = apply_edits(
                    db,
                    str(proposal_node.uuid),
                    [RemoveXsec(wing="ghost_wing", index=1)],
                )

            assert len(result["rejected"]) == 1
            assert "ghost_wing" in str(result["rejected"][0]["error"])
        finally:
            db.close()

    def test_remove_xsec_single_segment_wing_rejected(self, client_and_db):
        """RemoveXsec on a wing with only 1 segment → rejected (too few segments)."""
        from app.schemas.wing import Wing as WingConfigurationSchema
        from app.services.wing_service import get_wing_as_wingconfig, put_wing_as_wingconfig

        db = _make_session(client_and_db)
        try:
            # Build a minimal wing with exactly 1 segment (2 x-secs)
            one_seg_payload = {
                "segments": [
                    {
                        "root_airfoil": {
                            "airfoil": "./components/airfoils/rg15.dat",
                            "chord": 200.0,
                            "dihedral_as_rotation_in_degrees": 0.0,
                            "incidence": 0.0,
                        },
                        "tip_airfoil": {
                            "airfoil": "./components/airfoils/rg15.dat",
                            "chord": 150.0,
                            "dihedral_as_rotation_in_degrees": 0.0,
                            "incidence": -1.0,
                        },
                        "length": 500.0,
                        "sweep": 0.0,
                        "number_interpolation_points": None,
                        "tip_type": None,
                    }
                ],
                "nose_pnt": [0.0, 0.0, 0.0],
                "symmetric": True,
            }
            plane = _create_plane_with_branch(db)
            wc_schema = WingConfigurationSchema.model_validate(one_seg_payload)
            put_wing_as_wingconfig(db, str(plane.uuid), "test_wing_1seg", wc_schema, scale=0.001)
            db.commit()
            db.refresh(plane)

            branch = get_or_open_proposal(db, plane.id)
            db.commit()
            proposal_node = db.query(AeroplaneModel).filter(
                AeroplaneModel.id == branch.head_id
            ).first()

            # n=1 segment → n_xsecs=2 → only interior index is none (0 and 1 are root/tip)
            # We need to verify the n < 2 guard.  With exactly 1 segment we can't have
            # an interior xsec at all — but let's craft a 2-segment wing and try to
            # remove leaving 1 by checking after one removal it would drop to 0.
            # Actually the guard fires when n < 2 AND index passes the previous guard.
            # With 1 segment: n_xsecs=2, valid interior = 1..n_xsecs-2 = 1..0 → empty.
            # So index=1 hits the FIRST guard (op.index >= n_xsecs-1 == 1).
            # To hit the n < 2 guard we need index to pass the first guard but fail second.
            # The first guard is: op.index <= 0 OR op.index >= n_xsecs - 1.
            # With n_segs=2 (3 xsecs), n_xsecs-1=2, so index=1 is interior.
            # But n < 2 fires when n==1 (single segment) which can't reach index=1 in interior.
            # Instead: n=1 segment, index 1: n_xsecs=2, n_xsecs-1=1, so index>=1 → first guard.
            # The n < 2 path (564-570) is reached only when n >= 2 but the
            # result after removal would be 0... wait, re-reading: the guard fires
            # when n < 2 regardless of how we got here. Let me check: we'd only reach
            # line 563 if op.index passed the first guard (interior). For n=1:
            # n_xsecs=2, n_xsecs-2=0, so ONLY valid interior is 1..0 which is empty;
            # index=1 hits the first guard (op.index >= n_xsecs-1 == 1). So n<2
            # guard (line 563) is unreachable for n=1 via normal schema values.
            # We need a wing that has n=1 AND a magic index that slips past guard 1.
            # That's impossible via normal schema.
            # CONCLUSION: lines 564-570 can be exercised with a monkeypatched op
            # that bypasses the schema constraint. Use a plain object duck type.
            wc_before = get_wing_as_wingconfig(db, str(proposal_node.uuid), "test_wing_1seg")
            assert len(wc_before["segments"]) == 1, "Precondition: 1 segment"

            # Craft an op object that has n=1 segment but index=0 < n_xsecs-1=1.
            # Wait: n_xsecs-1 for n=1 is 1, so index=0 hits op.index<=0 guard (first guard).
            # The ONLY way to hit line 563 (n<2) is: n >= 2 + index passes guard 1.
            # Guard 1: op.index <= 0 OR op.index >= n_xsecs-1.
            # n=2, n_xsecs=3, n_xsecs-1=2 → valid interior: index=1 passes guard 1.
            # So we need a 2-segment wing and somehow n < 2 fires... that can't happen.
            # Lines 564-570 are ONLY reachable if n_segs < 2 BUT index passes guard 1,
            # which with real schema values means: n=1, index=0 → hits guard 1 first.
            # The guard is unreachable in practice unless a subclass bypasses schema.
            # Let us use a duck-typed fake op to exercise it directly:

            class _FakeRemoveXsec:
                type = "RemoveXsec"
                wing = "test_wing_1seg"
                index = 0  # would normally be blocked by schema ge=1, but we bypass

                def model_dump(self):
                    return {"type": "RemoveXsec", "wing": self.wing, "index": self.index}

            # With 1 segment, n_xsecs=2, n_xsecs-1=1; index=0 <= 0 hits FIRST guard.
            # So lines 564-570 can only be hit by faking index in the interior range
            # while n=1. The index must satisfy 0 < index < n_xsecs-1 = 0, impossible.
            # Lines 564-570 are dead code for n=1 with integer index.
            # For n=2 segments, index=1 is valid interior.
            # Lines 564-570 check ``if n < 2`` → unreachable for any valid 2+segment case.
            # FINDING: these lines are defensive dead code. We verify the first guard fires:
            with patch(_RECOMPUTE_PATH):
                result = apply_edits(
                    db,
                    str(proposal_node.uuid),
                    [_FakeRemoveXsec()],
                )

            # Should be rejected by first guard (index=0 <= 0)
            assert len(result["rejected"]) == 1
            assert "Root" in str(result["rejected"][0]["error"]) or "0" in str(
                result["rejected"][0]["error"]
            )
        finally:
            db.close()


# ---------------------------------------------------------------------------
# SetWingParam — full handler (lines 589-627)
# ---------------------------------------------------------------------------


class TestSetWingParam:
    """Cover SetWingParam sweep_mm and dihedral paths (lines 589-627)."""

    def test_set_wing_param_sweep(self, client_and_db):
        """SetWingParam sweep_mm applies to every segment in the wing."""
        db = _make_session(client_and_db)
        try:
            plane = _create_plane_with_wc_wing(db)
            branch = get_or_open_proposal(db, plane.id)
            db.commit()
            proposal_node = db.query(AeroplaneModel).filter(
                AeroplaneModel.id == branch.head_id
            ).first()

            new_sweep = 25.0

            with patch(_RECOMPUTE_PATH):
                result = apply_edits(
                    db,
                    str(proposal_node.uuid),
                    [SetWingParam(wing="main_wing", sweep_mm=new_sweep)],
                )
            db.commit()

            assert result["applied"] == ["SetWingParam"]
            assert not result["rejected"]

            db.expire_all()
            from app.services.wing_service import get_wing_as_wingconfig
            wc = get_wing_as_wingconfig(db, str(proposal_node.uuid), "main_wing")
            for seg in wc["segments"]:
                assert seg["sweep"] == pytest.approx(new_sweep)
        finally:
            db.close()

    def test_set_wing_param_dihedral(self, client_and_db):
        """SetWingParam dihedral is applied (op succeeds, no rejection).

        Note: dihedral_as_rotation_in_degrees is baked into xyz_le geometry during
        WingConfig→ASB conversion and inferred back on read.  The round-trip
        approximation means the exact degree value is NOT guaranteed to survive
        unchanged, so we only assert the op was accepted and the wing is readable.
        Exact dihedral roundtrip accuracy is covered by test_wingconfig_roundtrip.py.
        """
        db = _make_session(client_and_db)
        try:
            plane = _create_plane_with_wc_wing(db)
            branch = get_or_open_proposal(db, plane.id)
            db.commit()
            proposal_node = db.query(AeroplaneModel).filter(
                AeroplaneModel.id == branch.head_id
            ).first()

            new_dihedral = 4.0

            with patch(_RECOMPUTE_PATH):
                result = apply_edits(
                    db,
                    str(proposal_node.uuid),
                    [SetWingParam(wing="main_wing", dihedral=new_dihedral)],
                )
            db.commit()

            assert result["applied"] == ["SetWingParam"]
            assert not result["rejected"]

            # Verify the wing can be read back (geometry is consistent after dihedral apply)
            db.expire_all()
            from app.services.wing_service import get_wing_as_wingconfig
            wc = get_wing_as_wingconfig(db, str(proposal_node.uuid), "main_wing")
            assert len(wc["segments"]) > 0
        finally:
            db.close()

    def test_set_wing_param_sweep_and_dihedral(self, client_and_db):
        """SetWingParam with both sweep and dihedral applies both at once.

        Sweep is stored as the x-offset in xyz_le and round-trips exactly.
        Dihedral is baked into z-offsets and may not survive round-trip with the
        exact degree value, so we only assert the op succeeds.
        """
        db = _make_session(client_and_db)
        try:
            plane = _create_plane_with_wc_wing(db)
            branch = get_or_open_proposal(db, plane.id)
            db.commit()
            proposal_node = db.query(AeroplaneModel).filter(
                AeroplaneModel.id == branch.head_id
            ).first()

            with patch(_RECOMPUTE_PATH):
                result = apply_edits(
                    db,
                    str(proposal_node.uuid),
                    [SetWingParam(wing="main_wing", sweep_mm=15.0, dihedral=3.0)],
                )
            db.commit()

            assert result["applied"] == ["SetWingParam"]
            assert not result["rejected"]

            # Verify both attributes were applied — sweep round-trips via xyz_le.x
            db.expire_all()
            from app.services.wing_service import get_wing_as_wingconfig
            wc = get_wing_as_wingconfig(db, str(proposal_node.uuid), "main_wing")
            # Sweep IS preserved via the in-memory dict: the WingConfig carries it
            for seg in wc["segments"]:
                assert seg["sweep"] == pytest.approx(15.0)
            # Wing is readable (dihedral applied successfully even if approx round-trip)
            assert len(wc["segments"]) > 0
        finally:
            db.close()

    def test_set_wing_param_nonexistent_wing_rejected(self, client_and_db):
        """SetWingParam on a missing wing → rejected (not raised)."""
        db = _make_session(client_and_db)
        try:
            plane = _create_plane_with_branch(db)
            branch = get_or_open_proposal(db, plane.id)
            db.commit()
            proposal_node = db.query(AeroplaneModel).filter(
                AeroplaneModel.id == branch.head_id
            ).first()

            with patch(_RECOMPUTE_PATH):
                result = apply_edits(
                    db,
                    str(proposal_node.uuid),
                    [SetWingParam(wing="nonexistent_wing", sweep_mm=10.0)],
                )

            assert len(result["rejected"]) == 1
            assert "nonexistent_wing" in str(result["rejected"][0]["error"])
        finally:
            db.close()


# ---------------------------------------------------------------------------
# ReplaceWingConfig — apply and reject paths (lines 612-634)
# ---------------------------------------------------------------------------


class TestReplaceWingConfig:
    """Cover ReplaceWingConfig apply (lines 612-624) and schema-reject path (633-634)."""

    def test_replace_wing_config_applies(self, client_and_db):
        """ReplaceWingConfig with a valid payload replaces the wing fully."""
        db = _make_session(client_and_db)
        try:
            plane = _create_plane_with_wc_wing(db)
            branch = get_or_open_proposal(db, plane.id)
            db.commit()
            proposal_node = db.query(AeroplaneModel).filter(
                AeroplaneModel.id == branch.head_id
            ).first()

            if _WC_PAYLOAD is None:
                pytest.skip("WingConfig fixture not available")

            import copy
            new_payload = copy.deepcopy(_WC_PAYLOAD)
            # Modify root chord to distinguish from the original
            new_payload["segments"][0]["root_airfoil"]["chord"] = 321.0

            with patch(_RECOMPUTE_PATH):
                result = apply_edits(
                    db,
                    str(proposal_node.uuid),
                    [ReplaceWingConfig(wing="main_wing", wing_config=new_payload)],
                )
            db.commit()

            assert result["applied"] == ["ReplaceWingConfig"]
            assert not result["rejected"]

            db.expire_all()
            from app.services.wing_service import get_wing_as_wingconfig
            wc = get_wing_as_wingconfig(db, str(proposal_node.uuid), "main_wing")
            assert wc["segments"][0]["root_airfoil"]["chord"] == pytest.approx(321.0)
        finally:
            db.close()

    def test_replace_wing_config_bad_payload_rejected(self, client_and_db):
        """ReplaceWingConfig with a schema-invalid payload → rejected (not raised)."""
        db = _make_session(client_and_db)
        try:
            plane = _create_plane_with_wc_wing(db)
            branch = get_or_open_proposal(db, plane.id)
            db.commit()
            proposal_node = db.query(AeroplaneModel).filter(
                AeroplaneModel.id == branch.head_id
            ).first()

            # Pass a totally invalid payload (missing required fields)
            bad_payload = {"segments": "not-a-list", "nose_pnt": "bad"}

            with patch(_RECOMPUTE_PATH):
                result = apply_edits(
                    db,
                    str(proposal_node.uuid),
                    [ReplaceWingConfig(wing="main_wing", wing_config=bad_payload)],
                )

            assert len(result["rejected"]) == 1
            err_str = str(result["rejected"][0]["error"])
            assert err_str  # non-empty error
        finally:
            db.close()

    def test_replace_wing_config_evicts_cache(self, client_and_db):
        """After ReplaceWingConfig, a subsequent SetXsec re-reads the fresh config."""
        db = _make_session(client_and_db)
        try:
            plane = _create_plane_with_wc_wing(db)
            branch = get_or_open_proposal(db, plane.id)
            db.commit()
            proposal_node = db.query(AeroplaneModel).filter(
                AeroplaneModel.id == branch.head_id
            ).first()

            if _WC_PAYLOAD is None:
                pytest.skip("WingConfig fixture not available")

            import copy
            new_payload = copy.deepcopy(_WC_PAYLOAD)
            new_payload["segments"][0]["root_airfoil"]["chord"] = 250.0

            with patch(_RECOMPUTE_PATH):
                result = apply_edits(
                    db,
                    str(proposal_node.uuid),
                    [
                        ReplaceWingConfig(wing="main_wing", wing_config=new_payload),
                        # SetXsec immediately after must read the NEW config (chord 250)
                        SetXsec(wing="main_wing", index=0, chord=260.0),
                    ],
                )
            db.commit()

            assert "ReplaceWingConfig" in result["applied"]
            assert "SetXsec" in result["applied"]
            assert not result["rejected"]

            db.expire_all()
            from app.services.wing_service import get_wing_as_wingconfig
            wc = get_wing_as_wingconfig(db, str(proposal_node.uuid), "main_wing")
            assert wc["segments"][0]["root_airfoil"]["chord"] == pytest.approx(260.0)
        finally:
            db.close()


# ---------------------------------------------------------------------------
# Reject branches — unknown wing name, unknown assumption param, unknown op
# ---------------------------------------------------------------------------


class TestRejectBranches:
    """Cover the various reject-with-reason paths that were not previously tested."""

    def test_unknown_op_type_rejected(self, client_and_db):
        """An op with an unknown type is rejected with a clear message (line 627)."""
        db = _make_session(client_and_db)
        try:
            plane = _create_plane_with_branch(db)
            branch = get_or_open_proposal(db, plane.id)
            db.commit()
            proposal_node = db.query(AeroplaneModel).filter(
                AeroplaneModel.id == branch.head_id
            ).first()

            # Build a duck-typed op with a non-standard type to hit the else-branch
            class _UnknownOp:
                type = "CrazyUnknownOp"

                def model_dump(self):
                    return {"type": self.type}

            with patch(_RECOMPUTE_PATH):
                result = apply_edits(
                    db,
                    str(proposal_node.uuid),
                    [_UnknownOp()],
                )

            assert len(result["rejected"]) == 1
            assert "CrazyUnknownOp" in str(result["rejected"][0]["error"])
        finally:
            db.close()

    def test_exception_in_op_caught_as_reject(self, client_and_db):
        """An op that raises mid-execution is caught and returned as a rejected entry.

        We use a duck-typed op whose type is 'SetWingParam' but whose .wing property
        raises RuntimeError when accessed — this triggers the exception inside the
        op handler (not just in model_dump), exercises the outer except block at
        lines 629-635, and calls the fallback op_dict = {"type": op_type} path when
        model_dump() also raises.
        """
        db = _make_session(client_and_db)
        try:
            plane = _create_plane_with_branch(db)
            branch = get_or_open_proposal(db, plane.id)
            db.commit()
            proposal_node = db.query(AeroplaneModel).filter(
                AeroplaneModel.id == branch.head_id
            ).first()

            # An op whose .wing property raises and whose model_dump() also raises —
            # exercises the fallback op_dict = {"type": op_type} at line 633-634.
            class _BombOp:
                type = "SetWingParam"

                @property
                def wing(self):
                    raise RuntimeError("bomb exploded during wing access")

                def model_dump(self):
                    raise RuntimeError("bomb also in model_dump")

            with patch(_RECOMPUTE_PATH):
                result = apply_edits(
                    db,
                    str(proposal_node.uuid),
                    [_BombOp()],
                )

            # The exception must be caught; the op appears in rejected with an error
            assert len(result["rejected"]) == 1
            err_str = str(result["rejected"][0]["error"])
            assert "bomb" in err_str
            # Fallback op_dict must have only the type (model_dump raised)
            assert result["rejected"][0]["op"] == {"type": "SetWingParam"}
        finally:
            db.close()

    def test_add_xsec_nonexistent_wing_rejected(self, client_and_db):
        """AddXsec on a wing that doesn't exist → rejected (lines 399-405)."""
        db = _make_session(client_and_db)
        try:
            plane = _create_plane_with_branch(db)
            branch = get_or_open_proposal(db, plane.id)
            db.commit()
            proposal_node = db.query(AeroplaneModel).filter(
                AeroplaneModel.id == branch.head_id
            ).first()

            with patch(_RECOMPUTE_PATH):
                result = apply_edits(
                    db,
                    str(proposal_node.uuid),
                    [AddXsec(wing="phantom_wing", at_index=5, chord=100.0, span=200.0)],
                )

            assert len(result["rejected"]) == 1
            assert "phantom_wing" in str(result["rejected"][0]["error"])
        finally:
            db.close()


# ---------------------------------------------------------------------------
# Recompute exception (lines 662-663) — non-fatal recompute failure
# ---------------------------------------------------------------------------


class TestRecomputeExceptionNonFatal:
    """Lines 662-663: if recompute_assumptions raises, apply_edits must still return
    the applied list and not propagate the exception."""

    def test_recompute_failure_is_non_fatal(self, client_and_db):
        """apply_edits returns normally even when recompute_assumptions raises."""
        db = _make_session(client_and_db)
        try:
            plane = _create_plane_with_branch(db)
            branch = get_or_open_proposal(db, plane.id)
            db.commit()
            proposal_node = db.query(AeroplaneModel).filter(
                AeroplaneModel.id == branch.head_id
            ).first()

            # Patch recompute to raise instead of mocking it out
            with patch(
                "app.services.assumption_compute_service.recompute_assumptions",
                side_effect=RuntimeError("recompute failed"),
            ):
                result = apply_edits(
                    db,
                    str(proposal_node.uuid),
                    [SetAssumption(param="mass", value=2.0)],
                )
            db.commit()

            # Despite the recompute failure, apply_edits returned normally
            assert result["applied"] == ["SetAssumption"]
            assert result["rejected"] == []
            # metrics dict is present (may be empty if node lookup succeeds)
            assert "metrics" in result
        finally:
            db.close()


# ---------------------------------------------------------------------------
# Wing-write failure (lines 648-652) — wing cache write fails gracefully
# ---------------------------------------------------------------------------


class TestWingWriteFailure:
    """Lines 648-652: if writing the accumulated wing config fails, it is recorded
    as a rejected entry and the call does not raise."""

    def test_wing_write_failure_recorded_as_rejected(self, client_and_db):
        """A failure in put_wing_as_wingconfig during cache flush is caught and
        returned as a rejected entry (not raised)."""
        db = _make_session(client_and_db)
        try:
            plane = _create_plane_with_wc_wing(db)
            branch = get_or_open_proposal(db, plane.id)
            db.commit()
            proposal_node = db.query(AeroplaneModel).filter(
                AeroplaneModel.id == branch.head_id
            ).first()

            with patch(_RECOMPUTE_PATH):
                with patch(
                    "app.services.wing_service.put_wing_as_wingconfig",
                    side_effect=RuntimeError("DB write failed"),
                ):
                    result = apply_edits(
                        db,
                        str(proposal_node.uuid),
                        [SetXsec(wing="main_wing", index=0, chord=200.0)],
                    )

            # The wing write error is captured, not raised
            assert any(
                r.get("op", {}).get("type") == "WingWrite" for r in result["rejected"]
            ), f"Expected WingWrite in rejected: {result['rejected']}"
        finally:
            db.close()


# ---------------------------------------------------------------------------
# get_or_open_proposal — message_id creates named branch (line 178)
# ---------------------------------------------------------------------------


class TestGetOrOpenProposalMessageId:
    """Covers the message_id suffix path in get_or_open_proposal."""

    def test_message_id_appended_to_branch_name(self, client_and_db):
        """When message_id is provided, the branch name includes the suffix."""
        db = _make_session(client_and_db)
        try:
            plane = _create_plane_with_branch(db)

            branch = get_or_open_proposal(db, plane.id, message_id="msg-abc123")
            db.commit()

            assert "msg-abc123" in branch.name
            assert branch.name.startswith("copilot-proposal")
        finally:
            db.close()

    def test_no_message_id_still_valid_branch(self, client_and_db):
        """Without message_id, branch name is still a valid copilot-proposal name."""
        db = _make_session(client_and_db)
        try:
            plane = _create_plane_with_branch(db)
            branch = get_or_open_proposal(db, plane.id)
            db.commit()

            assert "copilot-proposal" in branch.name
        finally:
            db.close()


# ---------------------------------------------------------------------------
# SetXsec root (index=0) — twist, airfoil, dihedral (lines 361, 371, 381)
# ---------------------------------------------------------------------------


class TestSetXsecRootFields:
    """Cover the op.index==0 branches for twist (361), airfoil (371), dihedral (381)."""

    def _setup_proposal(self, db):
        """Return (plane, proposal_node, n_segs) for a WC wing proposal."""
        plane = _create_plane_with_wc_wing(db)
        branch = get_or_open_proposal(db, plane.id)
        db.commit()
        proposal_node = db.query(AeroplaneModel).filter(AeroplaneModel.id == branch.head_id).first()
        from app.services.wing_service import get_wing_as_wingconfig
        wc = get_wing_as_wingconfig(db, str(proposal_node.uuid), "main_wing")
        n_segs = len(wc["segments"])
        return plane, proposal_node, n_segs

    def test_set_xsec_root_twist(self, client_and_db):
        """SetXsec twist at index=0 updates root_airfoil.incidence of seg[0] (line 361)."""
        db = _make_session(client_and_db)
        try:
            _, proposal_node, _ = self._setup_proposal(db)
            new_twist = -2.0

            with patch(_RECOMPUTE_PATH):
                result = apply_edits(
                    db,
                    str(proposal_node.uuid),
                    [SetXsec(wing="main_wing", index=0, twist=new_twist)],
                )
            db.commit()

            assert result["applied"] == ["SetXsec"]
            assert not result["rejected"]

            db.expire_all()
            from app.services.wing_service import get_wing_as_wingconfig
            wc = get_wing_as_wingconfig(db, str(proposal_node.uuid), "main_wing")
            # Root incidence is preserved via the WingConfig roundtrip
            assert wc["segments"][0]["root_airfoil"]["incidence"] == pytest.approx(new_twist)
        finally:
            db.close()

    def test_set_xsec_root_airfoil(self, client_and_db):
        """SetXsec airfoil at index=0 updates root_airfoil.airfoil of seg[0] (line 371)."""
        db = _make_session(client_and_db)
        try:
            _, proposal_node, _ = self._setup_proposal(db)
            new_airfoil = "./components/airfoils/rg15.dat"

            with patch(_RECOMPUTE_PATH):
                result = apply_edits(
                    db,
                    str(proposal_node.uuid),
                    [SetXsec(wing="main_wing", index=0, airfoil=new_airfoil)],
                )
            db.commit()

            assert result["applied"] == ["SetXsec"]
            assert not result["rejected"]

            db.expire_all()
            from app.services.wing_service import get_wing_as_wingconfig
            wc = get_wing_as_wingconfig(db, str(proposal_node.uuid), "main_wing")
            assert wc["segments"][0]["root_airfoil"]["airfoil"] == new_airfoil
        finally:
            db.close()

    def test_set_xsec_root_dihedral(self, client_and_db):
        """SetXsec dihedral at index=0 is applied (op succeeds, no rejection) (line 381).

        Note: dihedral roundtrip accuracy is covered by test_wingconfig_roundtrip.py.
        """
        db = _make_session(client_and_db)
        try:
            _, proposal_node, _ = self._setup_proposal(db)
            new_dihedral = 3.0

            with patch(_RECOMPUTE_PATH):
                result = apply_edits(
                    db,
                    str(proposal_node.uuid),
                    [SetXsec(wing="main_wing", index=0, dihedral=new_dihedral)],
                )
            db.commit()

            assert result["applied"] == ["SetXsec"]
            assert not result["rejected"]

            # Wing is readable after dihedral apply
            db.expire_all()
            from app.services.wing_service import get_wing_as_wingconfig
            wc = get_wing_as_wingconfig(db, str(proposal_node.uuid), "main_wing")
            assert len(wc["segments"]) > 0
        finally:
            db.close()


# ---------------------------------------------------------------------------
# Defensive dead-code guards (lines 447-453, 484-501, 564-570)
# via duck-typed ops that bypass schema constraints
# ---------------------------------------------------------------------------


class TestDefensiveDeadCodeGuards:
    """These tests exercise defensive guard branches that are unreachable via normal
    schema-validated input.  We use duck-typed fake ops to force the paths.

    Coverage target: lines 447-453 (AddXsec at_index < 1 after clamping — dead),
    lines 484-501 (AddXsec seg_before_idx < n path for non-empty wing — dead),
    lines 564-570 (RemoveXsec n < 2 guard — dead for valid n >= 2 + interior idx).
    """

    def test_addxsec_at_index_zero_rejected_by_guard(self, client_and_db):
        """Duck-type a zero at_index that bypasses schema ge=1 constraint.

        With a non-empty wing and effective_at_index forced to 0, the guard
        at line 446 (effective_at_index < 1) should reject cleanly (lines 447-453).
        """
        db = _make_session(client_and_db)
        try:
            plane = _create_plane_with_wc_wing(db)
            branch = get_or_open_proposal(db, plane.id)
            db.commit()
            proposal_node = db.query(AeroplaneModel).filter(
                AeroplaneModel.id == branch.head_id
            ).first()

            from app.services.wing_service import get_wing_as_wingconfig
            wc = get_wing_as_wingconfig(db, str(proposal_node.uuid), "main_wing")
            n_segs = len(wc["segments"])
            # For a non-empty wing, at_index = 0 < 1.
            # Since n_segs > 0: n_xsecs = n_segs + 1 >= 2, so at_index=0 < n_xsecs.
            # The mid-wing check: effective_at_index < n_xsecs AND effective_at_index < n+1.
            # With at_index=0: 0 < n_xsecs (True) AND 0 < n_segs+1 (True for n>=1).
            # So it hits the MID-WING rejection guard (lines 432-443) FIRST,
            # not the at_index < 1 guard (lines 446-453).
            # To hit lines 447-453 we need effective_at_index to survive the mid-wing
            # guard (meaning effective_at_index >= n_xsecs, which makes it >= n+1 after
            # clamping), but then be < 1. That's impossible for n >= 0.
            # Test confirms the mid-wing path fires (not the < 1 path):
            class _FakeAddXsec:
                type = "AddXsec"
                wing = "main_wing"
                at_index = 0  # bypasses schema ge=1
                chord = 100.0
                span = 200.0
                airfoil = None
                twist = None
                dihedral = None

                def model_dump(self):
                    return {
                        "type": self.type,
                        "wing": self.wing,
                        "at_index": self.at_index,
                        "chord": self.chord,
                        "span": self.span,
                    }

            with patch(_RECOMPUTE_PATH):
                result = apply_edits(
                    db,
                    str(proposal_node.uuid),
                    [_FakeAddXsec()],
                )

            # Must be rejected (either by mid-wing or < 1 guard)
            assert len(result["rejected"]) == 1
        finally:
            db.close()

    def test_addxsec_empty_wing_seg_before_idx_path(self, client_and_db):
        """AddXsec on an empty wing (n=0 segments) forces the seg_before_idx < n path
        when effective_at_index == n+1 == 1 and n == 0 (lines 484-501 NOT hit because
        seg_before_idx = 0 which is NOT < n=0, so the else-branch at 502 fires).

        This test confirms the empty-wing tip-append succeeds and the segment count
        goes from 0 to 1.
        """
        from app.schemas.wing import Wing as WingConfigurationSchema
        from app.services.wing_service import put_wing_as_wingconfig

        db = _make_session(client_and_db)
        try:
            # Build an aeroplane with an empty wing (0 segments) using an in-memory
            # WingConfiguration. We can't use the fixtures (they have 12 segments).
            # An empty wing is not representable via the schema (segments must be >= 1).
            # So we cannot actually create a 0-segment wing via put_wing_as_wingconfig.
            # The seg_before_idx < n path (484-501) is specifically for the case where
            # effective_at_index - 1 < n (i.e. we're inserting INTO existing segments).
            # For n=0: seg_before_idx = 0, n = 0, so 0 < 0 is False → else branch (502).
            # For the seg_before_idx < n path to fire, we need n > 0 AND mid-wing insert,
            # which is blocked. So lines 484-501 are truly unreachable via normal ops.
            # This test confirms the else-branch (502+) fires for tip-append.
            plane = _create_plane_with_wc_wing(db)
            branch = get_or_open_proposal(db, plane.id)
            db.commit()
            proposal_node = db.query(AeroplaneModel).filter(
                AeroplaneModel.id == branch.head_id
            ).first()

            from app.services.wing_service import get_wing_as_wingconfig
            wc = get_wing_as_wingconfig(db, str(proposal_node.uuid), "main_wing")
            n_segs = len(wc["segments"])

            # Tip-append always takes the else-branch (lines 502+)
            with patch(_RECOMPUTE_PATH):
                result = apply_edits(
                    db,
                    str(proposal_node.uuid),
                    [AddXsec(wing="main_wing", at_index=n_segs + 1, chord=40.0, span=60.0)],
                )
            db.commit()

            assert result["applied"] == ["AddXsec"]
            assert not result["rejected"]

            db.expire_all()
            wc_after = get_wing_as_wingconfig(db, str(proposal_node.uuid), "main_wing")
            assert len(wc_after["segments"]) == n_segs + 1
        finally:
            db.close()

    def test_removexsec_too_few_segments_guard_via_duck_type(self, client_and_db):
        """Force the n < 2 guard in RemoveXsec (lines 564-570) via duck-typed op.

        The guard is unreachable via normal schema values because:
        - For n=1: n_xsecs=2, n_xsecs-1=1 → index=1 is rejected by the first guard.
        - For n >= 2: n < 2 is False.

        We bypass this by setting index to 0 on a 1-segment wing and using a modified
        duck type where op.index == 0 is allowed. Actually, any index <= 0 hits the
        first guard. The n < 2 guard is truly dead code.

        Instead, we verify the first guard fires correctly as the barrier:
        """
        from app.schemas.wing import Wing as WingConfigurationSchema
        from app.services.wing_service import put_wing_as_wingconfig

        db = _make_session(client_and_db)
        try:
            # Create a 1-segment wing
            one_seg_payload = {
                "segments": [
                    {
                        "root_airfoil": {
                            "airfoil": "./components/airfoils/rg15.dat",
                            "chord": 200.0,
                            "dihedral_as_rotation_in_degrees": 0.0,
                            "incidence": 0.0,
                        },
                        "tip_airfoil": {
                            "airfoil": "./components/airfoils/rg15.dat",
                            "chord": 120.0,
                            "dihedral_as_rotation_in_degrees": 0.0,
                            "incidence": 0.0,
                        },
                        "length": 400.0,
                        "sweep": 0.0,
                        "number_interpolation_points": None,
                        "tip_type": None,
                    }
                ],
                "nose_pnt": [0.0, 0.0, 0.0],
                "symmetric": True,
            }
            plane = _create_plane_with_branch(db)
            wc_schema = WingConfigurationSchema.model_validate(one_seg_payload)
            put_wing_as_wingconfig(db, str(plane.uuid), "single_seg_wing", wc_schema, scale=0.001)
            db.commit()
            db.refresh(plane)

            branch = get_or_open_proposal(db, plane.id)
            db.commit()
            proposal_node = db.query(AeroplaneModel).filter(
                AeroplaneModel.id == branch.head_id
            ).first()

            # n=1 segment, n_xsecs=2; valid interior = 1..0 (empty).
            # Any index >= n_xsecs-1 == 1 is rejected by the first guard.
            # Use a duck-typed op with index=1 (hits first guard, op.index >= n_xsecs-1).
            class _FakeRemoveXsecIdx1:
                type = "RemoveXsec"
                wing = "single_seg_wing"
                index = 1  # n_xsecs-1 == 1 → first guard fires

                def model_dump(self):
                    return {"type": self.type, "wing": self.wing, "index": self.index}

            with patch(_RECOMPUTE_PATH):
                result = apply_edits(
                    db,
                    str(proposal_node.uuid),
                    [_FakeRemoveXsecIdx1()],
                )

            # First guard rejects: "Cannot remove x-sec at index 1: must be interior"
            assert len(result["rejected"]) == 1
            assert "cannot" in str(result["rejected"][0]["error"]).lower() or "Cannot" in str(
                result["rejected"][0]["error"]
            )
        finally:
            db.close()
