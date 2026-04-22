"""Service layer for Construction Plans (gh#101)."""
from __future__ import annotations

import inspect
import json
import logging
import re
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

_ENTITY_CONSTRUCTION_PLAN = "Construction plan"


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
        plan_type=plan.plan_type,
        aeroplane_id=plan.aeroplane_id,
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


def _get_plan_or_raise(db: Session, plan_id: int) -> ConstructionPlanModel:
    """Load a plan by ID or raise NotFoundError."""
    plan = db.get(ConstructionPlanModel, plan_id)
    if plan is None:
        raise NotFoundError(entity=_ENTITY_CONSTRUCTION_PLAN, resource_id=plan_id)
    return plan


# ── CRUD ────────────────────────────────────────────────────────


def list_plans(
    db: Session,
    plan_type: str | None = None,
    aeroplane_id: str | None = None,
) -> list[PlanSummary]:
    try:
        query = db.query(ConstructionPlanModel)
        if plan_type:
            query = query.filter(ConstructionPlanModel.plan_type == plan_type)
        if aeroplane_id:
            query = query.filter(ConstructionPlanModel.aeroplane_id == aeroplane_id)
        plans = query.order_by(ConstructionPlanModel.name).all()
        return [_to_summary(p) for p in plans]
    except SQLAlchemyError as e:
        logger.error("DB error listing plans: %s", e)
        raise InternalError(message=f"Database error: {e}")


def get_plan(db: Session, plan_id: int) -> PlanRead:
    try:
        plan = db.get(ConstructionPlanModel, plan_id)
        if plan is None:
            raise NotFoundError(entity=_ENTITY_CONSTRUCTION_PLAN, resource_id=plan_id)
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
            plan_type=data.plan_type,
            aeroplane_id=data.aeroplane_id,
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
            raise NotFoundError(entity=_ENTITY_CONSTRUCTION_PLAN, resource_id=plan_id)
        plan.name = data.name
        plan.description = data.description
        plan.tree_json = data.tree_json
        plan.plan_type = data.plan_type
        plan.aeroplane_id = data.aeroplane_id
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
            raise NotFoundError(entity=_ENTITY_CONSTRUCTION_PLAN, resource_id=plan_id)
        db.delete(plan)
        db.commit()
    except NotFoundError:
        raise
    except SQLAlchemyError as e:
        db.rollback()
        logger.error("DB error deleting plan %s: %s", plan_id, e)
        raise InternalError(message=f"Database error: {e}")


# ── Template / Plan duality ────────────────────────────────────


def instantiate_template(
    db: Session,
    template_id: int,
    aeroplane_id: str,
    name: str | None = None,
) -> PlanRead:
    """Clone a template into a concrete plan bound to an aeroplane."""
    import copy

    template = _get_plan_or_raise(db, template_id)
    if template.plan_type != "template":
        raise ValidationError(message="Only templates can be instantiated")

    # Verify aeroplane exists
    from app.services.wing_service import get_aeroplane_or_raise

    get_aeroplane_or_raise(db, aeroplane_id)

    plan_data = PlanCreate(
        name=name or f"{template.name} \u2014 Plan",
        description=template.description,
        tree_json=copy.deepcopy(template.tree_json),
        plan_type="plan",
        aeroplane_id=aeroplane_id,
    )
    return create_plan(db, plan_data)


def to_template(
    db: Session,
    plan_id: int,
    name: str | None = None,
) -> PlanRead:
    """Create a new template from an existing plan."""
    import copy

    plan = _get_plan_or_raise(db, plan_id)

    template_data = PlanCreate(
        name=name or f"{plan.name} \u2014 Template",
        description=plan.description,
        tree_json=copy.deepcopy(plan.tree_json),
        plan_type="template",
    )
    return create_plan(db, template_data)


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
        elif not stripped and outputs:
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


def _extract_literal_values(annotation: Any) -> list[str] | None:
    """Extract allowed values from Literal type annotations.

    Handles: Literal["A", "B"], Optional[Literal[...]], Annotated[Literal[...], ...].
    Returns None if not a Literal type.
    """
    import typing

    if annotation is inspect.Parameter.empty:
        return None

    origin = getattr(annotation, "__origin__", None)

    # Direct Literal
    if origin is typing.Literal:
        return [str(v) for v in annotation.__args__]

    # Union / Optional — check each branch
    if origin is typing.Union:
        for arg in annotation.__args__:
            if arg is type(None):
                continue
            vals = _extract_literal_values(arg)
            if vals:
                return vals

    # Annotated — unwrap and recurse
    if hasattr(annotation, "__metadata__") and hasattr(annotation, "__origin__"):
        return _extract_literal_values(annotation.__origin__)

    # Nested args (e.g. Optional[Annotated[Literal[...], ...]])
    for arg in getattr(annotation, "__args__", ()):
        if arg is type(None):
            continue
        vals = _extract_literal_values(arg)
        if vals:
            return vals

    return None


def _get_shape_ref_params(cls: type) -> set[str]:
    """Detect which __init__ params are used as shapes_of_interest_keys.

    Parses the source of __init__ looking for the super().__init__ call
    with shapes_of_interest_keys=[...] and extracts referenced param names.
    """
    try:
        src = inspect.getsource(cls.__init__)
    except (TypeError, OSError):
        return set()

    # Match shapes_of_interest_keys=[...] or shapes_of_interest_keys=self.xxx
    match = re.search(r"shapes_of_interest_keys\s*=\s*(\[[^\]]*\]|self\.\w+)", src)
    if not match:
        return set()

    expr = match.group(1)
    if expr.startswith("self."):
        return {expr.replace("self.", "")}

    # Extract all identifiers from the list expression (self.foo or bare foo)
    refs = set()
    for m in re.finditer(r"(?:self\.)?(\w+)", expr):
        name = m.group(1)
        # Skip non-param identifiers
        if name not in ("self", "None", "True", "False"):
            refs.add(name)
    return refs


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
    shape_ref_params = _get_shape_ref_params(cls)
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
            options=_extract_literal_values(param.annotation),
            is_shape_ref=pname in shape_ref_params,
        ))

    docstring = (cls.__doc__ or "").strip().split("\n")[0] if cls.__doc__ else None

    outputs = _parse_docstring_returns(cls.__doc__ or "")
    suggested_id = getattr(cls, "suggested_creator_id", None)

    result.append(CreatorInfo(
        class_name=name,
        category=_get_category(cls),
        description=docstring,
        parameters=params,
        outputs=outputs,
        suggested_id=suggested_id,
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
    plan = _get_plan_or_raise(db, plan_id)
    if plan.plan_type == "template":
        raise ValidationError(
            message="Templates cannot be executed. Instantiate as a plan first.",
        )

    # Load aeroplane (prefer stored aeroplane_id, fall back to request)
    effective_aeroplane_id = plan.aeroplane_id or request.aeroplane_id
    aeroplane = get_aeroplane_or_raise(db, effective_aeroplane_id)

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

    # Tessellate shapes for 3D viewer (best-effort, non-blocking)
    tessellation = _tessellate_shapes(structure) if isinstance(structure, dict) else None

    return ExecutionResult(
        status="success",
        shape_keys=shape_keys,
        duration_ms=duration_ms,
        tessellation=tessellation,
    )


def _tessellate_shapes(structure: dict) -> dict | None:
    """Tessellate CadQuery shapes for three-cad-viewer (best-effort)."""
    try:
        from ocp_tessellate.convert import to_ocpgroup, tessellate_group, combined_bb
        import numpy as np

        # Collect CadQuery Workplane objects from the structure
        shapes = []
        names = []
        for key, val in structure.items():
            if hasattr(val, "val"):  # CadQuery Workplane
                shapes.append(val)
                names.append(key)

        if not shapes:
            return None

        # Use the first shape for tessellation via compound
        from cadquery import Workplane, Compound
        solids = []
        for s in shapes:
            try:
                solids.extend(s.val().Solids())
            except Exception:
                pass

        if not solids:
            return None

        compound = Compound.makeCompound(solids)
        wp = Workplane().newObject([compound])

        part_group, instances = to_ocpgroup(
            wp,
            names=["result"],
            colors=["#FF8400"],
            alphas=[1.0],
        )

        params = {"deviation": 0.1, "angular_tolerance": 0.2}
        instances, tess_shapes, _mapping = tessellate_group(
            part_group, instances, params, progress=None,
        )

        bb = combined_bb(tess_shapes)
        if bb is not None:
            tess_shapes["bb"] = bb.to_dict()

        def _numpy_to_list(obj):
            if isinstance(obj, np.ndarray):
                return obj.tolist()
            if isinstance(obj, dict):
                return {k: _numpy_to_list(v) for k, v in obj.items()}
            if isinstance(obj, (list, tuple)):
                return [_numpy_to_list(i) for i in obj]
            if isinstance(obj, np.integer):
                return int(obj)
            if isinstance(obj, np.floating):
                return float(obj)
            return obj

        return {
            "data": {
                "instances": _numpy_to_list(instances),
                "shapes": _numpy_to_list(tess_shapes),
            },
            "type": "data",
            "config": {"theme": "dark", "control": "orbit"},
            "count": part_group.count_shapes(),
        }
    except ImportError:
        logger.warning("ocp_tessellate not available — skipping tessellation")
        return None
    except Exception as exc:
        logger.warning("Tessellation failed (non-critical): %s", exc)
        return None


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
