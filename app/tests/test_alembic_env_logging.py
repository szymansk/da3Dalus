"""Running the migrations in-process leaves the host process's loggers working (gh-1357).

``alembic/env.py`` configures logging from ``alembic.ini``. With ``fileConfig``'s default
``disable_existing_loggers=True`` every logger that already exists in the process is disabled, so a
migration test silenced e.g. ``aero_kernel.runtime`` for every later test in the same pytest worker
(``test_runtime_routing`` then saw zero "worker died" warnings).
"""

from __future__ import annotations

import logging
from pathlib import Path

import pytest
from alembic import command
from alembic.config import Config

REPO_ROOT = Path(__file__).resolve().parent.parent.parent


def test_an_in_process_migration_keeps_existing_loggers_enabled(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch, caplog: pytest.LogCaptureFixture
) -> None:
    monkeypatch.delenv("SQLALCHEMY_DATABASE_URL", raising=False)  # env.py would override the URL
    existing = logging.getLogger("gh1357.created_before_the_migration")
    root = logging.getLogger()
    saved_handlers, saved_level = root.handlers[:], root.level
    cfg = Config(str(REPO_ROOT / "alembic.ini"))
    cfg.set_main_option("script_location", str(REPO_ROOT / "alembic"))
    cfg.set_main_option("sqlalchemy.url", f"sqlite:///{tmp_path / 'gh1357.db'}")
    try:
        command.upgrade(cfg, "head")
    finally:
        for handler in root.handlers[:]:
            if handler not in saved_handlers:
                root.removeHandler(handler)
        for handler in saved_handlers:
            if handler not in root.handlers:
                root.addHandler(handler)
        root.setLevel(saved_level)
    assert not existing.disabled
    with caplog.at_level(logging.WARNING, logger=existing.name):
        existing.warning("still heard after the migration")
    assert [r.getMessage() for r in caplog.records] == ["still heard after the migration"]
