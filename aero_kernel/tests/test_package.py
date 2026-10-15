"""Package skeleton tests: boundary to ``app`` (Q9), logging contract (ch. 8.14), async runner."""

import ast
import asyncio
import importlib
import logging
import subprocess
import sys
from pathlib import Path

import pytest

PACKAGE_NAME = "aero_kernel"
FORBIDDEN_ROOTS = frozenset({"app", "cad_designer", "scripts"})


def _imported_roots(path: Path, package_root: Path) -> set[str]:
    """Return the top-level module names a source file imports.

    A relative import is resolved against the file's position. One that climbs out of
    the package is reported by the first segment of the module it reaches, or as
    ``".."`` when it names nothing outside (``from .. import app``).

    Args:
        path: Python source file inside the package.
        package_root: Directory of the ``aero_kernel`` package.

    Returns:
        Set of top-level names imported by the file (``aero_kernel`` itself included).
    """
    tree = ast.parse(path.read_text(encoding="utf-8"), filename=str(path))
    # Package containing the module, as parts, e.g. ["aero_kernel", "formulas"].
    package_parts = [PACKAGE_NAME, *path.parent.relative_to(package_root).parts]
    roots: set[str] = set()
    for node in ast.walk(tree):
        if isinstance(node, ast.Import):
            roots.update(alias.name.split(".")[0] for alias in node.names)
        elif isinstance(node, ast.ImportFrom):
            if node.level == 0:
                roots.add((node.module or "").split(".")[0])
                continue
            keep = len(package_parts) - (node.level - 1)
            if keep < 1:
                # Climbs above aero_kernel: the target is a sibling of the package.
                names = [node.module.split(".")[0]] if node.module else [a.name for a in node.names]
                roots.update(names)
                roots.add("..")
            else:
                roots.add(PACKAGE_NAME)
    return roots


def _violations(package_root: Path) -> list[str]:
    """List ``file: root`` pairs where a module imports across the package boundary."""
    found: list[str] = []
    for path in sorted(package_root.rglob("*.py")):
        roots = _imported_roots(path, package_root)
        bad = sorted((roots & FORBIDDEN_ROOTS) | ({".."} & roots))
        found.extend(f"{path.relative_to(package_root)}: {name}" for name in bad)
    return found


def test_package_does_not_import_from_app(package_root: Path) -> None:
    """Q9: no module under aero_kernel imports app, cad_designer or scripts."""
    assert _violations(package_root) == []


@pytest.mark.parametrize(
    "source",
    [
        "import app",
        "import app.services.x",
        "from app.services import x",
        "from cad_designer import y",
        "import scripts.run",
        "from .. import app",
        "from ..app import x",
        "from ... import x",
    ],
)
def test_boundary_detector_flags_forbidden_imports(tmp_path: Path, source: str) -> None:
    """The detector itself catches absolute and package-escaping relative imports."""
    root = tmp_path / PACKAGE_NAME
    root.mkdir()
    (root / "bad.py").write_text(source + "\n", encoding="utf-8")
    assert _violations(root) != []


@pytest.mark.parametrize(
    "source",
    ["import json", "from . import sibling", "from .sub import x", "from aero_kernel import y"],
)
def test_boundary_detector_accepts_internal_imports(tmp_path: Path, source: str) -> None:
    """Standard-library and in-package imports are not violations."""
    root = tmp_path / PACKAGE_NAME
    root.mkdir()
    (root / "ok.py").write_text(source + "\n", encoding="utf-8")
    assert _violations(root) == []


def test_logger_has_only_a_null_handler() -> None:
    """Ch. 8.14: the package adds a NullHandler and configures nothing else."""
    code = (
        "import logging, aero_kernel;"
        "lg = logging.getLogger('aero_kernel');"
        "print([type(h).__name__ for h in lg.handlers], lg.level, lg.propagate,"
        " logging.getLogger().handlers)"
    )
    out = subprocess.run(
        [sys.executable, "-c", code], capture_output=True, text=True, check=True
    ).stdout.strip()
    assert out == "['NullHandler'] 0 True []"


def test_importing_package_keeps_logger_unconfigured() -> None:
    """In-process: exactly one NullHandler on the logger, level unset."""
    importlib.import_module(PACKAGE_NAME)
    logger = logging.getLogger(PACKAGE_NAME)
    assert [type(h) for h in logger.handlers if isinstance(h, logging.NullHandler)] == [
        logging.NullHandler
    ]
    assert logger.level == logging.NOTSET


def test_version_constant() -> None:
    """The package exposes a plain version string and an empty public API for now."""
    package = importlib.import_module(PACKAGE_NAME)
    assert package.__version__ == "0.1.0"
    assert package.__all__ == []


@pytest.mark.asyncio
async def test_pytest_asyncio_runs_coroutines() -> None:
    """Smoke test: pytest-asyncio executes coroutine tests in strict mode."""
    await asyncio.sleep(0)
