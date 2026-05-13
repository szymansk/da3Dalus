"""Tests for Loading Scenarios (gh-488) — CG envelope from loading scenarios.

TDD RED phase: all tests fail until production code is implemented.

Covers:
- LoadingScenario CRUD
- Loading envelope computation
- Stability envelope computation
- Validation (Loading ⊆ Stability)
- 5-tier SM classification
- Backward compatibility (cg_agg_m remains)
- Templates per aircraft_class
- Retrim integration
"""
from __future__ import annotations

import uuid
from datetime import datetime, timezone
from typing import Tuple

import pytest
from fastapi.testclient import TestClient
from sqlalchemy.orm import Session

from app.models.aeroplanemodel import AeroplaneModel, DesignAssumptionModel


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

def _make_aeroplane(session: Session, *, name: str = "test-plane") -> AeroplaneModel:
    a = AeroplaneModel(name=name, uuid=uuid.uuid4(), total_mass_kg=1.5)
    session.add(a)
    session.commit()
    session.refresh(a)
    return a


def _seed_assumptions(session: Session, aeroplane_id: int, extra: dict | None = None) -> None:
    """Seed minimal design assumptions needed for CG envelope tests."""
    params = {
        "mass": 1.5,
        "cg_x": 0.15,
        "cl_max": 1.4,
        "cd0": 0.03,
        "target_static_margin": 0.08,
        "g_limit": 3.0,
        **(extra or {}),
    }
    for name, value in params.items():
        session.add(
            DesignAssumptionModel(
                aeroplane_id=aeroplane_id,
                parameter_name=name,
                estimate_value=value,
                active_source="ESTIMATE",
                updated_at=datetime.now(timezone.utc),
            )
        )
    session.commit()


def _scenario_payload(**overrides) -> dict:
    """Base loading scenario creation payload."""
    base = {
        "name": "Test Scenario",
        "aircraft_class": "rc_trainer",
        "component_overrides": {
            "toggles": [],
            "mass_overrides": [],
            "position_overrides": [],
            "adhoc_items": [],
        },
        "is_default": False,
    }
    base.update(overrides)
    return base


# ---------------------------------------------------------------------------
# TestLoadingScenarioCrud
# ---------------------------------------------------------------------------


class TestLoadingScenarioCrud:
    def test_create_scenario_with_overrides(self, client_and_db: Tuple[TestClient, any]) -> None:
        client, SessionLocal = client_and_db
        with SessionLocal() as session:
            plane = _make_aeroplane(session)
            aeroplane_uuid = str(plane.uuid)

        payload = _scenario_payload(
            name="Battery Fwd",
            component_overrides={
                "toggles": [],
                "mass_overrides": [
                    {"component_uuid": "abc123", "mass_kg_override": 0.3}
                ],
                "position_overrides": [
                    {"component_uuid": "abc123", "x_m_override": 0.05}
                ],
                "adhoc_items": [],
            },
        )
        resp = client.post(f"/aeroplanes/{aeroplane_uuid}/loading-scenarios", json=payload)
        assert resp.status_code == 201, resp.text
        data = resp.json()
        assert data["name"] == "Battery Fwd"
        assert data["aircraft_class"] == "rc_trainer"
        assert len(data["component_overrides"]["mass_overrides"]) == 1
        assert data["id"] is not None

    def test_create_scenario_with_adhoc_items(self, client_and_db: Tuple[TestClient, any]) -> None:
        """Adhoc items (Pilot, Payload) can be added to a scenario."""
        client, SessionLocal = client_and_db
        with SessionLocal() as session:
            plane = _make_aeroplane(session)
            aeroplane_uuid = str(plane.uuid)

        payload = _scenario_payload(
            name="With FPV Gear",
            component_overrides={
                "toggles": [],
                "mass_overrides": [],
                "position_overrides": [],
                "adhoc_items": [
                    {
                        "name": "FPV Camera",
                        "mass_kg": 0.05,
                        "x_m": 0.05,
                        "y_m": 0.0,
                        "z_m": 0.0,
                        "category": "fpv_gear",
                    }
                ],
            },
        )
        resp = client.post(f"/aeroplanes/{aeroplane_uuid}/loading-scenarios", json=payload)
        assert resp.status_code == 201, resp.text
        data = resp.json()
        assert len(data["component_overrides"]["adhoc_items"]) == 1
        assert data["component_overrides"]["adhoc_items"][0]["category"] == "fpv_gear"

    def test_list_scenarios(self, client_and_db: Tuple[TestClient, any]) -> None:
        client, SessionLocal = client_and_db
        with SessionLocal() as session:
            plane = _make_aeroplane(session)
            aeroplane_uuid = str(plane.uuid)

        client.post(
            f"/aeroplanes/{aeroplane_uuid}/loading-scenarios",
            json=_scenario_payload(name="Scenario A"),
        )
        client.post(
            f"/aeroplanes/{aeroplane_uuid}/loading-scenarios",
            json=_scenario_payload(name="Scenario B"),
        )

        resp = client.get(f"/aeroplanes/{aeroplane_uuid}/loading-scenarios")
        assert resp.status_code == 200, resp.text
        data = resp.json()
        assert len(data) == 2
        names = {s["name"] for s in data}
        assert names == {"Scenario A", "Scenario B"}

    def test_update_scenario(self, client_and_db: Tuple[TestClient, any]) -> None:
        client, SessionLocal = client_and_db
        with SessionLocal() as session:
            plane = _make_aeroplane(session)
            aeroplane_uuid = str(plane.uuid)

        create_resp = client.post(
            f"/aeroplanes/{aeroplane_uuid}/loading-scenarios",
            json=_scenario_payload(name="Old Name"),
        )
        scenario_id = create_resp.json()["id"]

        patch_resp = client.patch(
            f"/aeroplanes/{aeroplane_uuid}/loading-scenarios/{scenario_id}",
            json={"name": "New Name"},
        )
        assert patch_resp.status_code == 200, patch_resp.text
        assert patch_resp.json()["name"] == "New Name"

    def test_delete_scenario(self, client_and_db: Tuple[TestClient, any]) -> None:
        client, SessionLocal = client_and_db
        with SessionLocal() as session:
            plane = _make_aeroplane(session)
            aeroplane_uuid = str(plane.uuid)

        create_resp = client.post(
            f"/aeroplanes/{aeroplane_uuid}/loading-scenarios",
            json=_scenario_payload(name="To Delete"),
        )
        scenario_id = create_resp.json()["id"]

        del_resp = client.delete(
            f"/aeroplanes/{aeroplane_uuid}/loading-scenarios/{scenario_id}"
        )
        assert del_resp.status_code == 204, del_resp.text

        list_resp = client.get(f"/aeroplanes/{aeroplane_uuid}/loading-scenarios")
        assert list_resp.status_code == 200
        assert list_resp.json() == []

    def test_is_default_flag(self, client_and_db: Tuple[TestClient, any]) -> None:
        """is_default=True marks a scenario as the default for backward-compat cg_agg_m."""
        client, SessionLocal = client_and_db
        with SessionLocal() as session:
            plane = _make_aeroplane(session)
            aeroplane_uuid = str(plane.uuid)

        resp = client.post(
            f"/aeroplanes/{aeroplane_uuid}/loading-scenarios",
            json=_scenario_payload(name="Default Scenario", is_default=True),
        )
        assert resp.status_code == 201, resp.text
        assert resp.json()["is_default"] is True

    def test_list_scenarios_returns_empty_for_no_scenarios(
        self, client_and_db: Tuple[TestClient, any]
    ) -> None:
        client, SessionLocal = client_and_db
        with SessionLocal() as session:
            plane = _make_aeroplane(session)
            aeroplane_uuid = str(plane.uuid)

        resp = client.get(f"/aeroplanes/{aeroplane_uuid}/loading-scenarios")
        assert resp.status_code == 200
        assert resp.json() == []


# ---------------------------------------------------------------------------
# TestLoadingEnvelope
# ---------------------------------------------------------------------------


class TestLoadingEnvelope:
    def test_loading_envelope_min_max_across_scenarios(
        self, client_and_db: Tuple[TestClient, any]
    ) -> None:
        """Loading envelope is min/max CG across all scenarios with adhoc items."""
        from app.services.loading_scenario_service import compute_loading_envelope_for_aeroplane

        client, SessionLocal = client_and_db
        with SessionLocal() as session:
            plane = _make_aeroplane(session)
            _seed_assumptions(session, plane.id)
            aeroplane_uuid = str(plane.uuid)

        # Scenario A: forward CG (heavy item at front)
        client.post(
            f"/aeroplanes/{aeroplane_uuid}/loading-scenarios",
            json=_scenario_payload(
                name="Fwd",
                component_overrides={
                    "toggles": [],
                    "mass_overrides": [],
                    "position_overrides": [],
                    "adhoc_items": [
                        {"name": "Ballast", "mass_kg": 0.5, "x_m": 0.05, "y_m": 0.0, "z_m": 0.0}
                    ],
                },
            ),
        )
        # Scenario B: aft CG (heavy item at rear)
        client.post(
            f"/aeroplanes/{aeroplane_uuid}/loading-scenarios",
            json=_scenario_payload(
                name="Aft",
                component_overrides={
                    "toggles": [],
                    "mass_overrides": [],
                    "position_overrides": [],
                    "adhoc_items": [
                        {"name": "Payload", "mass_kg": 0.5, "x_m": 0.40, "y_m": 0.0, "z_m": 0.0}
                    ],
                },
            ),
        )

        with SessionLocal() as session:
            plane = session.query(AeroplaneModel).filter_by(uuid=plane.uuid).first()
            envelope = compute_loading_envelope_for_aeroplane(session, plane)

        assert envelope["cg_loading_fwd_m"] < envelope["cg_loading_aft_m"]
        # fwd scenario shifts CG forward from base (0.15), aft scenario shifts it aft
        assert envelope["cg_loading_fwd_m"] < 0.15
        assert envelope["cg_loading_aft_m"] > 0.15

    def test_adhoc_items_shift_cg(self, client_and_db: Tuple[TestClient, any]) -> None:
        """Adding adhoc items to a scenario changes the computed CG."""
        from app.services.loading_scenario_service import compute_scenario_cg

        _client, SessionLocal = client_and_db
        with SessionLocal() as session:
            plane = _make_aeroplane(session)
            _seed_assumptions(session, plane.id)

        # Base mass 1.5 kg at x=0.15, adding 0.5 kg at x=0.05
        # Expected CG = (1.5*0.15 + 0.5*0.05) / (1.5+0.5) = (0.225+0.025)/2.0 = 0.125
        adhoc = [{"name": "Fwd Ballast", "mass_kg": 0.5, "x_m": 0.05, "y_m": 0.0, "z_m": 0.0}]
        cg_x = compute_scenario_cg(
            base_mass_kg=1.5,
            base_cg_x=0.15,
            adhoc_items=adhoc,
            mass_overrides=[],
        )
        assert abs(cg_x - 0.125) < 1e-9, f"Expected 0.125, got {cg_x}"

    def test_toggles_disable_components(self, client_and_db: Tuple[TestClient, any]) -> None:
        """A disabled toggle reduces mass (and shifts CG)."""
        from app.services.loading_scenario_service import compute_scenario_cg

        _client, _SessionLocal = client_and_db

        # Remove 0.3 kg item at x=0.30 from 1.5 kg plane
        # Remaining: 1.2 kg at weighted CG
        # This test just checks cg_x computes differently with a toggle
        # We model toggles by subtracting the item from the base mass.
        # If no component data is available (pure unit test), just verify the function signature.
        cg_x_no_toggle = compute_scenario_cg(
            base_mass_kg=1.5,
            base_cg_x=0.15,
            adhoc_items=[],
            mass_overrides=[],
        )
        assert cg_x_no_toggle == pytest.approx(0.15)

    def test_no_scenarios_returns_base_cg(self, client_and_db: Tuple[TestClient, any]) -> None:
        """Without any loading scenarios, loading envelope uses the base design cg_x."""
        from app.services.loading_scenario_service import compute_loading_envelope_for_aeroplane

        _client, SessionLocal = client_and_db
        with SessionLocal() as session:
            plane = _make_aeroplane(session)
            _seed_assumptions(session, plane.id)
            envelope = compute_loading_envelope_for_aeroplane(session, plane)

        # No scenarios → forward = aft = design cg_x (0.15 from assumptions)
        assert envelope["cg_loading_fwd_m"] == pytest.approx(0.15)
        assert envelope["cg_loading_aft_m"] == pytest.approx(0.15)


# ---------------------------------------------------------------------------
# TestStabilityEnvelope
# ---------------------------------------------------------------------------


class TestStabilityEnvelope:
    def test_stability_envelope_aft_uses_target_sm(
        self, client_and_db: Tuple[TestClient, any]
    ) -> None:
        """cg_stability_aft = x_NP - target_sm * MAC (Anderson §7.5)."""
        from app.services.loading_scenario_service import compute_stability_envelope

        # x_NP = 0.30, MAC = 0.20, target_sm = 0.08
        # cg_stability_aft = 0.30 - 0.08 * 0.20 = 0.284
        envelope = compute_stability_envelope(
            x_np=0.30,
            mac=0.20,
            target_sm=0.08,
        )
        assert envelope["cg_stability_aft_m"] == pytest.approx(0.30 - 0.08 * 0.20)

    def test_stability_envelope_fwd_stub(
        self, client_and_db: Tuple[TestClient, any]
    ) -> None:
        """cg_stability_fwd uses stub value: x_NP - 0.30 * MAC.

        TODO: replace with full elevator-authority calculation as follow-up ticket.
        Conservative stub per Anderson §7.7.
        """
        from app.services.loading_scenario_service import compute_stability_envelope

        # x_NP = 0.30, MAC = 0.20
        # cg_stability_fwd = 0.30 - 0.30 * 0.20 = 0.24
        envelope = compute_stability_envelope(
            x_np=0.30,
            mac=0.20,
            target_sm=0.08,
        )
        assert envelope["cg_stability_fwd_m"] == pytest.approx(0.30 - 0.30 * 0.20)

    def test_stability_envelope_aft_gt_fwd(
        self, client_and_db: Tuple[TestClient, any]
    ) -> None:
        """Aft stability limit must be forward of NP; fwd must be forward of aft."""
        from app.services.loading_scenario_service import compute_stability_envelope

        envelope = compute_stability_envelope(x_np=0.30, mac=0.20, target_sm=0.08)
        # fwd < aft < NP
        assert envelope["cg_stability_fwd_m"] < envelope["cg_stability_aft_m"]
        assert envelope["cg_stability_aft_m"] < 0.30


# ---------------------------------------------------------------------------
# TestValidation
# ---------------------------------------------------------------------------


class TestValidation:
    def test_loading_envelope_within_stability_envelope_passes(
        self, client_and_db: Tuple[TestClient, any]
    ) -> None:
        """No warning when loading CG range is within stability envelope."""
        from app.services.loading_scenario_service import validate_cg_envelope

        warnings = validate_cg_envelope(
            cg_loading_fwd_m=0.22,
            cg_loading_aft_m=0.26,
            cg_stability_fwd_m=0.18,
            cg_stability_aft_m=0.28,
        )
        assert warnings == []

    def test_loading_envelope_outside_stability_aft_raises(
        self, client_and_db: Tuple[TestClient, any]
    ) -> None:
        """Error when loading CG aft exceeds stability aft limit."""
        from app.services.loading_scenario_service import validate_cg_envelope

        warnings = validate_cg_envelope(
            cg_loading_fwd_m=0.22,
            cg_loading_aft_m=0.30,  # Exceeds stability aft 0.28
            cg_stability_fwd_m=0.18,
            cg_stability_aft_m=0.28,
        )
        assert any("aft" in w.lower() for w in warnings)

    def test_loading_envelope_outside_stability_fwd_warns(
        self, client_and_db: Tuple[TestClient, any]
    ) -> None:
        """Warning when loading CG forward is ahead of stability forward limit."""
        from app.services.loading_scenario_service import validate_cg_envelope

        warnings = validate_cg_envelope(
            cg_loading_fwd_m=0.16,  # Forward of stability fwd 0.18
            cg_loading_aft_m=0.26,
            cg_stability_fwd_m=0.18,
            cg_stability_aft_m=0.28,
        )
        assert any("forward" in w.lower() or "fwd" in w.lower() for w in warnings)


# ---------------------------------------------------------------------------
# TestSmClassification5Tier
# ---------------------------------------------------------------------------


_SM_CASES = [
    # (sm, target, expected_tier)
    (0.01, 0.08, "error"),    # sm < 0.02 → ERROR (unstable)
    (0.04, 0.08, "warn"),     # 0.02 ≤ sm < target → WARN (low margin)
    (0.10, 0.08, "ok"),       # target ≤ sm ≤ 0.20 → OK
    (0.22, 0.08, "warn"),     # 0.20 < sm ≤ 0.30 → WARN (heavy nose)
    (0.32, 0.08, "error"),    # sm > 0.30 → ERROR (elevator authority)
]


class TestSmClassification5Tier:
    @pytest.mark.parametrize("sm,target,expected", _SM_CASES)
    def test_classification_relative_to_target_sm(
        self, sm: float, target: float, expected: str, client_and_db: Tuple[TestClient, any]
    ) -> None:
        from app.services.loading_scenario_service import classify_sm

        result = classify_sm(sm=sm, target_sm=target)
        assert result == expected, f"classify_sm({sm}, {target}) = {result!r}, want {expected!r}"


# ---------------------------------------------------------------------------
# TestBackwardCompat
# ---------------------------------------------------------------------------


class TestBackwardCompat:
    def test_cg_agg_m_remains_in_context(self, client_and_db: Tuple[TestClient, any]) -> None:
        """assumption_computation_context still contains cg_agg_m after gh-488."""
        _client, SessionLocal = client_and_db
        with SessionLocal() as session:
            plane = _make_aeroplane(session)
            # Write a fake context that has cg_agg_m (simulating pre-existing data)
            plane.assumption_computation_context = {
                "cg_agg_m": 0.15,
                "mac_m": 0.18,
                "x_np_m": 0.25,
                "target_static_margin": 0.08,
            }
            session.commit()
            session.refresh(plane)
            ctx = plane.assumption_computation_context
            assert "cg_agg_m" in ctx

    def test_new_keys_additively_added(self, client_and_db: Tuple[TestClient, any]) -> None:
        """New context keys (cg_forward_m, cg_aft_m, sm_at_fwd, sm_at_aft) are additive."""
        from app.services.loading_scenario_service import enrich_context_with_cg_envelope

        ctx: dict = {
            "cg_agg_m": 0.15,
            "mac_m": 0.18,
            "x_np_m": 0.25,
            "target_static_margin": 0.08,
        }
        enriched = enrich_context_with_cg_envelope(
            ctx=ctx,
            cg_loading_fwd_m=0.14,
            cg_loading_aft_m=0.17,
            cg_stability_fwd_m=0.10,
            cg_stability_aft_m=0.23,
        )
        # Original keys preserved
        assert enriched["cg_agg_m"] == 0.15
        # New keys added
        assert "cg_forward_m" in enriched
        assert "cg_aft_m" in enriched
        assert "sm_at_fwd" in enriched
        assert "sm_at_aft" in enriched

    def test_no_scenarios_falls_back_to_legacy_cg(
        self, client_and_db: Tuple[TestClient, any]
    ) -> None:
        """Without loading scenarios, cg_agg_m equals design cg_x (backward compat)."""
        from app.services.loading_scenario_service import compute_loading_envelope_for_aeroplane

        _client, SessionLocal = client_and_db
        with SessionLocal() as session:
            plane = _make_aeroplane(session)
            _seed_assumptions(session, plane.id)
            envelope = compute_loading_envelope_for_aeroplane(session, plane)

        # No scenarios → fwd = aft = design cg_x = 0.15
        assert envelope["cg_loading_fwd_m"] == pytest.approx(0.15)
        assert envelope["cg_loading_aft_m"] == pytest.approx(0.15)

    def test_cg_endpoint_still_returns_cg_envelope_read(
        self, client_and_db: Tuple[TestClient, any]
    ) -> None:
        """GET /cg-envelope returns the CgEnvelopeRead schema."""
        client, SessionLocal = client_and_db
        with SessionLocal() as session:
            plane = _make_aeroplane(session)
            _seed_assumptions(session, plane.id)
            aeroplane_uuid = str(plane.uuid)

        resp = client.get(f"/aeroplanes/{aeroplane_uuid}/cg-envelope")
        assert resp.status_code == 200, resp.text
        data = resp.json()
        required_keys = {
            "cg_loading_fwd_m",
            "cg_loading_aft_m",
            "cg_stability_fwd_m",
            "cg_stability_aft_m",
            "sm_at_fwd",
            "sm_at_aft",
            "classification",
            "warnings",
        }
        assert required_keys.issubset(data.keys()), f"Missing keys: {required_keys - data.keys()}"


# ---------------------------------------------------------------------------
# TestTemplatesPerAircraftClass
# ---------------------------------------------------------------------------


_AIRCRAFT_CLASSES = [
    "rc_trainer",
    "rc_aerobatic",
    "rc_combust",
    "uav_survey",
    "glider",
    "boxwing",
]


class TestTemplatesPerAircraftClass:
    @pytest.mark.parametrize("ac", _AIRCRAFT_CLASSES)
    def test_template_for_class(
        self, ac: str, client_and_db: Tuple[TestClient, any]
    ) -> None:
        """Every aircraft_class has at least one loading scenario template."""
        from app.services.loading_template_service import get_templates_for_class

        templates = get_templates_for_class(ac)
        assert len(templates) >= 1, f"No templates for {ac}"
        for t in templates:
            assert "name" in t, f"Template missing 'name': {t}"

    def test_templates_endpoint(self, client_and_db: Tuple[TestClient, any]) -> None:
        """GET /loading-scenarios/templates?aircraft_class=rc_trainer returns templates."""
        client, SessionLocal = client_and_db
        with SessionLocal() as session:
            plane = _make_aeroplane(session)
            aeroplane_uuid = str(plane.uuid)

        resp = client.get(
            f"/aeroplanes/{aeroplane_uuid}/loading-scenarios/templates",
            params={"aircraft_class": "rc_trainer"},
        )
        assert resp.status_code == 200, resp.text
        data = resp.json()
        assert isinstance(data, list)
        assert len(data) >= 1


# ---------------------------------------------------------------------------
# TestRetrimIntegration
# ---------------------------------------------------------------------------


class TestRetrimIntegration:
    def test_loading_scenario_change_marks_ops_dirty(
        self, client_and_db: Tuple[TestClient, any]
    ) -> None:
        """Creating a loading scenario triggers mark_ops_dirty for the aeroplane."""
        from app.models.analysismodels import OperatingPointModel
        from app.tests.conftest import make_operating_point

        client, SessionLocal = client_and_db
        with SessionLocal() as session:
            plane = _make_aeroplane(session)
            aeroplane_uuid = str(plane.uuid)
            op = make_operating_point(session, aircraft_id=plane.id, status="TRIMMED")

        # Create a loading scenario → should mark OPs DIRTY
        client.post(
            f"/aeroplanes/{aeroplane_uuid}/loading-scenarios",
            json=_scenario_payload(name="Dirty Trigger"),
        )

        with SessionLocal() as session:
            op_row = session.query(OperatingPointModel).filter_by(id=op.id).first()
            assert op_row is not None
            assert op_row.status == "DIRTY", f"Expected DIRTY, got {op_row.status}"

    def test_assumption_changed_event_emitted(
        self, client_and_db: Tuple[TestClient, any]
    ) -> None:
        """Creating a loading scenario emits AssumptionChanged(cg_x) event."""
        from app.core.events import AssumptionChanged, event_bus

        received: list[AssumptionChanged] = []
        event_bus.subscribe(AssumptionChanged, received.append)

        client, SessionLocal = client_and_db
        with SessionLocal() as session:
            plane = _make_aeroplane(session)
            aeroplane_uuid = str(plane.uuid)

        try:
            client.post(
                f"/aeroplanes/{aeroplane_uuid}/loading-scenarios",
                json=_scenario_payload(name="Event Trigger"),
            )
        finally:
            event_bus._subscribers.pop(AssumptionChanged, None)

        assert any(e.parameter_name == "cg_x" for e in received), (
            f"AssumptionChanged(cg_x) not emitted. Got: {received}"
        )


# ---------------------------------------------------------------------------
# TestComponentOverridesAffectCg  (Issue C — all 4 override types)
# ---------------------------------------------------------------------------


def _make_weight_items(session, aeroplane_id: int) -> tuple:
    """Create two WeightItemModel rows: 'fuselage' and 'battery'.

    Returns (fuselage_item, battery_item) — both committed and refreshed.
    """
    from app.models.aeroplanemodel import WeightItemModel

    fuselage = WeightItemModel(
        aeroplane_id=aeroplane_id,
        name="Fuselage",
        mass_kg=1.0,
        x_m=0.20,
        y_m=0.0,
        z_m=0.0,
        category="structural",
    )
    battery = WeightItemModel(
        aeroplane_id=aeroplane_id,
        name="Battery",
        mass_kg=0.3,
        x_m=0.10,
        y_m=0.0,
        z_m=0.0,
        category="electronics",
    )
    session.add_all([fuselage, battery])
    session.commit()
    session.refresh(fuselage)
    session.refresh(battery)
    return fuselage, battery


class TestComponentOverridesAffectCg:
    """Issue C: compute_scenario_cg must honour all 4 override types."""

    def test_mass_override_shifts_cg(self, client_and_db: Tuple[TestClient, any]) -> None:
        """Doubling the battery mass (0.3→0.6 kg) shifts CG toward battery position."""
        from app.services.loading_scenario_service import compute_scenario_cg

        _client, SessionLocal = client_and_db
        with SessionLocal() as session:
            plane = _make_aeroplane(session)
            fuselage, battery = _make_weight_items(session, plane.id)
            fus_uuid = str(fuselage.id)
            bat_uuid = str(battery.id)

        # Components as plain dicts (same shape as WeightItemModel fields)
        components = [
            {"id": fus_uuid, "mass_kg": 1.0, "x_m": 0.20, "y_m": 0.0, "z_m": 0.0},
            {"id": bat_uuid, "mass_kg": 0.3, "x_m": 0.10, "y_m": 0.0, "z_m": 0.0},
        ]

        # Base CG: (1.0*0.20 + 0.3*0.10) / 1.3 = 0.23/1.3 ≈ 0.1769
        base_cg = compute_scenario_cg(
            base_mass_kg=1.3,
            base_cg_x=0.0,  # ignored when components provided
            adhoc_items=[],
            mass_overrides=[],
            toggles=[],
            position_overrides=[],
            components=components,
        )
        assert abs(base_cg - (1.0 * 0.20 + 0.3 * 0.10) / 1.3) < 1e-9

        # Override battery mass 0.3→0.6 kg → CG shifts toward battery (x=0.10, forward)
        overridden_cg = compute_scenario_cg(
            base_mass_kg=1.6,
            base_cg_x=0.0,
            adhoc_items=[],
            mass_overrides=[{"component_uuid": bat_uuid, "mass_kg_override": 0.6}],
            toggles=[],
            position_overrides=[],
            components=components,
        )
        # Expected: (1.0*0.20 + 0.6*0.10) / 1.6 = 0.26/1.6 = 0.1625
        assert abs(overridden_cg - (1.0 * 0.20 + 0.6 * 0.10) / 1.6) < 1e-9
        # Battery is forward of base CG → heavier battery → more forward CG
        assert overridden_cg < base_cg

    def test_position_override_shifts_cg(self, client_and_db: Tuple[TestClient, any]) -> None:
        """Moving battery 50mm forward (x=0.10→0.05) shifts CG forward."""
        from app.services.loading_scenario_service import compute_scenario_cg

        _client, SessionLocal = client_and_db
        with SessionLocal() as session:
            plane = _make_aeroplane(session)
            fuselage, battery = _make_weight_items(session, plane.id)
            fus_uuid = str(fuselage.id)
            bat_uuid = str(battery.id)

        components = [
            {"id": fus_uuid, "mass_kg": 1.0, "x_m": 0.20, "y_m": 0.0, "z_m": 0.0},
            {"id": bat_uuid, "mass_kg": 0.3, "x_m": 0.10, "y_m": 0.0, "z_m": 0.0},
        ]

        base_cg = compute_scenario_cg(
            base_mass_kg=1.3, base_cg_x=0.0,
            adhoc_items=[], mass_overrides=[], toggles=[], position_overrides=[],
            components=components,
        )

        # Move battery from x=0.10 to x=0.05 (50mm forward)
        shifted_cg = compute_scenario_cg(
            base_mass_kg=1.3, base_cg_x=0.0,
            adhoc_items=[], mass_overrides=[], toggles=[],
            position_overrides=[{"component_uuid": bat_uuid, "x_m_override": 0.05}],
            components=components,
        )
        # Expected: (1.0*0.20 + 0.3*0.05) / 1.3 = 0.215/1.3 ≈ 0.1654
        assert abs(shifted_cg - (1.0 * 0.20 + 0.3 * 0.05) / 1.3) < 1e-9
        assert shifted_cg < base_cg

    def test_toggle_disabled_excludes_component(
        self, client_and_db: Tuple[TestClient, any]
    ) -> None:
        """Battery enabled=False → CG computed without battery contribution."""
        from app.services.loading_scenario_service import compute_scenario_cg

        _client, SessionLocal = client_and_db
        with SessionLocal() as session:
            plane = _make_aeroplane(session)
            fuselage, battery = _make_weight_items(session, plane.id)
            fus_uuid = str(fuselage.id)
            bat_uuid = str(battery.id)

        components = [
            {"id": fus_uuid, "mass_kg": 1.0, "x_m": 0.20, "y_m": 0.0, "z_m": 0.0},
            {"id": bat_uuid, "mass_kg": 0.3, "x_m": 0.10, "y_m": 0.0, "z_m": 0.0},
        ]

        # Disable battery → only fuselage remains
        no_battery_cg = compute_scenario_cg(
            base_mass_kg=1.3, base_cg_x=0.0,
            adhoc_items=[], mass_overrides=[],
            toggles=[{"component_uuid": bat_uuid, "enabled": False}],
            position_overrides=[],
            components=components,
        )
        # Expected: fuselage only → CG = 0.20
        assert abs(no_battery_cg - 0.20) < 1e-9

    def test_combined_overrides(self, client_and_db: Tuple[TestClient, any]) -> None:
        """All 4 override types applied simultaneously produce correct CG."""
        from app.services.loading_scenario_service import compute_scenario_cg

        _client, SessionLocal = client_and_db
        with SessionLocal() as session:
            plane = _make_aeroplane(session)
            fuselage, battery = _make_weight_items(session, plane.id)
            fus_uuid = str(fuselage.id)
            bat_uuid = str(battery.id)

        # Add a third component (motor)
        from app.models.aeroplanemodel import WeightItemModel
        with SessionLocal() as session:
            motor = WeightItemModel(
                aeroplane_id=plane.id, name="Motor", mass_kg=0.2,
                x_m=0.35, y_m=0.0, z_m=0.0, category="propulsion",
            )
            session.add(motor)
            session.commit()
            session.refresh(motor)
            motor_uuid = str(motor.id)

        components = [
            {"id": fus_uuid, "mass_kg": 1.0, "x_m": 0.20, "y_m": 0.0, "z_m": 0.0},
            {"id": bat_uuid, "mass_kg": 0.3, "x_m": 0.10, "y_m": 0.0, "z_m": 0.0},
            {"id": motor_uuid, "mass_kg": 0.2, "x_m": 0.35, "y_m": 0.0, "z_m": 0.0},
        ]

        # mass_override: battery 0.3→0.5 kg
        # position_override: motor x=0.35→0.30
        # toggle: fuselage stays on, motor stays on
        # adhoc: 0.1 kg camera at x=0.05
        cg = compute_scenario_cg(
            base_mass_kg=1.5, base_cg_x=0.0,
            adhoc_items=[{"name": "Camera", "mass_kg": 0.1, "x_m": 0.05, "y_m": 0.0, "z_m": 0.0}],
            mass_overrides=[{"component_uuid": bat_uuid, "mass_kg_override": 0.5}],
            toggles=[],
            position_overrides=[{"component_uuid": motor_uuid, "x_m_override": 0.30}],
            components=components,
        )
        # Expected:
        #   fuselage: 1.0 kg @ 0.20
        #   battery:  0.5 kg @ 0.10 (mass override)
        #   motor:    0.2 kg @ 0.30 (position override)
        #   camera:   0.1 kg @ 0.05 (adhoc)
        # total: 1.8, moment: 0.20 + 0.05 + 0.06 + 0.005 = 0.315
        # CG = 0.315/1.8 = 0.175
        expected = (1.0 * 0.20 + 0.5 * 0.10 + 0.2 * 0.30 + 0.1 * 0.05) / (1.0 + 0.5 + 0.2 + 0.1)
        assert abs(cg - expected) < 1e-9

    def test_overrides_fall_back_to_base_when_no_components(
        self, client_and_db: Tuple[TestClient, any]
    ) -> None:
        """When components=None, function uses legacy base_mass/base_cg_x (backward compat)."""
        from app.services.loading_scenario_service import compute_scenario_cg

        _client, SessionLocal = client_and_db

        # Old call signature — no components param
        cg = compute_scenario_cg(
            base_mass_kg=1.5,
            base_cg_x=0.15,
            adhoc_items=[{"name": "Item", "mass_kg": 0.5, "x_m": 0.05, "y_m": 0.0, "z_m": 0.0}],
            mass_overrides=[],
        )
        # (1.5*0.15 + 0.5*0.05) / 2.0 = 0.25/2.0 = 0.125
        assert abs(cg - 0.125) < 1e-9


# ---------------------------------------------------------------------------
# TestMissingContextFallback  (Issue A — no deceptive x_np synthesis)
# ---------------------------------------------------------------------------


class TestMissingContextFallback:
    def test_stability_envelope_returns_none_when_no_context(
        self, client_and_db: Tuple[TestClient, any]
    ) -> None:
        """compute_stability_envelope with x_np=None returns None values."""
        from app.services.loading_scenario_service import compute_stability_envelope

        result = compute_stability_envelope(x_np=None, mac=None, target_sm=0.08)
        assert result["cg_stability_aft_m"] is None
        assert result["cg_stability_fwd_m"] is None

    def test_cg_envelope_warns_when_stability_unknown(
        self, client_and_db: Tuple[TestClient, any]
    ) -> None:
        """GET /cg-envelope returns 'stability_unavailable' warning when x_np not computed yet."""
        client, SessionLocal = client_and_db
        with SessionLocal() as session:
            plane = _make_aeroplane(session)
            _seed_assumptions(session, plane.id)
            # Deliberately NO assumption_computation_context → x_np missing
            plane.assumption_computation_context = {}
            session.commit()
            aeroplane_uuid = str(plane.uuid)

        resp = client.get(f"/aeroplanes/{aeroplane_uuid}/cg-envelope")
        assert resp.status_code == 200, resp.text
        data = resp.json()

        # Stability fields must be null, not fabricated
        assert data["cg_stability_fwd_m"] is None
        assert data["cg_stability_aft_m"] is None
        assert data["sm_at_fwd"] is None
        assert data["sm_at_aft"] is None

        # Classification must be "unknown" (not "ok" from a fake-perfect envelope)
        assert data["classification"] == "unknown"

        # Must contain an explicit stability_unavailable warning
        assert any("stability" in w.lower() and "unavailable" in w.lower() for w in data["warnings"]), (
            f"Expected 'stability unavailable' warning. Got: {data['warnings']}"
        )

    def test_no_false_positive_perfect_envelope(
        self, client_and_db: Tuple[TestClient, any]
    ) -> None:
        """Without real aero data, sm_at_aft must NOT equal target_sm (deceptive)."""
        client, SessionLocal = client_and_db
        with SessionLocal() as session:
            plane = _make_aeroplane(session)
            _seed_assumptions(session, plane.id)
            plane.assumption_computation_context = {}
            session.commit()
            aeroplane_uuid = str(plane.uuid)

        resp = client.get(f"/aeroplanes/{aeroplane_uuid}/cg-envelope")
        assert resp.status_code == 200, resp.text
        data = resp.json()

        # The old code synthesised x_np = cg_x + target_sm*MAC which made
        # sm_at_aft == target_sm always (deceptive "perfect" envelope).
        # After the fix, sm_at_aft must be None.
        assert data["sm_at_aft"] is None, (
            f"sm_at_aft should be None when x_np not computed. Got {data['sm_at_aft']!r}"
        )


# ---------------------------------------------------------------------------
# TestCgAggMatchesDefaultScenario  (Issue B — cg_agg_m wiring)
# ---------------------------------------------------------------------------


class TestCgAggMatchesDefaultScenario:
    def test_cg_agg_m_equals_default_scenario_cg_after_recompute(
        self, client_and_db: Tuple[TestClient, any]
    ) -> None:
        """cg_agg_m in context equals the CG of the is_default scenario."""
        from app.services.loading_scenario_service import compute_scenario_cg

        client, SessionLocal = client_and_db
        with SessionLocal() as session:
            plane = _make_aeroplane(session)
            _seed_assumptions(session, plane.id)
            aeroplane_uuid = str(plane.uuid)

        # Create a default scenario with an adhoc item that shifts CG
        create_resp = client.post(
            f"/aeroplanes/{aeroplane_uuid}/loading-scenarios",
            json=_scenario_payload(
                name="Default",
                is_default=True,
                component_overrides={
                    "toggles": [],
                    "mass_overrides": [],
                    "position_overrides": [],
                    "adhoc_items": [
                        {"name": "Payload", "mass_kg": 0.5, "x_m": 0.25, "y_m": 0.0, "z_m": 0.0}
                    ],
                },
            ),
        )
        assert create_resp.status_code == 201, create_resp.text

        # Manually call compute_cg_agg_for_aeroplane to check it matches
        from app.services.loading_scenario_service import compute_cg_agg_for_aeroplane

        with SessionLocal() as session:
            plane_row = session.query(AeroplaneModel).filter_by(uuid=plane.uuid).first()
            cg_agg = compute_cg_agg_for_aeroplane(session, plane_row)

        # base: mass=1.5, cg_x=0.15; adhoc: 0.5 kg at 0.25
        # expected CG = (1.5*0.15 + 0.5*0.25) / 2.0 = (0.225 + 0.125) / 2.0 = 0.175
        expected = (1.5 * 0.15 + 0.5 * 0.25) / 2.0
        assert abs(cg_agg - expected) < 1e-9, f"Expected {expected}, got {cg_agg}"

    def test_cg_agg_m_falls_back_to_legacy_when_no_scenarios(
        self, client_and_db: Tuple[TestClient, any]
    ) -> None:
        """When no loading scenarios exist, compute_cg_agg falls back to legacy weight items."""
        from app.services.loading_scenario_service import compute_cg_agg_for_aeroplane
        from app.models.aeroplanemodel import WeightItemModel

        _client, SessionLocal = client_and_db
        with SessionLocal() as session:
            plane = _make_aeroplane(session)
            _seed_assumptions(session, plane.id)
            # Add weight items (no loading scenarios)
            wi = WeightItemModel(
                aeroplane_id=plane.id, name="Motor", mass_kg=0.5,
                x_m=0.30, y_m=0.0, z_m=0.0, category="propulsion",
            )
            session.add(wi)
            session.commit()
            session.refresh(plane)

        with SessionLocal() as session:
            plane_row = session.query(AeroplaneModel).filter_by(uuid=plane.uuid).first()
            cg_agg = compute_cg_agg_for_aeroplane(session, plane_row)

        # No scenarios → falls back to weight-items aggregation → motor at x=0.30
        # Only one item → cg = 0.30
        assert abs(cg_agg - 0.30) < 1e-9, f"Expected 0.30 (legacy fallback), got {cg_agg}"
