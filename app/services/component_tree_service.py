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
            parent = db.query(ComponentTreeNodeModel).filter(
                ComponentTreeNodeModel.id == data.parent_id,
                ComponentTreeNodeModel.aeroplane_id == aeroplane_id,
            ).first()
            if not parent:
                raise NotFoundError(entity="Parent node", resource_id=data.parent_id)

        payload = data.model_dump()

        if data.construction_part_id is not None:
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
            # Snapshot — only fill fields the caller didn't explicitly set.
            explicit = data.model_dump(exclude_unset=True)
            if "volume_mm3" not in explicit and part.volume_mm3 is not None:
                payload["volume_mm3"] = part.volume_mm3
            if "area_mm2" not in explicit and part.area_mm2 is not None:
                payload["area_mm2"] = part.area_mm2
            if "material_id" not in explicit and part.material_component_id is not None:
                payload["material_id"] = part.material_component_id

        node = ComponentTreeNodeModel(aeroplane_id=aeroplane_id, **payload)
        db.add(node)
        db.commit()
        db.refresh(node)
        return _to_schema(node)
    except (NotFoundError, ValidationError):
        raise
    except SQLAlchemyError as exc:
        db.rollback()
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
            raise NotFoundError(entity="Component tree node", resource_id=node_id)

        for key, value in data.model_dump().items():
            setattr(node, key, value)
        db.commit()
        db.refresh(node)
        return _to_schema(node)
    except NotFoundError:
        raise
    except SQLAlchemyError as exc:
        db.rollback()
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
            raise NotFoundError(entity="Component tree node", resource_id=node_id)

        if node.synced_from:
            raise ValidationError(
                message=f"Cannot delete synced node '{node.name}' (synced from {node.synced_from}). "
                        "Use move instead.",
            )

        # Delete children recursively
        _delete_subtree(db, aeroplane_id, node_id)
        db.delete(node)
        db.commit()
    except (NotFoundError, ValidationError):
        raise
    except SQLAlchemyError as exc:
        db.rollback()
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
            raise NotFoundError(entity="Component tree node", resource_id=node_id)

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
        db.commit()
        db.refresh(node)
        return _to_schema(node)
    except (NotFoundError, ValidationError):
        raise
    except SQLAlchemyError as exc:
        db.rollback()
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


def calculate_weight(db: Session, aeroplane_id: str, node_id: int) -> WeightResponse:
    """Calculate recursive weight for a node."""
    node = db.query(ComponentTreeNodeModel).filter(
        ComponentTreeNodeModel.id == node_id,
        ComponentTreeNodeModel.aeroplane_id == aeroplane_id,
    ).first()
    if not node:
        raise NotFoundError(entity="Component tree node", resource_id=node_id)

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


def _calculate_own_weight(
    db: Session, node: ComponentTreeNodeModel
) -> tuple[Optional[float], str]:
    """Calculate a single node's own weight."""
    # Manual override takes precedence
    if node.weight_override_g is not None:
        return node.weight_override_g, "override"

    # COTS component: use mass_g from catalog
    if node.node_type == "cots" and node.component_id:
        comp = db.query(ComponentModel).filter(ComponentModel.id == node.component_id).first()
        if comp and comp.mass_g is not None:
            return comp.mass_g * (node.quantity or 1), "cots"

    # CAD shape: calculate from volume/area + material
    if node.node_type == "cad_shape" and node.material_id:
        material = db.query(ComponentModel).filter(ComponentModel.id == node.material_id).first()
        if material:
            specs = material.specs or {}
            density = specs.get("density_kg_m3")
            if density:
                if node.print_type == "surface" and node.area_mm2 is not None:
                    resolution = specs.get("print_resolution_mm", 0.4)
                    # area_mm2 * resolution_mm * density_kg_m3 / 1e9 → kg, * 1000 → g
                    weight_g = node.area_mm2 * resolution * density / 1e6 * node.scale_factor
                    return weight_g, "calculated"
                elif node.volume_mm3 is not None:
                    # volume_mm3 * density_kg_m3 / 1e9 → kg, * 1000 → g
                    weight_g = node.volume_mm3 * density / 1e6 * node.scale_factor
                    return weight_g, "calculated"

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
