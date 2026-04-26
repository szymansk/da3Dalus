"""Unit tests for artifact_service template-run helpers (gh#339)."""

from __future__ import annotations

from pathlib import Path

import pytest

from app.core.config import settings
from app.services import artifact_service


@pytest.fixture()
def tmp_artifacts(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> Path:
    """Point ARTIFACTS_BASE_DIR at a clean tmp dir for each test."""
    monkeypatch.setattr(settings, "ARTIFACTS_BASE_DIR", tmp_path)
    return tmp_path


class TestCreateTemplateExecutionDir:
    def test_creates_directory_under_template_runs(self, tmp_artifacts: Path):
        execution_id, abs_path = artifact_service.create_template_execution_dir(42)

        assert abs_path.exists()
        assert abs_path.is_dir()
        assert abs_path.parent == tmp_artifacts / "_template_runs" / "42"
        assert abs_path.name == execution_id

    def test_wipes_previous_template_run(self, tmp_artifacts: Path):
        # First run with a leftover file
        _, first_dir = artifact_service.create_template_execution_dir(7)
        (first_dir / "leftover.stl").write_text("old")
        assert first_dir.exists()

        # Second run must wipe everything under _template_runs/7/
        _, second_dir = artifact_service.create_template_execution_dir(7)

        assert not first_dir.exists(), "previous execution dir should be wiped"
        assert second_dir.exists()
        assert second_dir.parent == tmp_artifacts / "_template_runs" / "7"

    def test_does_not_touch_other_template_runs(self, tmp_artifacts: Path):
        _, dir_a = artifact_service.create_template_execution_dir(1)
        (dir_a / "a.txt").write_text("keep")
        _, dir_b = artifact_service.create_template_execution_dir(2)

        assert dir_a.exists()
        assert (dir_a / "a.txt").read_text() == "keep"
        assert dir_b.exists()
