"""gh-1187: the data migration that proposes ``wings.surface_type`` for existing rows.

Two layers: the pure proposal function (name hints, main wing, geometry fallback) and
``alembic upgrade`` / ``downgrade`` against a throw-away SQLite file (never the real DB).
"""

from __future__ import annotations

import importlib.util
import json
import os
import sqlite3
import subprocess
import sys
import tempfile
from pathlib import Path

import pytest

WORKTREE = Path(__file__).resolve().parents[2]
ALEMBIC_CFG = WORKTREE / "alembic.ini"
MIGRATION_PATH = WORKTREE / "alembic" / "versions" / "d90a2284bf83_gh1187_wing_surface_type.py"
PREV_REVISION = "a1157f5e11a0"
THIS_REVISION = "d90a2284bf83"


def _load_migration():
    spec = importlib.util.spec_from_file_location("migration_gh1187", MIGRATION_PATH)
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


migration = _load_migration()


def _wing(wing_id: int, name: str, area: float, symmetric: bool = True, root_x: float = 0.0):
    return {
        "id": wing_id,
        "name": name,
        "symmetric": symmetric,
        "area": area,
        "root_x": root_x,
    }


# ── name hints ────────────────────────────────────────────────────────────────


@pytest.mark.parametrize(
    ("name", "expected"),
    [
        ("Canard", "canard"),
        ("Winglet left", "winglet"),
        ("V-Leitwerk", "v_tail"),
        ("V-Tail", "v_tail"),
        ("Seitenleitwerk", "vertical_tail"),
        ("SLW", "vertical_tail"),
        ("Fin", "vertical_tail"),
        ("Rudder", "vertical_tail"),
        ("vertical stabilizer", "vertical_tail"),
        ("Höhenleitwerk", "horizontal_tail"),
        ("HLW", "horizontal_tail"),
        ("Elevator", "horizontal_tail"),
        ("Stabilizer", "horizontal_tail"),
        ("horizontal_tail", "horizontal_tail"),
        ("Tragflaeche", None),
        ("Main Wing", None),
        ("Final wing", None),
        ("Entenhausen", None),
        ("", None),
    ],
)
def test_name_hint(name: str, expected: str | None) -> None:
    assert migration._name_hint(name) == expected


# ── proposal per aeroplane ────────────────────────────────────────────────────


def test_no_wings_no_proposal() -> None:
    assert migration.propose_surface_types([]) == {}


def test_largest_unhinted_wing_is_main_and_hints_win_for_the_rest() -> None:
    wings = [
        _wing(1, "HLW", 0.9),
        _wing(2, "Tragflaeche", 0.2),
        _wing(3, "Seitenleitwerk", 0.5, symmetric=False),
    ]
    assert migration.propose_surface_types(wings) == {
        1: "horizontal_tail",
        2: "main_wing",
        3: "vertical_tail",
    }


def test_a_hinted_tail_never_becomes_main_while_an_unhinted_wing_exists() -> None:
    wings = [_wing(1, "Stabilizer", 5.0), _wing(2, "Wing", 0.1)]
    assert migration.propose_surface_types(wings)[2] == "main_wing"


def test_all_hinted_the_largest_wing_is_main() -> None:
    wings = [_wing(1, "Stabilizer", 0.1), _wing(2, "Fin", 0.4)]
    proposal = migration.propose_surface_types(wings)
    assert proposal == {1: "horizontal_tail", 2: "main_wing"}


def test_single_wing_is_main_even_with_a_tail_name() -> None:
    assert migration.propose_surface_types([_wing(7, "Stabilizer", 0.3)]) == {7: "main_wing"}


def test_unhinted_secondary_wings_use_geometry() -> None:
    wings = [
        _wing(1, "A", 1.0, root_x=0.10),
        _wing(2, "B", 0.2, symmetric=False, root_x=0.50),
        _wing(3, "C", 0.2, root_x=0.02),
        _wing(4, "D", 0.2, root_x=0.45),
    ]
    assert migration.propose_surface_types(wings) == {
        1: "main_wing",
        2: "vertical_tail",
        3: "canard",
        4: "horizontal_tail",
    }


def test_equal_areas_pick_the_lowest_id_deterministically() -> None:
    wings = [_wing(2, "B", 1.0), _wing(1, "A", 1.0)]
    assert migration.propose_surface_types(wings)[1] == "main_wing"


def test_exactly_one_main_wing_per_aeroplane() -> None:
    wings = [_wing(i, f"Wing {i}", float(i)) for i in range(1, 6)]
    proposal = migration.propose_surface_types(wings)
    assert sum(1 for v in proposal.values() if v == "main_wing") == 1


# ── alembic upgrade / downgrade on a throw-away SQLite file ───────────────────


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


@pytest.fixture
def tmp_db():
    fd, path = tempfile.mkstemp(suffix=".db", prefix="gh1187_test_")
    os.close(fd)
    try:
        yield path
    finally:
        os.unlink(path)


def _insert_plane(conn: sqlite3.Connection, name: str) -> int:
    import uuid

    cols = [r[1] for r in conn.execute("PRAGMA table_info(aeroplanes)").fetchall()]
    values = {"uuid": uuid.uuid4().hex, "name": name, "xyz_ref": "[]"}
    if "is_immutable" in cols:
        values["is_immutable"] = 0
    names = ", ".join(values)
    marks = ", ".join("?" for _ in values)
    cur = conn.execute(f"INSERT INTO aeroplanes ({names}) VALUES ({marks})", tuple(values.values()))
    return cur.lastrowid


def _insert_wing(
    conn: sqlite3.Connection, plane_id: int, name: str, ribs: list[tuple[float, list[float]]]
) -> int:
    cur = conn.execute(
        "INSERT INTO wings (name, symmetric, aeroplane_id) VALUES (?, 1, ?)", (name, plane_id)
    )
    wing_id = cur.lastrowid
    for index, (chord, xyz) in enumerate(ribs):
        conn.execute(
            "INSERT INTO wing_xsecs (xyz_le, chord, twist, airfoil, wing_id, sort_index)"
            " VALUES (?, ?, 0, 'naca0012', ?, ?)",
            (json.dumps(xyz), chord, wing_id, index),
        )
    return wing_id


def _roles(db_path: str) -> dict[str, tuple[str, int]]:
    conn = sqlite3.connect(db_path)
    try:
        rows = conn.execute(
            "SELECT name, surface_type, surface_type_inferred FROM wings"
        ).fetchall()
        return {name: (role, flag) for name, role, flag in rows}
    finally:
        conn.close()


def test_upgrade_proposes_roles_flags_them_inferred_and_downgrade_drops_columns(tmp_db) -> None:
    db_url = f"sqlite:///{tmp_db}"
    _run_alembic(db_url, f"upgrade {PREV_REVISION}")
    conn = sqlite3.connect(tmp_db)
    try:
        plane_a = _insert_plane(conn, "plane-a")
        plane_b = _insert_plane(conn, "plane-b")
        _insert_wing(conn, plane_a, "Tragflaeche", [(0.2, [0, 0, 0]), (0.1, [0.05, 0.8, 0.0])])
        _insert_wing(conn, plane_a, "HLW", [(0.1, [0.6, 0, 0]), (0.08, [0.62, 0.3, 0.0])])
        _insert_wing(conn, plane_a, "SLW", [(0.1, [0.6, 0, 0]), (0.08, [0.62, 0.0, 0.3])])
        _insert_wing(conn, plane_b, "Stabilizer", [(0.1, [0.6, 0, 0]), (0.08, [0.62, 0.3, 0.0])])
        conn.commit()
    finally:
        conn.close()

    _run_alembic(db_url, f"upgrade {THIS_REVISION}")
    roles = _roles(tmp_db)
    assert roles == {
        "Tragflaeche": ("main_wing", 1),
        "HLW": ("horizontal_tail", 1),
        "SLW": ("vertical_tail", 1),
        "Stabilizer": ("main_wing", 1),
    }

    conn = sqlite3.connect(tmp_db)
    try:
        info = {r[1]: r for r in conn.execute("PRAGMA table_info(wings)").fetchall()}
    finally:
        conn.close()
    assert info["surface_type"][3] == 1, "surface_type must be NOT NULL after the migration"

    _run_alembic(db_url, f"downgrade {PREV_REVISION}")
    conn = sqlite3.connect(tmp_db)
    try:
        columns = [r[1] for r in conn.execute("PRAGMA table_info(wings)").fetchall()]
    finally:
        conn.close()
    assert "surface_type" not in columns
    assert "surface_type_inferred" not in columns


def test_upgrade_on_an_empty_wings_table_succeeds(tmp_db) -> None:
    db_url = f"sqlite:///{tmp_db}"
    _run_alembic(db_url, f"upgrade {THIS_REVISION}")
    assert _roles(tmp_db) == {}


def test_migration_chains_onto_the_previous_head() -> None:
    assert migration.down_revision == PREV_REVISION
    assert migration.revision == THIS_REVISION
