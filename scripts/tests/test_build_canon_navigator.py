"""Tests for scripts/build_canon_navigator.py: the page is generated from the canon alone (#1218)."""

from __future__ import annotations

import pathlib
import re
import sys

import pytest

SCRIPTS = pathlib.Path(__file__).resolve().parents[1]
sys.path.insert(0, str(SCRIPTS))

import build_canon_navigator as nav  # noqa: E402

TEMPLATE = SCRIPTS / "canon_navigator_template.html"


@pytest.fixture(scope="module")
def built() -> tuple[str, dict]:
    return nav.build()


def test_the_template_holds_no_domain_maps() -> None:
    text = TEMPLATE.read_text(encoding="utf-8")
    for name in ("MODULES", "POINTS", "STAGES", "GROUPS", "DISC", "DESC", "XCUT", "TOOLS"):
        assert not re.search(rf"const {name}=\{{\s*'|const {name}=new Set\(\[", text), name
    assert "/probe$/" not in text


def test_the_data_carries_the_taxonomy(built: tuple[str, dict]) -> None:
    taxonomy = built[1]["tax"]
    assert [m["id"] for m in taxonomy["modules"]][:2] == ["envelope-targets", "design-targets"]
    assert {t["id"] for t in taxonomy["tools"]} >= {"OPT", "AVL", "APP"}


def test_a_probe_names_what_it_checks(built: tuple[str, dict]) -> None:
    quantities = built[1]["Q"]
    assert quantities["static-margin-probe"]["checks"] == "static-margin"
    assert quantities["static-margin"]["checks"] == ""


def test_the_real_canon_has_no_implausible_module_tag(built: tuple[str, dict]) -> None:
    assert nav.plausibility(built[1]) == []


def test_a_reference_tagged_with_a_foreign_module_is_reported(built: tuple[str, dict]) -> None:
    data = {**built[1], "Q": {k: dict(v) for k, v in built[1]["Q"].items()}}
    data["Q"]["air-density"]["module"] = "construction"
    notes = nav.plausibility(data)
    assert len(notes) == 1
    assert notes[0].startswith("air-density is tagged module/construction")
