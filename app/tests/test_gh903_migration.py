"""TDD test for gh-903: versioning DB model + migration + backfill.

Uses a throw-away SQLite DB (via SQLALCHEMY_DATABASE_URL env var) so the
user's real database is NEVER touched.

What is tested:
1. ``alembic upgrade head`` succeeds against a pre-populated DB.
2. After upgrade:
   - ``branches`` table exists with correct columns.
   - ``aeroplanes`` table has all new versioning columns.
   - ``design_versions`` table is GONE.
   - Every pre-existing aeroplane has a corresponding ``main`` branch
     (is_main=true, root_id=aeroplane.id, head_id=aeroplane.id).
   - Every aeroplane's ``root_id`` and ``branch_id`` are set (not null).
   - ``is_immutable`` is 0 (false) for all existing aeroplanes.
3. ``alembic downgrade -1`` succeeds:
   - ``design_versions`` table is back (empty).
   - The new columns are gone from ``aeroplanes``.
   - ``branches`` table is gone.
"""

from __future__ import annotations

import os
import sqlite3
import sys
import tempfile
from pathlib import Path

import pytest


# ── helpers ───────────────────────────────────────────────────────────────────

WORKTREE = Path(__file__).resolve().parents[2]  # /…/cad-gh901
ALEMBIC_CFG = WORKTREE / "alembic.ini"

# The interpreter running the tests — portable across machines and CI runners
# (NEVER hardcode a local virtualenv path; it won't exist on CI).
PYTHON = sys.executable

# The revision *before* our gh-903 migration (used to seed the temp DB).
PREV_REVISION = "16cbb884a838"


def _run_alembic(db_url: str, command: str) -> None:
    """Run an alembic CLI command against ``db_url`` via subprocess."""
    import subprocess

    env = os.environ.copy()
    env["SQLALCHEMY_DATABASE_URL"] = db_url
    env["PYTHONPATH"] = str(WORKTREE)

    result = subprocess.run(
        [PYTHON, "-m", "alembic", "-c", str(ALEMBIC_CFG), *command.split()],
        cwd=str(WORKTREE),
        env=env,
        capture_output=True,
        text=True,
    )
    if result.returncode != 0:
        raise RuntimeError(
            f"alembic {command!r} failed:\n"
            f"STDOUT:\n{result.stdout}\n"
            f"STDERR:\n{result.stderr}"
        )


def _seed_db_to_prev_head(db_path: str) -> None:
    """Upgrade to the revision *before* our migration (PREV_REVISION)."""
    db_url = f"sqlite:///{db_path}"
    _run_alembic(db_url, f"upgrade {PREV_REVISION}")


def _insert_aeroplanes(db_path: str, count: int = 2) -> list[int]:
    """Insert ``count`` minimal aeroplane rows; return their ids."""
    import uuid as _uuid

    conn = sqlite3.connect(db_path)
    try:
        ids = []
        for i in range(count):
            uid = _uuid.uuid4().hex  # 32-char hex string (GUID/CHAR(32) format)
            if _has_col(conn, "aeroplanes", "is_immutable"):
                cur = conn.execute(
                    "INSERT INTO aeroplanes (uuid, name, xyz_ref, is_immutable)"
                    " VALUES (?, ?, '[]', 0)",
                    (uid, f"test-plane-{i}"),
                )
            else:
                cur = conn.execute(
                    "INSERT INTO aeroplanes (uuid, name, xyz_ref) VALUES (?, ?, '[]')",
                    (uid, f"test-plane-{i}"),
                )
            ids.append(cur.lastrowid)
        conn.commit()
        return ids
    finally:
        conn.close()


def _has_col(conn: sqlite3.Connection, table: str, col: str) -> bool:
    cols = [r[1] for r in conn.execute(f"PRAGMA table_info({table})").fetchall()]
    return col in cols


def _table_exists(conn: sqlite3.Connection, table: str) -> bool:
    return (
        conn.execute(
            "SELECT 1 FROM sqlite_master WHERE type='table' AND name=?", (table,)
        ).fetchone()
        is not None
    )


def _col_names(conn: sqlite3.Connection, table: str) -> list[str]:
    return [r[1] for r in conn.execute(f"PRAGMA table_info({table})").fetchall()]


# ── fixtures ──────────────────────────────────────────────────────────────────


@pytest.fixture()
def tmp_db():
    """Yield a path to a fresh temp SQLite file; delete it after the test."""
    fd, path = tempfile.mkstemp(suffix=".db", prefix="gh903_test_")
    os.close(fd)
    try:
        yield path
    finally:
        try:
            os.unlink(path)
        except OSError:
            pass


# ── tests ─────────────────────────────────────────────────────────────────────


class TestGh903Migration:
    """Alembic upgrade + backfill + downgrade against a throw-away SQLite DB."""

    def test_upgrade_creates_branches_table(self, tmp_db):
        _seed_db_to_prev_head(tmp_db)
        _insert_aeroplanes(tmp_db, count=2)
        _run_alembic(f"sqlite:///{tmp_db}", "upgrade head")

        conn = sqlite3.connect(tmp_db)
        try:
            assert _table_exists(conn, "branches"), "branches table must exist after upgrade"
        finally:
            conn.close()

    def test_upgrade_adds_versioning_columns_to_aeroplanes(self, tmp_db):
        _seed_db_to_prev_head(tmp_db)
        _insert_aeroplanes(tmp_db, count=1)
        _run_alembic(f"sqlite:///{tmp_db}", "upgrade head")

        conn = sqlite3.connect(tmp_db)
        try:
            cols = _col_names(conn, "aeroplanes")
            for expected in (
                "branch_id",
                "predecessor_id",
                "root_id",
                "is_immutable",
                "version_label",
                "version_note",
                "created_by",
                "provenance_message_id",
                "preview_png",
            ):
                assert expected in cols, f"Column '{expected}' missing from aeroplanes after upgrade"
        finally:
            conn.close()

    def test_upgrade_drops_design_versions_table(self, tmp_db):
        _seed_db_to_prev_head(tmp_db)
        _run_alembic(f"sqlite:///{tmp_db}", "upgrade head")

        conn = sqlite3.connect(tmp_db)
        try:
            assert not _table_exists(conn, "design_versions"), (
                "design_versions table must be dropped after upgrade"
            )
        finally:
            conn.close()

    def test_backfill_creates_main_branch_per_aeroplane(self, tmp_db):
        _seed_db_to_prev_head(tmp_db)
        ap_ids = _insert_aeroplanes(tmp_db, count=3)
        _run_alembic(f"sqlite:///{tmp_db}", "upgrade head")

        conn = sqlite3.connect(tmp_db)
        try:
            branches = conn.execute(
                "SELECT root_id, head_id, name, is_main FROM branches ORDER BY id"
            ).fetchall()
            assert len(branches) == len(ap_ids), (
                f"Expected {len(ap_ids)} branches, got {len(branches)}"
            )
            branch_root_ids = {b[0] for b in branches}
            for ap_id in ap_ids:
                assert ap_id in branch_root_ids, (
                    f"Aeroplane {ap_id} has no main branch"
                )
            for root_id, head_id, name, is_main in branches:
                assert name == "main", f"Branch name should be 'main', got {name!r}"
                assert root_id == head_id, "root_id and head_id should both be the aeroplane id"
                assert is_main in (1, True), "is_main should be true for the main branch"
        finally:
            conn.close()

    def test_backfill_sets_aeroplane_root_id_and_branch_id(self, tmp_db):
        _seed_db_to_prev_head(tmp_db)
        ap_ids = _insert_aeroplanes(tmp_db, count=2)
        _run_alembic(f"sqlite:///{tmp_db}", "upgrade head")

        conn = sqlite3.connect(tmp_db)
        try:
            rows = conn.execute(
                "SELECT id, root_id, branch_id, is_immutable FROM aeroplanes"
            ).fetchall()
            assert len(rows) == len(ap_ids)
            for ap_id, root_id, branch_id, is_immutable in rows:
                assert root_id == ap_id, (
                    f"Aeroplane {ap_id}: root_id should be self, got {root_id}"
                )
                assert branch_id is not None, (
                    f"Aeroplane {ap_id}: branch_id must not be null after backfill"
                )
                assert is_immutable in (0, False), (
                    f"Aeroplane {ap_id}: is_immutable should be false after backfill"
                )
        finally:
            conn.close()

    def test_downgrade_restores_design_versions_and_removes_branches(self, tmp_db):
        _seed_db_to_prev_head(tmp_db)
        _insert_aeroplanes(tmp_db, count=2)
        _run_alembic(f"sqlite:///{tmp_db}", "upgrade head")
        # Downgrade to the revision *before* gh-903 rather than a relative
        # "-1": the gh-903 migration is no longer guaranteed to be head once
        # later migrations are added, so target the stable named revision.
        _run_alembic(f"sqlite:///{tmp_db}", f"downgrade {PREV_REVISION}")

        conn = sqlite3.connect(tmp_db)
        try:
            assert _table_exists(conn, "design_versions"), (
                "design_versions must be recreated after downgrade"
            )
            assert not _table_exists(conn, "branches"), (
                "branches table must be dropped after downgrade"
            )
            cols = _col_names(conn, "aeroplanes")
            for removed in (
                "branch_id",
                "predecessor_id",
                "root_id",
                "is_immutable",
                "version_label",
                "version_note",
                "created_by",
                "provenance_message_id",
                "preview_png",
            ):
                assert removed not in cols, (
                    f"Column '{removed}' should be gone after downgrade, still present"
                )
        finally:
            conn.close()

    def test_empty_db_upgrade_and_downgrade(self, tmp_db):
        """Migration must work even when aeroplanes table is empty."""
        _seed_db_to_prev_head(tmp_db)
        # No aeroplanes inserted
        _run_alembic(f"sqlite:///{tmp_db}", "upgrade head")
        # Downgrade to the revision *before* gh-903 (stable named revision)
        # instead of a relative "-1", which assumed gh-903 was head.
        _run_alembic(f"sqlite:///{tmp_db}", f"downgrade {PREV_REVISION}")

        conn = sqlite3.connect(tmp_db)
        try:
            assert _table_exists(conn, "design_versions")
            assert not _table_exists(conn, "branches")
        finally:
            conn.close()
