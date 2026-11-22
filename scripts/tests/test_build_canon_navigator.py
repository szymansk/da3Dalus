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
    assert quantities["minimum-drag-speed-probe"]["checks"] == "minimum-drag-speed"
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


# --- entry_issues, to_tex, application_edges, closure, kernel_status, to_ascii (gh-1457) -------


def entry(front: str, body: str = "x") -> str:
    """A canon entry text: front matter between two separators, then a body."""
    return f"---\n{front}\n---\n\n{body}\n"


def kinds(issues: list) -> list[str]:
    return [issue["kind"] for issue in issues]


def test_a_draft_entry_without_a_source_declares_the_open_source_issue() -> None:
    text = entry("source_status: NO_SOURCE_FOUND\nstatus: draft", "**Source.** none found.")
    assert nav.entry_issues(text) == [
        {"kind": "source", "title": "No published source found.", "text": "none found."}
    ]


def test_an_approved_entry_without_a_source_declares_no_issue() -> None:
    # Canon README: a missing source adopted on the maintainer's authority is legitimate.
    text = entry("source_status: NO_SOURCE_FOUND\nstatus: approved", "**Source.** none found.")
    assert nav.entry_issues(text) == []


def test_a_partly_sourced_draft_says_so_and_stops_the_source_text_at_the_next_paragraph() -> None:
    text = entry("source_status: PARTIAL\nstatus: draft", "**Source.** half.\n\n**Next.** more")
    assert nav.entry_issues(text) == [
        {"kind": "source", "title": "Only partly sourced.", "text": "half."}
    ]


def test_an_approximation_is_an_issue_only_while_it_is_a_draft() -> None:
    assert kinds(nav.entry_issues(entry("shape: approximation\nstatus: draft"))) == [
        "approximation"
    ]
    assert nav.entry_issues(entry("shape: approximation\nstatus: approved")) == []


def test_an_unparseable_dimensional_check_is_an_issue() -> None:
    assert kinds(nav.entry_issues(entry("dimensional_check: UNPARSEABLE"))) == ["dimensions"]
    assert nav.entry_issues(entry("dimensional_check: OK")) == []


def test_a_conflict_flag_carries_the_text_of_its_conflict_section() -> None:
    body = "## \u26a0\ufe0f Conflict\nA says 1.\nB says 2.\n\n## Next\nunrelated"
    assert nav.entry_issues(entry("tags:\n  - flag/conflict", body)) == [
        {
            "kind": "conflict",
            "title": "Two producers disagree (flag/conflict).",
            "text": "A says 1. B says 2.",
        }
    ]


def test_a_red_callout_is_a_broken_assumption_with_its_quoted_lines() -> None:
    body = "> \U0001f534 **Wrong claim**\n> first line\n> second line\n\nafter"
    assert nav.entry_issues(entry("status: draft", body)) == [
        {"kind": "broken", "title": "Wrong claim", "text": "first line second line"}
    ]


def test_an_entry_with_no_marker_declares_no_issue() -> None:
    assert nav.entry_issues(entry("status: draft")) == []


def test_to_tex_typesets_subscripts_roots_and_products() -> None:
    # Derived from the rules: S -> S_{S}; sqrt( -> \sqrt{...} around the balanced argument;
    # '*' -> thin space; 'max' after the comma subscript -> '\max ' (the code keeps the trailing
    # blank of the \max command).
    assert nav.to_tex("V_S = sqrt(2*W/(rho*S_ref*C_L,max))") == (
        r"V_{S} = \sqrt{2\,W/(\rho\,S_{ref}\,C_{L,\max })}"
    )


def test_to_tex_gives_nothing_for_a_procedure_or_an_empty_form() -> None:
    assert nav.to_tex("argmax over x") is None
    assert nav.to_tex("") is None


def application_model(bind: dict, produce: dict) -> dict:
    """A canon-model stub with one formula ``f`` of one application."""
    application = {"id": "default", "bind": bind, "produce": produce, "given": None}
    return {"namespaces": {"calc": {"formulas": {"f": {"applications": [application]}}}}}


def test_application_edges_run_from_each_input_to_each_output() -> None:
    model = application_model({"a": "calc:q-a"}, {"y": "calc:q-y"})
    formulas = {"f": {"out": []}}
    edges = nav.application_edges(formulas, {"q-a": {}, "q-y": {}}, model)
    assert edges == [("q-a", "q-y", "f")]
    assert formulas["f"]["ins"] == ["q-a"]
    assert formulas["f"]["out"] == ["q-y"]


def test_a_formula_that_lists_its_own_output_as_input_stops_the_build() -> None:
    model = application_model({"a": "calc:q-y"}, {"y": "calc:q-y"})
    with pytest.raises(SystemExit, match="self-edge: f lists its own output 'q-y'"):
        nav.application_edges({"f": {"out": []}}, {"q-y": {}}, model)


def test_a_model_that_lacks_a_documented_formula_stops_the_build() -> None:
    model = application_model({}, {})
    with pytest.raises(SystemExit, match="re-run the importer first"):
        nav.application_edges({"f": {"out": []}, "g": {"out": []}}, {}, model)


def test_closure_collects_everything_upstream_through_a_diamond() -> None:
    pred = {"a": set(), "b": {"a"}, "c": {"a"}, "d": {"b", "c"}, "e": set()}
    assert nav.closure({"d"}, pred) == {"a", "b", "c", "d"}
    assert nav.closure({"a"}, pred) == {"a"}


def test_closure_terminates_on_a_cycle() -> None:
    assert nav.closure({"a"}, {"a": {"b"}, "b": {"a"}}) == {"a", "b"}


def kernel_data() -> dict:
    """q-in -> f-mid -> q-mid -> f-done -> q-scalar, q-curve; q-in -> f-open -> q-open."""
    return {
        "Q": {
            "q-in": {"type": "scalar"},
            "q-mid": {"type": "scalar"},
            "q-scalar": {"type": "scalar"},
            "q-curve": {"type": "curve"},
            "q-open": {"type": "scalar"},
        },
        "F": {
            "f-mid": {"out": ["q-mid"], "direction": "analysis"},
            "f-done": {"out": ["q-scalar", "q-curve"], "direction": "analysis"},
            "f-open": {"out": ["q-open"], "direction": "analysis"},
        },
        "edges": [
            ("q-in", "q-mid", "f-mid"),
            ("q-mid", "q-scalar", "f-done"),
            ("q-mid", "q-curve", "f-done"),
            ("q-in", "q-open", "f-open"),
        ],
        "inputs": ["q-in"],
    }


def kernel_dir(tmp_path: pathlib.Path, source: str) -> pathlib.Path:
    folder = tmp_path / "formulas"
    folder.mkdir()
    (folder / "f_done.py").write_text(source, encoding="utf-8")
    return folder


def test_kernel_status_marks_done_nonscalar_open_and_input(
    tmp_path: pathlib.Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    monkeypatch.setattr(nav, "MVP_RESULTS", ("q-scalar",))
    monkeypatch.setattr(nav, "OPEN_TICKETS", {"f-open": "#7"})
    data = kernel_data()
    nav.kernel_status(data, kernel_dir(tmp_path, '@formula("f-done")\ndef f() -> None: ...\n'))
    assert data["status"] == {
        "q-in": "input",
        "q-mid": "open",
        "q-scalar": "done",
        "q-curve": "nonscalar",
        "q-open": "open",
    }
    assert data["F"]["f-done"]["impl"] == "aero_kernel/formulas/f_done.py"
    assert data["F"]["f-mid"]["impl"] == ""
    assert data["F"]["f-open"]["ticket"] == "#7"
    assert data["F"]["f-done"]["ticket"] == ""


def test_the_mvp_is_the_upstream_closure_of_its_results(
    tmp_path: pathlib.Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    monkeypatch.setattr(nav, "MVP_RESULTS", ("q-scalar",))
    data = kernel_data()
    nav.kernel_status(data, kernel_dir(tmp_path, '@formula("f-done")\n'))
    # q-scalar <- q-mid <- q-in; q-curve and q-open are not upstream of it.
    assert data["mvp"] == ["q-in", "q-mid", "q-scalar"]
    assert data["mvp_results"] == ["q-scalar"]


def test_a_kernel_formula_the_canon_lacks_stops_the_build(tmp_path: pathlib.Path) -> None:
    with pytest.raises(SystemExit, match="ghost"):
        nav.kernel_status(kernel_data(), kernel_dir(tmp_path, '@formula("ghost")\n'))


def test_an_open_ticket_for_an_implemented_formula_stops_the_build(
    tmp_path: pathlib.Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    monkeypatch.setattr(nav, "OPEN_TICKETS", {"f-done": "#9"})
    with pytest.raises(SystemExit, match="f-done"):
        nav.kernel_status(kernel_data(), kernel_dir(tmp_path, '@formula("f-done")\n'))


def test_to_ascii_escapes_per_region_instead_of_destroying_characters() -> None:
    # html: &#<code>;  style: \<hex> followed by a blank  script: \u<4 hex>
    # a = U+00E4 = 228, arrow = U+2192, rho = U+03C1, u-umlaut = U+00FC = 252
    source = (
        '<p>\u00e4</p><style>a::before{content:"\u2192"}</style>'
        '<script type="module">var s="\u03c1";</script>\u00fc'
    )
    assert nav.to_ascii(source) == (
        '<p>&#228;</p><style>a::before{content:"\\2192 "}</style>'
        '<script type="module">var s="\\u03c1";</script>&#252;'
    )
    assert nav.to_ascii("plain ascii") == "plain ascii"
