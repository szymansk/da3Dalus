"""The importer against the real canon document, and the importer's place in the package."""

import ast
import runpy
from pathlib import Path

import pytest
from aero_kernel.canon.load import load_canon_model
from aero_kernel.importer.pipeline import import_canon
from aero_kernel.tests.importer_builders import SOURCE_COMMIT, write_canon

REPO_ROOT = Path(__file__).resolve().parents[2]
CANON = REPO_ROOT / "_reversa_sdd" / "calculations" / "canon"
PACKAGE = REPO_ROOT / "aero_kernel"


def test_the_real_canon_imports_without_a_finding(tmp_path: Path) -> None:
    result = import_canon(CANON, SOURCE_COMMIT)
    assert result.findings == (), [str(finding) for finding in result.findings]
    assert result.model_json is not None
    (tmp_path / "canon_model.json").write_text(result.model_json, encoding="utf-8")
    content = load_canon_model(tmp_path / "canon_model.json").namespaces["calc"]
    assert len(content.formulas) == len(list((CANON / "formulas").glob("*.md")))
    assert len(content.quantities) == len(list((CANON / "quantities").glob("*.md")))
    assert len(content.defaults) == 7
    for default in content.defaults.values():
        assert default.source
        assert default.regime
        assert default.unit


def test_the_real_canon_imports_byte_identically_twice() -> None:
    first, second = import_canon(CANON, SOURCE_COMMIT), import_canon(CANON, SOURCE_COMMIT)
    assert first.model_json is not None
    assert (first.model_json, first.report) == (second.model_json, second.report)


def imported_modules(source: str, package: tuple[str, ...]) -> set[str]:
    """Return the absolute names of the modules a source text imports, relative imports resolved.

    Args:
        source: Python source.
        package: The package the module lives in, e.g. ``("aero_kernel", "canon")``.
    """
    names: set[str] = set()
    for node in ast.walk(ast.parse(source)):
        if isinstance(node, ast.Import):
            names.update(alias.name for alias in node.names)
        elif isinstance(node, ast.ImportFrom):
            if node.level:
                base = [*package[: len(package) - node.level + 1], *(node.module or "").split(".")]
                module = ".".join(part for part in base if part)
            else:
                module = node.module or ""
            names.add(module)
            names.update(f"{module}.{alias.name}" for alias in node.names)
    return names


def test_the_import_scan_resolves_relative_imports() -> None:
    found = imported_modules(
        "from .. import importer\nfrom ..importer import x", ("aero_kernel", "canon")
    )
    assert {"aero_kernel", "aero_kernel.importer", "aero_kernel.importer.x"} <= found


def test_no_runtime_module_imports_the_importer_or_yaml() -> None:
    """Q12: the importer is a dev-time tool; the kernel runs without it and without PyYAML."""
    offenders: list[str] = []
    for path in PACKAGE.rglob("*.py"):
        relative = path.relative_to(PACKAGE).parts
        if relative[0] in ("importer", "tests"):
            continue
        package = ("aero_kernel", *relative[:-1])
        for name in imported_modules(path.read_text(encoding="utf-8"), package):
            if name.split(".")[0] == "yaml" or name.startswith("aero_kernel.importer"):
                offenders.append(f"{path.relative_to(REPO_ROOT)} imports {name}")
    assert offenders == []


def test_python_m_aero_kernel_importer_runs_the_command_line(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    canon = write_canon(tmp_path)
    out = tmp_path / "out"
    argv = ["importer", str(canon), "--out", str(out), "--source-commit", SOURCE_COMMIT]
    monkeypatch.setattr("sys.argv", argv)
    with pytest.raises(SystemExit) as exit_info:
        runpy.run_module("aero_kernel.importer", run_name="__main__")
    assert exit_info.value.code == 0
    assert (out / "canon_model.json").is_file()
