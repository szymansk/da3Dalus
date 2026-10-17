"""The importer against the real canon document, and the importer's place in the package."""

import ast
import runpy
from pathlib import Path

import pytest
from aero_kernel.canon.load import load_canon_model
from aero_kernel.importer.cli import main
from aero_kernel.tests.importer_builders import SOURCE_COMMIT

REPO_ROOT = Path(__file__).resolve().parents[2]
CANON = REPO_ROOT / "_reversa_sdd" / "calculations" / "canon"
PACKAGE = REPO_ROOT / "aero_kernel"


def test_the_real_canon_imports_without_a_finding(
    tmp_path: Path, capsys: pytest.CaptureFixture[str]
) -> None:
    exit_code = main([str(CANON), "--out", str(tmp_path), "--source-commit", SOURCE_COMMIT])
    assert exit_code == 0, capsys.readouterr().out
    model = load_canon_model(tmp_path / "canon_model.json")
    content = model.namespaces["calc"]
    assert len(content.formulas) == len(list((CANON / "formulas").glob("*.md")))
    assert len(content.quantities) == len(list((CANON / "quantities").glob("*.md")))
    assert len(content.defaults) == 7
    for default in content.defaults.values():
        assert default.source
        assert default.regime
        assert default.unit


def test_the_real_canon_imports_byte_identically_twice(tmp_path: Path) -> None:
    for name in ("one", "two"):
        assert (
            main([str(CANON), "--out", str(tmp_path / name), "--source-commit", SOURCE_COMMIT]) == 0
        )
    for name in ("canon_model.json", "IMPORT_REPORT.md"):
        assert (tmp_path / "one" / name).read_bytes() == (tmp_path / "two" / name).read_bytes()


def test_no_runtime_module_imports_the_importer() -> None:
    """Q12: the importer is a dev-time tool; the kernel runs without it (and without PyYAML)."""
    offenders: list[str] = []
    for path in PACKAGE.rglob("*.py"):
        relative = path.relative_to(PACKAGE).parts
        if relative[0] in ("importer", "tests"):
            continue
        for node in ast.walk(ast.parse(path.read_text(encoding="utf-8"))):
            names: list[str] = []
            if isinstance(node, ast.Import):
                names = [alias.name for alias in node.names]
            elif isinstance(node, ast.ImportFrom):
                base = node.module or ""
                names = [base, *(f"{base}.{alias.name}" for alias in node.names)]
            if any(name.split(".")[:2] == ["aero_kernel", "importer"] for name in names):
                offenders.append(str(path.relative_to(REPO_ROOT)))
    assert offenders == []


def test_python_m_aero_kernel_importer_runs_the_command_line(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    argv = ["importer", str(CANON), "--out", str(tmp_path), "--source-commit", SOURCE_COMMIT]
    monkeypatch.setattr("sys.argv", argv)
    with pytest.raises(SystemExit) as exit_info:
        runpy.run_module("aero_kernel.importer", run_name="__main__")
    assert exit_info.value.code == 0
    assert (tmp_path / "canon_model.json").is_file()
