"""The kernel configuration: numeric self-check tolerances, closed, validated, never overridable (gh-1299)."""

import copy
from collections.abc import Callable
from pathlib import Path
from typing import Any

import pytest
import yaml
from aero_kernel.build import shipped_build
from aero_kernel.canon.model import KernelConfig
from aero_kernel.config import config
from aero_kernel.importer.pipeline import import_canon
from aero_kernel.rules import rule_override_errors
from aero_kernel.schema import AircraftInput
from aero_kernel.tests.importer_builders import write_canon
from aero_kernel.validate import validate_values
from pydantic import ValidationError

CANON_CONFIG = Path(__file__).resolve().parents[2] / "_reversa_sdd/calculations/canon/config.yaml"
DOCUMENT: dict[str, Any] = yaml.safe_load(CANON_CONFIG.read_text(encoding="utf-8"))


def test_the_shipped_config_is_the_canon_file_with_every_field_described() -> None:
    shipped = config()
    assert shipped == KernelConfig.model_validate(DOCUMENT)
    for name in KernelConfig.model_fields:
        entry = getattr(shipped, name)
        assert entry.value > 0.0, name
        assert entry.unit, name
        assert entry.guards, name
        assert entry.source, name


def test_the_config_is_part_of_the_model_hash_and_so_of_the_build_digest(tmp_path: Path) -> None:
    """A changed value changes canon_model.json, which the build digest hashes into every cache key."""
    first = import_canon(write_canon(tmp_path / "a", {"config.yaml": yaml.safe_dump(DOCUMENT)}))
    changed = copy.deepcopy(DOCUMENT)
    changed["avl_cl_tolerance"]["value"] = 0.0002
    second = import_canon(write_canon(tmp_path / "b", {"config.yaml": yaml.safe_dump(changed)}))
    assert first.model is not None
    assert second.model is not None
    assert first.model.content_hash != second.model.content_hash


def _add_unknown(d: dict[str, Any]) -> None:
    d["an_unknown_tolerance"] = d["avl_cl_tolerance"]


def _drop(d: dict[str, Any]) -> None:
    del d["avl_cl_tolerance"]


def _zero_value(d: dict[str, Any]) -> None:
    d["avl_cl_tolerance"]["value"] = 0.0


def _empty_unit(d: dict[str, Any]) -> None:
    d["avl_cl_tolerance"]["unit"] = ""


def _blank_guards(d: dict[str, Any]) -> None:
    d["avl_cl_tolerance"]["guards"] = " "


@pytest.mark.parametrize(
    ("edit", "field"),
    [
        (_add_unknown, "an_unknown_tolerance"),
        (_drop, "avl_cl_tolerance"),
        (_zero_value, "avl_cl_tolerance.value"),
        (_empty_unit, "avl_cl_tolerance.unit"),
        (_blank_guards, "avl_cl_tolerance.guards"),
    ],
)
def test_a_malformed_config_is_a_finding_in_config_yaml(
    tmp_path: Path, edit: Callable[[dict[str, Any]], None], field: str
) -> None:
    document = copy.deepcopy(DOCUMENT)
    edit(document)
    result = import_canon(write_canon(tmp_path, {"config.yaml": yaml.safe_dump(document)}))
    assert result.model is None
    assert ("config.yaml", field) in [(f.file, f.field) for f in result.findings]


def test_a_canon_without_config_yaml_has_no_config(tmp_path: Path) -> None:
    result = import_canon(write_canon(tmp_path))
    assert result.model is not None
    assert result.model.namespaces["calc"].config is None


def test_the_caller_has_no_way_to_override_a_config_value() -> None:
    """No AircraftInput field, no rule parameter, no value slug reaches the config."""
    assert "config" not in AircraftInput.model_fields
    with pytest.raises(ValidationError, match="extra_forbidden"):
        AircraftInput.model_validate(
            {"airplane": {"name": "t"}, "values": {}, "config": {"avl_cl_tolerance": 1.0}}
        )
    model = shipped_build().model
    names = list(KernelConfig.model_fields)
    errors = rule_override_errors({f"config.{name}": 1.0 for name in names}, model)
    assert {e.code for e in errors} == {"unknown_rule_parameter"}
    assert len(errors) == len(names)
    plain = rule_override_errors(dict.fromkeys(names, 1.0), model)
    assert len(plain) == len(names)
    refused = validate_values(dict.fromkeys(names, 1.0), model)
    assert {e.code for e in refused} == {"unknown_quantity"}
    assert len(refused) == len(names)
