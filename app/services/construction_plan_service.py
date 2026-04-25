"""Service layer for Construction Plans (gh#101)."""
from __future__ import annotations

import inspect
import json
import logging
import os
import re
import threading
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


def _flush_attribute(
    result: dict[str, str], name: str | None, desc: list[str],
) -> None:
    """Write accumulated attribute to *result* if *name* and *desc* exist."""
    if name and desc:
        result[name] = " ".join(desc).strip()


def _is_section_header(stripped: str) -> bool:
    """Detect the start of a new docstring section (e.g. ``Returns:``)."""
    return (
        bool(stripped)
        and not stripped.startswith("_")
        and stripped.endswith(":")
        and "(" not in stripped
    )


def _parse_attribute_line(stripped: str) -> tuple[str, str] | None:
    """Match ``name (type): desc`` and return *(name, desc_start)* or *None*."""
    match = re.match(r"(\w+)\s*\([^)]*\)\s*:\s*(.*)", stripped)
    if match:
        return match.group(1), match.group(2)
    return None


def _process_attribute_line(
    stripped: str,
    result: dict[str, str],
    current_name: str | None,
    current_desc: list[str],
) -> tuple[str | None, list[str], bool]:
    """Process a single line within the Attributes section.

    Returns (current_name, current_desc, should_break).
    """
    if _is_section_header(stripped):
        _flush_attribute(result, current_name, current_desc)
        return None, [], True

    parsed = _parse_attribute_line(stripped)
    if parsed:
        _flush_attribute(result, current_name, current_desc)
        name, desc_start = parsed
        return name, ([desc_start] if desc_start else []), False

    if current_name and stripped:
        current_desc.append(stripped)
        return current_name, current_desc, False

    if not stripped and current_name:
        _flush_attribute(result, current_name, current_desc)
        return None, [], False

    return current_name, current_desc, False


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

        current_name, current_desc, should_break = _process_attribute_line(
            stripped, result, current_name, current_desc
        )
        if should_break:
            break

    _flush_attribute(result, current_name, current_desc)
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
    # Handle generic aliases (e.g. list[ShapeId]) BEFORE __name__ check,
    # because list[X].__name__ == "list" (loses the subscript).
    if hasattr(annotation, "__args__"):
        raw = str(annotation).replace("typing.", "")
        raw = re.sub(r"cad_designer\.airplane\.types\.", "", raw)
        return raw
    if hasattr(annotation, "__name__"):
        return annotation.__name__
    raw = str(annotation).replace("typing.", "")
    raw = re.sub(r"cad_designer\.airplane\.types\.", "", raw)
    return raw


def _find_literal_in_args(args: tuple) -> list[str] | None:
    """Iterate over type *args*, skip NoneType, and return the first Literal values found."""
    for arg in args:
        if arg is type(None):
            continue
        vals = _extract_literal_values(arg)
        if vals:
            return vals
    return None


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
        return _find_literal_in_args(annotation.__args__)

    # Annotated — unwrap and recurse
    if hasattr(annotation, "__metadata__") and hasattr(annotation, "__origin__"):
        return _extract_literal_values(annotation.__origin__)

    # Nested args (e.g. Optional[Annotated[Literal[...], ...]])
    args = getattr(annotation, "__args__", None)
    if args:
        return _find_literal_in_args(args)

    return None


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
            options=_extract_literal_values(param.annotation),
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


# Process-wide lock guarding os.chdir during plan execution. Without this,
# concurrent execute_plan calls would write to each other's artifact dirs
# because chdir mutates global process state. Long term: pass artifact_dir
# explicitly to creators instead of relying on cwd.
_EXECUTE_CHDIR_LOCK = threading.Lock()


def execute_plan(
    db: Session,
    plan_id: int,
    request: ExecuteRequest,
) -> ExecutionResult:
    """Execute a plan against an aeroplane configuration."""
    from app.services.wing_service import get_aeroplane_or_raise, get_wing_or_raise
    from app.services.artifact_service import create_execution_dir
    from app.converters.model_schema_converters import wing_model_to_wing_config

    # Load plan
    plan = _get_plan_or_raise(db, plan_id)
    if plan.plan_type == "template":
        raise ValidationError(
            message="Templates cannot be executed. Instantiate as a plan first.",
        )

    # Load aeroplane (prefer stored aeroplane_id, fall back to request)
    effective_aeroplane_id = plan.aeroplane_id or request.aeroplane_id
    aeroplane = get_aeroplane_or_raise(db, effective_aeroplane_id)

    # Create artifact directory for this execution
    execution_id, artifact_dir = create_execution_dir(effective_aeroplane_id, plan_id)

    # Build wing_config map: all wings
    wing_config: dict = {}
    for wing in aeroplane.wings:
        try:
            wc = wing_model_to_wing_config(wing, scale=1000.0)
            wing_config[wing.name] = wc
        except Exception as exc:
            logger.warning("Failed to convert wing '%s': %s", wing.name, exc)

    # Load printer_settings from component library (if available)
    printer_settings = _load_printer_settings(db)

    # Decode tree_json with GeneralJSONDecoder
    t0 = time.monotonic()
    try:
        from cad_designer.airplane.GeneralJSONEncoderDecoder import GeneralJSONDecoder

        json_string = json.dumps(plan.tree_json)
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
        logger.exception(
            "Failed to decode plan tree_json: plan_id=%s execution_id=%s",
            plan_id, execution_id,
        )
        raise ValidationError(
            message=f"Failed to decode construction plan: {exc}",
        ) from exc

    # Execute (chdir into artifact_dir so creators using relative paths land there).
    # Guarded by a process-wide lock because os.chdir mutates global state.
    with _EXECUTE_CHDIR_LOCK:
        cwd_before = os.getcwd()
        try:
            os.chdir(artifact_dir)
            structure = root_node.create_shape()
            duration_ms = int((time.monotonic() - t0) * 1000)
        except Exception as exc:
            duration_ms = int((time.monotonic() - t0) * 1000)
            logger.exception(
                "Plan execution failed: plan_id=%s aeroplane_id=%s execution_id=%s",
                plan_id, effective_aeroplane_id, execution_id,
            )
            return ExecutionResult(
                status="error",
                error=f"{type(exc).__name__}: {exc}",
                duration_ms=duration_ms,
                artifact_dir=str(artifact_dir),
                execution_id=execution_id,
            )
        finally:
            try:
                os.chdir(cwd_before)
            except OSError:
                logger.exception("Failed to restore cwd to %s", cwd_before)

    shape_keys = list(structure.keys()) if isinstance(structure, dict) else []

    # Tessellate shapes for 3D viewer (best-effort, non-blocking)
    tessellation = _tessellate_shapes(structure) if isinstance(structure, dict) else None

    return ExecutionResult(
        status="success",
        shape_keys=shape_keys,
        duration_ms=duration_ms,
        tessellation=tessellation,
        artifact_dir=str(artifact_dir),
        execution_id=execution_id,
    )


def _numpy_to_list(obj: Any) -> Any:
    """Recursively convert numpy arrays and scalars to plain Python types."""
    try:
        import numpy as np
    except ImportError:
        return obj

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


def _collect_shapes(structure: dict) -> tuple[list, list[str]]:
    """Extract CadQuery Workplane objects and their keys from *structure*."""
    shapes = []
    names = []
    for key, val in structure.items():
        if hasattr(val, "val"):  # CadQuery Workplane
            shapes.append(val)
            names.append(key)
    return shapes, names


def _extract_solids(shapes: list) -> list:
    """Safely extract solids from each shape, skipping failures."""
    solids = []
    for s in shapes:
        try:
            solids.extend(s.val().Solids())
        except Exception:
            pass
    return solids


def _tessellate_shapes(structure: dict) -> dict | None:
    """Tessellate CadQuery shapes for three-cad-viewer (best-effort)."""
    try:
        from ocp_tessellate.convert import to_ocpgroup, tessellate_group, combined_bb

        shapes, _names = _collect_shapes(structure)
        if not shapes:
            return None

        from cadquery import Workplane, Compound

        solids = _extract_solids(shapes)
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
