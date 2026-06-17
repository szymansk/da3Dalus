"""Guard the pytest collection config (maintainer-authorized chore).

A root-level ``pytest`` run recurses into sibling git worktrees kept
under ``.worktrees/`` (concurrent WIP whose test files share basenames
with the main checkout), which trips "import file mismatch" collection
errors. ``.worktrees`` must therefore be listed in ``norecursedirs``.

This is a config regression guard: if someone drops ``.worktrees`` from
``norecursedirs`` the multi-worktree collection error comes back. The
clean CI checkout has no sibling worktrees, so the error itself is not
reproducible there — we assert the config value instead.
"""

from __future__ import annotations

import sys
import tomllib
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parent.parent.parent
sys.path.insert(0, str(REPO_ROOT))


def _norecursedirs() -> list[str]:
    pyproject = REPO_ROOT / "pyproject.toml"
    data = tomllib.loads(pyproject.read_text(encoding="utf-8"))
    return data["tool"]["pytest"]["ini_options"]["norecursedirs"]


def test_worktrees_excluded_from_collection() -> None:
    """`.worktrees` must be excluded so root-level pytest skips sibling worktrees."""
    assert ".worktrees" in _norecursedirs()


def test_existing_exclusions_preserved() -> None:
    """The pre-existing exclusions stay in place (no regression)."""
    dirs = _norecursedirs()
    assert "external" in dirs
    assert ".claude" in dirs
