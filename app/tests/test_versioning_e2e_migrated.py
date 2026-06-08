"""End-to-end versioning lifecycle against a REAL alembic-migrated schema.

The create_all-based unit tests build the schema from the models, which has
historically missed migration-only constraints (e.g. the
``uq_branches_one_main_per_root`` partial unique index — gh-912). This test
upgrades a throwaway DB with ``alembic upgrade head`` and then exercises the
full versioning lifecycle (create → snapshot → branch → adopt → re-adopt →
restore → compare → tree → discard + guards) via the service layer, so any
real-schema bug is caught.

Runs in an isolated subprocess via ``sys.executable`` (never a hardcoded venv
path) so it works on CI runners too.
"""
from __future__ import annotations

import os
import subprocess
import sys
import tempfile
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parents[2]
E2E_SCRIPT = REPO_ROOT / "scripts" / "e2e_versioning.py"


def _env(db_url: str) -> dict[str, str]:
    env = os.environ.copy()
    env["SQLALCHEMY_DATABASE_URL"] = db_url
    env["PYTHONPATH"] = str(REPO_ROOT)
    return env


def test_versioning_lifecycle_on_migrated_schema() -> None:
    assert E2E_SCRIPT.exists(), f"missing e2e script: {E2E_SCRIPT}"
    with tempfile.TemporaryDirectory() as tmp:
        db_path = Path(tmp) / "e2e.db"
        db_url = f"sqlite:///{db_path}"
        env = _env(db_url)

        upgrade = subprocess.run(
            [sys.executable, "-m", "alembic", "-c", str(REPO_ROOT / "alembic.ini"), "upgrade", "head"],
            cwd=str(REPO_ROOT),
            env=env,
            capture_output=True,
            text=True,
        )
        assert upgrade.returncode == 0, (
            f"alembic upgrade head failed:\nSTDOUT:\n{upgrade.stdout}\nSTDERR:\n{upgrade.stderr}"
        )

        run = subprocess.run(
            [sys.executable, str(E2E_SCRIPT)],
            cwd=str(REPO_ROOT),
            env=env,
            capture_output=True,
            text=True,
        )
        # The script prints PASS/FAIL per check and exits non-zero on any failure.
        assert run.returncode == 0, (
            f"versioning E2E failed against the migrated schema:\n{run.stdout}\n{run.stderr}"
        )
        assert "0 failed" in run.stdout, run.stdout
