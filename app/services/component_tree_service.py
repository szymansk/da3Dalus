"""Component Tree Service — CRUD + weight calculation for the assembly tree."""

import logging
from typing import Optional

from sqlalchemy.exc import SQLAlchemyError
from sqlalchemy.orm import Session

from app.core.exceptions import InternalError, NotFoundError, ValidationError
from app.models.component_tree import ComponentTreeNodeModel
from app.models.component import ComponentModel
from app.models.construction_part import ConstructionPartModel
from app.schemas.component_tree import (
    ComponentTreeNodeRead,
    ComponentTreeNodeWithChildren,
    ComponentTreeNodeWrite,
    ComponentTreeResponse,
    WeightResponse,
)

logger = logging.getLogger(__name__)

# --- Shared error entity (S1192) ---
_ENTITY_COMPONENT_TREE_NODE = "Component tree node"


def _to_schema(m: ComponentTreeNodeModel) -> ComponentTreeNodeRead:
    return ComponentTreeNodeRead(
        id=m.id,
        aeroplane_id=m.aeroplane_id,
        parent_id=m.parent_id,
        sort_index=m.sort_index,
        node_type=m.node_type,
        name=m.name,
        shape_key=m.shape_key,
        shape_hash=m.shape_hash,
        volume_mm3=m.volume_mm3,
        area_mm2=m.area_mm2,
        component_id=m.component_id,
        quantity=m.quantity,
        construction_part_id=m.construction_part_id,
        pos_x=m.pos_x,
        pos_y=m.pos_y,
        pos_z=m.pos_z,
        rot_x=m.rot_x,
        rot_y=m.rot_y,
        rot_z=m.rot_z,
        material_id=m.material_id,
        weight_override_g=m.weight_override_g,
        print_type=m.print_type,
        scale_factor=m.scale_factor,
        synced_from=m.synced_from,
        created_at=m.created_at,
        updated_at=m.updated_at,
    )


def _build_tree(
    nodes: list[ComponentTreeNodeModel],
) -> list[ComponentTreeNodeWithChildren]:
    """Build nested tree from flat list of nodes."""
    node_map: dict[int, ComponentTreeNodeWithChildren] = {}
    for n in nodes:
        node_map[n.id] = ComponentTreeNodeWithChildren(**_to_schema(n).model_dump(), children=[])

    roots: list[ComponentTreeNodeWithChildren] = []
    for n in nodes:
        child = node_map[n.id]
        if n.parent_id and n.parent_id in node_map:
            node_map[n.parent_id].children.append(child)
        else:
            roots.append(child)

    # Sort children by sort_index
    for node in node_map.values():
        node.children.sort(key=lambda c: c.sort_index)
    roots.sort(key=lambda c: c.sort_index)

    return roots


def _roll_up_weights(
    node: ComponentTreeNodeWithChildren,
    own_weights: dict[int, tuple[Optional[float], str]],
) -> None:
    """Populate own_weight_g / own_weight_source / total_weight_g / weight_status
    on `node` and all its descendants (post-order traversal).

    Logic (gh#78):
      * Own source comes from `own_weights[node_id]` (computed elsewhere).
      * Leaf: status = valid if has_own else invalid.
      * Non-leaf:
          - all children valid → valid
          - all children invalid → invalid when own is absent, else partial
          - mixed → partial
      * total_weight_g = (own_weight_g or 0) + sum(child.total_weight_g).
    """
    for child in node.children:
        _roll_up_weights(child, own_weights)

    own, source = own_weights.get(node.id, (None, "none"))
    has_own = source != "none"

    node.own_weight_g = own
    node.own_weight_source = source  # type: ignore[assignment]
    node.total_weight_g = (own or 0.0) + sum(c.total_weight_g for c in node.children)

    if not node.children:
        node.weight_status = "valid" if has_own else "invalid"  # type: ignore[assignment]
        return

    child_statuses = [c.weight_status for c in node.children]
    all_valid = all(s == "valid" for s in child_statuses)
    all_invalid = all(s == "invalid" for s in child_statuses)
    if all_valid:
        node.weight_status = "valid"  # type: ignore[assignment]
    elif all_invalid:
        node.weight_status = "partial" if has_own else "invalid"  # type: ignore[assignment]
    else:
        node.weight_status = "partial"  # type: ignore[assignment]


def get_tree(db: Session, aeroplane_id: str) -> ComponentTreeResponse:
    """Get the full component tree for an aeroplane (with weight enrichment per gh#78)."""
    nodes = (
        db.query(ComponentTreeNodeModel)
        .filter(ComponentTreeNodeModel.aeroplane_id == aeroplane_id)
        .order_by(ComponentTreeNodeModel.sort_index)
        .all()
    )
    tree = _build_tree(nodes)

    # Pre-compute own weight + source for every node once, so the recursion
    # below doesn't re-hit the DB N times.
    own_weights: dict[int, tuple[Optional[float], str]] = {
        n.id: _calculate_own_weight(db, n) for n in nodes
    }
    for root in tree:
        _roll_up_weights(root, own_weights)

    return ComponentTreeResponse(
        aeroplane_id=aeroplane_id,
        root_nodes=tree,
        total_nodes=len(nodes),
    )


def _validate_parent_exists(db: Session, aeroplane_id: str, parent_id: int) -> None:
    """Raise NotFoundError if the parent node does not exist."""
    parent = db.query(ComponentTreeNodeModel).filter(
        ComponentTreeNodeModel.id == parent_id,
        ComponentTreeNodeModel.aeroplane_id == aeroplane_id,
    ).first()
    if not parent:
        raise NotFoundError(entity="Parent node", resource_id=parent_id)


def _snapshot_construction_part_fields(
    db: Session, aeroplane_id: str, data: ComponentTreeNodeWrite, payload: dict
) -> None:
    """Copy volume/area/material from the construction part onto payload for unset fields."""
    part = (
        db.query(ConstructionPartModel)
        .filter(
            ConstructionPartModel.id == data.construction_part_id,
            ConstructionPartModel.aeroplane_id == aeroplane_id,
        )
        .first()
    )
    if part is None:
        raise ValidationError(
            message=(
                f"construction_part_id={data.construction_part_id} does not "
                f"exist for aeroplane '{aeroplane_id}'."
            ),
        )
    explicit = data.model_dump(exclude_unset=True)
    if "volume_mm3" not in explicit and part.volume_mm3 is not None:
        payload["volume_mm3"] = part.volume_mm3
    if "area_mm2" not in explicit and part.area_mm2 is not None:
        payload["area_mm2"] = part.area_mm2
    if "material_id" not in explicit and part.material_component_id is not None:
        payload["material_id"] = part.material_component_id


def add_node(
    db: Session, aeroplane_id: str, data: ComponentTreeNodeWrite
) -> ComponentTreeNodeRead:
    """Add a node to the tree.

    When `construction_part_id` is set, the referenced part is loaded and its
    `volume_mm3`, `area_mm2`, and `material_component_id` are snapshotted onto
    the new node — but only for fields the caller did NOT explicitly pass
    (explicit values always win).
    """
    try:
        if data.parent_id:
            _validate_parent_exists(db, aeroplane_id, data.parent_id)

        payload = data.model_dump()

        if data.construction_part_id is not None:
            _snapshot_construction_part_fields(db, aeroplane_id, data, payload)

        node = ComponentTreeNodeModel(aeroplane_id=aeroplane_id, **payload)
        db.add(node)
        db.flush()
        db.refresh(node)
        _sync_aircraft_mass(db, aeroplane_id)
        return _to_schema(node)
    except (NotFoundError, ValidationError):
        raise
    except SQLAlchemyError as exc:
        logger.error("DB error in add_node: %s", exc)
        raise InternalError(message=f"Database error: {exc}") from exc


def update_node(
    db: Session, aeroplane_id: str, node_id: int, data: ComponentTreeNodeWrite
) -> ComponentTreeNodeRead:
    """Update a node in the tree."""
    try:
        node = db.query(ComponentTreeNodeModel).filter(
            ComponentTreeNodeModel.id == node_id,
            ComponentTreeNodeModel.aeroplane_id == aeroplane_id,
        ).first()
        if not node:
            raise NotFoundError(entity=_ENTITY_COMPONENT_TREE_NODE, resource_id=node_id)

        for key, value in data.model_dump().items():
            setattr(node, key, value)
        db.flush()
        db.refresh(node)
        _sync_aircraft_mass(db, aeroplane_id)
        return _to_schema(node)
    except NotFoundError:
        raise
    except SQLAlchemyError as exc:
        logger.error("DB error in update_node: %s", exc)
        raise InternalError(message=f"Database error: {exc}") from exc


def delete_node(db: Session, aeroplane_id: str, node_id: int) -> None:
    """Delete a node (and its children) from the tree."""
    try:
        node = db.query(ComponentTreeNodeModel).filter(
            ComponentTreeNodeModel.id == node_id,
            ComponentTreeNodeModel.aeroplane_id == aeroplane_id,
        ).first()
        if not node:
            raise NotFoundError(entity=_ENTITY_COMPONENT_TREE_NODE, resource_id=node_id)

        if node.synced_from:
            raise ValidationError(
                message=f"Cannot delete synced node '{node.name}' (synced from {node.synced_from}). "
                        "Use move instead.",
            )

        # Delete children recursively
        _delete_subtree(db, aeroplane_id, node_id)
        db.delete(node)
        db.flush()
        _sync_aircraft_mass(db, aeroplane_id)
    except (NotFoundError, ValidationError):
        raise
    except SQLAlchemyError as exc:
        logger.error("DB error in delete_node: %s", exc)
        raise InternalError(message=f"Database error: {exc}") from exc


def _delete_subtree(db: Session, aeroplane_id: str, parent_id: int) -> None:
    """Recursively delete all children of a node."""
    children = db.query(ComponentTreeNodeModel).filter(
        ComponentTreeNodeModel.aeroplane_id == aeroplane_id,
        ComponentTreeNodeModel.parent_id == parent_id,
    ).all()
    for child in children:
        _delete_subtree(db, aeroplane_id, child.id)
        db.delete(child)


def move_node(
    db: Session, aeroplane_id: str, node_id: int, new_parent_id: Optional[int], sort_index: int
) -> ComponentTreeNodeRead:
    """Move a node to a new parent."""
    try:
        node = db.query(ComponentTreeNodeModel).filter(
            ComponentTreeNodeModel.id == node_id,
            ComponentTreeNodeModel.aeroplane_id == aeroplane_id,
        ).first()
        if not node:
            raise NotFoundError(entity=_ENTITY_COMPONENT_TREE_NODE, resource_id=node_id)

        if new_parent_id:
            parent = db.query(ComponentTreeNodeModel).filter(
                ComponentTreeNodeModel.id == new_parent_id,
                ComponentTreeNodeModel.aeroplane_id == aeroplane_id,
            ).first()
            if not parent:
                raise NotFoundError(entity="New parent node", resource_id=new_parent_id)
            # Prevent moving to own descendant
            if _is_descendant(db, aeroplane_id, new_parent_id, node_id):
                raise ValidationError(message="Cannot move a node under its own subtree.")

        node.parent_id = new_parent_id
        node.sort_index = sort_index
        db.flush()
        db.refresh(node)
        return _to_schema(node)
    except (NotFoundError, ValidationError):
        raise
    except SQLAlchemyError as exc:
        logger.error("DB error in move_node: %s", exc)
        raise InternalError(message=f"Database error: {exc}") from exc


def _is_descendant(db: Session, aeroplane_id: str, candidate_id: int, ancestor_id: int) -> bool:
    """Check if candidate is a descendant of ancestor."""
    current = db.query(ComponentTreeNodeModel).filter(
        ComponentTreeNodeModel.id == candidate_id,
        ComponentTreeNodeModel.aeroplane_id == aeroplane_id,
    ).first()
    while current and current.parent_id:
        if current.parent_id == ancestor_id:
            return True
        current = db.query(ComponentTreeNodeModel).filter(
            ComponentTreeNodeModel.id == current.parent_id,
        ).first()
    return False


def _sync_aircraft_mass(db: Session, aeroplane_id: str) -> None:
    """Re-sync the mass design assumption after a tree mutation.

    Lazy-imported to avoid a circular import at module load. Errors are
    swallowed because a failed mass sync should NOT block the original
    component-tree CRUD operation.
    """
    try:
        from app.services.mass_cg_service import sync_component_tree_to_mass

        sync_component_tree_to_mass(db, aeroplane_id)
    except Exception:
        logger.warning(
            "Failed to sync aircraft mass after component-tree change for %s",
            aeroplane_id,
            exc_info=True,
        )


def get_aircraft_total_weight_kg(db: Session, aeroplane_id: str) -> Optional[float]:
    """Sum the weight of all top-level component-tree nodes (kg).

    Top-level here means parent_id IS NULL — that captures every wing,
    fuselage, payload, etc. since their synced groups are root nodes.
    Returns None if the tree is empty (so the caller knows to clear the
    mass calculated_value).
    """
    roots = (
        db.query(ComponentTreeNodeModel)
        .filter(
            ComponentTreeNodeModel.aeroplane_id == aeroplane_id,
            ComponentTreeNodeModel.parent_id.is_(None),
        )
        .all()
    )
    if not roots:
        return None
    total_g = 0.0
    for r in roots:
        own, _ = _calculate_own_weight(db, r)
        total_g += (own or 0.0) + _calculate_children_weight(
            db, aeroplane_id, r.id
        )
    return total_g / 1000.0 if total_g > 0 else None


def calculate_weight(db: Session, aeroplane_id: str, node_id: int) -> WeightResponse:
    """Calculate recursive weight for a node."""
    node = db.query(ComponentTreeNodeModel).filter(
        ComponentTreeNodeModel.id == node_id,
        ComponentTreeNodeModel.aeroplane_id == aeroplane_id,
    ).first()
    if not node:
        raise NotFoundError(entity=_ENTITY_COMPONENT_TREE_NODE, resource_id=node_id)

    own_weight, source = _calculate_own_weight(db, node)
    children_weight = _calculate_children_weight(db, aeroplane_id, node_id)

    return WeightResponse(
        node_id=node_id,
        name=node.name,
        own_weight_g=own_weight,
        children_weight_g=children_weight,
        total_weight_g=(own_weight or 0) + children_weight,
        source=source,
    )


def _weight_from_cots(db: Session, node: ComponentTreeNodeModel) -> Optional[float]:
    """Return weight in grams for a COTS component, or None."""
    if node.node_type != "cots" or not node.component_id:
        return None
    comp = db.query(ComponentModel).filter(ComponentModel.id == node.component_id).first()
    if comp and comp.mass_g is not None:
        return comp.mass_g * (node.quantity or 1)
    return None


def _weight_from_cad_shape(db: Session, node: ComponentTreeNodeModel) -> Optional[float]:
    """Return weight in grams for a CAD shape using material density, or None."""
    if node.node_type != "cad_shape" or not node.material_id:
        return None
    material = db.query(ComponentModel).filter(ComponentModel.id == node.material_id).first()
    if not material:
        return None
    specs = material.specs or {}
    density = specs.get("density_kg_m3")
    if not density:
        return None
    if node.print_type == "surface" and node.area_mm2 is not None:
        resolution = specs.get("print_resolution_mm", 0.4)
        return node.area_mm2 * resolution * density / 1e6 * node.scale_factor
    if node.volume_mm3 is not None:
        return node.volume_mm3 * density / 1e6 * node.scale_factor
    return None


def _calculate_own_weight(
    db: Session, node: ComponentTreeNodeModel
) -> tuple[Optional[float], str]:
    """Calculate a single node's own weight."""
    if node.weight_override_g is not None:
        return node.weight_override_g, "override"

    cots_weight = _weight_from_cots(db, node)
    if cots_weight is not None:
        return cots_weight, "cots"

    cad_weight = _weight_from_cad_shape(db, node)
    if cad_weight is not None:
        return cad_weight, "calculated"

    return None, "none"


def _calculate_children_weight(db: Session, aeroplane_id: str, parent_id: int) -> float:
    """Recursively sum children weights."""
    children = db.query(ComponentTreeNodeModel).filter(
        ComponentTreeNodeModel.aeroplane_id == aeroplane_id,
        ComponentTreeNodeModel.parent_id == parent_id,
    ).all()
    total = 0.0
    for child in children:
        own, _ = _calculate_own_weight(db, child)
        children_sum = _calculate_children_weight(db, aeroplane_id, child.id)
        total += (own or 0) + children_sum
    return total


# ── Auto-Sync (gh#108) ────────────────────────────────────────────


def sync_group_for_wing(db: Session, aeroplane_id: str, wing_name: str) -> None:
    """Ensure a synced group exists in the component tree for a wing."""
    synced_from = f"wing:{wing_name}"
    existing = db.query(ComponentTreeNodeModel).filter(
        ComponentTreeNodeModel.aeroplane_id == aeroplane_id,
        ComponentTreeNodeModel.synced_from == synced_from,
    ).first()
    if existing:
        return  # already exists
    node = ComponentTreeNodeModel(
        aeroplane_id=aeroplane_id,
        parent_id=None,
        sort_index=0,
        node_type="group",
        name=wing_name,
        synced_from=synced_from,
    )
    db.add(node)
    db.flush()


def sync_group_for_fuselage(db: Session, aeroplane_id: str, fuselage_name: str) -> None:
    """Ensure a synced group exists in the component tree for a fuselage."""
    synced_from = f"fuselage:{fuselage_name}"
    existing = db.query(ComponentTreeNodeModel).filter(
        ComponentTreeNodeModel.aeroplane_id == aeroplane_id,
        ComponentTreeNodeModel.synced_from == synced_from,
    ).first()
    if existing:
        return
    node = ComponentTreeNodeModel(
        aeroplane_id=aeroplane_id,
        parent_id=None,
        sort_index=0,
        node_type="group",
        name=fuselage_name,
        synced_from=synced_from,
    )
    db.add(node)
    db.flush()


def delete_synced_nodes(db: Session, aeroplane_id: str, synced_from_prefix: str) -> None:
    """Delete all synced nodes (and their children) matching a prefix."""
    nodes = db.query(ComponentTreeNodeModel).filter(
        ComponentTreeNodeModel.aeroplane_id == aeroplane_id,
        ComponentTreeNodeModel.synced_from.like(f"{synced_from_prefix}%"),
    ).all()
    for node in nodes:
        _delete_subtree(db, aeroplane_id, node.id)
        db.delete(node)
    db.flush()


def upsert_synced_servo(
    db: Session,
    aeroplane_id: str,
    wing_name: str,
    xsec_index: int,
    component_id: int | None,
    symmetric: bool = False,
) -> None:
    """Create or update a synced servo COTS node under the wing group."""
    synced_from = f"servo:{wing_name}:{xsec_index}"

    # Find or create the wing group
    wing_group = db.query(ComponentTreeNodeModel).filter(
        ComponentTreeNodeModel.aeroplane_id == aeroplane_id,
        ComponentTreeNodeModel.synced_from == f"wing:{wing_name}",
    ).first()

    if component_id is None:
        # Servo removed — delete synced node if it exists
        existing = db.query(ComponentTreeNodeModel).filter(
            ComponentTreeNodeModel.aeroplane_id == aeroplane_id,
            ComponentTreeNodeModel.synced_from == synced_from,
        ).first()
        if existing:
            db.delete(existing)
            db.flush()
        return

    # Resolve component name
    comp = db.query(ComponentModel).filter(ComponentModel.id == component_id).first()
    comp_name = comp.name if comp else f"Servo #{component_id}"

    existing = db.query(ComponentTreeNodeModel).filter(
        ComponentTreeNodeModel.aeroplane_id == aeroplane_id,
        ComponentTreeNodeModel.synced_from == synced_from,
    ).first()

    if existing:
        existing.component_id = component_id
        existing.name = comp_name
        existing.quantity = 2 if symmetric else 1
    else:
        node = ComponentTreeNodeModel(
            aeroplane_id=aeroplane_id,
            parent_id=wing_group.id if wing_group else None,
            sort_index=xsec_index,
            node_type="cots",
            name=comp_name,
            component_id=component_id,
            quantity=2 if symmetric else 1,
            synced_from=synced_from,
        )
        db.add(node)
    db.flush()
