"""The published APC 13x8E table (reference/powertrain/apc_13x8e.json): its source and its numbers."""

import gzip
import json
from pathlib import Path
from typing import Any

from aero_kernel.components import PropellerTable
from aero_kernel.tests.components_builders import PROPELLER_TABLE, apc_13x8e_table

SNAPSHOT = Path(__file__).resolve().parents[2] / "data" / "cots" / "apc_props.json.gz"


def document() -> dict[str, Any]:
    return json.loads(PROPELLER_TABLE.read_text(encoding="utf-8"))


def test_the_table_names_its_source_file_url_and_version() -> None:
    doc = document()
    assert doc["source_file"] == "PER3_13x8E.dat"
    assert doc["source_url"] == "https://www.apcprop.com/files/PER3_13x8E.dat"
    assert doc["source_version"]
    assert (doc["diameter_in"], doc["pitch_in"]) == (13.0, 8.0)


def test_the_table_has_the_shape_of_the_contract_and_every_block_is_ordered() -> None:
    table = PropellerTable.model_validate(apc_13x8e_table())
    assert len(table.blocks) == 18
    assert [b.rpm for b in table.blocks] == [1000.0 * k for k in range(1, 19)]
    for block in table.blocks:
        assert len(block.j) == len(block.ct) == len(block.cp) >= 29
        assert block.j[0] == 0.0
        assert all(a < b for a, b in zip(block.j, block.j[1:], strict=False))


def test_every_point_equals_the_repository_snapshot_of_apcs_file() -> None:
    with gzip.open(SNAPSHOT, "rt", encoding="utf-8") as handle:
        snapshot = json.loads(handle.read())
    record = next(r for r in snapshot if r["name"] == "APC 13x8E")
    assert record["source_url"] == document()["source_url"]
    for block, polar in zip(apc_13x8e_table()["blocks"], record["polars"], strict=True):
        assert block["rpm"] == polar["rpm"]
        assert block["j"] == [s["J"] for s in polar["samples"]]
        assert block["ct"] == [s["Ct"] for s in polar["samples"]]
        assert block["cp"] == [s["Cp"] for s in polar["samples"]]
