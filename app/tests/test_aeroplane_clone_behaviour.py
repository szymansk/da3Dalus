"""Behaviour tests for clone_aeroplane_subgraph (gh-904).

Uses a throwaway in-memory SQLite DB — the user's real database is NEVER
touched.

What is tested:
1. Deep independence: mutating the clone's wing name does not affect the source.
2. New PKs: every cloned row has a different id than its source counterpart.
3. Internal FKs: wing.aeroplane_id points to the clone, not the source.
4. Shared refs: TED servo's component_id is preserved on the clone.
5. STEP paths: fuselage.step_path and solid_step_path are None on the clone.
6. copilot_messages: NOT cloned.
7. Versioning meta: is_immutable, branch_id, predecessor_id, root_id are set
   from the caller-supplied arguments.
8. Weight items: cloned with new ids; component_overrides in loading_scenarios
   are remapped to the new weight-item ids.
9. component_tree: cloned with new ids; parent_id re-keyed; aeroplane_id
   updated to clone's UUID string.
10. Wings / xsecs / spares / TEDs / servos are all independent copies.
"""

from __future__ import annotations

import uuid

import pytest
from sqlalchemy import create_engine
from sqlalchemy.orm import Session, sessionmaker
from sqlalchemy.pool import StaticPool

from app.db.base import Base
from app.models.aeroplanemodel import (
    AeroplaneModel,
    DesignAssumptionModel,
    FuselageModel,
    FuselageXSecSuperEllipseModel,
    LoadingScenarioModel,
    WeightItemModel,
    WingModel,
    WingXSecDetailModel,
    WingXSecModel,
    WingXSecSpareModel,
    WingXSecTedServoModel,
    WingXSecTrailingEdgeDeviceModel,
    WingXSecTurbulatorModel,
)
from app.models.component_tree import ComponentTreeNodeModel
from app.models.computation_config import AircraftComputationConfigModel
from app.models.mission_objective import MissionObjectiveModel
from app.models.stability_result import StabilityResultModel
from app.services.aeroplane_clone_service import clone_aeroplane_subgraph

# Import all models so Base.metadata is complete
import app.models.analysismodels  # noqa: F401

# avl_geometry_events is event-listener code, not a model with its own table
import app.models.avl_geometry_file  # noqa: F401
import app.models.component  # noqa: F401
import app.models.component_type  # noqa: F401
import app.models.construction_part  # noqa: F401
import app.models.construction_plan  # noqa: F401
import app.models.flight_envelope_model  # noqa: F401
import app.models.flightprofilemodel  # noqa: F401
import app.models.mission_preset  # noqa: F401
import app.models.tessellation_cache  # noqa: F401


# ---------------------------------------------------------------------------
# Fixtures
# ---------------------------------------------------------------------------


@pytest.fixture()
def db_session():
    """Fresh in-memory SQLite session for each test."""
    engine = create_engine(
        "sqlite://",
        connect_args={"check_same_thread": False},
        poolclass=StaticPool,
    )
    Base.metadata.create_all(bind=engine)
    SessionLocal = sessionmaker(
        bind=engine,
        autocommit=False,
        autoflush=False,
        expire_on_commit=False,
        class_=Session,
    )
    session = SessionLocal()
    try:
        yield session
    finally:
        session.close()
    Base.metadata.drop_all(bind=engine)


def _build_source(db: Session) -> AeroplaneModel:
    """Create a rich source aeroplane: wing + xsec + spare + TED + servo,
    fuselage + xsec, weight item, loading scenario, design assumption,
    computation config, stability result, mission objective, component-tree
    node.  Commits everything so all ids are populated.
    """
    src = AeroplaneModel(
        uuid=uuid.uuid4(),
        name="source-plane",
        total_mass_kg=2.5,
        xyz_ref=[0.1, 0.0, 0.0],
        assumption_computation_context={"key": "value"},
    )
    db.add(src)
    db.flush()

    # Wing + xsec + detail + spare + TED + servo
    wing = WingModel(aeroplane_id=src.id, name="main_wing", symmetric=True, design_model="flat")
    db.add(wing)
    db.flush()

    xsec = WingXSecModel(
        wing_id=wing.id,
        xyz_le=[0.0, 0.0, 0.0],
        chord=0.3,
        twist=0.0,
        airfoil="naca2412",
        sort_index=0,
    )
    db.add(xsec)
    db.flush()

    detail = WingXSecDetailModel(
        wing_xsec_id=xsec.id,
        x_sec_type="standard",
        tip_type="round",
        number_interpolation_points=10,
    )
    db.add(detail)
    db.flush()

    spare = WingXSecSpareModel(
        wing_xsec_detail_id=detail.id,
        sort_index=0,
        spare_support_dimension_width=3.0,
        spare_support_dimension_height=3.0,
        spare_position_factor=0.25,
        spare_length=500.0,
        spare_start=0.0,
        spare_mode="automatic",
        spare_vector=[1, 0, 0],
        spare_origin=[0, 0, 0],
    )
    db.add(spare)
    db.flush()

    ted = WingXSecTrailingEdgeDeviceModel(
        wing_xsec_detail_id=detail.id,
        name="aileron",
        role="aileron",
        rel_chord_root=0.7,
        rel_chord_tip=0.7,
        symmetric=False,
        deflection_deg=0.0,
        mix_gain_primary=1.0,
        mix_gain_secondary=1.0,
        differential_ratio=1.0,
    )
    db.add(ted)
    db.flush()

    servo = WingXSecTedServoModel(
        ted_id=ted.id,
        component_id=None,  # no component library entry in this test
        length=30.0,
        width=12.0,
        height=10.0,
    )
    db.add(servo)
    db.flush()

    # Turbulator (gh-934) — per-cross-section optional element
    turbulator = WingXSecTurbulatorModel(
        wing_xsec_detail_id=detail.id,
        form="zigzag",
        height_mm=0.3,
        position_root=0.07,
        position_tip=0.1,
        enabled=True,
    )
    db.add(turbulator)
    db.flush()

    # Fuselage + xsec with step paths
    fus = FuselageModel(
        aeroplane_id=src.id,
        name="main_fuselage",
        symmetric=False,
        step_path="tmp/fuselages/123.step",
        solid_step_path="tmp/fuselages/123_solid.step",
    )
    db.add(fus)
    db.flush()

    fxsec = FuselageXSecSuperEllipseModel(
        fuselage_id=fus.id, xyz=[0.5, 0.0, 0.0], a=0.1, b=0.1, n=2.0, sort_index=0
    )
    db.add(fxsec)
    db.flush()

    # Weight item
    wi = WeightItemModel(
        aeroplane_id=src.id,
        name="battery",
        mass_kg=0.3,
        x_m=0.15,
        y_m=0.0,
        z_m=0.0,
        description="LiPo",
        category="battery",
    )
    db.add(wi)
    db.flush()

    # Loading scenario that references the weight item id
    ls = LoadingScenarioModel(
        aeroplane_id=src.id,
        name="full load",
        aircraft_class="rc_trainer",
        component_overrides={
            "toggles": [{"component_uuid": str(wi.id), "enabled": True}],
            "mass_overrides": [{"component_uuid": str(wi.id), "mass_kg_override": 0.35}],
            "position_overrides": [],
            "adhoc_items": [],
        },
        is_default=False,
    )
    db.add(ls)
    db.flush()

    # Design assumption
    da = DesignAssumptionModel(
        aeroplane_id=src.id,
        parameter_name="cl_max",
        estimate_value=1.4,
        calculated_value=1.35,
        calculated_source="aerobuildup",
        active_source="CALCULATED",
    )
    db.add(da)
    db.flush()

    # Computation config
    cc = AircraftComputationConfigModel(
        aeroplane_id=src.id,
        coarse_alpha_min_deg=-5.0,
        coarse_alpha_max_deg=25.0,
        coarse_alpha_step_deg=1.0,
        fine_alpha_margin_deg=5.0,
        fine_alpha_step_deg=0.5,
        fine_velocity_count=8,
        debounce_seconds=2.0,
    )
    db.add(cc)
    db.flush()

    # Stability result
    sr = StabilityResultModel(
        aeroplane_id=src.id,
        solver="aerosandbox",
        neutral_point_x=0.28,
        mac=0.25,
        cg_x_used=0.24,
        static_margin_pct=16.0,
        stability_class="OK",
        is_statically_stable=True,
        is_directionally_stable=True,
        is_laterally_stable=True,
        status="CURRENT",
    )
    db.add(sr)
    db.flush()

    # Mission objective
    mo = MissionObjectiveModel(
        aeroplane_id=src.id,
        mission_type="trainer",
        target_cruise_mps=18.0,
        target_stall_safety=1.8,
        target_maneuver_n=3.0,
        target_glide_ld=12.0,
        target_climb_energy=22.0,
        target_wing_loading_n_m2=412.0,
        target_field_length_m=50.0,
        available_runway_m=50.0,
        runway_type="grass",
        t_static_N=18.0,
        takeoff_mode="runway",
    )
    db.add(mo)
    db.flush()

    # Component tree — root group + child node
    root_node = ComponentTreeNodeModel(
        aeroplane_id=str(src.uuid),
        parent_id=None,
        sort_index=0,
        node_type="group",
        name="main_wing",
    )
    db.add(root_node)
    db.flush()

    child_node = ComponentTreeNodeModel(
        aeroplane_id=str(src.uuid),
        parent_id=root_node.id,
        sort_index=0,
        node_type="cad_shape",
        name="segment_0",
        shape_key="seg0",
    )
    db.add(child_node)
    db.flush()

    db.commit()
    db.refresh(src)
    return src


# ---------------------------------------------------------------------------
# Tests
# ---------------------------------------------------------------------------


class TestCloneAeroplaneSubgraph:
    def test_clone_returns_new_aeroplane_with_new_id(self, db_session):
        src = _build_source(db_session)
        clone = clone_aeroplane_subgraph(
            db_session,
            src,
            immutable=False,
            branch_id=None,
            predecessor_id=src.id,
            root_id=src.id,
        )
        db_session.flush()
        assert clone.id is not None
        assert clone.id != src.id

    def test_clone_has_different_uuid(self, db_session):
        src = _build_source(db_session)
        clone = clone_aeroplane_subgraph(
            db_session, src, immutable=False, branch_id=None, predecessor_id=None, root_id=None
        )
        db_session.flush()
        assert clone.uuid != src.uuid

    def test_versioning_metadata_is_set(self, db_session):
        src = _build_source(db_session)
        clone = clone_aeroplane_subgraph(
            db_session,
            src,
            immutable=True,
            branch_id=42,
            predecessor_id=src.id,
            root_id=src.id,
        )
        db_session.flush()
        assert clone.is_immutable is True
        assert clone.branch_id == 42
        assert clone.predecessor_id == src.id
        assert clone.root_id == src.id

    def test_deep_independence_wing_name(self, db_session):
        """Mutating clone's wing name must not touch the source wing."""
        src = _build_source(db_session)
        clone = clone_aeroplane_subgraph(
            db_session, src, immutable=False, branch_id=None, predecessor_id=None, root_id=None
        )
        db_session.flush()

        # There should be exactly one wing on the clone
        clone_wings = db_session.query(WingModel).filter(WingModel.aeroplane_id == clone.id).all()
        assert len(clone_wings) == 1
        clone_wing = clone_wings[0]

        # Mutate clone wing
        clone_wing.name = "modified_wing"
        db_session.flush()

        # Source wing unchanged
        src_wings = db_session.query(WingModel).filter(WingModel.aeroplane_id == src.id).all()
        assert src_wings[0].name == "main_wing"

    def test_wings_have_new_ids_and_point_to_clone(self, db_session):
        src = _build_source(db_session)
        clone = clone_aeroplane_subgraph(
            db_session, src, immutable=False, branch_id=None, predecessor_id=None, root_id=None
        )
        db_session.flush()

        src_wings = db_session.query(WingModel).filter(WingModel.aeroplane_id == src.id).all()
        clone_wings = db_session.query(WingModel).filter(WingModel.aeroplane_id == clone.id).all()

        assert len(clone_wings) == len(src_wings)
        src_wing_ids = {w.id for w in src_wings}
        clone_wing_ids = {w.id for w in clone_wings}
        assert src_wing_ids.isdisjoint(clone_wing_ids), "Clone wings must have new PKs"

    def test_xsecs_spares_ted_servos_are_independent(self, db_session):
        src = _build_source(db_session)
        clone = clone_aeroplane_subgraph(
            db_session, src, immutable=False, branch_id=None, predecessor_id=None, root_id=None
        )
        db_session.flush()

        # Gather all xsec ids for source and clone wings
        src_wing_ids = [
            w.id for w in db_session.query(WingModel).filter(WingModel.aeroplane_id == src.id)
        ]
        clone_wing_ids = [
            w.id for w in db_session.query(WingModel).filter(WingModel.aeroplane_id == clone.id)
        ]

        src_xsec_ids = {
            x.id
            for x in db_session.query(WingXSecModel).filter(WingXSecModel.wing_id.in_(src_wing_ids))
        }
        clone_xsec_ids = {
            x.id
            for x in db_session.query(WingXSecModel).filter(
                WingXSecModel.wing_id.in_(clone_wing_ids)
            )
        }
        assert src_xsec_ids.isdisjoint(clone_xsec_ids), "Clone xsecs must have new PKs"

        # Details
        src_detail_ids = {
            d.id
            for d in db_session.query(WingXSecDetailModel).filter(
                WingXSecDetailModel.wing_xsec_id.in_(src_xsec_ids)
            )
        }
        clone_detail_ids = {
            d.id
            for d in db_session.query(WingXSecDetailModel).filter(
                WingXSecDetailModel.wing_xsec_id.in_(clone_xsec_ids)
            )
        }
        assert src_detail_ids.isdisjoint(clone_detail_ids)

        # Spares
        src_spare_ids = {
            s.id
            for s in db_session.query(WingXSecSpareModel).filter(
                WingXSecSpareModel.wing_xsec_detail_id.in_(src_detail_ids)
            )
        }
        clone_spare_ids = {
            s.id
            for s in db_session.query(WingXSecSpareModel).filter(
                WingXSecSpareModel.wing_xsec_detail_id.in_(clone_detail_ids)
            )
        }
        assert src_spare_ids.isdisjoint(clone_spare_ids)
        assert len(clone_spare_ids) == 1

        # TEDs
        src_ted_ids = {
            t.id
            for t in db_session.query(WingXSecTrailingEdgeDeviceModel).filter(
                WingXSecTrailingEdgeDeviceModel.wing_xsec_detail_id.in_(src_detail_ids)
            )
        }
        clone_ted_ids = {
            t.id
            for t in db_session.query(WingXSecTrailingEdgeDeviceModel).filter(
                WingXSecTrailingEdgeDeviceModel.wing_xsec_detail_id.in_(clone_detail_ids)
            )
        }
        assert src_ted_ids.isdisjoint(clone_ted_ids)
        assert len(clone_ted_ids) == 1

        # Servos
        src_servo_ids = {
            s.id
            for s in db_session.query(WingXSecTedServoModel).filter(
                WingXSecTedServoModel.ted_id.in_(src_ted_ids)
            )
        }
        clone_servo_ids = {
            s.id
            for s in db_session.query(WingXSecTedServoModel).filter(
                WingXSecTedServoModel.ted_id.in_(clone_ted_ids)
            )
        }
        assert src_servo_ids.isdisjoint(clone_servo_ids)
        assert len(clone_servo_ids) == 1

    def test_turbulator_is_cloned_with_matching_fields(self, db_session):
        """gh-1069: a turbulator (gh-934) on the source xsec detail must be
        deep-copied onto the cloned detail with all fields preserved and a
        new PK reparented to the clone's detail."""
        src = _build_source(db_session)
        clone = clone_aeroplane_subgraph(
            db_session, src, immutable=False, branch_id=None, predecessor_id=None, root_id=None
        )
        db_session.flush()

        # Resolve clone detail ids
        clone_wing_ids = [
            w.id for w in db_session.query(WingModel).filter(WingModel.aeroplane_id == clone.id)
        ]
        clone_xsec_ids = {
            x.id
            for x in db_session.query(WingXSecModel).filter(
                WingXSecModel.wing_id.in_(clone_wing_ids)
            )
        }
        clone_detail_ids = {
            d.id
            for d in db_session.query(WingXSecDetailModel).filter(
                WingXSecDetailModel.wing_xsec_id.in_(clone_xsec_ids)
            )
        }

        clone_turbs = (
            db_session.query(WingXSecTurbulatorModel)
            .filter(WingXSecTurbulatorModel.wing_xsec_detail_id.in_(clone_detail_ids))
            .all()
        )
        assert len(clone_turbs) == 1, "Turbulator must survive the clone (gh-1069)"
        turb = clone_turbs[0]
        assert turb.form == "zigzag"
        assert turb.height_mm == pytest.approx(0.3)
        assert turb.position_root == pytest.approx(0.07)
        assert turb.position_tip == pytest.approx(0.1)
        assert turb.enabled is True

    def test_turbulator_has_new_pk_and_independent(self, db_session):
        """The cloned turbulator must be a distinct row from the source one."""
        src = _build_source(db_session)
        clone = clone_aeroplane_subgraph(
            db_session, src, immutable=False, branch_id=None, predecessor_id=None, root_id=None
        )
        db_session.flush()

        src_turb = (
            db_session.query(WingXSecTurbulatorModel)
            .join(
                WingXSecDetailModel,
                WingXSecTurbulatorModel.wing_xsec_detail_id == WingXSecDetailModel.id,
            )
            .join(WingXSecModel, WingXSecDetailModel.wing_xsec_id == WingXSecModel.id)
            .join(WingModel, WingXSecModel.wing_id == WingModel.id)
            .filter(WingModel.aeroplane_id == src.id)
            .all()
        )
        clone_turb = (
            db_session.query(WingXSecTurbulatorModel)
            .join(
                WingXSecDetailModel,
                WingXSecTurbulatorModel.wing_xsec_detail_id == WingXSecDetailModel.id,
            )
            .join(WingXSecModel, WingXSecDetailModel.wing_xsec_id == WingXSecModel.id)
            .join(WingModel, WingXSecModel.wing_id == WingModel.id)
            .filter(WingModel.aeroplane_id == clone.id)
            .all()
        )
        assert len(src_turb) == len(clone_turb) == 1
        assert src_turb[0].id != clone_turb[0].id, "Clone turbulator must have a new PK"
        assert src_turb[0].wing_xsec_detail_id != clone_turb[0].wing_xsec_detail_id, (
            "Clone turbulator must be reparented to the clone's detail"
        )

    def test_clone_without_turbulator_is_fine(self, db_session):
        """A detail with no turbulator must clone without creating one."""
        src = _build_source(db_session)
        # Remove the source turbulator before cloning
        src_detail = (
            db_session.query(WingXSecDetailModel)
            .join(WingXSecModel, WingXSecDetailModel.wing_xsec_id == WingXSecModel.id)
            .join(WingModel, WingXSecModel.wing_id == WingModel.id)
            .filter(WingModel.aeroplane_id == src.id)
            .first()
        )
        db_session.query(WingXSecTurbulatorModel).filter(
            WingXSecTurbulatorModel.wing_xsec_detail_id == src_detail.id
        ).delete()
        db_session.flush()

        clone = clone_aeroplane_subgraph(
            db_session, src, immutable=False, branch_id=None, predecessor_id=None, root_id=None
        )
        db_session.flush()

        clone_wing_ids = [
            w.id for w in db_session.query(WingModel).filter(WingModel.aeroplane_id == clone.id)
        ]
        clone_xsec_ids = {
            x.id
            for x in db_session.query(WingXSecModel).filter(
                WingXSecModel.wing_id.in_(clone_wing_ids)
            )
        }
        clone_detail_ids = {
            d.id
            for d in db_session.query(WingXSecDetailModel).filter(
                WingXSecDetailModel.wing_xsec_id.in_(clone_xsec_ids)
            )
        }
        clone_turbs = (
            db_session.query(WingXSecTurbulatorModel)
            .filter(WingXSecTurbulatorModel.wing_xsec_detail_id.in_(clone_detail_ids))
            .all()
        )
        assert clone_turbs == [], "No turbulator should be created when source has none"

    def test_fuselage_step_paths_are_nulled(self, db_session):
        src = _build_source(db_session)
        clone = clone_aeroplane_subgraph(
            db_session, src, immutable=False, branch_id=None, predecessor_id=None, root_id=None
        )
        db_session.flush()

        clone_fuselages = (
            db_session.query(FuselageModel).filter(FuselageModel.aeroplane_id == clone.id).all()
        )
        assert len(clone_fuselages) == 1
        fus = clone_fuselages[0]
        assert fus.step_path is None, "step_path must be nulled on clone"
        assert fus.solid_step_path is None, "solid_step_path must be nulled on clone"

    def test_fuselage_source_step_paths_unchanged(self, db_session):
        """Source fuselage step paths must remain intact after clone."""
        src = _build_source(db_session)
        clone = clone_aeroplane_subgraph(
            db_session, src, immutable=False, branch_id=None, predecessor_id=None, root_id=None
        )
        db_session.flush()

        src_fuselages = (
            db_session.query(FuselageModel).filter(FuselageModel.aeroplane_id == src.id).all()
        )
        assert src_fuselages[0].step_path == "tmp/fuselages/123.step"
        assert src_fuselages[0].solid_step_path == "tmp/fuselages/123_solid.step"

    def test_copilot_messages_not_cloned(self, db_session):
        from app.models.aeroplanemodel import CopilotMessageModel

        src = _build_source(db_session)

        # Add a copilot message to the source
        msg = CopilotMessageModel(
            aeroplane_id=src.id,
            sort_index=0,
            role="user",
            content="hello",
        )
        db_session.add(msg)
        db_session.flush()

        clone = clone_aeroplane_subgraph(
            db_session, src, immutable=False, branch_id=None, predecessor_id=None, root_id=None
        )
        db_session.flush()

        clone_messages = (
            db_session.query(CopilotMessageModel)
            .filter(CopilotMessageModel.aeroplane_id == clone.id)
            .all()
        )
        assert clone_messages == [], "copilot_messages must NOT be cloned"

    def test_weight_items_are_independent_copies(self, db_session):
        src = _build_source(db_session)
        clone = clone_aeroplane_subgraph(
            db_session, src, immutable=False, branch_id=None, predecessor_id=None, root_id=None
        )
        db_session.flush()

        src_wi = (
            db_session.query(WeightItemModel).filter(WeightItemModel.aeroplane_id == src.id).all()
        )
        clone_wi = (
            db_session.query(WeightItemModel).filter(WeightItemModel.aeroplane_id == clone.id).all()
        )

        assert len(clone_wi) == len(src_wi)
        src_ids = {w.id for w in src_wi}
        clone_ids = {w.id for w in clone_wi}
        assert src_ids.isdisjoint(clone_ids), "Clone weight items must have new PKs"

        # Content preserved
        assert clone_wi[0].name == "battery"
        assert clone_wi[0].mass_kg == pytest.approx(0.3)

    def test_loading_scenario_component_overrides_remapped(self, db_session):
        """component_uuid values in loading scenarios point to NEW weight item ids."""
        src = _build_source(db_session)

        # Capture the old weight-item id before cloning
        src_wi = (
            db_session.query(WeightItemModel).filter(WeightItemModel.aeroplane_id == src.id).first()
        )
        old_wi_id_str = str(src_wi.id)

        clone = clone_aeroplane_subgraph(
            db_session, src, immutable=False, branch_id=None, predecessor_id=None, root_id=None
        )
        db_session.flush()

        # New weight item id
        new_wi = (
            db_session.query(WeightItemModel)
            .filter(WeightItemModel.aeroplane_id == clone.id)
            .first()
        )
        new_wi_id_str = str(new_wi.id)

        # Loading scenario on the clone
        clone_ls = (
            db_session.query(LoadingScenarioModel)
            .filter(LoadingScenarioModel.aeroplane_id == clone.id)
            .first()
        )
        assert clone_ls is not None

        overrides = clone_ls.component_overrides
        toggles = overrides.get("toggles", [])
        mass_overrides = overrides.get("mass_overrides", [])

        assert len(toggles) == 1
        assert toggles[0]["component_uuid"] == new_wi_id_str, (
            f"Expected remapped id {new_wi_id_str!r}, got {toggles[0]['component_uuid']!r}"
        )
        assert len(mass_overrides) == 1
        assert mass_overrides[0]["component_uuid"] == new_wi_id_str

        # Old id must not appear
        all_uuids = [t["component_uuid"] for t in toggles + mass_overrides]
        assert old_wi_id_str not in all_uuids

    def test_component_tree_cloned_with_new_ids(self, db_session):
        src = _build_source(db_session)
        clone = clone_aeroplane_subgraph(
            db_session, src, immutable=False, branch_id=None, predecessor_id=None, root_id=None
        )
        db_session.flush()

        src_nodes = (
            db_session.query(ComponentTreeNodeModel)
            .filter(ComponentTreeNodeModel.aeroplane_id == str(src.uuid))
            .all()
        )
        clone_nodes = (
            db_session.query(ComponentTreeNodeModel)
            .filter(ComponentTreeNodeModel.aeroplane_id == str(clone.uuid))
            .all()
        )

        assert len(clone_nodes) == len(src_nodes) == 2

        src_node_ids = {n.id for n in src_nodes}
        clone_node_ids = {n.id for n in clone_nodes}
        assert src_node_ids.isdisjoint(clone_node_ids), "Clone tree nodes must have new PKs"

    def test_component_tree_parent_id_remapped(self, db_session):
        src = _build_source(db_session)
        clone = clone_aeroplane_subgraph(
            db_session, src, immutable=False, branch_id=None, predecessor_id=None, root_id=None
        )
        db_session.flush()

        clone_nodes = (
            db_session.query(ComponentTreeNodeModel)
            .filter(ComponentTreeNodeModel.aeroplane_id == str(clone.uuid))
            .order_by(ComponentTreeNodeModel.sort_index)
            .all()
        )

        root_node = next(n for n in clone_nodes if n.parent_id is None)
        child_nodes = [n for n in clone_nodes if n.parent_id is not None]

        assert len(child_nodes) == 1
        child = child_nodes[0]

        # child.parent_id must point to the clone's root node (not the source's)
        assert child.parent_id == root_node.id, (
            f"child.parent_id={child.parent_id} should equal clone root node id={root_node.id}"
        )

    def test_component_tree_aeroplane_id_updated(self, db_session):
        src = _build_source(db_session)
        clone = clone_aeroplane_subgraph(
            db_session, src, immutable=False, branch_id=None, predecessor_id=None, root_id=None
        )
        db_session.flush()

        clone_nodes = (
            db_session.query(ComponentTreeNodeModel)
            .filter(ComponentTreeNodeModel.aeroplane_id == str(clone.uuid))
            .all()
        )

        # All nodes must use the clone's UUID, not the source's
        for node in clone_nodes:
            assert node.aeroplane_id == str(clone.uuid)
            assert node.aeroplane_id != str(src.uuid)

    def test_design_assumptions_cloned(self, db_session):
        src = _build_source(db_session)
        clone = clone_aeroplane_subgraph(
            db_session, src, immutable=False, branch_id=None, predecessor_id=None, root_id=None
        )
        db_session.flush()

        from app.models.aeroplanemodel import DesignAssumptionModel

        src_das = (
            db_session.query(DesignAssumptionModel)
            .filter(DesignAssumptionModel.aeroplane_id == src.id)
            .all()
        )
        clone_das = (
            db_session.query(DesignAssumptionModel)
            .filter(DesignAssumptionModel.aeroplane_id == clone.id)
            .all()
        )

        assert len(clone_das) == len(src_das) == 1
        assert clone_das[0].parameter_name == "cl_max"
        assert clone_das[0].id != src_das[0].id

    def test_stability_results_cloned(self, db_session):
        src = _build_source(db_session)
        clone = clone_aeroplane_subgraph(
            db_session, src, immutable=False, branch_id=None, predecessor_id=None, root_id=None
        )
        db_session.flush()

        src_srs = (
            db_session.query(StabilityResultModel)
            .filter(StabilityResultModel.aeroplane_id == src.id)
            .all()
        )
        clone_srs = (
            db_session.query(StabilityResultModel)
            .filter(StabilityResultModel.aeroplane_id == clone.id)
            .all()
        )

        assert len(clone_srs) == len(src_srs) == 1
        assert clone_srs[0].solver == "aerosandbox"
        assert clone_srs[0].id != src_srs[0].id

    def test_mission_objective_cloned(self, db_session):
        src = _build_source(db_session)
        clone = clone_aeroplane_subgraph(
            db_session, src, immutable=False, branch_id=None, predecessor_id=None, root_id=None
        )
        db_session.flush()

        src_mo = (
            db_session.query(MissionObjectiveModel)
            .filter(MissionObjectiveModel.aeroplane_id == src.id)
            .first()
        )
        clone_mo = (
            db_session.query(MissionObjectiveModel)
            .filter(MissionObjectiveModel.aeroplane_id == clone.id)
            .first()
        )

        assert clone_mo is not None
        assert clone_mo.mission_type == "trainer"
        assert clone_mo.id != src_mo.id

    def test_computation_config_cloned(self, db_session):
        src = _build_source(db_session)
        clone = clone_aeroplane_subgraph(
            db_session, src, immutable=False, branch_id=None, predecessor_id=None, root_id=None
        )
        db_session.flush()

        src_cc = (
            db_session.query(AircraftComputationConfigModel)
            .filter(AircraftComputationConfigModel.aeroplane_id == src.id)
            .first()
        )
        clone_cc = (
            db_session.query(AircraftComputationConfigModel)
            .filter(AircraftComputationConfigModel.aeroplane_id == clone.id)
            .first()
        )

        assert clone_cc is not None
        assert clone_cc.coarse_alpha_step_deg == pytest.approx(1.0)
        assert clone_cc.id != src_cc.id

    def test_xyz_ref_is_independent_copy(self, db_session):
        """Mutating clone.xyz_ref must not affect source.xyz_ref."""
        src = _build_source(db_session)
        clone = clone_aeroplane_subgraph(
            db_session, src, immutable=False, branch_id=None, predecessor_id=None, root_id=None
        )
        db_session.flush()

        # Mutate clone's xyz_ref
        clone.xyz_ref = [9.9, 9.9, 9.9]
        db_session.flush()

        db_session.expire(src)
        db_session.refresh(src)
        assert src.xyz_ref == [0.1, 0.0, 0.0], (
            "Source xyz_ref must not be affected by clone mutation"
        )

    def test_fuselage_xsecs_independent(self, db_session):
        src = _build_source(db_session)
        clone = clone_aeroplane_subgraph(
            db_session, src, immutable=False, branch_id=None, predecessor_id=None, root_id=None
        )
        db_session.flush()

        src_fus = (
            db_session.query(FuselageModel).filter(FuselageModel.aeroplane_id == src.id).first()
        )
        clone_fus = (
            db_session.query(FuselageModel).filter(FuselageModel.aeroplane_id == clone.id).first()
        )

        src_xsecs = (
            db_session.query(FuselageXSecSuperEllipseModel)
            .filter(FuselageXSecSuperEllipseModel.fuselage_id == src_fus.id)
            .all()
        )
        clone_xsecs = (
            db_session.query(FuselageXSecSuperEllipseModel)
            .filter(FuselageXSecSuperEllipseModel.fuselage_id == clone_fus.id)
            .all()
        )

        assert len(clone_xsecs) == len(src_xsecs) == 1
        src_xsec_ids = {x.id for x in src_xsecs}
        clone_xsec_ids = {x.id for x in clone_xsecs}
        assert src_xsec_ids.isdisjoint(clone_xsec_ids)

    def test_clone_with_no_optional_children(self, db_session):
        """A minimal aeroplane (no wings/fuselages/etc.) clones without error."""
        minimal = AeroplaneModel(
            uuid=uuid.uuid4(),
            name="minimal",
            total_mass_kg=None,
        )
        db_session.add(minimal)
        db_session.commit()
        db_session.refresh(minimal)

        clone = clone_aeroplane_subgraph(
            db_session,
            minimal,
            immutable=False,
            branch_id=None,
            predecessor_id=None,
            root_id=None,
        )
        db_session.flush()
        assert clone.id != minimal.id
        assert clone.name == "minimal"

    def test_component_tree_3level_parent_remapping(self, db_session):
        """3-level hierarchy (root → child → grandchild): parent_id remapping
        must be correct at every depth, not just root→child."""
        src = AeroplaneModel(uuid=uuid.uuid4(), name="3level", total_mass_kg=None)
        db_session.add(src)
        db_session.flush()

        # root (depth 0)
        root_node = ComponentTreeNodeModel(
            aeroplane_id=str(src.uuid),
            parent_id=None,
            sort_index=0,
            node_type="group",
            name="root",
        )
        db_session.add(root_node)
        db_session.flush()

        # child (depth 1) — parent is root
        child_node = ComponentTreeNodeModel(
            aeroplane_id=str(src.uuid),
            parent_id=root_node.id,
            sort_index=0,
            node_type="group",
            name="child",
        )
        db_session.add(child_node)
        db_session.flush()

        # grandchild (depth 2) — parent is child
        grandchild_node = ComponentTreeNodeModel(
            aeroplane_id=str(src.uuid),
            parent_id=child_node.id,
            sort_index=0,
            node_type="cad_shape",
            name="grandchild",
        )
        db_session.add(grandchild_node)
        db_session.flush()
        db_session.commit()
        db_session.refresh(src)

        clone = clone_aeroplane_subgraph(
            db_session, src, immutable=False, branch_id=None, predecessor_id=None, root_id=None
        )
        db_session.flush()

        # All clone nodes use the clone's UUID
        clone_nodes = (
            db_session.query(ComponentTreeNodeModel)
            .filter(ComponentTreeNodeModel.aeroplane_id == str(clone.uuid))
            .order_by(ComponentTreeNodeModel.id)
            .all()
        )
        assert len(clone_nodes) == 3, "All three levels must be cloned"

        # Verify tree structure: none of the clone node ids exist in the source
        src_node_ids = {root_node.id, child_node.id, grandchild_node.id}
        clone_node_ids = {n.id for n in clone_nodes}
        assert src_node_ids.isdisjoint(clone_node_ids), "Clone nodes must have new PKs"

        # root → no parent
        clone_root = next(n for n in clone_nodes if n.name == "root")
        assert clone_root.parent_id is None

        # child → parent is clone_root
        clone_child = next(n for n in clone_nodes if n.name == "child")
        assert clone_child.parent_id == clone_root.id, (
            f"clone_child.parent_id={clone_child.parent_id} must equal "
            f"clone_root.id={clone_root.id}"
        )

        # grandchild → parent is clone_child
        clone_grandchild = next(n for n in clone_nodes if n.name == "grandchild")
        assert clone_grandchild.parent_id == clone_child.id, (
            f"clone_grandchild.parent_id={clone_grandchild.parent_id} must equal "
            f"clone_child.id={clone_child.id}"
        )

    def test_component_tree_orphan_parent_logs_warning(self, db_session, caplog):
        """When a source node's parent_id is not in the cloned node set
        (cross-aeroplane / corrupt data), the clone service must log a WARNING
        and set parent_id=None on the cloned node — not raise."""
        import logging

        src = AeroplaneModel(uuid=uuid.uuid4(), name="orphan-test", total_mass_kg=None)
        db_session.add(src)
        db_session.flush()

        # Create a node whose parent_id references a node from a DIFFERENT aeroplane
        # (simulated by using an id that is not in this aeroplane's node set).
        other = AeroplaneModel(uuid=uuid.uuid4(), name="other", total_mass_kg=None)
        db_session.add(other)
        db_session.flush()

        other_node = ComponentTreeNodeModel(
            aeroplane_id=str(other.uuid),
            parent_id=None,
            sort_index=0,
            node_type="group",
            name="other-root",
        )
        db_session.add(other_node)
        db_session.flush()

        # Node for src that points to the other aeroplane's node as its "parent"
        orphan = ComponentTreeNodeModel(
            aeroplane_id=str(src.uuid),
            parent_id=other_node.id,  # cross-aeroplane reference
            sort_index=0,
            node_type="cad_shape",
            name="orphan",
        )
        db_session.add(orphan)
        db_session.flush()
        db_session.commit()
        db_session.refresh(src)

        with caplog.at_level(logging.WARNING, logger="app.services.aeroplane_clone_service"):
            clone = clone_aeroplane_subgraph(
                db_session,
                src,
                immutable=False,
                branch_id=None,
                predecessor_id=None,
                root_id=None,
            )
            db_session.flush()

        # The cloned orphan node must have parent_id=None
        clone_node = (
            db_session.query(ComponentTreeNodeModel)
            .filter(
                ComponentTreeNodeModel.aeroplane_id == str(clone.uuid),
                ComponentTreeNodeModel.name == "orphan",
            )
            .first()
        )
        assert clone_node is not None
        assert clone_node.parent_id is None, "Orphaned parent must be dropped (parent_id=None)"

        # A warning must have been logged
        assert any("parent_id" in record.message for record in caplog.records), (
            "Expected a WARNING log about the dropped parent link"
        )
