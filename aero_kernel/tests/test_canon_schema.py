"""The committed JSON Schema of the canon model cannot drift from the types."""

import json
import runpy
import sys
from pathlib import Path
from typing import Any

import jsonschema
import pytest
from aero_kernel.canon.model import CanonModel
from aero_kernel.canon.schema_file import SCHEMA_PATH, schema_text, write_schema
from aero_kernel.tests.canon_builders import base_model
from pydantic import ValidationError


def test_committed_schema_equals_the_generated_one() -> None:
    assert SCHEMA_PATH.read_text(encoding="utf-8") == schema_text(), (
        "canon_model.schema.json is stale: run `python -m aero_kernel.canon.schema_file`"
    )


def test_schema_text_is_sorted_and_ends_with_newline() -> None:
    text = schema_text()
    assert text.endswith("}\n")
    assert json.loads(text) == json.loads(json.dumps(json.loads(text), sort_keys=True))


def test_write_schema_writes_the_text(tmp_path: Path) -> None:
    target = tmp_path / "schema.json"
    write_schema(target)
    assert target.read_text(encoding="utf-8") == schema_text()


def test_module_entry_point_writes_to_the_given_path(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    target = tmp_path / "out.json"
    monkeypatch.setattr(sys, "argv", ["schema_file", str(target)])
    # runpy warns when the module is already imported; run it afresh.
    monkeypatch.delitem(sys.modules, "aero_kernel.canon.schema_file")
    runpy.run_module("aero_kernel.canon.schema_file", run_name="__main__")
    assert target.read_text(encoding="utf-8") == schema_text()


def load_schema() -> dict[str, Any]:
    """Read the committed schema."""
    return json.loads(SCHEMA_PATH.read_text(encoding="utf-8"))


def test_schema_accepts_what_the_types_accept() -> None:
    jsonschema.validate(base_model(), load_schema())


FORMULA = ("namespaces", "calc", "formulas", "weight-from-mass")
QUANTITY = ("namespaces", "calc", "quantities", "weight")


@pytest.mark.parametrize(
    ("path", "key", "value"),
    [
        ((), "extra", 1),
        ((), "schema_version", 2),
        ((), "schema_version", True),
        ((), "source_commit", "abc"),
        (QUANTITY, "unit", "furlong"),
        (FORMULA, "tool", "X"),
    ],
)
def test_schema_and_types_reject_the_same_documents(
    path: tuple[str, ...], key: str, value: object
) -> None:
    raw = base_model()
    node = raw
    for step in path:
        node = node[step]
    node[key] = value
    with pytest.raises(ValidationError):
        CanonModel.model_validate(raw)
    with pytest.raises(jsonschema.ValidationError):
        jsonschema.validate(raw, load_schema())


def test_schema_and_types_agree_on_world_names() -> None:
    raw = base_model()
    formula = raw["namespaces"]["calc"]["formulas"]["weight-from-mass"]
    formula.update(uncertainty="interval", worlds=["avl", "Bad World"])
    with pytest.raises(ValidationError):
        CanonModel.model_validate(raw)
    with pytest.raises(jsonschema.ValidationError):
        jsonschema.validate(raw, load_schema())
