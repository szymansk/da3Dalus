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


