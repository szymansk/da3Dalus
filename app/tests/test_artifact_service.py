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


class TestResolveExecutionDir:
    def test_resolves_plan_execution_dir(self, tmp_artifacts: Path):
        # Plan execution lives under <base>/<aero_id>/<plan_id>/<exec_id>/
        execution_id, plan_dir = artifact_service.create_execution_dir("aero-x", 99)

        resolved = artifact_service._resolve_execution_dir(99, execution_id)

        assert resolved == plan_dir

    def test_resolves_template_execution_dir(self, tmp_artifacts: Path):
        execution_id, tpl_dir = artifact_service.create_template_execution_dir(55)

        resolved = artifact_service._resolve_execution_dir(55, execution_id)

        assert resolved == tpl_dir

    def test_plan_takes_precedence_over_template_when_id_collides(self, tmp_artifacts: Path):
        # Edge case: same id used for both (in real DB they wouldn't collide,
        # but the resolver must be deterministic).
        plan_exec_id, plan_dir = artifact_service.create_execution_dir("aero-y", 123)
        # Manually create a template-run dir with a different exec_id so they
        # don't both have the same dir name.
        tpl_root = tmp_artifacts / "_template_runs" / "123"
        tpl_root.mkdir(parents=True)
        (tpl_root / "20260101T000000Z").mkdir()

        # Plan exec_id resolves to plan dir
        assert artifact_service._resolve_execution_dir(123, plan_exec_id) == plan_dir
        # Template exec_id resolves to template dir
        assert (
            artifact_service._resolve_execution_dir(123, "20260101T000000Z")
            == tpl_root.resolve() / "20260101T000000Z"
        )

    def test_raises_not_found_for_unknown_execution(self, tmp_artifacts: Path):
        from app.core.exceptions import NotFoundError

        with pytest.raises(NotFoundError):
            artifact_service._resolve_execution_dir(404, "nonexistent")


class TestZipExecution:
    def test_zips_all_files_in_execution(self, tmp_artifacts: Path):
        execution_id, exec_dir = artifact_service.create_execution_dir("aero-z", 11)
        (exec_dir / "a.stl").write_bytes(b"AAAA")
        (exec_dir / "b.txt").write_text("hello")
        sub = exec_dir / "wing"
        sub.mkdir()
        (sub / "c.stp").write_bytes(b"CCCC")

        zip_path = artifact_service.zip_execution(11, execution_id)

        import zipfile

        with zipfile.ZipFile(zip_path) as zf:
            names = sorted(zf.namelist())
        assert names == ["a.stl", "b.txt", "wing/c.stp"]

    def test_returns_empty_zip_for_empty_execution(self, tmp_artifacts: Path):
        execution_id, _ = artifact_service.create_execution_dir("aero-z", 12)

        zip_path = artifact_service.zip_execution(12, execution_id)

        import zipfile

        with zipfile.ZipFile(zip_path) as zf:
            assert zf.namelist() == []

    def test_zips_template_execution(self, tmp_artifacts: Path):
        execution_id, exec_dir = artifact_service.create_template_execution_dir(33)
        (exec_dir / "out.stl").write_bytes(b"X")

        zip_path = artifact_service.zip_execution(33, execution_id)

        import zipfile

        with zipfile.ZipFile(zip_path) as zf:
            assert zf.namelist() == ["out.stl"]

    def test_raises_not_found_for_unknown_execution(self, tmp_artifacts: Path):
        from app.core.exceptions import NotFoundError

        with pytest.raises(NotFoundError):
            artifact_service.zip_execution(99, "doesnotexist")
