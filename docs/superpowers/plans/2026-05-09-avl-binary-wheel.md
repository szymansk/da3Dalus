# AVL Binary Platform Wheel — Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Package AVL binaries as platform-specific Python wheels so `poetry install` delivers a working binary on macOS arm64 and Linux x86_64 — eliminating worktree symlinks and enabling CI AVL tests.

**Architecture:** New top-level `avl-binary/` package exposes `avl_path() → Path`. Pre-built wheels are hosted as GitHub Release assets. The main project references them via direct URL dependencies with platform markers in `pyproject.toml`.

**Tech Stack:** Python wheel packaging (`build` module), Docker buildx (Linux binary extraction), GitHub Releases (hosting)

**Branch:** `chore/gh-458-avl-binary-wheel`
**Worktree:** `.worktrees/chore/gh-458-avl-binary-wheel`
**Remote:** `github` (not `origin`)

---

## File Map

| Action | File | Responsibility |
|--------|------|----------------|
| Create | `avl-binary/pyproject.toml` | Wheel metadata and build config |
| Create | `avl-binary/avl_binary/__init__.py` | Public API: `avl_path() → Path` |
| Create | `avl-binary/avl_binary/py.typed` | PEP 561 marker |
| Create | `avl-binary/avl_binary/bin/.gitkeep` | Placeholder for binary directory |
| Create | `avl-binary/build_wheels.py` | Script to build both platform wheels |
| Create | `avl-binary/tests/test_avl_binary.py` | Unit tests for avl_binary package |
| Modify | `pyproject.toml` | Add `avl-binary` URL dependency with platform markers |
| Modify | `app/services/avl_runner.py:17,72-96,108` | Replace `_resolve_avl_path()` with `avl_binary.avl_path()` |
| Modify | `app/tests/test_avl_runner.py:600-609` | Update default path assertion |
| Modify | `app/tests/test_avl_strip_forces_integration.py:1-9` | Use `avl_path()` instead of hardcoded path |
| Modify | `.claude/rules/worktree-setup.md` | Remove AVL symlink section |

---

### Task 1: Create `avl-binary` package with `avl_path()` API

**Files:**
- Create: `avl-binary/avl_binary/__init__.py`
- Create: `avl-binary/avl_binary/py.typed`
- Create: `avl-binary/avl_binary/bin/.gitkeep`
- Create: `avl-binary/pyproject.toml`
- Create: `avl-binary/tests/test_avl_binary.py`

- [ ] **Step 1: Write the failing test**

Create `avl-binary/tests/test_avl_binary.py`:

```python
from pathlib import Path

import pytest


def test_avl_path_returns_path_object():
    from avl_binary import avl_path

    result = avl_path()
    assert isinstance(result, Path)


def test_avl_path_points_to_bin_directory():
    from avl_binary import avl_path

    result = avl_path()
    assert result.parent.name == "bin"
    assert result.name == "avl"


def test_avl_path_raises_when_binary_missing(tmp_path, monkeypatch):
    import avl_binary

    monkeypatch.setattr(
        avl_binary, "__file__", str(tmp_path / "fake" / "__init__.py")
    )
    with pytest.raises(FileNotFoundError, match="AVL binary not found"):
        avl_binary.avl_path()
```

- [ ] **Step 2: Run tests to verify they fail**

Run: `cd avl-binary && python -m pytest tests/test_avl_binary.py -v`
Expected: FAIL — `ModuleNotFoundError: No module named 'avl_binary'`

- [ ] **Step 3: Create the package scaffolding**

Create `avl-binary/pyproject.toml`:

```toml
[project]
name = "avl-binary"
version = "1.0.0"
description = "Pre-compiled AVL (Athena Vortex Lattice) binary for da3Dalus"
requires-python = ">=3.11"

[build-system]
requires = ["setuptools>=75.0"]
build-backend = "setuptools.build_meta"

[tool.setuptools.package-data]
avl_binary = ["bin/*"]

[tool.pytest.ini_options]
pythonpath = ["."]
```

Create `avl-binary/avl_binary/__init__.py`:

```python
from pathlib import Path


def avl_path() -> Path:
    p = Path(__file__).parent / "bin" / "avl"
    if not p.exists():
        raise FileNotFoundError(
            f"AVL binary not found at {p}. "
            f"Is the correct platform wheel installed?"
        )
    return p
```

Create `avl-binary/avl_binary/py.typed` (empty file).

Create `avl-binary/avl_binary/bin/.gitkeep` (empty file).

- [ ] **Step 4: Copy the macOS binary into `bin/` for local testing**

```bash
cp exports/avl avl-binary/avl_binary/bin/avl
chmod +x avl-binary/avl_binary/bin/avl
```

Note: `avl-binary/avl_binary/bin/avl` must be gitignored — the actual
binary is distributed via wheels, not committed. Add to
`avl-binary/.gitignore`:

```
avl_binary/bin/avl
dist/
*.whl
```

- [ ] **Step 5: Run tests to verify they pass**

Run: `cd avl-binary && python -m pytest tests/test_avl_binary.py -v`
Expected: 3 passed

- [ ] **Step 6: Commit**

```bash
git add avl-binary/
git commit -m "feat(gh-458): create avl-binary package with avl_path() API"
```

---

### Task 2: Create the wheel build script

**Files:**
- Create: `avl-binary/build_wheels.py`

- [ ] **Step 1: Write the build script**

Create `avl-binary/build_wheels.py`:

```python
#!/usr/bin/env python3
"""Build platform-specific wheels for the avl-binary package.

Usage:
    python build_wheels.py --platform macos_arm64 --binary ../exports/avl
    python build_wheels.py --platform linux_x86_64 --binary ./avl_linux_x86_64

The script:
1. Copies the provided binary to avl_binary/bin/avl
2. Sets executable permissions
3. Builds a wheel via `python -m build`
4. Renames the wheel to the correct platform tag
5. Outputs to dist/
"""

import argparse
import shutil
import stat
import subprocess
import sys
from pathlib import Path

PLATFORM_TAGS = {
    "macos_arm64": "macosx_11_0_arm64",
    "linux_x86_64": "manylinux_2_17_x86_64.manylinux2014_x86_64",
}

PACKAGE_DIR = Path(__file__).parent
BIN_DIR = PACKAGE_DIR / "avl_binary" / "bin"
DIST_DIR = PACKAGE_DIR / "dist"


def build_wheel(platform: str, binary_path: Path) -> Path:
    target = BIN_DIR / "avl"
    shutil.copy2(binary_path, target)
    target.chmod(target.stat().st_mode | stat.S_IXUSR | stat.S_IXGRP | stat.S_IXOTH)

    DIST_DIR.mkdir(exist_ok=True)

    subprocess.run(
        [sys.executable, "-m", "build", "--wheel", "--outdir", str(DIST_DIR)],
        cwd=str(PACKAGE_DIR),
        check=True,
    )

    generic_wheel = next(DIST_DIR.glob("avl_binary-*.whl"))
    platform_tag = PLATFORM_TAGS[platform]
    parts = generic_wheel.stem.split("-")
    # Replace: name-version-pythontag-abitag-platformtag
    final_name = f"{parts[0]}-{parts[1]}-py3-none-{platform_tag}.whl"
    final_path = DIST_DIR / final_name
    generic_wheel.rename(final_path)

    target.unlink()

    print(f"Built: {final_path}")
    return final_path


def main() -> None:
    parser = argparse.ArgumentParser(description="Build avl-binary platform wheel")
    parser.add_argument(
        "--platform",
        required=True,
        choices=list(PLATFORM_TAGS.keys()),
    )
    parser.add_argument(
        "--binary",
        required=True,
        type=Path,
        help="Path to the AVL binary for this platform",
    )
    args = parser.parse_args()

    if not args.binary.exists():
        print(f"Error: binary not found at {args.binary}", file=sys.stderr)
        sys.exit(1)

    build_wheel(args.platform, args.binary)


if __name__ == "__main__":
    main()
```

- [ ] **Step 2: Verify the script runs for macOS**

```bash
cd avl-binary
python build_wheels.py --platform macos_arm64 --binary ../exports/avl
ls -la dist/*.whl
```

Expected: `dist/avl_binary-1.0.0-py3-none-macosx_11_0_arm64.whl` exists, ~1.6 MB

- [ ] **Step 3: Verify the wheel installs correctly**

```bash
pip install dist/avl_binary-1.0.0-py3-none-macosx_11_0_arm64.whl --force-reinstall
python -c "from avl_binary import avl_path; print(avl_path()); print('OK')"
```

Expected: prints the path inside the venv's `site-packages/avl_binary/bin/avl` and `OK`

- [ ] **Step 4: Commit**

```bash
git add avl-binary/build_wheels.py
git commit -m "feat(gh-458): add wheel build script for platform-specific AVL wheels"
```

---

### Task 3: Build Linux wheel and create GitHub Release

This task requires Docker Desktop with buildx. It produces the Linux
x86_64 wheel and uploads both wheels to a GitHub Release.

**Files:**
- No new files — produces artifacts

- [ ] **Step 1: Extract Linux AVL binary from Docker build**

```bash
docker buildx build --platform linux/amd64 --target build_avl -t avl-build --load .
docker create --name avl-extract avl-build
docker cp avl-extract:/home/avl/bin/avl avl-binary/avl_linux_x86_64
docker rm avl-extract
```

Verify: `file avl-binary/avl_linux_x86_64` should show `ELF 64-bit LSB executable, x86-64`

- [ ] **Step 2: Build Linux wheel**

```bash
cd avl-binary
python build_wheels.py --platform linux_x86_64 --binary avl_linux_x86_64
ls -la dist/*.whl
rm avl_linux_x86_64
```

Expected: `dist/avl_binary-1.0.0-py3-none-manylinux_2_17_x86_64.manylinux2014_x86_64.whl`

- [ ] **Step 3: Create GitHub Release and upload both wheels**

```bash
gh release create avl-binary-v1.0.0 \
  avl-binary/dist/avl_binary-1.0.0-py3-none-macosx_11_0_arm64.whl \
  avl-binary/dist/avl_binary-1.0.0-py3-none-manylinux_2_17_x86_64.manylinux2014_x86_64.whl \
  --title "AVL Binary v1.0.0" \
  --notes "Pre-compiled AVL binaries for poetry install. macOS arm64 + Linux x86_64."
```

- [ ] **Step 4: Verify release asset URLs are accessible**

```bash
gh release view avl-binary-v1.0.0 --json assets --jq '.assets[].url'
```

Both URLs should be publicly accessible.

---

### Task 4: Add `avl-binary` dependency to main project

**Files:**
- Modify: `pyproject.toml`

- [ ] **Step 1: Write the failing test**

The existing test `test_default_avl_command_resolves_to_exports` in
`app/tests/test_avl_runner.py:600` will serve as our canary — it currently
asserts the path ends with `exports/avl`. After we change the dependency,
it should fail because the path will come from the installed wheel.

Run: `poetry run pytest app/tests/test_avl_runner.py::TestAVLRunnerDefaults::test_default_avl_command_resolves_to_exports -v`
Expected: PASS (still using old code — confirms baseline)

- [ ] **Step 2: Add the dependency to `pyproject.toml`**

After line 26 (the `ocp-vscode` dependency), add the `avl-binary` entries
to the `dependencies` list in the `[project]` section:

```toml
    "avl-binary @ https://github.com/szymansk/da3Dalus/releases/download/avl-binary-v1.0.0/avl_binary-1.0.0-py3-none-macosx_11_0_arm64.whl ; sys_platform == 'darwin' and platform_machine == 'arm64'",
    "avl-binary @ https://github.com/szymansk/da3Dalus/releases/download/avl-binary-v1.0.0/avl_binary-1.0.0-py3-none-manylinux_2_17_x86_64.manylinux2014_x86_64.whl ; sys_platform == 'linux' and platform_machine == 'x86_64'",
```

- [ ] **Step 3: Run `poetry lock` and `poetry install`**

```bash
poetry lock --no-update
poetry install --no-interaction
```

- [ ] **Step 4: Verify the package is installed**

```bash
python -c "from avl_binary import avl_path; print(avl_path())"
```

Expected: prints a path inside the venv's `site-packages/avl_binary/bin/avl`

- [ ] **Step 5: Commit**

```bash
git add pyproject.toml poetry.lock
git commit -m "feat(gh-458): add avl-binary wheel dependency with platform markers"
```

---

### Task 5: Update `avl_runner.py` to use `avl_binary`

**Files:**
- Modify: `app/services/avl_runner.py:17,72-96,108`

- [ ] **Step 1: Verify current test passes (baseline)**

Run: `poetry run pytest app/tests/test_avl_runner.py::TestAVLRunnerDefaults -v`
Expected: PASS

- [ ] **Step 2: Update `avl_runner.py`**

In `app/services/avl_runner.py`:

Remove line 17:
```python
_PROJECT_ROOT = Path(__file__).resolve().parents[2]
```

Remove lines 72-96 (the entire `_resolve_avl_path()` function).

Add import at the top (after `from pathlib import Path`):
```python
from avl_binary import avl_path
```

Replace line 108:
```python
    DEFAULT_AVL_COMMAND = str(_resolve_avl_path())
```
with:
```python
    DEFAULT_AVL_COMMAND = str(avl_path())
```

- [ ] **Step 3: Update the default path test**

In `app/tests/test_avl_runner.py`, replace the test at line 600-609:

```python
    def test_default_avl_command_resolves_to_exports(self):
        from app.services.avl_runner import AVLRunner

        runner = AVLRunner(
            airplane=MagicMock(),
            op_point=MagicMock(),
            xyz_ref=[0, 0, 0],
        )
        assert runner.avl_command.endswith("exports/avl")
        assert "avl_runner.py" not in runner.avl_command
```

with:

```python
    def test_default_avl_command_resolves_to_avl_binary(self):
        from app.services.avl_runner import AVLRunner

        runner = AVLRunner(
            airplane=MagicMock(),
            op_point=MagicMock(),
            xyz_ref=[0, 0, 0],
        )
        assert Path(runner.avl_command).name == "avl"
        assert Path(runner.avl_command).exists()
```

- [ ] **Step 4: Run tests to verify**

Run: `poetry run pytest app/tests/test_avl_runner.py::TestAVLRunnerDefaults -v`
Expected: 2 passed

Run: `poetry run pytest app/tests/test_avl_runner.py -v --tb=short`
Expected: all tests pass

- [ ] **Step 5: Commit**

```bash
git add app/services/avl_runner.py app/tests/test_avl_runner.py
git commit -m "refactor(gh-458): replace _resolve_avl_path() with avl_binary.avl_path()"
```

---

### Task 6: Update integration test to use `avl_binary`

**Files:**
- Modify: `app/tests/test_avl_strip_forces_integration.py:1-9`

- [ ] **Step 1: Update the integration test**

In `app/tests/test_avl_strip_forces_integration.py`, replace lines 1-9:

```python
"""Integration test for AVL strip-force extraction via AVLRunner.

Requires the AVL binary at exports/avl.
"""

import pytest
from pathlib import Path

AVL_BINARY = Path(__file__).resolve().parents[2] / "exports" / "avl"
```

with:

```python
"""Integration test for AVL strip-force extraction via AVLRunner."""

import pytest

from avl_binary import avl_path

AVL_BINARY = str(avl_path())
```

- [ ] **Step 2: Run the integration test (if binary available)**

Run: `poetry run pytest app/tests/test_avl_strip_forces_integration.py -v --tb=short -m slow`
Expected: all slow tests pass (requires AVL binary)

If tests are skipped due to marker, verify at least that the import works:
```bash
python -c "from app.tests.test_avl_strip_forces_integration import AVL_BINARY; print(AVL_BINARY)"
```

- [ ] **Step 3: Commit**

```bash
git add app/tests/test_avl_strip_forces_integration.py
git commit -m "refactor(gh-458): use avl_binary in strip forces integration test"
```

---

### Task 7: Update worktree-setup.md and run full regression

**Files:**
- Modify: `.claude/rules/worktree-setup.md`

- [ ] **Step 1: Update worktree-setup.md**

Replace the full content of `.claude/rules/worktree-setup.md` with:

```markdown
# Worktree Setup

## Create the `tmp/` directory

The app mounts `tmp/` as a static-files directory at startup. Worktrees
don't have it:

```bash
mkdir -p "$WORKTREE_ROOT/tmp"
```

## AVL binary

The AVL binary is delivered via the `avl-binary` Python wheel. After
`poetry install` in a worktree, `avl_path()` returns the correct path.
No manual symlinks needed.
```

- [ ] **Step 2: Run full fast test suite**

```bash
poetry run pytest -m "not slow" --tb=short -q
```

Expected: all tests pass (same count as baseline, no regressions)

- [ ] **Step 3: Run lint**

```bash
poetry run ruff check app/services/avl_runner.py app/tests/test_avl_runner.py app/tests/test_avl_strip_forces_integration.py
```

Expected: no lint errors

- [ ] **Step 4: Commit**

```bash
git add .claude/rules/worktree-setup.md
git commit -m "docs(gh-458): remove AVL symlink from worktree-setup, binary now via wheel"
```

- [ ] **Step 5: Push all commits**

```bash
git push github chore/gh-458-avl-binary-wheel
```
