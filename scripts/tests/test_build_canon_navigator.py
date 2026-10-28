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
    assert quantities["static-margin-probe"]["checks"] == "static-margin-target"
    assert quantities["static-margin-measured"]["checks"] == ""


def test_the_real_canon_has_no_implausible_module_tag(built: tuple[str, dict]) -> None:
    assert nav.plausibility(built[1]) == []


def test_a_reference_tagged_with_a_foreign_module_is_reported(built: tuple[str, dict]) -> None:
    data = {**built[1], "Q": {k: dict(v) for k, v in built[1]["Q"].items()}}
    data["Q"]["air-density"]["module"] = "construction"
    notes = nav.plausibility(data)
    assert len(notes) == 1
    assert notes[0].startswith("air-density is tagged module/construction")


@pytest.fixture
def pages(
    tmp_path: pathlib.Path, monkeypatch: pytest.MonkeyPatch
) -> tuple[pathlib.Path, pathlib.Path]:
    """The generator pointed at two scratch outputs, with a tiny page instead of the real build."""
    published = tmp_path / "canon" / "navigator.html"
    served = tmp_path / "frontend" / "public" / "canon-navigator.html"
    published.parent.mkdir(parents=True)
    served.parent.mkdir(parents=True)
    monkeypatch.setattr(nav, "OUT_PATH", published)
    monkeypatch.setattr(nav, "FRONTEND_PATH", served)
    monkeypatch.setattr(
        nav,
        "build",
        lambda: (
            "<title>page</title>",
            {"Q": {}, "F": {}, "edges": [], "order": {}, "inputs": [], "outputs": [], "mvp": []},
        ),
    )
    monkeypatch.setattr(nav, "plausibility", lambda data: [])
    return published, served


def test_the_page_is_written_to_the_artifact_and_to_the_frontend(
    pages: tuple[pathlib.Path, pathlib.Path],
) -> None:
    published, served = pages
    nav.main([])
    assert published.read_text(encoding="ascii") == "<title>page</title>"
    assert served.read_text(encoding="ascii") == "<title>page</title>"


def test_check_passes_when_both_copies_are_current(
    pages: tuple[pathlib.Path, pathlib.Path], capsys: pytest.CaptureFixture[str]
) -> None:
    nav.main([])
    nav.main(["--check"])
    assert "navigator is current" in capsys.readouterr().out


def test_check_fails_when_the_frontend_copy_is_stale(
    pages: tuple[pathlib.Path, pathlib.Path],
) -> None:
    _, served = pages
    nav.main([])
    served.write_text("old", encoding="ascii")
    with pytest.raises(SystemExit) as stale:
        nav.main(["--check"])
    assert "canon-navigator.html" in str(stale.value)


def test_check_fails_when_the_frontend_copy_is_missing(
    pages: tuple[pathlib.Path, pathlib.Path],
) -> None:
    _, served = pages
    nav.main([])
    served.unlink()
    with pytest.raises(SystemExit) as stale:
        nav.main(["--check"])
    assert "canon-navigator.html" in str(stale.value)


def test_check_fails_when_the_artifact_is_stale(pages: tuple[pathlib.Path, pathlib.Path]) -> None:
    published, _ = pages
    nav.main([])
    published.write_text("old", encoding="ascii")
    with pytest.raises(SystemExit) as stale:
        nav.main(["--check"])
    assert "navigator.html" in str(stale.value)
