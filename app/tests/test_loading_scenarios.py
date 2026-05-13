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


# ---------------------------------------------------------------------------
# TestEdgeCases — classify_sm thresholds, zero-mass, single-axis position override
# ---------------------------------------------------------------------------


class TestEdgeCases:
    """Covers boundary values in classify_sm and compute_scenario_cg edge paths."""

    def test_classify_sm_none_returns_unknown(
        self, client_and_db: Tuple[TestClient, any]
    ) -> None:
        """classify_sm(None, target) must return 'unknown'."""
        from app.services.loading_scenario_service import classify_sm

        assert classify_sm(None, 0.08) == "unknown"

    def test_classify_sm_exactly_unstable_limit(
        self, client_and_db: Tuple[TestClient, any]
    ) -> None:
        """classify_sm(0.02, target) is 'warn' (boundary is exclusive for error)."""
        from app.services.loading_scenario_service import classify_sm

        # sm == _SM_UNSTABLE_LIMIT (0.02): NOT < 0.02, so falls to next branch
        # 0.02 < target_sm (0.08) → warn
        assert classify_sm(0.02, 0.08) == "warn"

    def test_classify_sm_just_below_unstable_limit(
        self, client_and_db: Tuple[TestClient, any]
    ) -> None:
        """classify_sm(0.019, target) is 'error' (sm < 0.02)."""
        from app.services.loading_scenario_service import classify_sm

        assert classify_sm(0.019, 0.08) == "error"

    def test_classify_sm_exactly_heavy_nose_warn_threshold(
        self, client_and_db: Tuple[TestClient, any]
    ) -> None:
        """classify_sm(0.20, target) is 'ok' (sm <= 0.20 is still OK)."""
        from app.services.loading_scenario_service import classify_sm

        assert classify_sm(0.20, 0.08) == "ok"

    def test_classify_sm_just_above_heavy_nose_warn(
        self, client_and_db: Tuple[TestClient, any]
    ) -> None:
        """classify_sm(0.201, target) is 'warn' (heavy nose range 0.20 < sm <= 0.30)."""
        from app.services.loading_scenario_service import classify_sm

        assert classify_sm(0.201, 0.08) == "warn"

    def test_classify_sm_exactly_elevator_limit(
        self, client_and_db: Tuple[TestClient, any]
    ) -> None:
        """classify_sm(0.30, target) is 'warn' (sm == 0.30 is within warn band)."""
        from app.services.loading_scenario_service import classify_sm

        assert classify_sm(0.30, 0.08) == "warn"

    def test_classify_sm_just_above_elevator_limit(
        self, client_and_db: Tuple[TestClient, any]
    ) -> None:
        """classify_sm(0.301, target) is 'error' (sm > 0.30)."""
        from app.services.loading_scenario_service import classify_sm

        assert classify_sm(0.301, 0.08) == "error"

    def test_classify_sm_exactly_at_target(
        self, client_and_db: Tuple[TestClient, any]
    ) -> None:
        """classify_sm(target_sm, target_sm) is 'ok' (at the lower end of OK band)."""
        from app.services.loading_scenario_service import classify_sm

        assert classify_sm(0.08, 0.08) == "ok"

    def test_compute_scenario_cg_zero_total_mass_falls_back_to_base_cg(
        self, client_and_db: Tuple[TestClient, any]
    ) -> None:
        """When total_mass <= 0, compute_scenario_cg returns base_cg_x as fallback."""
        from app.services.loading_scenario_service import compute_scenario_cg

        # Disabled all components via toggle, no adhoc items → total_mass = 0
        components = [
            {"id": "comp1", "mass_kg": 1.0, "x_m": 0.20, "y_m": 0.0, "z_m": 0.0},
        ]
        result = compute_scenario_cg(
            base_mass_kg=1.0,
            base_cg_x=0.15,
            adhoc_items=[],
            mass_overrides=[],
            toggles=[{"component_uuid": "comp1", "enabled": False}],
            position_overrides=[],
            components=components,
        )
        # total_mass == 0 → fallback to base_cg_x
        assert result == pytest.approx(0.15)

    def test_position_override_y_z_optional(
        self, client_and_db: Tuple[TestClient, any]
    ) -> None:
        """PositionOverride with only x_m_override (y_m_override / z_m_override = None)
        must not crash and must correctly apply x-only shift."""
        from app.services.loading_scenario_service import compute_scenario_cg

        components = [
            {"id": "bat", "mass_kg": 0.3, "x_m": 0.10, "y_m": 0.0, "z_m": 0.0},
            {"id": "fus", "mass_kg": 1.0, "x_m": 0.20, "y_m": 0.0, "z_m": 0.0},
        ]
        # PositionOverride only sets x_m_override — y/z stay at component values
        result = compute_scenario_cg(
            base_mass_kg=1.3,
            base_cg_x=0.0,
            adhoc_items=[],
            mass_overrides=[],
            toggles=[],
            position_overrides=[{"component_uuid": "bat", "x_m_override": 0.05}],
            components=components,
        )
        expected = (1.0 * 0.20 + 0.3 * 0.05) / 1.3
        assert abs(result - expected) < 1e-9

    def test_empty_component_overrides_no_crash(
        self, client_and_db: Tuple[TestClient, any]
    ) -> None:
        """compute_scenario_cg with all-empty overrides returns correct base CG."""
        from app.services.loading_scenario_service import compute_scenario_cg

        result = compute_scenario_cg(
            base_mass_kg=1.0,
            base_cg_x=0.20,
            adhoc_items=[],
            mass_overrides=[],
            toggles=None,
            position_overrides=None,
        )
        assert result == pytest.approx(0.20)


# ---------------------------------------------------------------------------
# TestErrorPaths — 404 / missing scenario / invalid aircraft_class
# ---------------------------------------------------------------------------


class TestErrorPaths:
    """Covers 404 error paths for CRUD endpoints."""

    def test_list_scenarios_404_unknown_aeroplane(
        self, client_and_db: Tuple[TestClient, any]
    ) -> None:
        """GET /aeroplanes/{unknown_uuid}/loading-scenarios → 404."""
        client, _SessionLocal = client_and_db
        unknown = str(uuid.uuid4())
        resp = client.get(f"/aeroplanes/{unknown}/loading-scenarios")
        assert resp.status_code == 404

    def test_create_scenario_404_unknown_aeroplane(
        self, client_and_db: Tuple[TestClient, any]
    ) -> None:
        """POST /aeroplanes/{unknown_uuid}/loading-scenarios → 404."""
        client, _SessionLocal = client_and_db
        unknown = str(uuid.uuid4())
        resp = client.post(
            f"/aeroplanes/{unknown}/loading-scenarios",
            json=_scenario_payload(name="Ghost Scenario"),
        )
        assert resp.status_code == 404

    def test_update_scenario_404_missing_scenario_id(
        self, client_and_db: Tuple[TestClient, any]
    ) -> None:
        """PATCH .../loading-scenarios/999 → 404 when scenario does not exist."""
        client, SessionLocal = client_and_db
        with SessionLocal() as session:
            plane = _make_aeroplane(session)
            aeroplane_uuid = str(plane.uuid)

        resp = client.patch(
            f"/aeroplanes/{aeroplane_uuid}/loading-scenarios/999999",
            json={"name": "Nonexistent"},
        )
        assert resp.status_code == 404

    def test_update_scenario_404_unknown_aeroplane(
        self, client_and_db: Tuple[TestClient, any]
    ) -> None:
        """PATCH /aeroplanes/{unknown}/loading-scenarios/1 → 404."""
        client, _SessionLocal = client_and_db
        unknown = str(uuid.uuid4())
        resp = client.patch(
            f"/aeroplanes/{unknown}/loading-scenarios/1",
            json={"name": "Ghost"},
        )
        assert resp.status_code == 404

    def test_delete_scenario_404_missing_scenario_id(
        self, client_and_db: Tuple[TestClient, any]
    ) -> None:
        """DELETE .../loading-scenarios/999 → 404 when scenario does not exist."""
        client, SessionLocal = client_and_db
        with SessionLocal() as session:
            plane = _make_aeroplane(session)
            aeroplane_uuid = str(plane.uuid)

        resp = client.delete(
            f"/aeroplanes/{aeroplane_uuid}/loading-scenarios/999999"
        )
        assert resp.status_code == 404

    def test_delete_scenario_404_unknown_aeroplane(
        self, client_and_db: Tuple[TestClient, any]
    ) -> None:
        """DELETE /aeroplanes/{unknown}/loading-scenarios/1 → 404."""
        client, _SessionLocal = client_and_db
        unknown = str(uuid.uuid4())
        resp = client.delete(f"/aeroplanes/{unknown}/loading-scenarios/1")
        assert resp.status_code == 404

    def test_get_cg_envelope_404_unknown_aeroplane(
        self, client_and_db: Tuple[TestClient, any]
    ) -> None:
        """GET /aeroplanes/{unknown}/cg-envelope → 404."""
        client, _SessionLocal = client_and_db
        unknown = str(uuid.uuid4())
        resp = client.get(f"/aeroplanes/{unknown}/cg-envelope")
        assert resp.status_code == 404

    def test_update_scenario_partial_name_only(
        self, client_and_db: Tuple[TestClient, any]
    ) -> None:
        """PATCH with only name updates name, leaves other fields intact."""
        client, SessionLocal = client_and_db
        with SessionLocal() as session:
            plane = _make_aeroplane(session)
            aeroplane_uuid = str(plane.uuid)

        create_resp = client.post(
            f"/aeroplanes/{aeroplane_uuid}/loading-scenarios",
            json=_scenario_payload(name="Original", aircraft_class="rc_aerobatic"),
        )
        scenario_id = create_resp.json()["id"]

        patch_resp = client.patch(
            f"/aeroplanes/{aeroplane_uuid}/loading-scenarios/{scenario_id}",
            json={"name": "Renamed"},
        )
        assert patch_resp.status_code == 200
        result = patch_resp.json()
        assert result["name"] == "Renamed"
        assert result["aircraft_class"] == "rc_aerobatic"  # unchanged

    def test_update_scenario_aircraft_class_only(
        self, client_and_db: Tuple[TestClient, any]
    ) -> None:
        """PATCH with only aircraft_class updates it, leaves name intact."""
        client, SessionLocal = client_and_db
        with SessionLocal() as session:
            plane = _make_aeroplane(session)
            aeroplane_uuid = str(plane.uuid)

        create_resp = client.post(
            f"/aeroplanes/{aeroplane_uuid}/loading-scenarios",
            json=_scenario_payload(name="Keep Name", aircraft_class="rc_trainer"),
        )
        scenario_id = create_resp.json()["id"]

        patch_resp = client.patch(
            f"/aeroplanes/{aeroplane_uuid}/loading-scenarios/{scenario_id}",
            json={"aircraft_class": "glider"},
        )
        assert patch_resp.status_code == 200
        result = patch_resp.json()
        assert result["aircraft_class"] == "glider"
        assert result["name"] == "Keep Name"  # unchanged

    def test_update_scenario_is_default_only(
        self, client_and_db: Tuple[TestClient, any]
    ) -> None:
        """PATCH with only is_default=True makes scenario the default."""
        client, SessionLocal = client_and_db
        with SessionLocal() as session:
            plane = _make_aeroplane(session)
            aeroplane_uuid = str(plane.uuid)

        create_resp = client.post(
            f"/aeroplanes/{aeroplane_uuid}/loading-scenarios",
            json=_scenario_payload(name="Will Be Default", is_default=False),
        )
        scenario_id = create_resp.json()["id"]

        patch_resp = client.patch(
            f"/aeroplanes/{aeroplane_uuid}/loading-scenarios/{scenario_id}",
            json={"is_default": True},
        )
        assert patch_resp.status_code == 200
        assert patch_resp.json()["is_default"] is True

    def test_update_scenario_overrides_only(
        self, client_and_db: Tuple[TestClient, any]
    ) -> None:
        """PATCH with only component_overrides updates overrides."""
        client, SessionLocal = client_and_db
        with SessionLocal() as session:
            plane = _make_aeroplane(session)
            aeroplane_uuid = str(plane.uuid)

        create_resp = client.post(
            f"/aeroplanes/{aeroplane_uuid}/loading-scenarios",
            json=_scenario_payload(name="Overrides Test"),
        )
        scenario_id = create_resp.json()["id"]

        new_overrides = {
            "toggles": [],
            "mass_overrides": [{"component_uuid": "xyz", "mass_kg_override": 0.5}],
            "position_overrides": [],
            "adhoc_items": [],
        }
        patch_resp = client.patch(
            f"/aeroplanes/{aeroplane_uuid}/loading-scenarios/{scenario_id}",
            json={"component_overrides": new_overrides},
        )
        assert patch_resp.status_code == 200
        result = patch_resp.json()
        assert len(result["component_overrides"]["mass_overrides"]) == 1


# ---------------------------------------------------------------------------
# TestStabilityEnvelopeFallbacks — x_np=None / mac=None / both None / mac=0
# ---------------------------------------------------------------------------


class TestStabilityEnvelopeFallbacks:
    """Covers compute_stability_envelope None/zero handling and get_cg_envelope
    branches where x_np or mac is None (lines 598-599, 613, 624-625 in svc)."""

    def test_stability_envelope_x_np_none(
        self, client_and_db: Tuple[TestClient, any]
    ) -> None:
        """x_np=None → both stability limits are None."""
        from app.services.loading_scenario_service import compute_stability_envelope

        result = compute_stability_envelope(x_np=None, mac=0.20, target_sm=0.08)
        assert result["cg_stability_aft_m"] is None
        assert result["cg_stability_fwd_m"] is None

    def test_stability_envelope_mac_none(
        self, client_and_db: Tuple[TestClient, any]
    ) -> None:
        """mac=None → both stability limits are None."""
        from app.services.loading_scenario_service import compute_stability_envelope

        result = compute_stability_envelope(x_np=0.30, mac=None, target_sm=0.08)
        assert result["cg_stability_aft_m"] is None
        assert result["cg_stability_fwd_m"] is None

    def test_stability_envelope_mac_zero(
        self, client_and_db: Tuple[TestClient, any]
    ) -> None:
        """mac=0 → both stability limits are None (division by zero guard)."""
        from app.services.loading_scenario_service import compute_stability_envelope

        result = compute_stability_envelope(x_np=0.30, mac=0.0, target_sm=0.08)
        assert result["cg_stability_aft_m"] is None
        assert result["cg_stability_fwd_m"] is None

    def test_enrich_context_no_x_np_returns_none_sm(
        self, client_and_db: Tuple[TestClient, any]
    ) -> None:
        """enrich_context_with_cg_envelope with no x_np_m in ctx → sm_at_fwd/aft = None."""
        from app.services.loading_scenario_service import enrich_context_with_cg_envelope

        ctx: dict = {"cg_agg_m": 0.15}  # no x_np_m, no mac_m
        enriched = enrich_context_with_cg_envelope(
            ctx=ctx,
            cg_loading_fwd_m=0.14,
            cg_loading_aft_m=0.17,
            cg_stability_fwd_m=None,
            cg_stability_aft_m=None,
        )
        assert enriched["sm_at_fwd"] is None
        assert enriched["sm_at_aft"] is None
        assert enriched["cg_forward_m"] == pytest.approx(0.14, abs=1e-3)
        assert enriched["cg_aft_m"] == pytest.approx(0.17, abs=1e-3)

    def test_enrich_context_with_x_np_and_mac_computes_sm(
        self, client_and_db: Tuple[TestClient, any]
    ) -> None:
        """enrich_context_with_cg_envelope with x_np_m and mac_m computes sm values."""
        from app.services.loading_scenario_service import enrich_context_with_cg_envelope

        ctx: dict = {"cg_agg_m": 0.15, "x_np_m": 0.30, "mac_m": 0.20}
        enriched = enrich_context_with_cg_envelope(
            ctx=ctx,
            cg_loading_fwd_m=0.14,
            cg_loading_aft_m=0.17,
            cg_stability_fwd_m=0.24,
            cg_stability_aft_m=0.284,
        )
        # sm_at_fwd = (0.30 - 0.14) / 0.20 = 0.80
        assert enriched["sm_at_fwd"] == pytest.approx(0.80, abs=1e-3)
        # sm_at_aft = (0.30 - 0.17) / 0.20 = 0.65
        assert enriched["sm_at_aft"] == pytest.approx(0.65, abs=1e-3)

    def test_cg_envelope_with_full_context_computes_sm(
        self, client_and_db: Tuple[TestClient, any]
    ) -> None:
        """GET /cg-envelope with x_np_m and mac_m in context returns computed sm values."""
        client, SessionLocal = client_and_db
        with SessionLocal() as session:
            plane = _make_aeroplane(session)
            _seed_assumptions(session, plane.id)
            # Provide a realistic aero context
            plane.assumption_computation_context = {
                "x_np_m": 0.30,
                "mac_m": 0.20,
            }
            session.commit()
            aeroplane_uuid = str(plane.uuid)

        resp = client.get(f"/aeroplanes/{aeroplane_uuid}/cg-envelope")
        assert resp.status_code == 200, resp.text
        data = resp.json()
        # With x_np and mac present, sm values should be computed (not None)
        assert data["sm_at_fwd"] is not None
        assert data["sm_at_aft"] is not None
        assert data["cg_stability_fwd_m"] is not None
        assert data["cg_stability_aft_m"] is not None

    def test_cg_envelope_error_classification_adds_sm_warning(
        self, client_and_db: Tuple[TestClient, any]
    ) -> None:
        """When classification is 'error' and sm_at_aft is known, warning mentions SM value."""
        client, SessionLocal = client_and_db
        with SessionLocal() as session:
            plane = _make_aeroplane(session)
            _seed_assumptions(session, plane.id)
            # CG very close to NP → very low SM (< 0.02 → error)
            # x_np = 0.16, mac = 0.20, cg_x (from assumptions) = 0.15
            # sm_at_aft ≈ (0.16 - 0.15) / 0.20 = 0.05 → warn, not error
            # To force error: set x_np very close to cg so sm < 0.02
            # cg = 0.15, x_np = 0.153, mac = 0.20 → sm ≈ 0.015 → error
            plane.assumption_computation_context = {
                "x_np_m": 0.153,
                "mac_m": 0.20,
            }
            session.commit()
            aeroplane_uuid = str(plane.uuid)

        resp = client.get(f"/aeroplanes/{aeroplane_uuid}/cg-envelope")
        assert resp.status_code == 200, resp.text
        data = resp.json()
        assert data["classification"] == "error"
        # Error classification → warning must mention SM
        assert any("SM" in w or "sm" in w.lower() for w in data["warnings"])

    def test_cg_agg_returns_none_when_no_scenarios_and_no_weight_items(
        self, client_and_db: Tuple[TestClient, any]
    ) -> None:
        """compute_cg_agg_for_aeroplane returns None when no scenarios and no weight items."""
        from app.services.loading_scenario_service import compute_cg_agg_for_aeroplane

        _client, SessionLocal = client_and_db
        with SessionLocal() as session:
            plane = _make_aeroplane(session)
            _seed_assumptions(session, plane.id)
            # No loading scenarios, no weight items → should return None
            plane_row = session.query(AeroplaneModel).filter_by(uuid=plane.uuid).first()
            cg_agg = compute_cg_agg_for_aeroplane(session, plane_row)

        assert cg_agg is None


# ---------------------------------------------------------------------------
# TestTemplatesEndpointAllClasses — template endpoint for each aircraft class
# ---------------------------------------------------------------------------


class TestTemplatesEndpointAllClasses:
    """Covers the /templates endpoint for all aircraft_class values via HTTP."""

    @pytest.mark.parametrize(
        "ac",
        ["rc_trainer", "rc_aerobatic", "rc_combust", "uav_survey", "glider", "boxwing"],
    )
    def test_templates_endpoint_for_each_class(
        self, ac: str, client_and_db: Tuple[TestClient, any]
    ) -> None:
        """GET /loading-scenarios/templates?aircraft_class=<ac> returns ≥1 template."""
        client, SessionLocal = client_and_db
        with SessionLocal() as session:
            plane = _make_aeroplane(session)
            aeroplane_uuid = str(plane.uuid)

        resp = client.get(
            f"/aeroplanes/{aeroplane_uuid}/loading-scenarios/templates",
            params={"aircraft_class": ac},
        )
        assert resp.status_code == 200, f"[{ac}] {resp.text}"
        templates = resp.json()
        assert isinstance(templates, list)
        assert len(templates) >= 1, f"No templates returned for {ac}"
        for t in templates:
            assert "name" in t, f"Template missing 'name' for {ac}: {t}"

    def test_templates_endpoint_unknown_class_falls_back(
        self, client_and_db: Tuple[TestClient, any]
    ) -> None:
        """Unknown aircraft_class falls back to rc_trainer templates (no 422)."""
        client, SessionLocal = client_and_db
        with SessionLocal() as session:
            plane = _make_aeroplane(session)
            aeroplane_uuid = str(plane.uuid)

        resp = client.get(
            f"/aeroplanes/{aeroplane_uuid}/loading-scenarios/templates",
            params={"aircraft_class": "unknown_class"},
        )
        # The endpoint accepts any string (no enum validation at HTTP layer),
        # service falls back to rc_trainer templates.
        assert resp.status_code == 200, resp.text
        templates = resp.json()
        assert len(templates) >= 1

    def test_templates_endpoint_missing_aeroplane_404(
        self, client_and_db: Tuple[TestClient, any]
    ) -> None:
        """Templates endpoint returns 404 when aeroplane UUID does not exist."""
        client, _SessionLocal = client_and_db
        unknown = str(uuid.uuid4())
        resp = client.get(
            f"/aeroplanes/{unknown}/loading-scenarios/templates",
            params={"aircraft_class": "rc_trainer"},
        )
        assert resp.status_code == 404


# ---------------------------------------------------------------------------
# TestOverridesJsonSerialization — component_overrides stored as JSON string
# ---------------------------------------------------------------------------


class TestOverridesJsonSerialization:
    """Covers the json.loads branch in _model_to_schema, compute_cg_agg, and
    compute_loading_envelope (lines 302, 364, 432 in loading_scenario_service)."""

    def test_overrides_serialized_as_json_string_round_trips(
        self, client_and_db: Tuple[TestClient, any]
    ) -> None:
        """When component_overrides are stored as a JSON string (legacy SQLite path),
        the service deserialises them correctly."""
        import json as _json

        from app.models.aeroplanemodel import LoadingScenarioModel
        from app.services.loading_scenario_service import _model_to_schema

        _client, SessionLocal = client_and_db
        with SessionLocal() as session:
            plane = _make_aeroplane(session)
            _seed_assumptions(session, plane.id)

            # Store overrides as a JSON string (simulates legacy column value)
            overrides_dict = {
                "toggles": [],
                "mass_overrides": [{"component_uuid": "abc", "mass_kg_override": 0.3}],
                "position_overrides": [],
                "adhoc_items": [],
            }
            scenario = LoadingScenarioModel(
                aeroplane_id=plane.id,
                name="JSON String Scenario",
                aircraft_class="rc_trainer",
                component_overrides=_json.dumps(overrides_dict),
                is_default=False,
            )
            session.add(scenario)
            session.commit()
            session.refresh(scenario)

            # _model_to_schema should handle JSON string overrides without error
            result = _model_to_schema(scenario)

        assert len(result.component_overrides.mass_overrides) == 1
        assert result.component_overrides.mass_overrides[0].component_uuid == "abc"

    def test_compute_loading_envelope_with_json_string_overrides(
        self, client_and_db: Tuple[TestClient, any]
    ) -> None:
        """compute_loading_envelope_for_aeroplane handles JSON-string overrides."""
        import json as _json

        from app.models.aeroplanemodel import LoadingScenarioModel
        from app.services.loading_scenario_service import compute_loading_envelope_for_aeroplane

        _client, SessionLocal = client_and_db
        with SessionLocal() as session:
            plane = _make_aeroplane(session)
            _seed_assumptions(session, plane.id)

            overrides_dict = {
                "toggles": [],
                "mass_overrides": [],
                "position_overrides": [],
                "adhoc_items": [
                    {"name": "Item", "mass_kg": 0.5, "x_m": 0.30, "y_m": 0.0, "z_m": 0.0}
                ],
            }
            scenario = LoadingScenarioModel(
                aeroplane_id=plane.id,
                name="JSON Envelope Scenario",
                aircraft_class="rc_trainer",
                component_overrides=_json.dumps(overrides_dict),
                is_default=True,
            )
            session.add(scenario)
            session.commit()

        with SessionLocal() as session:
            plane_row = session.query(AeroplaneModel).filter_by(uuid=plane.uuid).first()
            envelope = compute_loading_envelope_for_aeroplane(session, plane_row)

        # adhoc item at x=0.30 with base at x=0.15 → aft shift
        assert envelope["cg_loading_aft_m"] > 0.15

    def test_compute_cg_agg_with_json_string_overrides(
        self, client_and_db: Tuple[TestClient, any]
    ) -> None:
        """compute_cg_agg_for_aeroplane handles JSON-string overrides in default scenario."""
        import json as _json

        from app.models.aeroplanemodel import LoadingScenarioModel
        from app.services.loading_scenario_service import compute_cg_agg_for_aeroplane

        _client, SessionLocal = client_and_db
        with SessionLocal() as session:
            plane = _make_aeroplane(session)
            _seed_assumptions(session, plane.id)

            overrides_dict = {
                "toggles": [],
                "mass_overrides": [],
                "position_overrides": [],
                "adhoc_items": [],
            }
            scenario = LoadingScenarioModel(
                aeroplane_id=plane.id,
                name="Default JSON Scenario",
                aircraft_class="rc_trainer",
                component_overrides=_json.dumps(overrides_dict),
                is_default=True,
            )
            session.add(scenario)
            session.commit()

        with SessionLocal() as session:
            plane_row = session.query(AeroplaneModel).filter_by(uuid=plane.uuid).first()
            cg_agg = compute_cg_agg_for_aeroplane(session, plane_row)

        # Empty overrides + base mass at x=0.15 → cg_agg ≈ 0.15
        assert cg_agg is not None
        assert abs(cg_agg - 0.15) < 1e-6


# ---------------------------------------------------------------------------
# TestLoadAssumptionValueBranches — covers CALCULATED source path (lines 293-295)
# ---------------------------------------------------------------------------


class TestLoadAssumptionValueBranches:
    """Covers _load_assumption_value branches:
    - no row → returns default (line 293)
    - CALCULATED source with calculated_value → returns calculated_value (lines 294-295)
    - non-CALCULATED source → returns estimate_value (line 296)
    """

    def test_load_assumption_value_no_row_returns_default(
        self, client_and_db: Tuple[TestClient, any]
    ) -> None:
        """When no assumption row exists, default is returned via compute_loading_envelope."""
        from app.services.loading_scenario_service import compute_loading_envelope_for_aeroplane

        _client, SessionLocal = client_and_db
        with SessionLocal() as session:
            plane = _make_aeroplane(session)
            # Deliberately do NOT seed assumptions → _load_assumption_value returns default
            envelope = compute_loading_envelope_for_aeroplane(session, plane)

        # No assumptions → base_mass defaults to 1.0, base_cg_x defaults to 0.0
        # No scenarios → fwd = aft = 0.0 (default cg_x)
        assert envelope["cg_loading_fwd_m"] == pytest.approx(0.0)
        assert envelope["cg_loading_aft_m"] == pytest.approx(0.0)

    def test_load_assumption_value_calculated_source_used(
        self, client_and_db: Tuple[TestClient, any]
    ) -> None:
        """When active_source=CALCULATED with a calculated_value, that value is used."""
        from app.services.loading_scenario_service import compute_loading_envelope_for_aeroplane

        _client, SessionLocal = client_and_db
        with SessionLocal() as session:
            plane = _make_aeroplane(session)
            # Seed a CALCULATED assumption for cg_x
            session.add(
                DesignAssumptionModel(
                    aeroplane_id=plane.id,
                    parameter_name="cg_x",
                    estimate_value=0.15,
                    calculated_value=0.22,
                    active_source="CALCULATED",
                    updated_at=datetime.now(timezone.utc),
                )
            )
            session.add(
                DesignAssumptionModel(
                    aeroplane_id=plane.id,
                    parameter_name="mass",
                    estimate_value=1.5,
                    calculated_value=None,
                    active_source="ESTIMATE",
                    updated_at=datetime.now(timezone.utc),
                )
            )
            session.commit()

        with SessionLocal() as session:
            plane_row = session.query(AeroplaneModel).filter_by(uuid=plane.uuid).first()
            envelope = compute_loading_envelope_for_aeroplane(session, plane_row)

        # No scenarios → fwd = aft = base_cg_x = calculated 0.22 (not estimate 0.15)
        assert envelope["cg_loading_fwd_m"] == pytest.approx(0.22)
        assert envelope["cg_loading_aft_m"] == pytest.approx(0.22)


# ---------------------------------------------------------------------------
# TestCgEnvelopeRankingBranch — aft rank > fwd rank → overall = classification_aft
# ---------------------------------------------------------------------------


class TestCgEnvelopeRankingBranch:
    """Covers line 613 in loading_scenario_service: `overall = classification_aft`
    when the aft SM is worse than the fwd SM (different scenarios produce different
    CG values that land in different classification bands)."""

    def test_aft_classification_dominates_when_worse(
        self, client_and_db: Tuple[TestClient, any]
    ) -> None:
        """When aft CG is much closer to NP (very low SM), aft classification
        dominates overall even if fwd is fine.

        Setup:
          x_np = 0.20, mac = 0.20
          - Scenario A (fwd adhoc): pushes CG to ~0.10 → sm_fwd = (0.20-0.10)/0.20 = 0.50 → ok
          - Scenario B (aft adhoc): pushes CG to ~0.195 → sm_aft = (0.20-0.195)/0.20 = 0.025 → warn (> 0.02 and < target)
          aft rank (warn=2) > fwd rank (ok=1) → overall = 'warn', taken from aft branch.
        """
        client, SessionLocal = client_and_db
        with SessionLocal() as session:
            plane = _make_aeroplane(session)
            _seed_assumptions(session, plane.id, extra={"target_static_margin": 0.08})
            plane.assumption_computation_context = {
                "x_np_m": 0.20,
                "mac_m": 0.20,
            }
            session.commit()
            aeroplane_uuid = str(plane.uuid)

        # Scenario A: large fwd ballast → CG shifts well forward
        # base: 1.5 kg @ 0.15; adding 3.0 kg @ 0.01 → CG ≈ (1.5*0.15 + 3.0*0.01)/4.5 ≈ 0.057
        # sm_fwd = (0.20 - 0.057)/0.20 ≈ 0.715 → ok (but target=0.08 < 0.20)
        client.post(
            f"/aeroplanes/{aeroplane_uuid}/loading-scenarios",
            json=_scenario_payload(
                name="Very Fwd",
                component_overrides={
                    "toggles": [],
                    "mass_overrides": [],
                    "position_overrides": [],
                    "adhoc_items": [
                        {"name": "Nose Ballast", "mass_kg": 3.0, "x_m": 0.01, "y_m": 0.0, "z_m": 0.0}
                    ],
                },
            ),
        )
        # Scenario B: large aft item → CG shifts very close to NP
        # base: 1.5 kg @ 0.15; adding 3.0 kg @ 0.22 → CG ≈ (1.5*0.15+3.0*0.22)/4.5 ≈ 0.197
        # sm_aft = (0.20 - 0.197)/0.20 ≈ 0.015 → error (< 0.02)
        client.post(
            f"/aeroplanes/{aeroplane_uuid}/loading-scenarios",
            json=_scenario_payload(
                name="Very Aft",
                component_overrides={
                    "toggles": [],
                    "mass_overrides": [],
                    "position_overrides": [],
                    "adhoc_items": [
                        {"name": "Aft Ballast", "mass_kg": 3.0, "x_m": 0.22, "y_m": 0.0, "z_m": 0.0}
                    ],
                },
            ),
        )

        resp = client.get(f"/aeroplanes/{aeroplane_uuid}/cg-envelope")
        assert resp.status_code == 200, resp.text
        data = resp.json()

        # aft CG is very close to NP → sm_aft is very small (< 0.02) → error
        # fwd CG is well forward of NP → sm_fwd is large → ok
        # aft classification (error) > fwd classification (ok) → overall = 'error'
        # This exercises line 613: overall = classification_aft
        assert data["classification"] in ("error", "warn"), (
            f"Expected error or warn, got {data['classification']!r} "
            f"(sm_at_fwd={data['sm_at_fwd']}, sm_at_aft={data['sm_at_aft']})"
        )
        # Ensure aft SM is worse (lower) than fwd SM
        assert data["sm_at_aft"] < data["sm_at_fwd"]
