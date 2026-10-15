"""The geometry model against docs/geometry-format/airplane-geometry.schema.json.

The two must not drift: same fields (by format key), same required set, same enums, same defaults
(except the millimetre fields, whose defaults are metres in the model), and real documents parse.
"""

import copy
import json
import math
from pathlib import Path
from typing import Any, Literal, cast, get_args, get_origin

import pytest
from aero_kernel import geometry
from aero_kernel.geometry import AirplaneGeometry
from pydantic import BaseModel, ValidationError
from pydantic.fields import FieldInfo

REPO_ROOT = Path(__file__).resolve().parents[2]
SCHEMA_PATH = REPO_ROOT / "docs" / "geometry-format" / "airplane-geometry.schema.json"

# Schema definition -> model class. Point3 and Factor are scalars/tuples, not objects.
MODELS: dict[str, type[BaseModel]] = {
    "Wing": geometry.Wing,
    "WingUnits": geometry.WingUnits,
    "WingXSec": geometry.WingXSec,
    "ControlSurface": geometry.ControlSurface,
    "SpareDetail": geometry.SpareDetail,
    "TrailingEdgeDevice": geometry.TrailingEdgeDevice,
    "Servo": geometry.Servo,
    "Turbulator": geometry.Turbulator,
    "Fuselage": geometry.Fuselage,
    "FuselageXSecSuperEllipse": geometry.FuselageXSecSuperEllipse,
}

# Millimetre fields: the model default is the schema default in metres.
MILLIMETRE_KEYS = {"height_mm"}


def load_schema() -> dict[str, Any]:
    """Read the JSON Schema of the geometry format."""
    return json.loads(SCHEMA_PATH.read_text())


def format_key(name: str, field: FieldInfo) -> str:
    """Return the key the format uses for a model field: its validation alias, else its name."""
    alias = field.validation_alias
    if alias is None:
        return name
    assert isinstance(alias, str)
    return alias


def object_schemas() -> dict[str, dict[str, Any]]:
    """Return the root and every object definition of the schema, by definition name."""
    schema = load_schema()
    objects = {name: d for name, d in schema["$defs"].items() if "properties" in d}
    return {"Airplane": schema} | objects


def model_for(name: str) -> type[BaseModel]:
    """Return the model class for a schema definition name."""
    return AirplaneGeometry if name == "Airplane" else MODELS[name]


def literal_values(annotation: object) -> set[Any]:
    """Return all Literal values in an annotation, looking through ``| None`` unions."""
    if get_origin(annotation) is Literal:
        return set(get_args(annotation))
    values: set[Any] = set()
    for arg in get_args(annotation):
        values |= literal_values(arg)
    return values


def assert_close(actual: float, expected: float) -> None:
    """Assert equality up to the rounding of a mm -> m multiplication."""
    assert math.isclose(actual, expected, rel_tol=1e-12), (actual, expected)


def test_published_json_schema_shows_the_format_default_under_the_format_key() -> None:
    """The model's JSON Schema speaks the format: height_mm defaults to 0.3 (mm), not 0.0003."""
    published = geometry.Turbulator.model_json_schema(mode="validation")
    assert published["properties"]["height_mm"]["default"] == 0.3


# Where the model deliberately accepts more than the schema: the inline airfoil (ch. 8.11).
EXTRA_BRANCHES: dict[tuple[str, str], frozenset[Any]] = {
    ("WingXSec", "airfoil"): frozenset({("ref", "InlineAirfoil")}),
}

Signature = frozenset[Any]


def type_signature(node: dict[str, Any], defs: dict[str, Any]) -> Signature:
    """Reduce a JSON Schema node to the set of type branches it admits.

    Branches: ``"null"``, ``"number"``, ``"integer"``, ``"string"``, ``"boolean"``,
    ``("enum", values)``, ``("ref", name)`` for an object definition, ``"point3"``,
    ``("array", item signature)`` and ``("object", value signature)``. Numeric bounds, array
    lengths other than for a point, and descriptions are left out on purpose: the model carries
    no physical constraint (ch. 8.11), so only the type structure is compared.
    """
    if "$ref" in node:
        name = node["$ref"].rsplit("/", 1)[-1]
        target = defs[name]
        if "properties" in target:
            return frozenset({("ref", name)})
        return type_signature(target, defs)
    if "anyOf" in node:
        return frozenset().union(*(type_signature(b, defs) for b in node["anyOf"]))
    if "const" in node:
        return frozenset({("enum", frozenset({node["const"]}))})
    if "enum" in node:
        values = set(node["enum"])
        branches: set[Any] = {("enum", frozenset(values - {None}))}
        if None in values:
            branches.add("null")
        return frozenset(branches)
    kinds = node["type"] if isinstance(node["type"], list) else [node["type"]]
    return frozenset().union(*(kind_signature(kind, node, defs) for kind in kinds))


def kind_signature(kind: str, node: dict[str, Any], defs: dict[str, Any]) -> Signature:
    """Reduce one JSON ``type`` of a node (with its array and object details) to branches."""
    if kind == "array":
        if node.get("minItems") == node.get("maxItems") == 3:
            return frozenset({"point3"})
        return frozenset({("array", type_signature(node["items"], defs))})
    if kind == "object":
        values = node.get("additionalProperties")
        return frozenset({("object", type_signature(values, defs) if values else frozenset())})
    return frozenset({kind})


def test_field_types_match_the_schema() -> None:
    """Per field: same type branches, nullability and refs as the JSON Schema."""
    model_doc = AirplaneGeometry.model_json_schema(mode="validation")
    schema_doc = load_schema()
    pairs = [("Airplane", model_doc, schema_doc)] + [
        (name, model_doc["$defs"][name], definition)
        for name, definition in object_schemas().items()
        if name != "Airplane"
    ]
    for name, model_def, schema_def in pairs:
        for key, prop in schema_def["properties"].items():
            expected = type_signature(prop, schema_doc.get("$defs", {}))
            actual = type_signature(model_def["properties"][key], model_doc["$defs"])
            extra = EXTRA_BRANCHES.get((name, key), frozenset())
            assert actual - extra == expected, (name, key, actual, expected)
            assert extra <= actual, (name, key)


def test_every_object_definition_has_a_model() -> None:
    names = set(object_schemas()) - {"Airplane"}
    assert names == set(MODELS)


@pytest.mark.parametrize("name", sorted(object_schemas()))
def test_fields_required_set_and_additional_properties_match(name: str) -> None:
    definition = object_schemas()[name]
    model = model_for(name)
    keys = {format_key(n, f) for n, f in model.model_fields.items()}
    required = {format_key(n, f) for n, f in model.model_fields.items() if f.is_required()}
    assert keys == set(definition["properties"])
    assert required == set(definition.get("required", []))
    assert definition["additionalProperties"] is False
    assert model.model_config.get("extra") == "forbid"


@pytest.mark.parametrize("name", sorted(object_schemas()))
def test_enums_and_defaults_match(name: str) -> None:
    definition = object_schemas()[name]
    model = model_for(name)
    for field_name, field in model.model_fields.items():
        key = format_key(field_name, field)
        prop = definition["properties"][key]
        enum = prop.get("enum")
        if enum is not None:
            assert literal_values(field.annotation) == set(enum) - {None}, key
        if "const" in prop:
            assert literal_values(field.annotation) == {prop["const"]}, key
        if "default" in prop and key in MILLIMETRE_KEYS:
            assert_close(field.default, prop["default"] * 1e-3)
        elif "default" in prop:
            assert field.default == prop["default"] or tuple(prop["default"]) == field.default, key


FLEET_ROOT = REPO_ROOT / "scripts" / "canon_checks" / "reference_fleet"
FLEET_FILES = sorted(FLEET_ROOT.rglob("*.airplane.json"))
# These documents already satisfy the JSON Schema and are parsed as they are.
VALID_AS_WRITTEN = ["bryan/bryan.airplane.json", "snack/snack.airplane.json"]


def read_document(path: Path) -> dict[str, Any]:
    """Read a fleet document as written."""
    return json.loads(path.read_text())


def repair_for_schema(document: dict[str, Any]) -> dict[str, Any]:
    """Apply the two lossless repairs to a generated fleet document, and nothing else.

    1. Drop the pure-metadata top-level keys ``urmodell`` and ``herkunft``; they carry no geometry.
    2. Fill a missing wing or fuselage ``name`` from its dict key; the key is the name.

    ``control_surfaces`` is deliberately not repaired: it is the AeroSandbox list of mixing
    surfaces, the format's ``trailing_edge_device`` (with its role) is absent, and building one
    would mean guessing the roles.
    """
    repaired = {
        k: v for k, v in copy.deepcopy(document).items() if k not in {"urmodell", "herkunft"}
    }
    for group in ("wings", "fuselages"):
        bodies: dict[str, dict[str, Any]] = repaired.get(group) or {}
        for key, body in bodies.items():
            body.setdefault("name", key)
    return repaired


def has_control_surfaces(document: dict[str, Any]) -> bool:
    """Whether any rib of a fleet document carries the non-format ``control_surfaces`` list."""
    wings: dict[str, dict[str, Any]] = document.get("wings") or {}
    return any("control_surfaces" in rib for wing in wings.values() for rib in wing["x_secs"])


def repaired_fleet(*, conformant: bool) -> list[Path]:
    """Fleet files that are format-conformant after the two repairs, or those that are not."""
    return [
        path for path in FLEET_FILES if has_control_surfaces(read_document(path)) is not conformant
    ]


@pytest.mark.parametrize("relative", VALID_AS_WRITTEN)
def test_schema_valid_documents_parse_as_written(relative: str) -> None:
    airplane = AirplaneGeometry.model_validate(read_document(FLEET_ROOT / relative))
    assert airplane.wings


@pytest.mark.parametrize("path", FLEET_FILES, ids=lambda p: p.name)
def test_fleet_file_parses_or_is_rejected_only_for_control_surfaces(path: Path) -> None:
    """Invariant, not a count: a fleet file is conformant after the two repairs, or it fails
    on ``control_surfaces`` and on nothing else."""
    document = repair_for_schema(read_document(path))
    if not has_control_surfaces(document):
        AirplaneGeometry.model_validate(document)
        return
    with pytest.raises(ValidationError) as caught:
        AirplaneGeometry.model_validate(document)
    assert {tuple(e["loc"])[-1] for e in caught.value.errors()} == {"control_surfaces"}


@pytest.mark.parametrize("path", repaired_fleet(conformant=True), ids=lambda p: p.name)
def test_fleet_documents_parse_after_the_two_repairs(path: Path) -> None:
    airplane = AirplaneGeometry.model_validate(repair_for_schema(read_document(path)))
    assert airplane.wings or airplane.fuselages


def test_repair_does_not_mutate_its_input() -> None:
    path = repaired_fleet(conformant=False)[0]
    document = read_document(path)
    before = copy.deepcopy(document)
    repair_for_schema(document)
    assert document == before


def test_repair_leaves_control_surfaces_in_place() -> None:
    """Dropping them would silently turn a layout with elevons into one without devices."""
    path = repaired_fleet(conformant=False)[0]
    original = read_document(path)
    repaired = repair_for_schema(read_document(path))
    assert has_control_surfaces(repaired)
    for key, wing in original["wings"].items():
        assert repaired["wings"][key]["x_secs"] == wing["x_secs"]


def test_urmodell_documents_are_still_rejected_for_control_surfaces() -> None:
    """Deliberate tripwire: the fleet's ribs carry ASB control_surfaces, not devices (#1184).

    Flip to a positive test when #1184 regenerates the fleet.
    """
    path = repaired_fleet(conformant=False)[0]
    with pytest.raises(ValueError, match="control_surfaces"):
        AirplaneGeometry.model_validate(repair_for_schema(read_document(path)))


def test_a_schema_violation_in_a_fleet_document_is_still_rejected() -> None:
    document = read_document(FLEET_ROOT / "bryan" / "bryan.airplane.json")
    document["urmodell"] = {}
    with pytest.raises(ValueError, match="urmodell"):
        AirplaneGeometry.model_validate(document)


def full_document() -> dict[str, Any]:
    """A document that sets every field the schema defines, including CAD-only ones."""
    servo = dict.fromkeys(
        (
            "length", "width", "height", "leading_length", "latch_z", "latch_x",
            "latch_thickness", "latch_length", "cable_z", "screw_hole_lx", "screw_hole_d",
        ),
        1.0,
    ) | {"component_id": 4}  # fmt: skip
    device = {
        "name": "Aileron", "role": "aileron", "label": "left", "rel_chord_root": 0.7,
        "rel_chord_tip": 0.7, "hinge_spacing": 0.5, "side_spacing_root": 1.0,
        "side_spacing_tip": 1.0, "servo": servo, "servo_placement": "bottom",
        "rel_chord_servo_position": 0.5, "rel_length_servo_position": 0.5,
        "positive_deflection_deg": 25, "negative_deflection_deg": -25, "deflection_deg": 0,
        "trailing_edge_offset_factor": 1.2, "hinge_type": "middle", "symmetric": False,
        "mix_gain_primary": 1.0, "mix_gain_secondary": 1.0, "differential_ratio": 1.0,
    }  # fmt: skip
    spar = {
        "spare_support_dimension_width": 0.006, "spare_support_dimension_height": 0.004,
        "spare_position_factor": 0.25, "spare_length": 0.4, "spare_start": 0.0,
        "spare_mode": "normal", "spare_vector": [0, 1, 0], "spare_origin": [0, 0, 0],
    }  # fmt: skip
    rib = {
        "xyz_le": [0, 0, 0], "chord": 0.2, "twist": 1, "dihedral": 0, "airfoil": "naca0012",
        "control_surface": {"name": "Aileron", "hinge_point": 0.8, "symmetric": False, "deflection": 0},
        "x_sec_type": "root", "tip_type": "flat", "number_interpolation_points": 3,
        "spare_list": [spar], "trailing_edge_device": device,
        "turbulator": {"form": "thread", "height_mm": 0.3, "position_root": 0.3, "position_tip": 0.3, "enabled": True},
    }  # fmt: skip
    tip = {"xyz_le": [0, 1, 0], "chord": 0.1, "twist": 0, "airfoil": "naca0012"}
    wing = {
        "name": "W", "symmetric": True, "design_model": "wc", "x_secs": [rib, tip],
        "units": {"geometry_length": "m", "detail_length": "m", "angle": "deg"},
    }  # fmt: skip
    station = {"xyz": [0, 0, 0], "a": 0.1, "b": 0.1, "n": 2, "n_lower": 4}
    fuselage = {
        "name": "F", "x_secs": [station, station], "symmetric": False,
        "step_path": "a.step", "solid_step_path": "b.step",
    }  # fmt: skip
    return {
        "name": "Full", "total_mass_kg": 3.0, "xyz_ref": [0.1, 0, 0],
        "wings": {"W": wing}, "fuselages": {"F": fuselage},
    }  # fmt: skip


def collect_keys(node: object, keys: set[str]) -> None:
    """Add every dict key anywhere in a JSON document to ``keys``."""
    if isinstance(node, dict):
        # raw JSON: isinstance narrows to dict[Unknown, Unknown]; the keys are strings
        mapping = cast("dict[str, object]", node)
        for key, value in mapping.items():
            keys.add(key)
            collect_keys(value, keys)
    elif isinstance(node, list):
        for item in cast("list[object]", node):  # raw JSON, see above
            collect_keys(item, keys)


def test_a_document_setting_every_schema_field_is_accepted() -> None:
    document = full_document()
    used: set[str] = set()
    collect_keys(document, used)
    schema_keys: set[str] = set()
    for definition in object_schemas().values():
        schema_keys |= set(definition["properties"])
    assert schema_keys - used == set()
    airplane = AirplaneGeometry.model_validate(document)
    assert airplane.wings is not None
    assert airplane.wings["W"].x_secs[0].trailing_edge_device is not None
