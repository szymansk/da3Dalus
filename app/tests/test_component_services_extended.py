"""Extended tests for component_tree_service, component_service,
component_type_service, and construction_part_service.

Targets coverage gaps identified in GH Issue #294 (app/ Wave 4).
Focuses on uncovered functions and error/edge-case paths that the
existing integration tests do not exercise.
"""
from __future__ import annotations

import os
from pathlib import Path
from typing import Optional
from unittest.mock import patch

import pytest
from sqlalchemy.orm import Session

from app.core.exceptions import (
    ConflictError,
    InternalError,
    NotFoundError,
    ValidationError,
)
from app.models.component import ComponentModel
from app.models.component_tree import ComponentTreeNodeModel
from app.models.construction_part import ConstructionPartModel
from app.schemas.component_tree import ComponentTreeNodeWrite
from app.schemas.construction_part import ConstructionPartUpdate
from app.services import (
    component_service,
    component_tree_service,
    component_type_service,
    construction_part_service,
)


# --------------------------------------------------------------------------- #
# Fixtures
# --------------------------------------------------------------------------- #


@pytest.fixture()
def db(client_and_db):
    """Yield a plain Session for direct service-layer calls."""
    _, session_factory = client_and_db
    session = session_factory()
    try:
        yield session
    finally:
        session.close()


def _make_tree_node(
    db: Session,
    aeroplane_id: str = "aero-x",
    *,
    parent_id: Optional[int] = None,
    node_type: str = "group",
    name: str = "node",
    sort_index: int = 0,
    synced_from: Optional[str] = None,
    component_id: Optional[int] = None,
    material_id: Optional[int] = None,
    volume_mm3: Optional[float] = None,
    area_mm2: Optional[float] = None,
    weight_override_g: Optional[float] = None,
    print_type: Optional[str] = None,
    scale_factor: float = 1.0,
    quantity: int = 1,
    construction_part_id: Optional[int] = None,
) -> ComponentTreeNodeModel:
    node = ComponentTreeNodeModel(
        aeroplane_id=aeroplane_id,
        parent_id=parent_id,
        node_type=node_type,
        name=name,
        sort_index=sort_index,
        synced_from=synced_from,
        component_id=component_id,
        material_id=material_id,
        volume_mm3=volume_mm3,
        area_mm2=area_mm2,
        weight_override_g=weight_override_g,
        print_type=print_type,
        scale_factor=scale_factor,
        quantity=quantity,
        construction_part_id=construction_part_id,
    )
    db.add(node)
    db.commit()
    db.refresh(node)
    return node


def _make_component(
    db: Session,
    *,
    name: str = "TestComp",
    component_type: str = "generic",
    mass_g: Optional[float] = None,
    specs: Optional[dict] = None,
) -> ComponentModel:
    comp = ComponentModel(
        name=name,
        component_type=component_type,
        mass_g=mass_g,
        specs=specs or {},
    )
    db.add(comp)
    db.commit()
    db.refresh(comp)
    return comp


def _make_construction_part(
    db: Session,
    aeroplane_id: str = "aero-x",
    *,
    name: str = "Part",
    volume_mm3: Optional[float] = 5000.0,
    area_mm2: Optional[float] = 200.0,
    material_component_id: Optional[int] = None,
    locked: bool = False,
    file_path: Optional[str] = None,
    file_format: Optional[str] = None,
) -> ConstructionPartModel:
    part = ConstructionPartModel(
        aeroplane_id=aeroplane_id,
        name=name,
        volume_mm3=volume_mm3,
        area_mm2=area_mm2,
        material_component_id=material_component_id,
        locked=locked,
        file_path=file_path,
        file_format=file_format,
    )
    db.add(part)
    db.commit()
    db.refresh(part)
    return part


# =========================================================================== #
# component_tree_service
# =========================================================================== #


class TestBuildTree:
    """Test _build_tree and _roll_up_weights helper functions."""

    def test_build_tree_empty(self, db):
        tree = component_tree_service._build_tree([])
        assert tree == []

    def test_build_tree_single_root(self, db):
        node = _make_tree_node(db, name="root")
        tree = component_tree_service._build_tree([node])
        assert len(tree) == 1
        assert tree[0].name == "root"
        assert tree[0].children == []

    def test_build_tree_parent_child_sorted(self, db):
        root = _make_tree_node(db, name="root", sort_index=0)
        child_b = _make_tree_node(
            db, name="B", parent_id=root.id, sort_index=2
        )
        child_a = _make_tree_node(
            db, name="A", parent_id=root.id, sort_index=1
        )
        tree = component_tree_service._build_tree([root, child_b, child_a])
        assert len(tree) == 1
        assert [c.name for c in tree[0].children] == ["A", "B"]

    def test_build_tree_orphan_becomes_root(self, db):
        """A node whose parent_id is not in the list is treated as a root."""
        node = _make_tree_node(db, name="orphan")
        # Manually set parent_id to a nonexistent id
        node.parent_id = 99999
        tree = component_tree_service._build_tree([node])
        assert len(tree) == 1
        assert tree[0].name == "orphan"


class TestRollUpWeights:
    """Test weight rollup logic."""

    def test_leaf_valid_when_has_own_weight(self, db):
        node = _make_tree_node(db, name="leaf")
        tree = component_tree_service._build_tree([node])
        own_weights = {node.id: (10.0, "override")}
        component_tree_service._roll_up_weights(tree[0], own_weights)
        assert tree[0].own_weight_g == 10.0
        assert tree[0].own_weight_source == "override"
        assert tree[0].weight_status == "valid"
        assert tree[0].total_weight_g == 10.0

    def test_leaf_invalid_when_no_own_weight(self, db):
        node = _make_tree_node(db, name="leaf")
        tree = component_tree_service._build_tree([node])
        own_weights = {}
        component_tree_service._roll_up_weights(tree[0], own_weights)
        assert tree[0].weight_status == "invalid"
        assert tree[0].own_weight_g is None

    def test_parent_all_children_valid(self, db):
        root = _make_tree_node(db, name="root", sort_index=0)
        c1 = _make_tree_node(db, name="c1", parent_id=root.id, sort_index=0)
        c2 = _make_tree_node(db, name="c2", parent_id=root.id, sort_index=1)
        tree = component_tree_service._build_tree([root, c1, c2])
        own_weights = {
            root.id: (None, "none"),
            c1.id: (5.0, "calculated"),
            c2.id: (3.0, "cots"),
        }
        component_tree_service._roll_up_weights(tree[0], own_weights)
        assert tree[0].weight_status == "valid"
        assert tree[0].total_weight_g == 8.0

    def test_parent_all_children_invalid_no_own(self, db):
        root = _make_tree_node(db, name="root", sort_index=0)
        c1 = _make_tree_node(db, name="c1", parent_id=root.id, sort_index=0)
        tree = component_tree_service._build_tree([root, c1])
        own_weights = {
            root.id: (None, "none"),
            c1.id: (None, "none"),
        }
        component_tree_service._roll_up_weights(tree[0], own_weights)
        assert tree[0].weight_status == "invalid"

    def test_parent_all_children_invalid_with_own(self, db):
        root = _make_tree_node(db, name="root", sort_index=0)
        c1 = _make_tree_node(db, name="c1", parent_id=root.id, sort_index=0)
        tree = component_tree_service._build_tree([root, c1])
        own_weights = {
            root.id: (2.0, "override"),
            c1.id: (None, "none"),
        }
        component_tree_service._roll_up_weights(tree[0], own_weights)
        assert tree[0].weight_status == "partial"
        assert tree[0].total_weight_g == 2.0

    def test_parent_mixed_children_status(self, db):
        root = _make_tree_node(db, name="root", sort_index=0)
        c1 = _make_tree_node(db, name="c1", parent_id=root.id, sort_index=0)
        c2 = _make_tree_node(db, name="c2", parent_id=root.id, sort_index=1)
        tree = component_tree_service._build_tree([root, c1, c2])
        own_weights = {
            root.id: (None, "none"),
            c1.id: (5.0, "calculated"),
            c2.id: (None, "none"),
        }
        component_tree_service._roll_up_weights(tree[0], own_weights)
        assert tree[0].weight_status == "partial"


class TestWeightFromCots:
    """Test _weight_from_cots helper."""

    def test_not_cots_type_returns_none(self, db):
        node = _make_tree_node(db, node_type="group", name="grp")
        assert component_tree_service._weight_from_cots(db, node) is None

    def test_cots_no_component_id_returns_none(self, db):
        node = _make_tree_node(db, node_type="cots", name="cots_no_comp")
        assert component_tree_service._weight_from_cots(db, node) is None

    def test_cots_component_no_mass_returns_none(self, db):
        comp = _make_component(db, name="MasslessComp", mass_g=None)
        node = _make_tree_node(
            db, node_type="cots", name="cots", component_id=comp.id
        )
        assert component_tree_service._weight_from_cots(db, node) is None

    def test_cots_multiplied_by_quantity(self, db):
        comp = _make_component(db, name="Servo", mass_g=12.0)
        node = _make_tree_node(
            db,
            node_type="cots",
            name="servos",
            component_id=comp.id,
            quantity=3,
        )
        assert component_tree_service._weight_from_cots(db, node) == 36.0


class TestWeightFromCadShape:
    """Test _weight_from_cad_shape helper."""

    def test_not_cad_shape_returns_none(self, db):
        node = _make_tree_node(db, node_type="group", name="g")
        assert component_tree_service._weight_from_cad_shape(db, node) is None

    def test_no_material_returns_none(self, db):
        node = _make_tree_node(
            db, node_type="cad_shape", name="s", volume_mm3=1000.0
        )
        assert component_tree_service._weight_from_cad_shape(db, node) is None

    def test_material_no_density_returns_none(self, db):
        mat = _make_component(
            db,
            name="NoDensityMat",
            component_type="material",
            specs={},
        )
        node = _make_tree_node(
            db,
            node_type="cad_shape",
            name="s",
            material_id=mat.id,
            volume_mm3=1000.0,
        )
        assert component_tree_service._weight_from_cad_shape(db, node) is None

    def test_volume_calculation(self, db):
        mat = _make_component(
            db,
            name="PLA",
            component_type="material",
            specs={"density_kg_m3": 1240},
        )
        node = _make_tree_node(
            db,
            node_type="cad_shape",
            name="shell",
            material_id=mat.id,
            volume_mm3=10000.0,
            scale_factor=1.0,
        )
        weight = component_tree_service._weight_from_cad_shape(db, node)
        # 10000 * 1240 / 1e6 = 12.4 grams
        assert weight is not None
        assert abs(weight - 12.4) < 0.001

    def test_surface_calculation(self, db):
        mat = _make_component(
            db,
            name="SurfMat",
            component_type="material",
            specs={"density_kg_m3": 1000, "print_resolution_mm": 0.5},
        )
        node = _make_tree_node(
            db,
            node_type="cad_shape",
            name="skin",
            material_id=mat.id,
            area_mm2=2000.0,
            print_type="surface",
            scale_factor=1.0,
        )
        weight = component_tree_service._weight_from_cad_shape(db, node)
        # 2000 * 0.5 * 1000 / 1e6 * 1.0 = 1.0 gram
        assert weight is not None
        assert abs(weight - 1.0) < 0.001

    def test_surface_uses_default_resolution(self, db):
        mat = _make_component(
            db,
            name="MatNoRes",
            component_type="material",
            specs={"density_kg_m3": 1000},
        )
        node = _make_tree_node(
            db,
            node_type="cad_shape",
            name="skin",
            material_id=mat.id,
            area_mm2=1000.0,
            print_type="surface",
            scale_factor=1.0,
        )
        weight = component_tree_service._weight_from_cad_shape(db, node)
        # 1000 * 0.4 * 1000 / 1e6 * 1.0 = 0.4 gram (default resolution 0.4)
        assert weight is not None
        assert abs(weight - 0.4) < 0.001

    def test_cad_shape_no_volume_no_area_returns_none(self, db):
        mat = _make_component(
            db,
            name="MatX",
            component_type="material",
            specs={"density_kg_m3": 1000},
        )
        node = _make_tree_node(
            db,
            node_type="cad_shape",
            name="no_geom",
            material_id=mat.id,
        )
        assert component_tree_service._weight_from_cad_shape(db, node) is None

    def test_material_not_found_returns_none(self, db):
        node = _make_tree_node(
            db,
            node_type="cad_shape",
            name="no_mat",
            material_id=99999,
            volume_mm3=1000.0,
        )
        assert component_tree_service._weight_from_cad_shape(db, node) is None


class TestCalculateOwnWeight:
    """Test _calculate_own_weight priority chain."""

    def test_override_wins_over_everything(self, db):
        comp = _make_component(db, name="Comp", mass_g=50.0)
        node = _make_tree_node(
            db,
            node_type="cots",
            name="c",
            component_id=comp.id,
            weight_override_g=99.0,
        )
        weight, source = component_tree_service._calculate_own_weight(db, node)
        assert weight == 99.0
        assert source == "override"

    def test_cots_used_when_no_override(self, db):
        comp = _make_component(db, name="Motor", mass_g=50.0)
        node = _make_tree_node(
            db,
            node_type="cots",
            name="motor",
            component_id=comp.id,
        )
        weight, source = component_tree_service._calculate_own_weight(db, node)
        assert weight == 50.0
        assert source == "cots"

    def test_none_when_no_source(self, db):
        node = _make_tree_node(db, node_type="group", name="grp")
        weight, source = component_tree_service._calculate_own_weight(db, node)
        assert weight is None
        assert source == "none"


class TestAddNodeWithConstructionPart:
    """Test snapshot behaviour when construction_part_id is set."""

    def test_snapshots_volume_area_material_from_part(self, db):
        mat = _make_component(db, name="PLAMat", component_type="material")
        part = _make_construction_part(
            db,
            volume_mm3=7777.0,
            area_mm2=333.0,
            material_component_id=mat.id,
        )
        data = ComponentTreeNodeWrite(
            node_type="cad_shape",
            name="from_part",
            construction_part_id=part.id,
        )
        result = component_tree_service.add_node(db, "aero-x", data)
        assert result.volume_mm3 == 7777.0
        assert result.area_mm2 == 333.0
        assert result.material_id == mat.id

    def test_explicit_fields_win_over_snapshot(self, db):
        part = _make_construction_part(db, volume_mm3=7777.0)
        data = ComponentTreeNodeWrite(
            node_type="cad_shape",
            name="explicit",
            construction_part_id=part.id,
            volume_mm3=1111.0,
        )
        result = component_tree_service.add_node(db, "aero-x", data)
        assert result.volume_mm3 == 1111.0

    def test_invalid_construction_part_raises_validation(self, db):
        data = ComponentTreeNodeWrite(
            node_type="cad_shape",
            name="bad_part",
            construction_part_id=99999,
        )
        with pytest.raises(ValidationError, match="construction_part_id"):
            component_tree_service.add_node(db, "aero-x", data)

    def test_add_node_invalid_parent_raises_not_found(self, db):
        data = ComponentTreeNodeWrite(
            node_type="group",
            name="orphan",
            parent_id=99999,
        )
        with pytest.raises(NotFoundError):
            component_tree_service.add_node(db, "aero-x", data)


class TestUpdateNode:

    def test_update_missing_node_raises_not_found(self, db):
        data = ComponentTreeNodeWrite(node_type="group", name="x")
        with pytest.raises(NotFoundError):
            component_tree_service.update_node(db, "aero-x", 99999, data)

    def test_update_changes_fields(self, db):
        node = _make_tree_node(db, name="old_name")
        data = ComponentTreeNodeWrite(node_type="group", name="new_name")
        result = component_tree_service.update_node(
            db, "aero-x", node.id, data
        )
        assert result.name == "new_name"


class TestDeleteNode:

    def test_delete_missing_node_raises_not_found(self, db):
        with pytest.raises(NotFoundError):
            component_tree_service.delete_node(db, "aero-x", 99999)

    def test_delete_synced_node_raises_validation(self, db):
        node = _make_tree_node(
            db, name="synced", synced_from="wing:main_wing"
        )
        with pytest.raises(ValidationError, match="synced"):
            component_tree_service.delete_node(db, "aero-x", node.id)

    def test_delete_node_with_children(self, db):
        parent = _make_tree_node(db, name="parent")
        child = _make_tree_node(db, name="child", parent_id=parent.id)
        grandchild = _make_tree_node(
            db, name="grandchild", parent_id=child.id
        )
        component_tree_service.delete_node(db, "aero-x", parent.id)
        # All should be gone
        assert (
            db.query(ComponentTreeNodeModel)
            .filter(ComponentTreeNodeModel.id.in_([parent.id, child.id, grandchild.id]))
            .count()
            == 0
        )


class TestMoveNode:

    def test_move_to_nonexistent_parent_raises(self, db):
        node = _make_tree_node(db, name="move_me")
        with pytest.raises(NotFoundError):
            component_tree_service.move_node(db, "aero-x", node.id, 99999, 0)

    def test_move_nonexistent_node_raises(self, db):
        with pytest.raises(NotFoundError):
            component_tree_service.move_node(db, "aero-x", 99999, None, 0)

    def test_move_to_own_subtree_raises_validation(self, db):
        parent = _make_tree_node(db, name="parent")
        child = _make_tree_node(db, name="child", parent_id=parent.id)
        with pytest.raises(ValidationError, match="subtree"):
            component_tree_service.move_node(
                db, "aero-x", parent.id, child.id, 0
            )

    def test_move_to_root(self, db):
        parent = _make_tree_node(db, name="parent")
        child = _make_tree_node(db, name="child", parent_id=parent.id)
        result = component_tree_service.move_node(
            db, "aero-x", child.id, None, 5
        )
        assert result.parent_id is None
        assert result.sort_index == 5


class TestCalculateWeight:

    def test_calculate_weight_missing_node_raises(self, db):
        with pytest.raises(NotFoundError):
            component_tree_service.calculate_weight(db, "aero-x", 99999)

    def test_calculate_weight_returns_response(self, db):
        node = _make_tree_node(
            db, name="weighted", weight_override_g=15.0
        )
        result = component_tree_service.calculate_weight(
            db, "aero-x", node.id
        )
        assert result.own_weight_g == 15.0
        assert result.source == "override"
        assert result.total_weight_g == 15.0

    def test_calculate_children_weight_recursive(self, db):
        parent = _make_tree_node(db, name="parent")
        _make_tree_node(
            db,
            name="c1",
            parent_id=parent.id,
            weight_override_g=10.0,
        )
        child2 = _make_tree_node(
            db, name="c2", parent_id=parent.id
        )
        _make_tree_node(
            db,
            name="gc1",
            parent_id=child2.id,
            weight_override_g=5.0,
        )
        result = component_tree_service.calculate_weight(
            db, "aero-x", parent.id
        )
        assert result.children_weight_g == 15.0


class TestSyncGroups:

    def test_sync_group_for_wing_creates_node(self, db):
        component_tree_service.sync_group_for_wing(db, "aero-x", "main_wing")
        node = (
            db.query(ComponentTreeNodeModel)
            .filter(
                ComponentTreeNodeModel.aeroplane_id == "aero-x",
                ComponentTreeNodeModel.synced_from == "wing:main_wing",
            )
            .first()
        )
        assert node is not None
        assert node.name == "main_wing"
        assert node.node_type == "group"

    def test_sync_group_for_wing_idempotent(self, db):
        component_tree_service.sync_group_for_wing(db, "aero-x", "w1")
        component_tree_service.sync_group_for_wing(db, "aero-x", "w1")
        count = (
            db.query(ComponentTreeNodeModel)
            .filter(ComponentTreeNodeModel.synced_from == "wing:w1")
            .count()
        )
        assert count == 1

    def test_sync_group_for_fuselage_creates_node(self, db):
        component_tree_service.sync_group_for_fuselage(
            db, "aero-x", "fuse_main"
        )
        node = (
            db.query(ComponentTreeNodeModel)
            .filter(
                ComponentTreeNodeModel.synced_from == "fuselage:fuse_main",
            )
            .first()
        )
        assert node is not None
        assert node.name == "fuse_main"

    def test_sync_group_for_fuselage_idempotent(self, db):
        component_tree_service.sync_group_for_fuselage(db, "aero-x", "f1")
        component_tree_service.sync_group_for_fuselage(db, "aero-x", "f1")
        count = (
            db.query(ComponentTreeNodeModel)
            .filter(ComponentTreeNodeModel.synced_from == "fuselage:f1")
            .count()
        )
        assert count == 1

    def test_delete_synced_nodes_by_prefix(self, db):
        component_tree_service.sync_group_for_wing(db, "aero-x", "w_del")
        db.commit()
        # Also add a child under the synced group
        wing_group = (
            db.query(ComponentTreeNodeModel)
            .filter(ComponentTreeNodeModel.synced_from == "wing:w_del")
            .first()
        )
        _make_tree_node(
            db, name="child_of_synced", parent_id=wing_group.id
        )
        component_tree_service.delete_synced_nodes(
            db, "aero-x", "wing:w_del"
        )
        db.commit()
        remaining = (
            db.query(ComponentTreeNodeModel)
            .filter(ComponentTreeNodeModel.synced_from == "wing:w_del")
            .count()
        )
        assert remaining == 0


class TestUpsertSyncedServo:

    def test_create_synced_servo(self, db):
        component_tree_service.sync_group_for_wing(db, "aero-x", "mw")
        db.commit()
        comp = _make_component(db, name="TinyServo", mass_g=10.0)
        component_tree_service.upsert_synced_servo(
            db, "aero-x", "mw", 0, comp.id, symmetric=False
        )
        db.commit()
        node = (
            db.query(ComponentTreeNodeModel)
            .filter(ComponentTreeNodeModel.synced_from == "servo:mw:0")
            .first()
        )
        assert node is not None
        assert node.component_id == comp.id
        assert node.quantity == 1
        assert node.name == "TinyServo"

    def test_update_synced_servo(self, db):
        component_tree_service.sync_group_for_wing(db, "aero-x", "mw2")
        db.commit()
        comp1 = _make_component(db, name="Servo1", mass_g=10.0)
        comp2 = _make_component(db, name="Servo2", mass_g=15.0)
        component_tree_service.upsert_synced_servo(
            db, "aero-x", "mw2", 1, comp1.id, symmetric=False
        )
        db.commit()
        component_tree_service.upsert_synced_servo(
            db, "aero-x", "mw2", 1, comp2.id, symmetric=True
        )
        db.commit()
        node = (
            db.query(ComponentTreeNodeModel)
            .filter(ComponentTreeNodeModel.synced_from == "servo:mw2:1")
            .first()
        )
        assert node.component_id == comp2.id
        assert node.quantity == 2

    def test_remove_synced_servo(self, db):
        component_tree_service.sync_group_for_wing(db, "aero-x", "mw3")
        db.commit()
        comp = _make_component(db, name="Servo3", mass_g=10.0)
        component_tree_service.upsert_synced_servo(
            db, "aero-x", "mw3", 0, comp.id
        )
        db.commit()
        # Remove by passing component_id=None
        component_tree_service.upsert_synced_servo(
            db, "aero-x", "mw3", 0, None
        )
        db.commit()
        node = (
            db.query(ComponentTreeNodeModel)
            .filter(ComponentTreeNodeModel.synced_from == "servo:mw3:0")
            .first()
        )
        assert node is None

    def test_remove_nonexistent_servo_is_noop(self, db):
        # Should not raise
        component_tree_service.upsert_synced_servo(
            db, "aero-x", "nogroup", 0, None
        )

    def test_create_servo_without_wing_group(self, db):
        """When the wing group doesn't exist, parent_id is None."""
        comp = _make_component(db, name="OrphanServo", mass_g=5.0)
        component_tree_service.upsert_synced_servo(
            db, "aero-x", "no_wing", 0, comp.id
        )
        db.commit()
        node = (
            db.query(ComponentTreeNodeModel)
            .filter(ComponentTreeNodeModel.synced_from == "servo:no_wing:0")
            .first()
        )
        assert node is not None
        assert node.parent_id is None

    def test_create_servo_with_missing_component(self, db):
        """When component is not found, name falls back to default."""
        component_tree_service.upsert_synced_servo(
            db, "aero-x", "mw_fallback", 0, 99999
        )
        db.commit()
        node = (
            db.query(ComponentTreeNodeModel)
            .filter(
                ComponentTreeNodeModel.synced_from == "servo:mw_fallback:0"
            )
            .first()
        )
        assert node is not None
        assert "Servo #99999" in node.name


class TestGetTree:
    """Test the full get_tree response including weight enrichment."""

    def test_get_tree_enriches_weights(self, db):
        node = _make_tree_node(
            db, name="root_node", weight_override_g=42.0
        )
        tree_resp = component_tree_service.get_tree(db, "aero-x")
        assert tree_resp.total_nodes == 1
        root = tree_resp.root_nodes[0]
        assert root.own_weight_g == 42.0
        assert root.own_weight_source == "override"
        assert root.weight_status == "valid"


# =========================================================================== #
# component_type_service
# =========================================================================== #


class TestNormalizeSchema:
    """Test _normalize_schema for double-encoded and edge-case inputs."""

    def test_none_returns_empty(self):
        assert component_type_service._normalize_schema(None) == []

    def test_list_passes_through(self):
        data = [{"name": "x"}]
        assert component_type_service._normalize_schema(data) == data

    def test_string_json_list(self):
        import json

        data = [{"name": "x", "label": "X", "type": "string"}]
        encoded = json.dumps(data)
        assert component_type_service._normalize_schema(encoded) == data

    def test_string_non_json(self):
        assert component_type_service._normalize_schema("not json") == []

    def test_string_json_non_list(self):
        import json

        assert component_type_service._normalize_schema(json.dumps(42)) == []

    def test_unexpected_type(self):
        assert component_type_service._normalize_schema(12345) == []


class TestValidateSpecs:
    """Test specs validation against type schemas."""

    def test_unknown_type_raises_validation(self, db):
        with pytest.raises(ValidationError, match="Unknown component_type"):
            component_type_service.validate_specs(
                db, "nonexistent_type", {}
            )

    def test_missing_required_property_raises(self, db):
        with pytest.raises(ValidationError, match="missing"):
            component_type_service.validate_specs(
                db, "brushless_motor", {}
            )

    def test_valid_specs_pass(self, db):
        # Should not raise
        component_type_service.validate_specs(
            db, "brushless_motor", {"kv_rpm_per_volt": 1000}
        )

    def test_number_below_min_raises(self, db):
        with pytest.raises(ValidationError, match="below"):
            component_type_service.validate_specs(
                db, "material", {"density_kg_m3": 50}
            )

    def test_number_above_max_raises(self, db):
        with pytest.raises(ValidationError, match="exceeds"):
            component_type_service.validate_specs(
                db, "material", {"density_kg_m3": 999999}
            )

    def test_number_type_with_bool_raises(self, db):
        with pytest.raises(ValidationError, match="number"):
            component_type_service.validate_specs(
                db, "brushless_motor", {"kv_rpm_per_volt": True}
            )

    def test_number_type_with_string_raises(self, db):
        with pytest.raises(ValidationError, match="number"):
            component_type_service.validate_specs(
                db, "brushless_motor", {"kv_rpm_per_volt": "fast"}
            )

    def test_string_type_with_int_raises(self, db):
        with pytest.raises(ValidationError, match="string"):
            component_type_service.validate_specs(
                db, "propeller", {"diameter_in": 10, "pitch_in": 5, "blades": 2, "material": 42}
            )

    def test_boolean_type_with_string_raises(self, db):
        """Create a custom type with a boolean property and test validation."""
        from app.models.component_type import ComponentTypeModel

        ct = ComponentTypeModel(
            name="test_bool_type",
            label="Test Bool",
            schema_def=[
                {"name": "active", "label": "Active", "type": "boolean", "required": True},
            ],
            deletable=True,
        )
        db.add(ct)
        db.commit()
        with pytest.raises(ValidationError, match="true or false"):
            component_type_service.validate_specs(
                db, "test_bool_type", {"active": "yes"}
            )

    def test_enum_invalid_option_raises(self, db):
        with pytest.raises(ValidationError, match="not allowed"):
            component_type_service.validate_specs(
                db, "esc", {"max_current_a": 30, "protocol": "invalid_proto"}
            )

    def test_enum_valid_option_passes(self, db):
        component_type_service.validate_specs(
            db, "esc", {"max_current_a": 30, "protocol": "dshot300"}
        )

    def test_unknown_keys_ignored(self, db):
        # generic has empty schema, unknown keys are tolerated
        component_type_service.validate_specs(
            db, "generic", {"anything": "goes"}
        )


class TestListTypeNames:

    def test_returns_seeded_names(self, db):
        names = component_type_service.list_type_names(db)
        assert "material" in names
        assert "servo" in names
        assert "generic" in names


class TestComponentTypeCreateDuplicate:

    def test_create_duplicate_name_raises_conflict(self, db):
        from app.schemas.component_type import ComponentTypeWrite

        data = ComponentTypeWrite(
            name="dupe_test", label="Dupe", schema=[]
        )
        component_type_service.create_type(db, data)
        with pytest.raises(ConflictError, match="already exists"):
            component_type_service.create_type(db, data)


class TestComponentTypeDeleteProtections:

    def test_delete_seeded_raises_conflict(self, db):
        from app.models.component_type import ComponentTypeModel

        seeded = (
            db.query(ComponentTypeModel)
            .filter(ComponentTypeModel.name == "material")
            .first()
        )
        with pytest.raises(ConflictError, match="seeded"):
            component_type_service.delete_type(db, seeded.id)

    def test_delete_referenced_raises_conflict(self, db):
        from app.models.component_type import ComponentTypeModel
        from app.schemas.component_type import ComponentTypeWrite

        data = ComponentTypeWrite(
            name="ref_del_test", label="RefDel", schema=[]
        )
        ct = component_type_service.create_type(db, data)
        _make_component(db, name="Referencing", component_type="ref_del_test")
        with pytest.raises(ConflictError, match="referenced"):
            component_type_service.delete_type(db, ct.id)

    def test_delete_missing_raises_not_found(self, db):
        with pytest.raises(NotFoundError):
            component_type_service.delete_type(db, 99999)


class TestComponentTypeUpdate:

    def test_update_missing_raises_not_found(self, db):
        from app.schemas.component_type import ComponentTypeWrite

        data = ComponentTypeWrite(name="x", label="X", schema=[])
        with pytest.raises(NotFoundError):
            component_type_service.update_type(db, 99999, data)


# =========================================================================== #
# component_service
# =========================================================================== #


class TestComponentServiceListFiltering:

    def test_list_with_search_query(self, db):
        _make_component(db, name="Alpha Motor")
        _make_component(db, name="Beta Servo")
        result = component_service.list_components(db, q="Alpha")
        assert result.total == 1
        assert result.items[0].name == "Alpha Motor"

    def test_list_with_type_filter(self, db):
        _make_component(db, name="GenComp", component_type="generic")
        result = component_service.list_components(
            db, component_type="generic"
        )
        assert result.total >= 1
        assert all(
            c.component_type == "generic" for c in result.items
        )

    def test_list_empty(self, db):
        result = component_service.list_components(
            db, component_type="nonexistent_type_xyz"
        )
        assert result.total == 0


class TestComponentServiceCRUD:

    def test_get_missing_raises_not_found(self, db):
        with pytest.raises(NotFoundError):
            component_service.get_component(db, 99999)

    def test_update_missing_raises_not_found(self, db):
        from app.schemas.component import ComponentWrite

        data = ComponentWrite(
            name="X",
            component_type="generic",
            specs={},
        )
        with pytest.raises(NotFoundError):
            component_service.update_component(db, 99999, data)

    def test_delete_missing_raises_not_found(self, db):
        with pytest.raises(NotFoundError):
            component_service.delete_component(db, 99999)

    def test_create_and_delete_round_trip(self, db):
        from app.schemas.component import ComponentWrite

        data = ComponentWrite(
            name="Temp",
            component_type="generic",
            specs={},
        )
        created = component_service.create_component(db, data)
        assert created.id is not None
        component_service.delete_component(db, created.id)
        with pytest.raises(NotFoundError):
            component_service.get_component(db, created.id)


# =========================================================================== #
# construction_part_service
# =========================================================================== #


class TestValidateUpload:

    def test_empty_content_raises(self):
        with pytest.raises(ValidationError, match="empty"):
            construction_part_service._validate_upload("test.step", b"")

    def test_oversized_content_raises(self):
        huge = b"x" * (construction_part_service.MAX_FILE_SIZE_BYTES + 1)
        with pytest.raises(ConflictError, match="size"):
            construction_part_service._validate_upload("test.step", huge)

    def test_unsupported_extension_raises(self):
        with pytest.raises(ValidationError, match="Unsupported"):
            construction_part_service._validate_upload("model.obj", b"data")

    def test_step_extension_returns_step(self):
        suffix, fmt = construction_part_service._validate_upload(
            "model.step", b"data"
        )
        assert suffix == ".step"
        assert fmt == "step"

    def test_stp_extension_returns_step(self):
        suffix, fmt = construction_part_service._validate_upload(
            "model.STP", b"data"
        )
        assert suffix == ".stp"
        assert fmt == "step"

    def test_stl_extension_returns_stl(self):
        suffix, fmt = construction_part_service._validate_upload(
            "model.stl", b"data"
        )
        assert suffix == ".stl"
        assert fmt == "stl"

    def test_none_filename_uses_default(self):
        """No filename defaults to 'upload.unknown' which is unsupported."""
        with pytest.raises(ValidationError, match="Unsupported"):
            construction_part_service._validate_upload(None, b"data")


class TestStoreFile:

    def test_stores_file_on_disk(self, tmp_path):
        original_root = construction_part_service.STORAGE_ROOT
        construction_part_service.STORAGE_ROOT = tmp_path / "parts"
        try:
            dest = construction_part_service._store_file(
                "aero1", 42, b"step data", ".step"
            )
            assert dest.exists()
            assert dest.read_bytes() == b"step data"
            assert "aero1" in str(dest)
        finally:
            construction_part_service.STORAGE_ROOT = original_root


class TestCreatePart:

    def test_create_with_valid_step_file(self, db, tmp_path):
        original_root = construction_part_service.STORAGE_ROOT
        construction_part_service.STORAGE_ROOT = tmp_path / "parts"
        try:
            result = construction_part_service.create_part(
                db,
                "aero-x",
                filename="wing.step",
                content=b"fake step data",
                name="Wing Part",
                material_component_id=None,
                thumbnail_url=None,
            )
            assert result.name == "Wing Part"
            assert result.file_format == "step"
            assert result.aeroplane_id == "aero-x"
        finally:
            construction_part_service.STORAGE_ROOT = original_root

    def test_create_with_empty_name_raises(self, db):
        with pytest.raises(ValidationError, match="name"):
            construction_part_service.create_part(
                db,
                "aero-x",
                filename="wing.step",
                content=b"data",
                name="   ",
                material_component_id=None,
                thumbnail_url=None,
            )


class TestGetPartFile:

    def test_invalid_format_raises(self, db):
        part = _make_construction_part(
            db, file_path="/some/file.step", file_format="step"
        )
        with pytest.raises(ValidationError, match="Invalid format"):
            construction_part_service.get_part_file(
                db, "aero-x", part.id, "obj"
            )

    def test_missing_file_path_raises(self, db):
        part = _make_construction_part(db, file_path=None, file_format="step")
        with pytest.raises(NotFoundError):
            construction_part_service.get_part_file(
                db, "aero-x", part.id, "step"
            )

    def test_same_format_returns_path_directly(self, db, tmp_path):
        f = tmp_path / "test.step"
        f.write_bytes(b"step data")
        part = _make_construction_part(
            db, file_path=str(f), file_format="step"
        )
        path, mime = construction_part_service.get_part_file(
            db, "aero-x", part.id, "step"
        )
        assert path == f
        assert mime == "model/step"

    def test_stl_from_stl_source(self, db, tmp_path):
        f = tmp_path / "test.stl"
        f.write_bytes(b"stl data")
        part = _make_construction_part(
            db, file_path=str(f), file_format="stl"
        )
        path, mime = construction_part_service.get_part_file(
            db, "aero-x", part.id, "stl"
        )
        assert path == f
        assert mime == "model/stl"

    def test_step_from_stl_raises(self, db, tmp_path):
        f = tmp_path / "test.stl"
        f.write_bytes(b"stl data")
        part = _make_construction_part(
            db, file_path=str(f), file_format="stl"
        )
        with pytest.raises(ValidationError, match="cannot be regenerated"):
            construction_part_service.get_part_file(
                db, "aero-x", part.id, "step"
            )


class TestUpdatePart:

    def test_update_name(self, db):
        part = _make_construction_part(db, name="Old Name")
        data = ConstructionPartUpdate(name="New Name")
        result = construction_part_service.update_part(
            db, "aero-x", part.id, data
        )
        assert result.name == "New Name"

    def test_update_material(self, db):
        mat = _make_component(db, name="PLA", component_type="material")
        part = _make_construction_part(db)
        data = ConstructionPartUpdate(material_component_id=mat.id)
        result = construction_part_service.update_part(
            db, "aero-x", part.id, data
        )
        assert result.material_component_id == mat.id

    def test_update_thumbnail(self, db):
        part = _make_construction_part(db)
        data = ConstructionPartUpdate(thumbnail_url="/img/thumb.png")
        result = construction_part_service.update_part(
            db, "aero-x", part.id, data
        )
        assert result.thumbnail_url == "/img/thumb.png"

    def test_update_missing_part_raises(self, db):
        data = ConstructionPartUpdate(name="X")
        with pytest.raises(NotFoundError):
            construction_part_service.update_part(
                db, "aero-x", 99999, data
            )


class TestDeletePart:

    def test_delete_locked_raises_conflict(self, db):
        part = _make_construction_part(db, locked=True)
        with pytest.raises(ConflictError, match="locked"):
            construction_part_service.delete_part(db, "aero-x", part.id)

    def test_delete_missing_raises_not_found(self, db):
        with pytest.raises(NotFoundError):
            construction_part_service.delete_part(db, "aero-x", 99999)

    def test_delete_removes_file(self, db, tmp_path):
        f = tmp_path / "to_delete.step"
        f.write_bytes(b"data")
        part = _make_construction_part(
            db, file_path=str(f), file_format="step"
        )
        construction_part_service.delete_part(db, "aero-x", part.id)
        assert not f.exists()

    def test_delete_with_missing_file_succeeds(self, db):
        """If the file is already gone, delete should still succeed."""
        part = _make_construction_part(
            db, file_path="/nonexistent/path.step", file_format="step"
        )
        # Should not raise
        construction_part_service.delete_part(db, "aero-x", part.id)

    def test_delete_with_no_file_path(self, db):
        part = _make_construction_part(db, file_path=None)
        construction_part_service.delete_part(db, "aero-x", part.id)
        assert (
            db.query(ConstructionPartModel)
            .filter(ConstructionPartModel.id == part.id)
            .first()
            is None
        )


class TestExtractGeometry:

    def test_non_step_returns_empty(self, tmp_path):
        f = tmp_path / "test.stl"
        f.write_bytes(b"stl data")
        result = construction_part_service._extract_geometry(f, "stl")
        assert result["volume_mm3"] is None
        assert result["area_mm2"] is None

    @patch("app.services.construction_part_service.cad_available", return_value=False)
    def test_cad_unavailable_returns_empty(self, _mock, tmp_path):
        f = tmp_path / "test.step"
        f.write_bytes(b"step data")
        result = construction_part_service._extract_geometry(f, "step")
        assert result["volume_mm3"] is None


class TestConstructionPartListAndGet:

    def test_list_scoped_to_aeroplane(self, db):
        _make_construction_part(db, "aero-1", name="P1")
        _make_construction_part(db, "aero-2", name="P2")
        result = construction_part_service.list_parts(db, "aero-1")
        assert result.total == 1
        assert result.items[0].name == "P1"

    def test_get_part_not_found(self, db):
        with pytest.raises(NotFoundError):
            construction_part_service.get_part(db, "aero-x", 99999)

    def test_get_part_wrong_aeroplane(self, db):
        part = _make_construction_part(db, "aero-1", name="Scoped")
        with pytest.raises(NotFoundError):
            construction_part_service.get_part(db, "aero-wrong", part.id)
