"""gh-1428: alembic upgrade / downgrade of the spar section and material columns.

Runs against a throw-away SQLite file, never the real DB.
"""

from __future__ import annotations

import os
import sqlite3
import subprocess
import sys
import tempfile
from pathlib import Path

import pytest

WORKTREE = Path(__file__).resolve().parents[2]
ALEMBIC_CFG = WORKTREE / "alembic.ini"
PREV_REVISION = "ad6c09905023"
THIS_REVISION = "054bdccea9a7"


def _run_alembic(db_url: str, command: str) -> None:
    env = os.environ.copy()
    env["SQLALCHEMY_DATABASE_URL"] = db_url
    env["PYTHONPATH"] = str(WORKTREE)
    result = subprocess.run(
        [sys.executable, "-m", "alembic", "-c", str(ALEMBIC_CFG), *command.split()],
        cwd=str(WORKTREE),
        env=env,
        capture_output=True,
        text=True,
        check=False,
    )
    if result.returncode != 0:
        raise RuntimeError(f"alembic {command!r} failed:\n{result.stdout}\n{result.stderr}")


def _columns(path: str) -> list[str]:
    conn = sqlite3.connect(path)
    try:
        return [r[1] for r in conn.execute("PRAGMA table_info(wing_xsec_spares)").fetchall()]
    finally:
        conn.close()


@pytest.fixture
def tmp_db():
    fd, path = tempfile.mkstemp(suffix=".db", prefix="gh1428_test_")
    os.close(fd)
    try:
        yield path
    finally:
        os.unlink(path)


def test_upgrade_adds_both_columns_and_downgrade_drops_them(tmp_db) -> None:
    url = f"sqlite:///{tmp_db}"
    _run_alembic(url, f"upgrade {PREV_REVISION}")
    before = _columns(tmp_db)
    assert "section" not in before and "material" not in before

    _run_alembic(url, f"upgrade {THIS_REVISION}")
    after = _columns(tmp_db)
    assert {"section", "material"} <= set(after)
    assert [c for c in after if c not in ("section", "material")] == before

    _run_alembic(url, f"downgrade {PREV_REVISION}")
    assert _columns(tmp_db) == before


def test_existing_spars_keep_their_values_and_get_null_section_and_material(tmp_db) -> None:
    url = f"sqlite:///{tmp_db}"
    _run_alembic(url, f"upgrade {PREV_REVISION}")
    conn = sqlite3.connect(tmp_db)
    try:
        conn.execute("PRAGMA foreign_keys=OFF")
        conn.execute(
            "INSERT INTO wing_xsec_spares (wing_xsec_detail_id, sort_index, "
            "spare_support_dimension_width, spare_support_dimension_height) VALUES (1, 0, 6.0, 16.0)"
        )
        conn.commit()
    finally:
        conn.close()
    _run_alembic(url, f"upgrade {THIS_REVISION}")
    conn = sqlite3.connect(tmp_db)
    try:
        row = conn.execute(
            "SELECT spare_support_dimension_width, section, material FROM wing_xsec_spares"
        ).fetchone()
    finally:
        conn.close()
    assert row == (6.0, None, None)
    _run_alembic(url, f"downgrade {PREV_REVISION}")
    conn = sqlite3.connect(tmp_db)
    try:
        assert conn.execute(
            "SELECT spare_support_dimension_width FROM wing_xsec_spares"
        ).fetchone() == (6.0,)
    finally:
        conn.close()


def test_the_migration_is_the_single_head_and_chains_on_the_previous_one() -> None:
    import importlib.util

    path = WORKTREE / "alembic" / "versions" / "054bdccea9a7_gh1428_spar_section_material.py"
    spec = importlib.util.spec_from_file_location("migration_gh1428", path)
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    assert module.revision == THIS_REVISION
    assert module.down_revision == PREV_REVISION
