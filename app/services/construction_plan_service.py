"""Service layer for Construction Plans (gh#101)."""
from __future__ import annotations

import inspect
import json
import logging
import time
from typing import Any

from sqlalchemy.exc import SQLAlchemyError
from sqlalchemy.orm import Session

from app.core.exceptions import InternalError, NotFoundError, ValidationError
from app.models.construction_plan import ConstructionPlanModel
from app.schemas.construction_plan import (
    CreatorInfo,
    CreatorOutput,
    CreatorParam,
    ExecuteRequest,
    ExecutionResult,
    PlanCreate,
    PlanRead,
    PlanSummary,
)

logger = logging.getLogger(__name__)


# ── Helpers ─────────────────────────────────────────────────────


def _count_steps(tree_json: dict) -> int:
    """Recursively count ConstructionStepNode entries in a tree.

    Handles both dict-keyed successors (GeneralJSONEncoder format)
    and list successors (frontend simplified format).
    """
    successors = tree_json.get("successors")
    if not successors:
        return 0
    count = 0
    nodes = successors.values() if isinstance(successors, dict) else successors
    for node in nodes:
        if isinstance(node, dict):
            count += 1
            count += _count_steps(node)
    return count


def _to_summary(plan: ConstructionPlanModel) -> PlanSummary:
    return PlanSummary(
        id=plan.id,
        name=plan.name,
        description=plan.description,
        step_count=_count_steps(plan.tree_json or {}),
        created_at=plan.created_at,
    )


def _to_read(plan: ConstructionPlanModel) -> PlanRead:
    return PlanRead.model_validate(plan, from_attributes=True)


def _validate_tree_json(tree_json: dict) -> None:
    """Minimal validation: root must have $TYPE and creator_id."""
    if "$TYPE" not in tree_json:
        raise ValidationError(
            message="tree_json must contain a '$TYPE' field at the root level.",
        )
    if "creator_id" not in tree_json:
        raise ValidationError(
            message="tree_json must contain a 'creator_id' field at the root level.",
        )


# ── CRUD ────────────────────────────────────────────────────────


def list_plans(db: Session) -> list[PlanSummary]:
    try:
        plans = db.query(ConstructionPlanModel).order_by(ConstructionPlanModel.id).all()
        return [_to_summary(p) for p in plans]
    except SQLAlchemyError as e:
        logger.error("DB error listing plans: %s", e)
        raise InternalError(message=f"Database error: {e}")


def get_plan(db: Session, plan_id: int) -> PlanRead:
    try:
        plan = db.get(ConstructionPlanModel, plan_id)
        if plan is None:
            raise NotFoundError(entity="Construction plan", resource_id=plan_id)
        return _to_read(plan)
    except NotFoundError:
        raise
    except SQLAlchemyError as e:
        logger.error("DB error getting plan %s: %s", plan_id, e)
        raise InternalError(message=f"Database error: {e}")


def create_plan(db: Session, data: PlanCreate) -> PlanRead:
    _validate_tree_json(data.tree_json)
    try:
        plan = ConstructionPlanModel(
            name=data.name,
            description=data.description,
            tree_json=data.tree_json,
        )
        db.add(plan)
        db.commit()
        db.refresh(plan)
        return _to_read(plan)
    except SQLAlchemyError as e:
        db.rollback()
        logger.error("DB error creating plan: %s", e)
        raise InternalError(message=f"Database error: {e}")


def update_plan(db: Session, plan_id: int, data: PlanCreate) -> PlanRead:
    _validate_tree_json(data.tree_json)
    try:
        plan = db.get(ConstructionPlanModel, plan_id)
        if plan is None:
            raise NotFoundError(entity="Construction plan", resource_id=plan_id)
        plan.name = data.name
        plan.description = data.description
        plan.tree_json = data.tree_json
        db.commit()
        db.refresh(plan)
        return _to_read(plan)
    except NotFoundError:
        raise
    except SQLAlchemyError as e:
        db.rollback()
        logger.error("DB error updating plan %s: %s", plan_id, e)
        raise InternalError(message=f"Database error: {e}")


def delete_plan(db: Session, plan_id: int) -> None:
    try:
        plan = db.get(ConstructionPlanModel, plan_id)
        if plan is None:
            raise NotFoundError(entity="Construction plan", resource_id=plan_id)
        db.delete(plan)
        db.commit()
    except NotFoundError:
        raise
    except SQLAlchemyError as e:
        db.rollback()
        logger.error("DB error deleting plan %s: %s", plan_id, e)
        raise InternalError(message=f"Database error: {e}")


# ── Creator Catalog ─────────────────────────────────────────────


_INTERNAL_PARAMS = {
    "self", "loglevel", "kwargs",
    "creator_id",
    # Runtime-injected config (passed by GeneralJSONDecoder, not user-facing)
    "wing_config", "printer_settings", "servo_information",
    "engine_information", "component_information",
}


def _parse_docstring_attributes(docstring: str) -> dict[str, str]:
    """Extract parameter descriptions from a docstring's Attributes section.

    Parses lines like:
        param_name (type): Description text here.
    Returns a dict mapping param_name → description.
    """
    import re

    result: dict[str, str] = {}
    in_attributes = False
    current_name: str | None = None
    current_desc: list[str] = []

    for line in docstring.split("\n"):
        stripped = line.strip()

        if stripped.lower().startswith("attributes:"):
            in_attributes = True
            continue

        if not in_attributes:
            continue

        # End of Attributes section on next section header
        if stripped and not stripped.startswith("_") and stripped.endswith(":") and "(" not in stripped:
            # Flush last param
            if current_name and current_desc:
                result[current_name] = " ".join(current_desc).strip()
            break

        # New attribute line: "name (type): description"
        match = re.match(r"(\w+)\s*\([^)]*\)\s*:\s*(.*)", stripped)
        if match:
            # Flush previous
            if current_name and current_desc:
                result[current_name] = " ".join(current_desc).strip()
            current_name = match.group(1)
            current_desc = [match.group(2)] if match.group(2) else []
        elif current_name and stripped:
            # Continuation line
            current_desc.append(stripped)
        elif not stripped and current_name:
            # Empty line ends current param
            if current_desc:
                result[current_name] = " ".join(current_desc).strip()
            current_name = None
            current_desc = []

    # Flush final param
    if current_name and current_desc:
        result[current_name] = " ".join(current_desc).strip()

    return result


def _parse_docstring_returns(docstring: str) -> list[CreatorOutput]:
    """Extract output descriptions from a docstring's Returns section.

    Parses lines like:
        {id} (Workplane): The fused result shape.
    Returns a list of CreatorOutput.
    """
    import re

    outputs: list[CreatorOutput] = []
    in_returns = False

    for line in docstring.split("\n"):
        stripped = line.strip()

        if stripped.lower().startswith("returns:"):
            in_returns = True
            continue

        if not in_returns:
            continue

        # End on next section header
        if stripped and not stripped.startswith("{") and stripped.endswith(":") and "(" not in stripped:
            break

        # Output line: "{id}.name (type): Description"
        match = re.match(r"(\{[^}]*\}[^\s]*)\s*(?:\([^)]*\))?\s*:\s*(.*)", stripped)
        if match:
            outputs.append(CreatorOutput(
                key=match.group(1),
                description=match.group(2).strip(),
            ))
        elif not stripped:
            if outputs:
                break  # Empty line after outputs ends section

    return outputs


_CATEGORY_MAP = {
    "wing": "wing",
    "fuselage": "fuselage",
    "cad_operations": "cad_operations",
    "export_import": "export_import",
    "components": "components",
}


def _get_category(cls: type) -> str:
    module = cls.__module__ or ""
    for key, category in _CATEGORY_MAP.items():
        if f".creator.{key}" in module:
            return category
    return "other"


def _type_to_str(annotation: Any) -> str:
    if annotation is inspect.Parameter.empty:
        return "any"
    if hasattr(annotation, "__name__"):
        return annotation.__name__
    return str(annotation).replace("typing.", "")


def list_creators() -> list[CreatorInfo]:
    """Reflect over all AbstractShapeCreator subclasses and return metadata."""
    try:
        from cad_designer.airplane.AbstractShapeCreator import AbstractShapeCreator
    except ImportError:
        logger.warning("cad_designer not available — returning empty creator list")
        return []

    # Import creator modules to register all subclasses
    try:
        import cad_designer.airplane.creator  # noqa: F401
    except ImportError:
        pass

    result: list[CreatorInfo] = []
    seen: set[str] = set()

    for cls in AbstractShapeCreator.__subclasses__():
        _collect_creators(cls, result, seen)

    result.sort(key=lambda c: (c.category, c.class_name))
    return result


def _collect_creators(cls: type, result: list[CreatorInfo], seen: set[str]) -> None:
    """Recursively collect creator classes from the inheritance tree."""
    name = cls.__name__
    if name in seen or name in ("ConstructionRootNode", "ConstructionStepNode", "JSONStepNode"):
        seen.add(name)
        # Still recurse for subclasses
        for sub in cls.__subclasses__():
            _collect_creators(sub, result, seen)
        return

    seen.add(name)

    sig = inspect.signature(cls.__init__)
    param_descriptions = _parse_docstring_attributes(cls.__doc__ or "")
    params: list[CreatorParam] = []
    for pname, param in sig.parameters.items():
        if pname in _INTERNAL_PARAMS:
            continue
        params.append(CreatorParam(
            name=pname,
            type=_type_to_str(param.annotation),
            default=param.default if param.default is not inspect.Parameter.empty else None,
            required=param.default is inspect.Parameter.empty,
            description=param_descriptions.get(pname),
        ))

    docstring = (cls.__doc__ or "").strip().split("\n")[0] if cls.__doc__ else None

    outputs = _parse_docstring_returns(cls.__doc__ or "")

    result.append(CreatorInfo(
        class_name=name,
        category=_get_category(cls),
        description=docstring,
        parameters=params,
        outputs=outputs,
    ))

    for sub in cls.__subclasses__():
        _collect_creators(sub, result, seen)


# ── Execute ─────────────────────────────────────────────────────


def execute_plan(
    db: Session,
    plan_id: int,
    request: ExecuteRequest,
) -> ExecutionResult:
    """Execute a plan against an aeroplane configuration."""
    from app.services.wing_service import get_aeroplane_or_raise, get_wing_or_raise
    from app.converters.model_schema_converters import wingModelToWingConfig

    # Load plan
    plan = db.get(ConstructionPlanModel, plan_id)
    if plan is None:
        raise NotFoundError(entity="Construction plan", resource_id=plan_id)

    # Load aeroplane
    aeroplane = get_aeroplane_or_raise(db, request.aeroplane_id)

    # Build wing_config map: all wings
    wing_config: dict = {}
    for wing in aeroplane.wings:
        try:
            wc = wingModelToWingConfig(wing, scale=1000.0)
            wing_config[wing.name] = wc
        except Exception as exc:
            logger.warning("Failed to convert wing '%s': %s", wing.name, exc)

    # Load printer_settings from component library (if available)
    printer_settings = _load_printer_settings(db)

    # Decode tree_json with GeneralJSONDecoder
    try:
        from cad_designer.airplane.GeneralJSONEncoderDecoder import GeneralJSONDecoder

        json_string = json.dumps(plan.tree_json)
        t0 = time.monotonic()
        root_node = json.loads(
            json_string,
            cls=GeneralJSONDecoder,
            wing_config=wing_config,
            printer_settings=printer_settings,
            servo_information={},
            engine_information=None,
            component_information=None,
        )
    except Exception as exc:
        raise ValidationError(
            message=f"Failed to decode construction plan: {exc}",
        )

    # Execute
    try:
        structure = root_node.create_shape()
        duration_ms = int((time.monotonic() - t0) * 1000)
    except Exception as exc:
        duration_ms = int((time.monotonic() - t0) * 1000)
        return ExecutionResult(
            status="error",
            error=str(exc),
            duration_ms=duration_ms,
        )

    shape_keys = list(structure.keys()) if isinstance(structure, dict) else []

    return ExecutionResult(
        status="success",
        shape_keys=shape_keys,
        duration_ms=duration_ms,
    )


def _load_printer_settings(db: Session):
    """Try to load Printer3dSettings from a component of type 'printer_settings'."""
    try:
        from app.models.component import ComponentModel
        comp = (
            db.query(ComponentModel)
            .filter(ComponentModel.component_type == "printer_settings")
            .first()
        )
        if comp and comp.specs:
            from cad_designer.airplane.aircraft_topology.printer3d import Printer3dSettings
            return Printer3dSettings(
                layer_height=float(comp.specs.get("layer_height", 0.24)),
                wall_thickness=float(comp.specs.get("wall_thickness", 0.42)),
                rel_gap_wall_thickness=float(comp.specs.get("rel_gap_wall_thickness", 0.075)),
            )
    except Exception as exc:
        logger.warning("Could not load printer_settings: %s", exc)

    # Fallback defaults
    try:
        from cad_designer.airplane.aircraft_topology.printer3d import Printer3dSettings
        return Printer3dSettings(layer_height=0.24, wall_thickness=0.42, rel_gap_wall_thickness=0.075)
    except ImportError:
        return None
