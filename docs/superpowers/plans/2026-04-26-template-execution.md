# Template Execution Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Allow Construction Templates to be executed for testing, with generated files treated as ephemeral (downloadable individually or as zip, replaced on next run).

**Architecture:** Remove the execute-guards in `construction_plan_service.execute_plan` / `execute_plan_streaming`; route template runs to a dedicated `<ARTIFACTS_BASE_DIR>/_template_runs/<template_id>/<exec_id>/` tree with replace-on-next-run lifecycle; reuse existing artifact endpoints transparently via a resolver fallback; add a `/zip` download endpoint; extend `ExecutionResultDialog` with a Generated-files section.

**Tech Stack:** FastAPI, SQLAlchemy, pytest, Next.js 16 + React 19, vitest, SWR.

**Spec:** [`docs/superpowers/specs/2026-04-26-template-execution-design.md`](../specs/2026-04-26-template-execution-design.md) (commit `caaef54`).

**GH Issue:** [#339](https://github.com/szymansk/da3Dalus/issues/339)

**Branch:** `feat/gh-339-template-execution`

---

## File Map

| File | Role | Change |
|---|---|---|
| `app/services/artifact_service.py` | artifact dir lifecycle, file ops | + `create_template_execution_dir`; modify `_resolve_execution_dir` (fallback for `_template_runs`); + `zip_execution` |
| `app/services/construction_plan_service.py` | execute orchestration | remove guards (L603–606, L716–718), branch on `plan_type`, require `aeroplane_id` for templates |
| `app/api/v2/endpoints/construction_plans.py` | REST surface | + `GET /construction-plans/{plan_id}/artifacts/{execution_id}/zip` |
| `app/tests/test_artifact_service.py` | unit tests for artifact_service | NEW file — exercises new helpers |
| `app/tests/test_construction_plans.py` | integration tests via TestClient | + tests for template execute, zip download, plan-path-unchanged regression |
| `frontend/hooks/useConstructionPlans.ts` | SWR hooks + URL helpers | + `executionZipUrl(planId, executionId)` helper |
| `frontend/components/workbench/construction-plans/ExecutionResultDialog.tsx` | post-execution result UI | + Generated-files section (file list + zip button) |
| `frontend/__tests__/ExecutionResultDialog.test.tsx` | unit tests for the dialog | NEW file — exercises files section |

---

## Pre-flight: Branch + Worktree

- [ ] **Step 0.1: Create branch off main**

```bash
git checkout main
git pull github main
git checkout -b feat/gh-339-template-execution
```

- [ ] **Step 0.2: Verify clean baseline**

```bash
poetry run pytest app/tests/test_construction_plans.py -x -q
```

Expected: all tests pass (regression baseline). If any are already failing, stop and investigate before starting.

---

## Task 1: artifact_service — `create_template_execution_dir` (TDD)

**Files:**
- Test: `app/tests/test_artifact_service.py` (new)
- Modify: `app/services/artifact_service.py`

- [ ] **Step 1.1: Write failing test**

Create `app/tests/test_artifact_service.py`:

```python
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
```

- [ ] **Step 1.2: Run tests — expect FAIL**

```bash
poetry run pytest app/tests/test_artifact_service.py -x -q
```

Expected: `AttributeError: module 'app.services.artifact_service' has no attribute 'create_template_execution_dir'`.

- [ ] **Step 1.3: Implement `create_template_execution_dir`**

Add to `app/services/artifact_service.py` (just below `create_execution_dir`):

```python
TEMPLATE_RUNS_PREFIX = "_template_runs"


def create_template_execution_dir(template_id: int) -> tuple[str, Path]:
    """Create a fresh artifact directory for a template execution.

    Wipes any previous execution under <base>/_template_runs/<template_id>/
    so at most one template execution exists per template at any time.
    Returns (execution_id, absolute_path).
    """
    import shutil

    base = settings.ARTIFACTS_BASE_DIR
    template_root = _ensure_within_base(base / TEMPLATE_RUNS_PREFIX / str(template_id))
    if template_root.exists():
        try:
            shutil.rmtree(template_root)
        except OSError as exc:
            logger.exception("Failed to wipe template run dir %s", template_root)
            raise InternalError(
                message=f"Cannot reset template run directory: {exc}"
            ) from exc

    execution_id = new_execution_id()
    abs_path = _ensure_within_base(template_root / execution_id)
    try:
        abs_path.mkdir(parents=True, exist_ok=True)
    except OSError as exc:
        logger.exception("Failed to create template artifact dir %s", abs_path)
        raise InternalError(
            message=f"Cannot create template artifact directory: {exc}"
        ) from exc
    logger.info("Created template artifact dir: %s", abs_path)
    return execution_id, abs_path
```

Note: `_ensure_within_base` requires the path to exist for `.resolve()` containment. It does. The wipe runs *before* the new path is constructed, so the existence check at construction time is fine.

Note: import `shutil` inside the function to avoid adding a top-level import for a single-use call (consistent with how `delete_execution` already does it on line 151).

- [ ] **Step 1.4: Run tests — expect PASS**

```bash
poetry run pytest app/tests/test_artifact_service.py -x -q
```

Expected: 3 passed.

- [ ] **Step 1.5: Commit**

```bash
git add app/services/artifact_service.py app/tests/test_artifact_service.py
git commit -m "feat(gh-339): add create_template_execution_dir with replace-on-next-run"
```

---

## Task 2: artifact_service — resolver fallback for template runs (TDD)

**Files:**
- Test: `app/tests/test_artifact_service.py` (extend)
- Modify: `app/services/artifact_service.py` (`_resolve_execution_dir`)

- [ ] **Step 2.1: Add failing tests**

Append to `app/tests/test_artifact_service.py`:

```python
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

    def test_plan_takes_precedence_over_template_when_id_collides(
        self, tmp_artifacts: Path
    ):
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
```

- [ ] **Step 2.2: Run new tests — expect FAIL**

```bash
poetry run pytest app/tests/test_artifact_service.py::TestResolveExecutionDir -x -q
```

Expected: `test_resolves_template_execution_dir` fails with `NotFoundError` (resolver doesn't search `_template_runs/`).

- [ ] **Step 2.3: Modify `_resolve_execution_dir`**

In `app/services/artifact_service.py`, replace the existing `_resolve_execution_dir` (currently lines 162–171) with:

```python
def _resolve_execution_dir(plan_id: int, execution_id: str) -> Path:
    """Find and validate the execution directory for plan_id/execution_id.

    Searches first under <base>/<aero_id>/<plan_id>/<exec_id> (plan
    executions). If not found, falls back to
    <base>/_template_runs/<plan_id>/<exec_id> (template executions).
    """
    base = settings.ARTIFACTS_BASE_DIR
    if not base.exists():
        raise NotFoundError(message="No artifacts base directory")

    # 1) Search per-aeroplane plan execution dirs
    for aero_dir in base.iterdir():
        if not aero_dir.is_dir() or aero_dir.name == TEMPLATE_RUNS_PREFIX:
            continue
        candidate = aero_dir / str(plan_id) / execution_id
        if candidate.is_dir():
            return _ensure_within_base(candidate)

    # 2) Fall back to template runs
    tpl_candidate = base / TEMPLATE_RUNS_PREFIX / str(plan_id) / execution_id
    if tpl_candidate.is_dir():
        return _ensure_within_base(tpl_candidate)

    raise NotFoundError(message=f"Execution {execution_id} not found for plan {plan_id}")
```

Note: the `aero_dir.name == TEMPLATE_RUNS_PREFIX` guard is defensive — without it, `_template_runs` would be iterated as if it were an aeroplane id, and `_template_runs/<plan_id>/<exec_id>` would coincidentally match. The fallback path is explicit and clearer.

- [ ] **Step 2.4: Run all artifact_service tests — expect PASS**

```bash
poetry run pytest app/tests/test_artifact_service.py -x -q
```

Expected: 7 passed.

- [ ] **Step 2.5: Commit**

```bash
git add app/services/artifact_service.py app/tests/test_artifact_service.py
git commit -m "feat(gh-339): _resolve_execution_dir falls back to template runs"
```

---

## Task 3: artifact_service — `zip_execution` (TDD)

**Files:**
- Test: `app/tests/test_artifact_service.py` (extend)
- Modify: `app/services/artifact_service.py`

- [ ] **Step 3.1: Add failing tests**

Append to `app/tests/test_artifact_service.py`:

```python
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
```

- [ ] **Step 3.2: Run new tests — expect FAIL**

```bash
poetry run pytest app/tests/test_artifact_service.py::TestZipExecution -x -q
```

Expected: `AttributeError: module 'app.services.artifact_service' has no attribute 'zip_execution'`.

- [ ] **Step 3.3: Implement `zip_execution`**

Append to `app/services/artifact_service.py`:

```python
def zip_execution(plan_id: int, execution_id: str) -> Path:
    """Zip an entire execution directory and return the path to the zip file.

    The zip is written to a temp file (auto-cleaned by the OS / next
    template run). Empty executions yield a valid empty zip (200 OK
    semantics, not a 404).
    """
    import tempfile
    import zipfile

    exec_dir = _resolve_execution_dir(plan_id, execution_id)

    fd, tmp_name = tempfile.mkstemp(prefix=f"plan{plan_id}-{execution_id}-", suffix=".zip")
    import os as _os
    _os.close(fd)  # we re-open via zipfile
    zip_path = Path(tmp_name)

    try:
        with zipfile.ZipFile(zip_path, "w", zipfile.ZIP_DEFLATED) as zf:
            for file_path in sorted(exec_dir.rglob("*")):
                if not file_path.is_file():
                    continue
                arcname = file_path.relative_to(exec_dir).as_posix()
                zf.write(file_path, arcname=arcname)
    except OSError as exc:
        logger.exception("Failed to build zip for execution %s/%s", plan_id, execution_id)
        zip_path.unlink(missing_ok=True)
        raise InternalError(message=f"Cannot build zip: {exc}") from exc

    return zip_path
```

- [ ] **Step 3.4: Run new tests — expect PASS**

```bash
poetry run pytest app/tests/test_artifact_service.py -x -q
```

Expected: 11 passed.

- [ ] **Step 3.5: Commit**

```bash
git add app/services/artifact_service.py app/tests/test_artifact_service.py
git commit -m "feat(gh-339): add zip_execution streaming archive of artifact dir"
```

---

## Task 4: REST endpoint — zip download (TDD via TestClient)

**Files:**
- Test: `app/tests/test_construction_plans.py` (extend)
- Modify: `app/api/v2/endpoints/construction_plans.py`

- [ ] **Step 4.1: Add failing test**

Append to `app/tests/test_construction_plans.py` near the artifact-browser tests (or at the end of the file inside a new class):

```python
class TestZipDownload:
    """GH#339 — zip download endpoint for an execution dir."""

    def test_zip_endpoint_returns_zip_with_all_files(
        self, client, tmp_path, monkeypatch
    ):
        from app.core.config import settings
        from app.services import artifact_service

        monkeypatch.setattr(settings, "ARTIFACTS_BASE_DIR", tmp_path)
        execution_id, exec_dir = artifact_service.create_execution_dir(
            "aero-zipper", 501
        )
        (exec_dir / "alpha.stl").write_bytes(b"AAA")
        (exec_dir / "beta.txt").write_text("bb")

        resp = client.get(
            f"/construction-plans/501/artifacts/{execution_id}/zip"
        )

        assert resp.status_code == 200
        assert resp.headers["content-type"] == "application/zip"
        assert "attachment" in resp.headers.get("content-disposition", "")

        import io
        import zipfile
        with zipfile.ZipFile(io.BytesIO(resp.content)) as zf:
            assert sorted(zf.namelist()) == ["alpha.stl", "beta.txt"]

    def test_zip_endpoint_404_for_missing_execution(self, client, tmp_path, monkeypatch):
        from app.core.config import settings

        monkeypatch.setattr(settings, "ARTIFACTS_BASE_DIR", tmp_path)
        tmp_path.mkdir(exist_ok=True)

        resp = client.get("/construction-plans/9999/artifacts/missing/zip")
        assert resp.status_code == 404

    def test_zip_endpoint_returns_empty_zip_for_empty_execution(
        self, client, tmp_path, monkeypatch
    ):
        from app.core.config import settings
        from app.services import artifact_service

        monkeypatch.setattr(settings, "ARTIFACTS_BASE_DIR", tmp_path)
        execution_id, _ = artifact_service.create_execution_dir("aero-empty", 502)

        resp = client.get(
            f"/construction-plans/502/artifacts/{execution_id}/zip"
        )

        assert resp.status_code == 200
        assert resp.headers["content-type"] == "application/zip"
        import io
        import zipfile
        with zipfile.ZipFile(io.BytesIO(resp.content)) as zf:
            assert zf.namelist() == []
```

- [ ] **Step 4.2: Run new tests — expect FAIL**

```bash
poetry run pytest app/tests/test_construction_plans.py::TestZipDownload -x -q
```

Expected: 404 for the success case (route not registered).

- [ ] **Step 4.3: Add the endpoint**

Append to `app/api/v2/endpoints/construction_plans.py` (just after `delete_execution`):

```python
@router.get(
    "/construction-plans/{plan_id}/artifacts/{execution_id}/zip",
    tags=["construction-plans"],
    operation_id="download_execution_zip",
)
async def download_execution_zip(
    plan_id: Annotated[int, Path(...)],
    execution_id: Annotated[str, Path(...)],
):
    """Download all artifact files of an execution as a single zip."""
    from fastapi.responses import FileResponse

    try:
        zip_path = artifact_service.zip_execution(plan_id, execution_id)
        filename = f"plan-{plan_id}-{execution_id}.zip"
        return FileResponse(
            zip_path,
            media_type="application/zip",
            filename=filename,
        )
    except ServiceException as exc:
        _handle_service_error(exc)
```

Note: this route MUST be defined **before** the broader
`/construction-plans/{plan_id}/artifacts/{execution_id}/{filename:path}`
download route (line 208 in the existing file), otherwise the path
parameter `{filename:path}` would consume `zip` as a filename and
the new endpoint would never match. Insert it **above** the
`download_artifact_file` function definition.

- [ ] **Step 4.4: Run all construction_plans tests — expect PASS**

```bash
poetry run pytest app/tests/test_construction_plans.py -x -q
```

Expected: all pass (including the new TestZipDownload class).

- [ ] **Step 4.5: Commit**

```bash
git add app/api/v2/endpoints/construction_plans.py app/tests/test_construction_plans.py
git commit -m "feat(gh-339): add /artifacts/{exec_id}/zip download endpoint"
```

---

## Task 5: Backend — remove guards + branch on plan_type (TDD)

**Files:**
- Test: `app/tests/test_construction_plans.py` (extend)
- Modify: `app/services/construction_plan_service.py`

- [ ] **Step 5.1: Add failing tests for template execution**

Append to `app/tests/test_construction_plans.py`:

```python
class TestTemplateExecution:
    """GH#339 — templates can be executed against a chosen aeroplane."""

    @pytest.mark.skipif(not _can_import_cad(), reason="cadquery not available")
    def test_execute_template_returns_success(
        self, client, client_and_db, tmp_path, monkeypatch
    ):
        from app.core.config import settings

        monkeypatch.setattr(settings, "ARTIFACTS_BASE_DIR", tmp_path)
        _, SessionLocal = client_and_db
        from app.tests.conftest import make_aeroplane

        with SessionLocal() as session:
            aero = make_aeroplane(session, name="for-tpl-exec")
            aero_id = str(aero.uuid)

        # Create a template (plan_type defaults to "template" in helper)
        template = _create_plan(client, "Tpl A", tree=SAMPLE_TREE, plan_type="template")

        resp = client.post(
            f"/construction-plans/{template['id']}/execute",
            json={"aeroplane_id": aero_id},
        )

        assert resp.status_code == 200, resp.text
        body = resp.json()
        assert body["status"] in ("success", "error"), body  # decode may vary
        # Critical: no longer a 422 with "Templates cannot be executed"

    def test_execute_template_without_aeroplane_id_returns_422(self, client):
        template = _create_plan(client, "Tpl B", tree=SAMPLE_TREE, plan_type="template")

        resp = client.post(
            f"/construction-plans/{template['id']}/execute",
            json={},
        )

        assert resp.status_code == 422
        assert "aeroplane_id" in resp.json()["detail"].lower()

    @pytest.mark.skipif(not _can_import_cad(), reason="cadquery not available")
    def test_template_execution_replaces_previous_run(
        self, client, client_and_db, tmp_path, monkeypatch
    ):
        from app.core.config import settings

        monkeypatch.setattr(settings, "ARTIFACTS_BASE_DIR", tmp_path)
        _, SessionLocal = client_and_db
        from app.tests.conftest import make_aeroplane

        with SessionLocal() as session:
            aero = make_aeroplane(session, name="for-replace")
            aero_id = str(aero.uuid)

        template = _create_plan(client, "Tpl C", tree=SAMPLE_TREE, plan_type="template")

        # First execute
        resp1 = client.post(
            f"/construction-plans/{template['id']}/execute",
            json={"aeroplane_id": aero_id},
        )
        assert resp1.status_code == 200
        first_exec_id = resp1.json()["execution_id"]

        # Second execute
        resp2 = client.post(
            f"/construction-plans/{template['id']}/execute",
            json={"aeroplane_id": aero_id},
        )
        assert resp2.status_code == 200
        second_exec_id = resp2.json()["execution_id"]

        assert first_exec_id != second_exec_id
        # First execution dir is gone
        first_dir = tmp_path / "_template_runs" / str(template["id"]) / first_exec_id
        assert not first_dir.exists()
        # Second execution dir exists
        second_dir = tmp_path / "_template_runs" / str(template["id"]) / second_exec_id
        assert second_dir.is_dir()


class TestPlanExecutionPathRegression:
    """Plan executions still write to <aero>/<plan>/<exec> (gh#339)."""

    @pytest.mark.skipif(not _can_import_cad(), reason="cadquery not available")
    def test_plan_execution_path_unchanged(
        self, client, client_and_db, tmp_path, monkeypatch
    ):
        from app.core.config import settings

        monkeypatch.setattr(settings, "ARTIFACTS_BASE_DIR", tmp_path)
        _, SessionLocal = client_and_db
        from app.tests.conftest import make_aeroplane

        with SessionLocal() as session:
            aero = make_aeroplane(session, name="for-plan")
            aero_id = str(aero.uuid)

        plan = _create_plan(
            client, "Real Plan", tree=SAMPLE_TREE,
            plan_type="plan", aeroplane_id=aero_id,
        )

        resp = client.post(
            f"/construction-plans/{plan['id']}/execute",
            json={"aeroplane_id": aero_id},
        )
        assert resp.status_code == 200
        exec_id = resp.json()["execution_id"]

        # Plan dir under aeroplane root, NOT under _template_runs
        plan_dir = tmp_path / aero_id / str(plan["id"]) / exec_id
        assert plan_dir.is_dir()
        assert not (tmp_path / "_template_runs" / str(plan["id"])).exists()
```

- [ ] **Step 5.2: Run the new failing tests — expect FAIL**

```bash
poetry run pytest app/tests/test_construction_plans.py::TestTemplateExecution -x -q
```

Expected: `test_execute_template_returns_success` returns 422 with the existing guard message.

- [ ] **Step 5.3: Remove guards + branch in `execute_plan`**

In `app/services/construction_plan_service.py`, replace lines 601–613 (the `# Load plan` block through `create_execution_dir`) with:

```python
    # Load plan
    plan = _get_plan_or_raise(db, plan_id)

    # Resolve aeroplane: prefer stored aeroplane_id (real plans), fall back
    # to request (templates require it explicitly).
    effective_aeroplane_id = plan.aeroplane_id or request.aeroplane_id
    if plan.plan_type == "template" and not effective_aeroplane_id:
        raise ValidationError(
            message="aeroplane_id required for template execution"
        )
    aeroplane = get_aeroplane_or_raise(db, effective_aeroplane_id)

    # Create artifact directory: templates go to a dedicated _template_runs
    # tree with replace-on-next-run; plans go under <aeroplane>/<plan>/.
    if plan.plan_type == "template":
        execution_id, artifact_dir = artifact_service.create_template_execution_dir(plan_id)
    else:
        execution_id, artifact_dir = create_execution_dir(effective_aeroplane_id, plan_id)
```

Add the import at the top of the function (next to the existing `from app.services.artifact_service import create_execution_dir` on line 598):

```python
    from app.services import artifact_service
```

(Or replace the existing line with `from app.services import artifact_service` and use `artifact_service.create_execution_dir(...)` everywhere — pick whichever is cleaner.)

- [ ] **Step 5.4: Same change in `execute_plan_streaming`**

Replace lines 712–736 (`# Load plan — wrap setup` through `create_execution_dir`) with:

```python
    # Load plan — wrap setup in try/except to yield SSE errors instead of crashing
    try:
        plan = _get_plan_or_raise(db, plan_id)
    except (NotFoundError, ValidationError) as exc:
        yield f"event: error\ndata: {json.dumps({'error': str(exc)})}\n\n"
        return

    effective_aeroplane_id = plan.aeroplane_id or request.aeroplane_id
    if plan.plan_type == "template" and not effective_aeroplane_id:
        yield f"event: error\ndata: {json.dumps({'error': 'aeroplane_id required for template execution'})}\n\n"
        return

    try:
        aeroplane = get_aeroplane_or_raise(db, effective_aeroplane_id)
    except NotFoundError as exc:
        yield f"event: error\ndata: {json.dumps({'error': str(exc)})}\n\n"
        return

    wing_config: dict = {}
    for wing in aeroplane.wings:
        try:
            wc = wing_model_to_wing_config(wing, scale=1000.0)
            wing_config[wing.name] = wc
        except Exception as exc:
            logger.warning("Failed to convert wing '%s': %s", wing.name, exc)

    printer_settings = _load_printer_settings(db)

    # Templates: replace-on-next-run; plans: per-aeroplane persistent.
    if plan.plan_type == "template":
        execution_id, artifact_dir = artifact_service.create_template_execution_dir(plan_id)
    else:
        execution_id, artifact_dir = create_execution_dir(effective_aeroplane_id, plan_id)
```

(Match the import strategy from step 5.3 — either `from app.services import artifact_service` at the top of the streaming function, or use the module-level alias.)

- [ ] **Step 5.5: Run all backend tests — expect PASS**

```bash
poetry run pytest app/tests/test_construction_plans.py -x -q
poetry run pytest app/tests/test_artifact_service.py -x -q
```

Expected: all pass. Note: `test_execute_template_returns_success` and `_replaces_previous_run` are skipped on `linux/aarch64` (no cadquery). On dev machine they should pass.

- [ ] **Step 5.6: Commit**

```bash
git add app/services/construction_plan_service.py app/tests/test_construction_plans.py
git commit -m "feat(gh-339): allow template execution with ephemeral artifacts

Removes the execute-guards in execute_plan / execute_plan_streaming,
branches on plan_type to route template runs to _template_runs/<id>/
with replace-on-next-run lifecycle. Plans are unchanged."
```

---

## Task 6: Frontend — `executionZipUrl` helper (TDD lite)

**Files:**
- Modify: `frontend/hooks/useConstructionPlans.ts`

- [ ] **Step 6.1: Add the helper**

Append to `frontend/hooks/useConstructionPlans.ts` (next to `artifactDownloadUrl`):

```ts
export function executionZipUrl(planId: number, executionId: string): string {
  return `${API_BASE}/construction-plans/${planId}/artifacts/${encodeURIComponent(executionId)}/zip`;
}
```

- [ ] **Step 6.2: Type-check**

```bash
cd frontend && npx tsc --noEmit
```

Expected: no errors.

- [ ] **Step 6.3: Commit**

```bash
git add frontend/hooks/useConstructionPlans.ts
git commit -m "feat(gh-339): add executionZipUrl helper for download-all-zip button"
```

---

## Task 7: Frontend — Generated files section in ExecutionResultDialog (TDD)

**Files:**
- Test: `frontend/__tests__/ExecutionResultDialog.test.tsx` (new)
- Modify: `frontend/components/workbench/construction-plans/ExecutionResultDialog.tsx`

- [ ] **Step 7.1: Add `planId` + `executionId` props to the dialog**

Modify the props interface in `ExecutionResultDialog.tsx`:

```ts
interface ExecutionResultDialogProps {
  open: boolean;
  title: string;
  /** Pre-computed result (non-streaming mode). */
  result?: ExecutionResult | null;
  /** SSE URL for streaming mode. When set, streams shapes incrementally. */
  streamUrl?: string | null;
  /** Plan/template id for the artifact endpoints. */
  planId?: number | null;
  /** Execution id (resolved from result or streamed 'complete' event). */
  executionId?: string | null;
  onClose: () => void;
}
```

In the component, accept the new props and (for streaming) capture `execution_id` from the `complete` SSE event into local state. For non-streaming, derive `executionId` from `preResult?.execution_id`. Compute the effective execution id:

```ts
const [streamedExecutionId, setStreamedExecutionId] = useState<string | null>(null);

// inside the "complete" SSE handler, after JSON.parse(e.data):
if (data.execution_id) setStreamedExecutionId(data.execution_id);

// near the existing effective* derivations:
const effectiveExecutionId = isStreaming
  ? streamedExecutionId
  : (preResult?.execution_id ?? executionId ?? null);
```

- [ ] **Step 7.2: Write failing test**

Create `frontend/__tests__/ExecutionResultDialog.test.tsx`:

```tsx
import { describe, it, expect, vi, beforeEach } from "vitest";
import { render, screen, waitFor } from "@testing-library/react";
import "@testing-library/jest-dom/vitest";
import { ExecutionResultDialog } from "@/components/workbench/construction-plans/ExecutionResultDialog";

// Mock useArtifactFiles so the dialog can render without a real backend.
vi.mock("@/hooks/useConstructionPlans", async () => {
  const actual = await vi.importActual<typeof import("@/hooks/useConstructionPlans")>(
    "@/hooks/useConstructionPlans",
  );
  return {
    ...actual,
    useArtifactFiles: vi.fn(),
  };
});

import { useArtifactFiles } from "@/hooks/useConstructionPlans";

describe("ExecutionResultDialog — Generated files section", () => {
  beforeEach(() => {
    vi.mocked(useArtifactFiles).mockReset();
  });

  it("renders the file list when files are returned", async () => {
    vi.mocked(useArtifactFiles).mockReturnValue({
      files: [
        { name: "wing.stl", is_dir: false, size_bytes: 1024, modified: "" },
        { name: "fuselage.stp", is_dir: false, size_bytes: 2048, modified: "" },
      ],
      error: null,
      isLoading: false,
      mutate: vi.fn(),
    } as unknown as ReturnType<typeof useArtifactFiles>);

    render(
      <ExecutionResultDialog
        open
        title="Test"
        planId={42}
        result={{
          status: "success",
          shape_keys: [],
          duration_ms: 100,
          tessellation: null,
          artifact_dir: "/tmp/x",
          execution_id: "exec-1",
        }}
        onClose={() => {}}
      />,
    );

    await waitFor(() => {
      expect(screen.getByText("wing.stl")).toBeInTheDocument();
      expect(screen.getByText("fuselage.stp")).toBeInTheDocument();
    });
  });

  it("renders an empty state when no files were generated", async () => {
    vi.mocked(useArtifactFiles).mockReturnValue({
      files: [],
      error: null,
      isLoading: false,
      mutate: vi.fn(),
    } as unknown as ReturnType<typeof useArtifactFiles>);

    render(
      <ExecutionResultDialog
        open
        title="Test"
        planId={42}
        result={{
          status: "success",
          shape_keys: [],
          duration_ms: 100,
          tessellation: null,
          artifact_dir: "/tmp/x",
          execution_id: "exec-1",
        }}
        onClose={() => {}}
      />,
    );

    await waitFor(() => {
      expect(screen.getByText(/no files generated/i)).toBeInTheDocument();
    });
  });

  it("renders a Download zip button with the correct URL", async () => {
    vi.mocked(useArtifactFiles).mockReturnValue({
      files: [{ name: "a.stl", is_dir: false, size_bytes: 4, modified: "" }],
      error: null,
      isLoading: false,
      mutate: vi.fn(),
    } as unknown as ReturnType<typeof useArtifactFiles>);

    render(
      <ExecutionResultDialog
        open
        title="Test"
        planId={42}
        result={{
          status: "success",
          shape_keys: [],
          duration_ms: 100,
          tessellation: null,
          artifact_dir: "/tmp/x",
          execution_id: "exec-99",
        }}
        onClose={() => {}}
      />,
    );

    const zipLink = await screen.findByRole("link", { name: /download zip/i });
    expect(zipLink).toHaveAttribute(
      "href",
      expect.stringContaining("/construction-plans/42/artifacts/exec-99/zip"),
    );
  });
});
```

- [ ] **Step 7.3: Run new test — expect FAIL**

```bash
cd frontend && npm run test:unit -- ExecutionResultDialog
```

Expected: tests fail (no Generated-files section rendered).

- [ ] **Step 7.4: Implement the Generated-files section**

In `ExecutionResultDialog.tsx`:

1. Add imports at the top:

```ts
import { useArtifactFiles, artifactDownloadUrl, executionZipUrl } from "@/hooks/useConstructionPlans";
```

2. After the existing CadViewer body block (just before the closing `</div>` of the body container around line 177), insert:

```tsx
{effectiveStatus === "success" && (
  <GeneratedFilesSection
    planId={planId ?? null}
    executionId={effectiveExecutionId}
  />
)}
```

3. Add a small subcomponent at the bottom of the file (inside the same module):

```tsx
function GeneratedFilesSection({
  planId,
  executionId,
}: Readonly<{ planId: number | null; executionId: string | null }>) {
  const { files, isLoading } = useArtifactFiles(planId, executionId);

  if (planId == null || executionId == null) return null;

  return (
    <div className="border-t border-border px-6 py-4">
      <div className="mb-2 flex items-center gap-3">
        <span className="font-[family-name:var(--font-jetbrains-mono)] text-[12px] text-muted-foreground">
          Generated files
        </span>
        <span className="flex-1" />
        {files.length > 0 && (
          <a
            href={executionZipUrl(planId, executionId)}
            className="font-[family-name:var(--font-jetbrains-mono)] text-[11px] text-primary hover:underline"
            download
          >
            Download zip
          </a>
        )}
      </div>
      {isLoading ? (
        <p className="text-[12px] text-muted-foreground">Loading files…</p>
      ) : files.length === 0 ? (
        <p className="text-[12px] text-muted-foreground">No files generated.</p>
      ) : (
        <ul className="flex max-h-32 flex-col gap-1 overflow-y-auto">
          {files
            .filter((f) => !f.is_dir)
            .map((f) => (
              <li key={f.name} className="flex items-center gap-2 text-[12px]">
                <a
                  href={artifactDownloadUrl(planId, executionId, f.name)}
                  className="text-primary hover:underline"
                  download
                >
                  {f.name}
                </a>
                <span className="text-muted-foreground">
                  ({Math.max(1, Math.round(f.size_bytes / 1024))} KB)
                </span>
              </li>
            ))}
        </ul>
      )}
    </div>
  );
}
```

- [ ] **Step 7.5: Run tests — expect PASS**

```bash
cd frontend && npm run test:unit -- ExecutionResultDialog
```

Expected: 3 passed.

- [ ] **Step 7.6: Commit**

```bash
git add frontend/components/workbench/construction-plans/ExecutionResultDialog.tsx frontend/__tests__/ExecutionResultDialog.test.tsx
git commit -m "feat(gh-339): add Generated files section with individual + zip download"
```

---

## Task 8: Wire `planId` into ExecutionResultDialog at call sites

**Files:**
- Modify: `frontend/app/workbench/construction-plans/page.tsx`

- [ ] **Step 8.1: Pass `planId` prop**

Find every `<ExecutionResultDialog ...>` usage in `page.tsx` and add `planId={...}`. Use the appropriate id depending on context:
- For template runs: `planId={executeTemplateId ?? undefined}` (or whichever state holds the template id at the time of execution)
- For plan runs: `planId={selectedPlanId ?? undefined}`

```bash
grep -n "ExecutionResultDialog" frontend/app/workbench/construction-plans/page.tsx
```

Update each call site so the dialog has the id of the plan/template whose execution is being shown.

- [ ] **Step 8.2: Verify type-check + tests**

```bash
cd frontend && npx tsc --noEmit && npm run test:unit -- ExecutionResultDialog
```

Expected: no type errors, tests still pass.

- [ ] **Step 8.3: Commit**

```bash
git add frontend/app/workbench/construction-plans/page.tsx
git commit -m "feat(gh-339): pass planId to ExecutionResultDialog at call sites"
```

---

## Task 9: Manual smoke + lint + final regression

- [ ] **Step 9.1: Run full backend test suite**

```bash
poetry run pytest -x -q
```

Expected: all pass (or skipped on platform).

- [ ] **Step 9.2: Run lint**

```bash
poetry run ruff check .
poetry run ruff format --check .
```

Expected: clean (or autoformat any drift).

- [ ] **Step 9.3: Run frontend unit + dep checks**

```bash
cd frontend && npm run test:unit && npm run deps:check
```

Expected: all pass.

- [ ] **Step 9.4: Browser smoke test (per CLAUDE.md "UI changes" rule)**

```bash
# In one terminal
poetry run uvicorn app.main:app --host 0.0.0.0 --port 8001 --reload

# In another terminal
cd frontend && npm run dev
```

Then in the browser:
1. Open the Construction Plans workbench
2. Switch to **Template** mode
3. Pick a template, click Play, choose an aeroplane
4. After execution, verify:
   - Result dialog opens
   - "Generated files" section lists files
   - Individual file download works
   - "Download zip" link downloads a valid zip
5. Run again on the same template — verify the previous execution dir on disk (`<ARTIFACTS_BASE_DIR>/_template_runs/<id>/`) is gone, only the new one exists
6. Switch to **Plan** mode and execute a plan to confirm Plan flow is unchanged

If any step fails, fix the bug and add a regression test before continuing.

- [ ] **Step 9.5: Push branch + open PR**

```bash
git push github feat/gh-339-template-execution
gh pr create --title "feat(gh-339): enable template execution with ephemeral, downloadable artifacts" --body "$(cat <<'EOF'
## Summary
- Removes execute-guards in `execute_plan` / `execute_plan_streaming` (was: `ValidationError("Templates cannot be executed.")`).
- Routes template runs to `<ARTIFACTS_BASE_DIR>/_template_runs/<template_id>/<exec_id>/` with replace-on-next-run lifecycle.
- Adds `GET /construction-plans/{plan_id}/artifacts/{execution_id}/zip` for zip-all download.
- Extends `ExecutionResultDialog` with a Generated-files section (individual download + zip).
- Plan executions are unchanged (regression test included).

Spec: `docs/superpowers/specs/2026-04-26-template-execution-design.md`
Plan: `docs/superpowers/plans/2026-04-26-template-execution.md`

Closes #339

## Test plan
- [x] Backend unit tests for artifact_service helpers
- [x] Backend integration tests for template execute, zip download, plan-path-unchanged
- [x] Frontend unit tests for the Generated-files section
- [x] Manual smoke: template Play → file list → individual + zip download
- [x] Manual smoke: replace-on-next-run wipes previous template execution dir
- [x] Manual smoke: plan execution path unchanged

🤖 Generated with [Claude Code](https://claude.com/claude-code)
EOF
)"
```

---

## Self-Review

**Spec coverage:**
- Remove guard in `execute_plan` → Task 5
- Remove guard in `execute_plan_streaming` → Task 5
- New `_template_runs/<id>/<exec_id>/` path → Task 1
- Replace-on-next-run wipe → Task 1 (test covers it)
- `_resolve_execution_dir` fallback → Task 2
- Require `aeroplane_id` for template → Task 5 (test covers 422)
- New zip endpoint → Tasks 3 + 4
- ExecutionResultDialog Generated files section → Task 7
- Empty zip for empty exec → Tasks 3 + 4 (tests cover)
- Path-traversal still rejected → existing `_ensure_within_base` reused everywhere
- Plan path unchanged → Task 5 regression test

**Placeholder scan:** No "TBD", no "implement later", every code step has actual code. The single "(Or replace … pick whichever is cleaner.)" in Task 5.3 is a deliberate stylistic choice for the implementer; both options are concrete and complete.

**Type consistency:** `executionZipUrl(planId, executionId)` is defined in Task 6 with two args (number, string), used in Task 7 with the same signature. `useArtifactFiles(planId, executionId)` matches the existing hook signature. `artifactDownloadUrl(planId, executionId, filename)` matches existing. `create_template_execution_dir(template_id)` returns `(str, Path)` consistent with `create_execution_dir`. Function names are consistent across tasks (`create_template_execution_dir`, `zip_execution`, `_resolve_execution_dir`, `executionZipUrl`).

---

## Execution Handoff

Plan complete and saved to `docs/superpowers/plans/2026-04-26-template-execution.md`. Two execution options:

1. **Subagent-Driven (recommended)** — Dispatch a fresh subagent per task, review between tasks, fast iteration.
2. **Inline Execution** — Execute tasks in this session using executing-plans, batch execution with checkpoints.

**Which approach?**
