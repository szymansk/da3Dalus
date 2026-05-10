"""Tests for app.services.mass_cg_service — mass/CG design parameter computations."""

from __future__ import annotations

import math
import uuid

import pytest

from app.core.exceptions import NotFoundError, ValidationError
from app.schemas.design_assumption import PARAMETER_DEFAULTS
from app.schemas.weight_item import WeightItemWrite
from app.services import design_assumptions_service as da_svc
from app.services import mass_cg_service as svc
from app.services import weight_items_service as wi_svc
from app.tests.conftest import make_aeroplane


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

GRAVITY = 9.81
SEA_LEVEL_RHO = 1.225  # kg/m^3 (ISA sea level)


def _seed_and_get(db, aeroplane_uuid):
    """Seed design assumptions and return the summary."""
    return da_svc.seed_defaults(db, aeroplane_uuid)


def _make_weight_item(
    name: str = "battery",
    mass_kg: float = 0.5,
    x_m: float = 0.1,
    y_m: float = 0.0,
    z_m: float = 0.0,
) -> WeightItemWrite:
    return WeightItemWrite(name=name, mass_kg=mass_kg, x_m=x_m, y_m=y_m, z_m=z_m)


# ---------------------------------------------------------------------------
# compute_recommended_cg
# ---------------------------------------------------------------------------


class TestComputeRecommendedCG:
    def test_basic_formula(self):
        """CG_x = NP_x - target_SM * MAC."""
        np_x = 0.25
        mac = 0.20
        target_sm = 0.12
        result = svc.compute_recommended_cg(np_x, mac, target_sm)
        expected = np_x - target_sm * mac
        assert result == pytest.approx(expected)

    def test_zero_static_margin(self):
        """With SM=0, recommended CG equals NP."""
        np_x = 0.30
        mac = 0.15
        result = svc.compute_recommended_cg(np_x, mac, 0.0)
        assert result == pytest.approx(np_x)

    def test_large_static_margin(self):
        """SM=1.0 pushes CG forward by one full MAC."""
        np_x = 0.50
        mac = 0.20
        result = svc.compute_recommended_cg(np_x, mac, 1.0)
        assert result == pytest.approx(0.50 - 0.20)


# ---------------------------------------------------------------------------
# compute_design_metrics
# ---------------------------------------------------------------------------


class TestComputeDesignMetrics:
    def test_stall_speed(self):
        """V_stall = sqrt(2*m*g / (rho * S * CL_max))."""
        mass_kg = 1.5
        s_ref = 0.3
        cl_max = 1.4
        rho = SEA_LEVEL_RHO
        velocity = 15.0

        result = svc.compute_design_metrics(mass_kg, s_ref, cl_max, rho, velocity)
        expected_vs = math.sqrt(2 * mass_kg * GRAVITY / (rho * s_ref * cl_max))
        assert result.stall_speed_ms == pytest.approx(expected_vs)

    def test_wing_loading(self):
        """Wing loading = m*g / S."""
        mass_kg = 2.0
        s_ref = 0.4
        cl_max = 1.4
        rho = SEA_LEVEL_RHO
        velocity = 15.0

        result = svc.compute_design_metrics(mass_kg, s_ref, cl_max, rho, velocity)
        assert result.wing_loading_pa == pytest.approx(mass_kg * GRAVITY / s_ref)

    def test_required_cl(self):
        """CL_req = 2*m*g / (rho * V^2 * S)."""
        mass_kg = 1.5
        s_ref = 0.3
        cl_max = 1.4
        rho = SEA_LEVEL_RHO
        velocity = 20.0

        result = svc.compute_design_metrics(mass_kg, s_ref, cl_max, rho, velocity)
        q = 0.5 * rho * velocity**2
        expected_cl = mass_kg * GRAVITY / (q * s_ref)
        assert result.required_cl == pytest.approx(expected_cl)

    def test_cl_margin(self):
        """CL margin = CL_max - required_CL."""
        mass_kg = 1.5
        s_ref = 0.3
        cl_max = 1.4
        rho = SEA_LEVEL_RHO
        velocity = 20.0

        result = svc.compute_design_metrics(mass_kg, s_ref, cl_max, rho, velocity)
        assert result.cl_margin == pytest.approx(cl_max - result.required_cl)

    def test_zero_mass_raises(self):
        """Mass must be positive."""
        with pytest.raises(ValidationError):
            svc.compute_design_metrics(0.0, 0.3, 1.4, SEA_LEVEL_RHO, 15.0)

    def test_zero_s_ref_raises(self):
        """S_ref must be positive."""
        with pytest.raises(ValidationError):
            svc.compute_design_metrics(1.5, 0.0, 1.4, SEA_LEVEL_RHO, 15.0)

    def test_zero_cl_max_raises(self):
        """CL_max must be positive for stall speed computation."""
        with pytest.raises(ValidationError):
            svc.compute_design_metrics(1.5, 0.3, 0.0, SEA_LEVEL_RHO, 15.0)

    def test_zero_rho_raises(self):
        with pytest.raises(ValidationError):
            svc.compute_design_metrics(1.5, 0.3, 1.4, 0.0, 15.0)

    def test_zero_velocity_raises(self):
        with pytest.raises(ValidationError):
            svc.compute_design_metrics(1.5, 0.3, 1.4, SEA_LEVEL_RHO, 0.0)

    def test_response_fields(self):
        """All response fields are populated."""
        result = svc.compute_design_metrics(1.5, 0.3, 1.4, SEA_LEVEL_RHO, 15.0)
        assert result.mass_kg == 1.5
        assert result.s_ref == 0.3
        assert result.cl_max == 1.4


# ---------------------------------------------------------------------------
# compute_mass_sweep
# ---------------------------------------------------------------------------


class TestComputeMassSweep:
    def test_returns_correct_number_of_points(self):
        masses = [1.0, 1.5, 2.0, 2.5]
        result = svc.compute_mass_sweep(masses, 0.3, 1.4, SEA_LEVEL_RHO, 15.0)
        assert len(result) == 4

    def test_wing_loading_increases_with_mass(self):
        masses = [1.0, 2.0, 3.0]
        points = svc.compute_mass_sweep(masses, 0.3, 1.4, SEA_LEVEL_RHO, 15.0)
        loadings = [p.wing_loading_pa for p in points]
        assert loadings == sorted(loadings)

    def test_stall_speed_increases_with_mass(self):
        masses = [1.0, 2.0, 3.0]
        points = svc.compute_mass_sweep(masses, 0.3, 1.4, SEA_LEVEL_RHO, 15.0)
        speeds = [p.stall_speed_ms for p in points]
        assert speeds == sorted(speeds)

    def test_cl_margin_decreases_with_mass(self):
        masses = [1.0, 2.0, 3.0]
        points = svc.compute_mass_sweep(masses, 0.3, 1.4, SEA_LEVEL_RHO, 15.0)
        margins = [p.cl_margin for p in points]
        assert margins == sorted(margins, reverse=True)

    def test_single_mass_point(self):
        points = svc.compute_mass_sweep([1.5], 0.3, 1.4, SEA_LEVEL_RHO, 15.0)
        assert len(points) == 1
        assert points[0].mass_kg == 1.5

    def test_each_point_matches_single_computation(self):
        """Each sweep point must match a standalone compute_design_metrics call."""
        masses = [1.0, 1.5, 2.0]
        points = svc.compute_mass_sweep(masses, 0.3, 1.4, SEA_LEVEL_RHO, 15.0)
        for pt in points:
            single = svc.compute_design_metrics(pt.mass_kg, 0.3, 1.4, SEA_LEVEL_RHO, 15.0)
            assert pt.wing_loading_pa == pytest.approx(single.wing_loading_pa)
            assert pt.stall_speed_ms == pytest.approx(single.stall_speed_ms)
            assert pt.required_cl == pytest.approx(single.required_cl)
            assert pt.cl_margin == pytest.approx(single.cl_margin)


# ---------------------------------------------------------------------------
# aggregate_weight_items
# ---------------------------------------------------------------------------


class TestAggregateWeightItems:
    def test_empty_items(self):
        """No items -> None for mass and CG."""
        mass, cx, cy, cz = svc.aggregate_weight_items([])
        assert mass is None
        assert cx is None
        assert cy is None
        assert cz is None

    def test_single_item(self):
        """Single item -> mass and position equal to the item."""
        items = [{"mass_kg": 0.5, "x_m": 0.1, "y_m": 0.2, "z_m": 0.3}]
        mass, cx, cy, cz = svc.aggregate_weight_items(items)
        assert mass == pytest.approx(0.5)
        assert cx == pytest.approx(0.1)
        assert cy == pytest.approx(0.2)
        assert cz == pytest.approx(0.3)

    def test_two_equal_items(self):
        """Two equal items -> CG at midpoint."""
        items = [
            {"mass_kg": 1.0, "x_m": 0.0, "y_m": 0.0, "z_m": 0.0},
            {"mass_kg": 1.0, "x_m": 0.2, "y_m": 0.4, "z_m": 0.6},
        ]
        mass, cx, cy, cz = svc.aggregate_weight_items(items)
        assert mass == pytest.approx(2.0)
        assert cx == pytest.approx(0.1)
        assert cy == pytest.approx(0.2)
        assert cz == pytest.approx(0.3)

    def test_weighted_average(self):
        """CG is mass-weighted average of positions."""
        items = [
            {"mass_kg": 3.0, "x_m": 0.1, "y_m": 0.0, "z_m": 0.0},
            {"mass_kg": 1.0, "x_m": 0.5, "y_m": 0.0, "z_m": 0.0},
        ]
        mass, cx, cy, cz = svc.aggregate_weight_items(items)
        assert mass == pytest.approx(4.0)
        assert cx == pytest.approx((3.0 * 0.1 + 1.0 * 0.5) / 4.0)

    def test_zero_total_mass(self):
        """All items with zero mass -> None for CG."""
        items = [
            {"mass_kg": 0.0, "x_m": 0.1, "y_m": 0.0, "z_m": 0.0},
        ]
        mass, cx, cy, cz = svc.aggregate_weight_items(items)
        assert mass is None
        assert cx is None


# ---------------------------------------------------------------------------
# update_calculated_value (design_assumptions_service extension)
# ---------------------------------------------------------------------------


class TestUpdateCalculatedValue:
    def test_updates_mass_calculated(self, client_and_db):
        _, SessionLocal = client_and_db
        with SessionLocal() as db:
            aeroplane = make_aeroplane(db)
            _seed_and_get(db, aeroplane.uuid)

            da_svc.update_calculated_value(db, aeroplane.uuid, "mass", 2.0, "weight_items")
            summary = da_svc.list_assumptions(db, aeroplane.uuid)
            by_name = {a.parameter_name: a for a in summary.assumptions}
            assert by_name["mass"].calculated_value == 2.0
            assert by_name["mass"].calculated_source == "weight_items"

    def test_updates_cg_x_calculated(self, client_and_db):
        _, SessionLocal = client_and_db
        with SessionLocal() as db:
            aeroplane = make_aeroplane(db)
            _seed_and_get(db, aeroplane.uuid)

            da_svc.update_calculated_value(db, aeroplane.uuid, "cg_x", 0.12, "weight_items")
            summary = da_svc.list_assumptions(db, aeroplane.uuid)
            by_name = {a.parameter_name: a for a in summary.assumptions}
            assert by_name["cg_x"].calculated_value == 0.12
            assert by_name["cg_x"].calculated_source == "weight_items"

    def test_recomputes_divergence_on_update(self, client_and_db):
        _, SessionLocal = client_and_db
        with SessionLocal() as db:
            aeroplane = make_aeroplane(db)
            _seed_and_get(db, aeroplane.uuid)

            da_svc.update_calculated_value(db, aeroplane.uuid, "mass", 2.0, "weight_items")
            summary = da_svc.list_assumptions(db, aeroplane.uuid)
            by_name = {a.parameter_name: a for a in summary.assumptions}
            # estimate=1.5, calc=2.0 -> |1.5-2.0|/|2.0|*100 = 25.0
            assert by_name["mass"].divergence_pct == 25.0

    def test_clears_calculated_with_none(self, client_and_db):
        _, SessionLocal = client_and_db
        with SessionLocal() as db:
            aeroplane = make_aeroplane(db)
            _seed_and_get(db, aeroplane.uuid)

            da_svc.update_calculated_value(db, aeroplane.uuid, "mass", 2.0, "weight_items")
            da_svc.update_calculated_value(db, aeroplane.uuid, "mass", None, None)
            summary = da_svc.list_assumptions(db, aeroplane.uuid)
            by_name = {a.parameter_name: a for a in summary.assumptions}
            assert by_name["mass"].calculated_value is None
            assert by_name["mass"].calculated_source is None

    def test_raises_not_found_for_missing_param(self, client_and_db):
        _, SessionLocal = client_and_db
        with SessionLocal() as db:
            aeroplane = make_aeroplane(db)
            _seed_and_get(db, aeroplane.uuid)

            with pytest.raises(NotFoundError):
                da_svc.update_calculated_value(db, aeroplane.uuid, "nonexistent", 1.0, "test")

    def test_raises_not_found_for_missing_aeroplane(self, client_and_db):
        _, SessionLocal = client_and_db
        with SessionLocal() as db:
            with pytest.raises(NotFoundError):
                da_svc.update_calculated_value(db, uuid.uuid4(), "mass", 1.0, "test")


# ---------------------------------------------------------------------------
# sync_weight_items_to_assumptions (DB integration)
# ---------------------------------------------------------------------------


class TestSyncWeightItemsToAssumptions:
    def test_creates_calculated_values_from_items(self, client_and_db):
        _, SessionLocal = client_and_db
        with SessionLocal() as db:
            aeroplane = make_aeroplane(db)
            _seed_and_get(db, aeroplane.uuid)

            wi_svc.create_weight_item(
                db,
                aeroplane.uuid,
                _make_weight_item(name="motor", mass_kg=0.3, x_m=0.05),
            )
            wi_svc.create_weight_item(
                db,
                aeroplane.uuid,
                _make_weight_item(name="battery", mass_kg=0.5, x_m=0.15),
            )

            svc.sync_weight_items_to_assumptions(db, aeroplane.uuid)

            summary = da_svc.list_assumptions(db, aeroplane.uuid)
            by_name = {a.parameter_name: a for a in summary.assumptions}
            assert by_name["mass"].calculated_value == pytest.approx(0.8)
            # Mass auto-switches to CALCULATED on first sync (gh-465).
            assert by_name["mass"].active_source == "CALCULATED"
            # cg_x is NOT set by weight-item sync anymore (gh-465). The
            # cg_x assumption represents CG_aero = NP - SM × MAC, which
            # is owned by assumption_compute_service. CG_agg from weight
            # items is exposed via the computation context for comparison
            # only.
            assert by_name["cg_x"].calculated_value is None

    def test_clears_calculated_when_no_items(self, client_and_db):
        _, SessionLocal = client_and_db
        with SessionLocal() as db:
            aeroplane = make_aeroplane(db)
            _seed_and_get(db, aeroplane.uuid)

            da_svc.update_calculated_value(db, aeroplane.uuid, "mass", 1.0, "weight_items")

            svc.sync_weight_items_to_assumptions(db, aeroplane.uuid)

            summary = da_svc.list_assumptions(db, aeroplane.uuid)
            by_name = {a.parameter_name: a for a in summary.assumptions}
            assert by_name["mass"].calculated_value is None
            assert by_name["cg_x"].calculated_value is None

    def test_tolerates_missing_assumptions(self, client_and_db):
        """If assumptions are not seeded yet, sync is a no-op (no crash)."""
        _, SessionLocal = client_and_db
        with SessionLocal() as db:
            aeroplane = make_aeroplane(db)
            wi_svc.create_weight_item(
                db,
                aeroplane.uuid,
                _make_weight_item(name="motor", mass_kg=0.3, x_m=0.05),
            )
            svc.sync_weight_items_to_assumptions(db, aeroplane.uuid)


# ---------------------------------------------------------------------------
# get_cg_comparison (DB integration)
# ---------------------------------------------------------------------------


class TestGetCGComparison:
    def test_with_weight_items(self, client_and_db):
        _, SessionLocal = client_and_db
        with SessionLocal() as db:
            aeroplane = make_aeroplane(db)
            _seed_and_get(db, aeroplane.uuid)

            wi_svc.create_weight_item(
                db,
                aeroplane.uuid,
                _make_weight_item(name="motor", mass_kg=0.5, x_m=0.10),
            )
            wi_svc.create_weight_item(
                db,
                aeroplane.uuid,
                _make_weight_item(name="battery", mass_kg=0.5, x_m=0.20),
            )

            result = svc.get_cg_comparison(db, aeroplane.uuid)
            assert result.design_cg_x == PARAMETER_DEFAULTS["cg_x"]
            assert result.component_cg_x == pytest.approx(0.15)
            assert result.component_total_mass_kg == pytest.approx(1.0)
            assert result.delta_x == pytest.approx(PARAMETER_DEFAULTS["cg_x"] - 0.15)
            assert result.within_tolerance is (abs(PARAMETER_DEFAULTS["cg_x"] - 0.15) < 0.01)

    def test_without_weight_items(self, client_and_db):
        _, SessionLocal = client_and_db
        with SessionLocal() as db:
            aeroplane = make_aeroplane(db)
            _seed_and_get(db, aeroplane.uuid)

            result = svc.get_cg_comparison(db, aeroplane.uuid)
            assert result.design_cg_x == PARAMETER_DEFAULTS["cg_x"]
            assert result.component_cg_x is None
            assert result.delta_x is None
            assert result.within_tolerance is None

    def test_raises_not_found_for_missing_aeroplane(self, client_and_db):
        _, SessionLocal = client_and_db
        with SessionLocal() as db:
            with pytest.raises(NotFoundError):
                svc.get_cg_comparison(db, uuid.uuid4())


# ---------------------------------------------------------------------------
# get_effective_assumption_value helper
# ---------------------------------------------------------------------------


class TestGetEffectiveAssumptionValue:
    def test_returns_estimate_by_default(self, client_and_db):
        _, SessionLocal = client_and_db
        with SessionLocal() as db:
            aeroplane = make_aeroplane(db)
            _seed_and_get(db, aeroplane.uuid)

            val = svc.get_effective_assumption_value(db, aeroplane.uuid, "mass")
            assert val == PARAMETER_DEFAULTS["mass"]

    def test_returns_calculated_when_active(self, client_and_db):
        _, SessionLocal = client_and_db
        with SessionLocal() as db:
            aeroplane = make_aeroplane(db)
            _seed_and_get(db, aeroplane.uuid)

            from app.models.aeroplanemodel import DesignAssumptionModel
            from app.schemas.design_assumption import AssumptionSourceSwitch

            row = (
                db.query(DesignAssumptionModel)
                .filter(
                    DesignAssumptionModel.aeroplane_id == aeroplane.id,
                    DesignAssumptionModel.parameter_name == "mass",
                )
                .first()
            )
            row.calculated_value = 2.5
            row.calculated_source = "weight_items"
            db.flush()

            da_svc.switch_source(
                db,
                aeroplane.uuid,
                "mass",
                AssumptionSourceSwitch(active_source="CALCULATED"),
            )

            val = svc.get_effective_assumption_value(db, aeroplane.uuid, "mass")
            assert val == 2.5

    def test_falls_back_to_estimate_when_calculated_is_none(self, client_and_db):
        """When active_source is CALCULATED but calculated_value is None, return estimate."""
        _, SessionLocal = client_and_db
        with SessionLocal() as db:
            aeroplane = make_aeroplane(db)
            _seed_and_get(db, aeroplane.uuid)

            from app.models.aeroplanemodel import DesignAssumptionModel

            row = (
                db.query(DesignAssumptionModel)
                .filter(
                    DesignAssumptionModel.aeroplane_id == aeroplane.id,
                    DesignAssumptionModel.parameter_name == "mass",
                )
                .first()
            )
            row.active_source = "CALCULATED"
            row.calculated_value = None
            db.flush()

            val = svc.get_effective_assumption_value(db, aeroplane.uuid, "mass")
            assert val == PARAMETER_DEFAULTS["mass"]

    def test_raises_not_found(self, client_and_db):
        _, SessionLocal = client_and_db
        with SessionLocal() as db:
            aeroplane = make_aeroplane(db)
            _seed_and_get(db, aeroplane.uuid)

            with pytest.raises(NotFoundError):
                svc.get_effective_assumption_value(db, aeroplane.uuid, "nonexistent")


# ---------------------------------------------------------------------------
# aggregate_weight_items edge cases
# ---------------------------------------------------------------------------


class TestAggregateWeightItemsEdgeCases:
    def test_negative_mass_item(self):
        """Negative mass computes correctly (documents behavior)."""
        items = [
            {"mass_kg": 1.0, "x_m": 0.2, "y_m": 0.0, "z_m": 0.0},
            {"mass_kg": -0.5, "x_m": 0.4, "y_m": 0.0, "z_m": 0.0},
        ]
        mass, cx, cy, cz = svc.aggregate_weight_items(items)
        assert mass == pytest.approx(0.5)
        assert cx == pytest.approx((1.0 * 0.2 + (-0.5) * 0.4) / 0.5)


# ---------------------------------------------------------------------------
# Weight item CRUD sync resilience
# ---------------------------------------------------------------------------


class TestWeightItemSyncResilience:
    def test_crud_succeeds_without_seeded_assumptions(self, client_and_db):
        """Weight item create works even if no assumptions are seeded."""
        _, SessionLocal = client_and_db
        with SessionLocal() as db:
            aeroplane = make_aeroplane(db)
            item = wi_svc.create_weight_item(
                db,
                aeroplane.uuid,
                _make_weight_item(name="motor", mass_kg=0.3, x_m=0.05),
            )
            assert item.name == "motor"
            assert item.mass_kg == pytest.approx(0.3)
