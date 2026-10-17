"""The importer's place in the repository: README vocabularies, packaged model, CI step (ch. 8.9)."""

import re
from pathlib import Path
from typing import cast, get_args

import pytest
import yaml
from aero_kernel.canon import model
from aero_kernel.canon.load import default_model_path, load_canon_model
from aero_kernel.importer import source
from aero_kernel.importer.pipeline import import_canon
from aero_kernel.importer.source import commit_format_finding
from aero_kernel.tests.importer_builders import write_canon

REPO_ROOT = Path(__file__).resolve().parents[2]
README = REPO_ROOT / "_reversa_sdd" / "calculations" / "canon" / "README.md"
WORKFLOW = REPO_ROOT / ".github" / "workflows" / "test.yml"


def table_terms(readme: str, heading: str) -> set[str]:
    """The backticked first-column terms of the table under a README heading."""
    found = re.search(
        rf"^#+ [^\n]*{re.escape(heading)}[^\n]*$(.*?)(?=^#+ |\Z)", readme, re.MULTILINE | re.DOTALL
    )
    assert found is not None, f"no heading {heading!r} in the README"
    return set(re.findall(r"^\|\s*`([a-z_]+)`\s*\|", found.group(1), re.MULTILINE))


# --- Q6: the README tables and the model's vocabularies cannot drift apart -----------------------------------


@pytest.mark.parametrize(
    ("heading", "vocabulary"),
    [("Vocabulary of `when`", model.WhenTerm), ("Quantity types", model.QuantityType)],
)
def test_the_readme_table_is_the_models_vocabulary(heading: str, vocabulary: object) -> None:
    terms = table_terms(README.read_text(encoding="utf-8"), heading)
    assert terms, f"the README table under {heading!r} has no terms"
    assert terms == set(get_args(vocabulary))


def test_a_term_only_in_the_readme_or_only_in_the_model_is_drift() -> None:
    readme = README.read_text(encoding="utf-8")
    extra = readme.replace("| `has_aileron` |", "| `has_wings` | x |\n| `has_aileron` |", 1)
    assert table_terms(extra, "Vocabulary of `when`") != set(get_args(model.WhenTerm))
    missing = re.sub(r"^\| `components` \|.*\n", "", readme, flags=re.MULTILINE)
    assert table_terms(missing, "Quantity types") != set(get_args(model.QuantityType))


# --- Q12: the packaged model sits next to the model types -----------------------------------------------------


def test_the_packaged_model_and_report_are_in_the_source_tree() -> None:
    package = Path(model.__file__).resolve().parent
    assert default_model_path() == package / "canon_model.json"
    assert (package / "canon_model.json").is_file()
    assert (package / "IMPORT_REPORT.md").is_file()
    assert load_canon_model().namespaces["calc"].formulas


# --- Q9: the CI step ------------------------------------------------------------------------------------------


def workflow() -> dict[str, object]:
    """The parsed workflow file."""
    return cast("dict[str, object]", yaml.safe_load(WORKFLOW.read_text(encoding="utf-8")))


def test_the_fast_job_runs_the_import_check_after_pyright() -> None:
    jobs = cast("dict[str, dict[str, list[dict[str, str]]]]", workflow()["jobs"])
    runs = [step.get("run", "") for step in jobs["fast"]["steps"]]
    command = "poetry run python -m aero_kernel.importer _reversa_sdd/calculations/canon --check"
    assert command in runs
    assert runs.index(command) > runs.index("poetry run pyright aero_kernel")


def test_a_canon_only_change_triggers_the_backend_filter() -> None:
    jobs = cast("dict[str, dict[str, list[dict[str, dict[str, str]]]]]", workflow()["jobs"])
    filters = next(
        step["with"]["filters"]
        for step in jobs["changes"]["steps"]
        if "with" in step and "filters" in step["with"]
    )
    backend = cast("dict[str, list[str]]", yaml.safe_load(filters))["backend"]
    assert "_reversa_sdd/calculations/canon/**" in backend


# --- N5: both users of the commit format consult the shared pattern --------------------------------------------


def test_replacing_the_shared_pattern_changes_both_users(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    monkeypatch.setattr(source, "COMMIT_PATTERN", re.compile(".*"))
    assert commit_format_finding("not-a-sha") is None
    result = import_canon(write_canon(tmp_path), "zz")
    assert [f for f in result.findings if f.file == "command line"] == []
