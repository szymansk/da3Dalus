"""Where a supplied quantity comes from in our data: the location check of its ``data:`` sources.

A ``data`` source is ``<kind>:<location>`` (canon README "Two stages", #1251). The kind is closed
(the model types check it); this module checks, where it can, that the location exists:

``geometry``   a dotted property path in ``docs/geometry-format/airplane-geometry.schema.json``;
               maps and arrays are stepped through without a segment (``wings.x_secs.chord``);
               ``$`` is the whole document
``component``  ``<type>`` or ``<type>.<field>`` in the component-type seed of
               ``app/services/component_type_service.py``; a column every component has
               (``mass_g``) is a field of any type
``default``    a key of ``defaults.yaml``
``app``        ``<Class>.<field>`` of a pydantic model under ``app/schemas/``
``evaluation`` a name; nothing to check it against, it is read by the maintainer

The repository files are read as text (JSON, ``ast``); the importer never imports ``app``.
"""

import ast
import json
from collections.abc import Mapping
from dataclasses import dataclass
from pathlib import Path

from aero_kernel.canon.model import CanonModel
from aero_kernel.errors import DEFAULT_NAMESPACE
from aero_kernel.importer.findings import Finding
from aero_kernel.importer.yamlvalue import as_list, as_mapping

__all__ = [
    "Catalogue",
    "check_data_sources",
    "find_repo_root",
    "load_catalogue",
    "location_problem",
]

GEOMETRY_SCHEMA = Path("docs/geometry-format/airplane-geometry.schema.json")
COMPONENT_SEED = Path("app/services/component_type_service.py")
COMPONENT_MODEL = Path("app/models/component.py")
APP_SCHEMAS = Path("app/schemas")


@dataclass(frozen=True)
class Catalogue:
    """The repository facts a location is checked against; ``None`` means unavailable, unchecked.

    Attributes:
        geometry: The geometry JSON schema.
        components: Component type to its field names; ``None`` for a type whose schema the seed
            builds with a helper call, so that only the type is checkable.
        component_columns: The columns every component has, whatever its type (``mass_g``).
        app_fields: Pydantic class name to its field names.
    """

    geometry: object | None = None
    components: Mapping[str, frozenset[str] | None] | None = None
    component_columns: frozenset[str] = frozenset()
    app_fields: Mapping[str, frozenset[str]] | None = None


def find_repo_root(canon_dir: Path) -> Path | None:
    """Return the repository root above a canon directory, or ``None`` if there is none."""
    for candidate in canon_dir.resolve().parents:
        if (candidate / GEOMETRY_SCHEMA).is_file():
            return candidate
    return None


def _string(node: ast.expr | None) -> str | None:
    return node.value if isinstance(node, ast.Constant) and isinstance(node.value, str) else None


def _dict_entries(node: ast.Dict) -> dict[str, ast.expr]:
    """Return the string-keyed entries of a dict literal."""
    return {
        key.value: value
        for key, value in zip(node.keys, node.values, strict=True)
        if isinstance(key, ast.Constant) and isinstance(key.value, str)
    }


def _seed_types(tree: ast.AST) -> dict[str, frozenset[str] | None]:
    """Collect ``{"name": ..., "schema": [...]}`` dict literals: type name to field names."""
    types: dict[str, frozenset[str] | None] = {}
    for node in ast.walk(tree):
        if not isinstance(node, ast.Dict):
            continue
        entries = _dict_entries(node)
        name, schema = _string(entries.get("name")), entries.get("schema")
        if name is None or schema is None:
            continue
        if isinstance(schema, ast.List):
            fields = (
                _string(_dict_entries(item).get("name"))
                for item in schema.elts
                if isinstance(item, ast.Dict)
            )
            types[name] = frozenset(field for field in fields if field)
        else:
            types[name] = None
    return types


def _class_fields(tree: ast.AST) -> dict[str, frozenset[str]]:
    """Collect the annotated attributes of every class: class name to field names."""
    classes: dict[str, frozenset[str]] = {}
    for node in ast.walk(tree):
        if isinstance(node, ast.ClassDef):
            fields = {
                item.target.id
                for item in node.body
                if isinstance(item, ast.AnnAssign) and isinstance(item.target, ast.Name)
            }
            classes[node.name] = classes.get(node.name, frozenset()) | fields
    return classes


def _columns(tree: ast.AST, class_name: str) -> frozenset[str]:
    """Collect the ``name = Column(...)`` attributes of one class."""
    for node in ast.walk(tree):
        if isinstance(node, ast.ClassDef) and node.name == class_name:
            return frozenset(
                target.id
                for item in node.body
                if isinstance(item, ast.Assign) and isinstance(item.value, ast.Call)
                for target in item.targets
                if isinstance(target, ast.Name)
            )
    return frozenset()


def load_catalogue(repo_root: Path) -> Catalogue:
    """Read the repository facts under ``repo_root``; a file that is missing leaves its kind unchecked."""
    schema_path = repo_root / GEOMETRY_SCHEMA
    seed_path = repo_root / COMPONENT_SEED
    schemas = repo_root / APP_SCHEMAS
    geometry = (
        json.loads(schema_path.read_text(encoding="utf-8")) if schema_path.is_file() else None
    )
    components = (
        _seed_types(ast.parse(seed_path.read_text(encoding="utf-8")))
        if seed_path.is_file()
        else None
    )
    app_fields: dict[str, frozenset[str]] | None = None
    if schemas.is_dir():
        app_fields = {}
        for path in sorted(schemas.glob("*.py")):
            for name, fields in _class_fields(ast.parse(path.read_text(encoding="utf-8"))).items():
                app_fields[name] = app_fields.get(name, frozenset()) | fields
    model_path = repo_root / COMPONENT_MODEL
    columns = (
        _columns(ast.parse(model_path.read_text(encoding="utf-8")), "ComponentModel")
        if model_path.is_file()
        else frozenset[str]()
    )
    return Catalogue(
        geometry=geometry, components=components, component_columns=columns, app_fields=app_fields
    )


def _ref_target(schema: object, ref: str) -> object:
    """Return what a local ``$ref`` such as ``#/$defs/Wing`` points at."""
    target: object = schema
    for part in ref.removeprefix("#/").split("/"):
        target = (as_mapping(target) or {}).get(part)
    return target


def _step(node: dict[object, object]) -> object:
    """Return the schema one level down: the non-null ``anyOf`` branch, the array item, a map value."""
    for branch in as_list(node.get("anyOf") or node.get("oneOf")) or []:
        found = as_mapping(branch)
        if found is not None and found.get("type") != "null":
            return found
    return node.get("items") or node.get("additionalProperties")


def _resolve(schema: object, node: object) -> dict[object, object]:
    """Follow ``$ref`` and the wrappers (``anyOf``, ``items``, ``additionalProperties``) to an object schema."""
    current = as_mapping(node) or {}
    for _ in range(16):
        ref = current.get("$ref")
        if isinstance(ref, str):
            current = as_mapping(_ref_target(schema, ref)) or {}
            continue
        below = as_mapping(_step(current))
        if below is None or "properties" in current:
            return current
        current = below
    return current


def _geometry_problem(schema: object, location: str) -> str | None:
    if location == "$":
        return None
    node: object = schema
    walked: list[str] = []
    for segment in location.split("."):
        properties = as_mapping(_resolve(schema, node).get("properties"))
        if properties is None or segment not in properties:
            where = ".".join(walked) or "the document"
            return f"{where} has no property {segment!r} in {GEOMETRY_SCHEMA}"
        walked.append(segment)
        node = properties[segment]
    return None


def _component_problem(
    components: Mapping[str, frozenset[str] | None], columns: frozenset[str], location: str
) -> str | None:
    type_name, _, field = location.partition(".")
    if type_name not in components:
        return f"no component type {type_name!r} in {COMPONENT_SEED}"
    fields = components[type_name]
    if field and fields is not None and field not in fields and field not in columns:
        return f"component type {type_name!r} has no field {field!r} in {COMPONENT_SEED}"
    return None


def _app_problem(app_fields: Mapping[str, frozenset[str]], location: str) -> str | None:
    class_name, _, field = location.partition(".")
    if class_name not in app_fields:
        return f"no class {class_name!r} under {APP_SCHEMAS}"
    if not field or field not in app_fields[class_name]:
        return f"class {class_name!r} has no field {field!r} under {APP_SCHEMAS} (write <Class>.<field>)"
    return None


def location_problem(source: str, catalogue: Catalogue, defaults: frozenset[str]) -> str | None:
    """Return why the location of ``source`` does not exist, or ``None`` if it does or cannot be checked."""
    kind, _, location = source.partition(":")
    if kind == "default":
        return None if location in defaults else f"{location!r} is not a key of defaults.yaml"
    if kind == "geometry" and catalogue.geometry is not None:
        return _geometry_problem(catalogue.geometry, location)
    if kind == "component" and catalogue.components is not None:
        return _component_problem(catalogue.components, catalogue.component_columns, location)
    if kind == "app" and catalogue.app_fields is not None:
        return _app_problem(catalogue.app_fields, location)
    return None


def check_data_sources(model: CanonModel, catalogue: Catalogue) -> list[Finding]:
    """Check that every ``data`` source of the model names a location that exists.

    Args:
        model: The canon model, valid as a whole.
        catalogue: The repository facts to check against.

    Returns:
        One finding per source whose location does not exist; empty if all resolve.
    """
    content = model.namespaces[DEFAULT_NAMESPACE]
    defaults = frozenset(content.defaults)
    findings: list[Finding] = []
    for slug, quantity in sorted(content.quantities.items()):
        for source in quantity.data or []:
            message = location_problem(source, catalogue, defaults)
            if message is not None:
                findings.append(
                    Finding(
                        file=f"quantities/{slug}.md", field="data", message=f"{source}: {message}"
                    )
                )
    return findings
