from __future__ import annotations

import json
import math
from pathlib import Path

import pytest


def _assert_non_empty_solid(shape) -> None:
    solid = shape.findSolid()
    assert solid is not None

    bbox = solid.BoundingBox()
    assert bbox.xlen > 0
    assert bbox.ylen > 0
    assert bbox.zlen > 0


def test_ehawk_wing_workflow_end_to_end(tmp_path):
    pytest.importorskip("cadquery")
    pytest.importorskip("aerosandbox")

    from cad_designer.airplane import GeneralJSONDecoder, GeneralJSONEncoder
    from test.ehawk_workflow_helpers import build_ehawk_workflow

    repo_root = Path(__file__).resolve().parents[1]
    export_dir = tmp_path / "exports"
    export_dir.mkdir(parents=True, exist_ok=True)

    workflow = build_ehawk_workflow(repo_root=repo_root, export_dir=export_dir)

    json_data = json.dumps(workflow.root_node, indent=2, cls=GeneralJSONEncoder)

    constructions_dir = tmp_path / "constructions"
    constructions_dir.mkdir(parents=True, exist_ok=True)
    construction_json_path = constructions_dir / f"{workflow.root_node.identifier}.json"
    construction_json_path.write_text(json_data, encoding="utf-8")

    decoded_tree = json.loads(
        json_data,
        cls=GeneralJSONDecoder,
        servo_information=workflow.servo_information,
        wing_config={"main_wing": workflow.main_wing},
        printer_settings=workflow.printer_settings,
    )

    structure = decoded_tree.create_shape()

    expected_keys = {
        "vase_wing",
        "vase_wing[0]",
        "vase_wing[2].servo_mount",
        "vase_wing[0].print",
        "vase_wing[1].print",
        "winglet",
        "winglet.print",
        "vase_wing.aileron[2]",
        "vase_wing.aileron[3]",
        "vase_wing.aileron[2]*",
        "vase_wing.aileron[3]*",
    }
    missing_keys = sorted(expected_keys - set(structure))
    assert not missing_keys, f"Missing expected workflow keys: {missing_keys}"

    for shape_key in [
        "vase_wing",
        "vase_wing[0]",
        "winglet",
        "vase_wing[0].print",
        "winglet.print",
        "vase_wing.aileron[2]",
        "vase_wing[2].servo_mount",
    ]:
        _assert_non_empty_solid(structure[shape_key])

    export_basename = Path(f"{workflow.root_node.identifier}").stem
    step_bundle_path = export_dir / f"{export_basename}.stp"
    assert step_bundle_path.exists(), f"Missing STEP bundle: {step_bundle_path}"
    assert step_bundle_path.stat().st_size > 0

    step_parts = list(export_dir.glob(f"{export_basename}_*.step"))
    assert len(step_parts) >= 8

    asb_wing = workflow.airplane_configuration.wings[0].asb_wing(scale=1e-3)
    mac = asb_wing.mean_aerodynamic_chord()
    assert math.isfinite(mac)
    assert mac > 0

    airplane = workflow.airplane_configuration.asb_airplane
    neutral_point = airplane.aerodynamic_center(chord_fraction=0.25)
    assert len(neutral_point) == 3
    assert all(math.isfinite(component) for component in neutral_point)

    airplane.xyz_ref = tuple(neutral_point)
    avl_path = export_dir / "eHawk.AVL"
    airplane.export_AVL(filename=str(avl_path), include_fuselages=False)
    assert avl_path.exists(), f"Missing AVL export: {avl_path}"
    assert avl_path.stat().st_size > 0

    # Keep a contract check that serialization remains stable for the root creator id.
    assert "eHawk-wing.root" in construction_json_path.read_text(encoding="utf-8")
