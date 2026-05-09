# AVL Binary Platform Wheel — Design Spec

**Issue:** #458
**Date:** 2026-05-09
**Status:** Approved

## Problem

The vendored AVL binary (`exports/avl`) is gitignored and outside the
Python dependency graph. This causes:

- Git worktrees don't get the binary — requires manual symlink
  (`.claude/rules/worktree-setup.md`)
- CI (`ubuntu-latest`) runs without the binary — AVL integration
  tests cannot execute
- New developer onboarding requires manual binary placement
- Docker builds compile from source separately

## Solution: Direct URL Wheel Dependencies

Package pre-compiled AVL binaries into platform-specific Python wheels,
host them as GitHub Release assets, and reference them via direct URL
dependencies with platform markers in `pyproject.toml`.

## Package Structure

New top-level directory `avl-binary/` in the repo:

```
avl-binary/
├── pyproject.toml           # wheel metadata, build config
├── build_wheels.py          # builds both platform wheels
└── avl_binary/
    ├── __init__.py          # exposes avl_path() -> Path
    ├── py.typed
    └── bin/
        └── avl              # per-platform binary (replaced during build)
```

### Public API

```python
# avl_binary/__init__.py
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

Single function, no fallback logic, no magic.

## Wheel Building

### Platform Wheels

| Platform | Tag | Binary Source |
|----------|-----|---------------|
| macOS Apple Silicon | `py3-none-macosx_11_0_arm64` | `exports/avl` (existing) |
| Linux x86_64 | `py3-none-manylinux_2_17_x86_64` | Extracted from Docker build |

### Linux Binary Extraction

```bash
docker buildx build --platform linux/amd64 --target build_avl -t avl-build .
docker create --name avl-extract avl-build
docker cp avl-extract:/home/avl/bin/avl ./avl-binary/avl_linux_x86_64
docker rm avl-extract
```

### Build Script (`build_wheels.py`)

For each platform:
1. Copy the platform-appropriate binary to `avl_binary/bin/avl`
2. Set `chmod +x`
3. Build wheel with `python -m build`
4. Rename wheel to correct platform tag
5. Output to `avl-binary/dist/`

### Hosting

Upload wheels as assets on GitHub Release `avl-binary-v1.0.0`:

```bash
gh release create avl-binary-v1.0.0 \
  avl-binary/dist/avl_binary-1.0.0-py3-none-macosx_11_0_arm64.whl \
  avl-binary/dist/avl_binary-1.0.0-py3-none-manylinux_2_17_x86_64.whl \
  --title "AVL Binary v1.0.0" \
  --notes "Pre-compiled AVL binaries for poetry install"
```

## Integration

### `pyproject.toml`

```toml
[tool.poetry.dependencies]
avl-binary = [
    {url = "https://github.com/szymansk/da3Dalus/releases/download/avl-binary-v1.0.0/avl_binary-1.0.0-py3-none-macosx_11_0_arm64.whl", markers = "sys_platform == 'darwin' and platform_machine == 'arm64'"},
    {url = "https://github.com/szymansk/da3Dalus/releases/download/avl-binary-v1.0.0/avl_binary-1.0.0-py3-none-manylinux_2_17_x86_64.whl", markers = "sys_platform == 'linux' and platform_machine == 'x86_64'"},
]
```

### `app/services/avl_runner.py`

Replace `_resolve_avl_path()` and worktree fallback with:

```python
from avl_binary import avl_path

class AVLRunner:
    DEFAULT_AVL_COMMAND = str(avl_path())
```

Remove:
- `_resolve_avl_path()` function
- `_PROJECT_ROOT` constant (if only used for AVL path)

### `app/tests/test_avl_runner.py`

Update assertion that checks the default path:

```python
# Before: assert runner.avl_command.endswith("exports/avl")
# After:  assert Path(runner.avl_command).exists()
```

### `app/tests/test_avl_strip_forces_integration.py`

Replace hardcoded path:

```python
from avl_binary import avl_path
AVL_BINARY = str(avl_path())
```

### `.claude/rules/worktree-setup.md`

Remove the AVL symlink section. Keep only `mkdir -p tmp/`.

### `Dockerfile`

No changes. Docker continues compiling AVL from Fortran source.

### `.github/workflows/test.yml`

No changes. `poetry install` now delivers the binary automatically.

## Acceptance Criteria

1. `poetry install` on macOS arm64 delivers a working AVL binary via `avl_path()`
2. `poetry install` on Linux x86_64 (CI) delivers a working AVL binary via `avl_path()`
3. `poetry run pytest -m "not slow"` — all existing tests green, no regression
4. `poetry run pytest -m slow` — AVL integration tests find the binary without symlink
5. Fresh git worktree + `poetry install` — AVL tests pass without manual symlink
6. `_resolve_avl_path()` and worktree fallback logic removed from `avl_runner.py`
7. Docker build remains functional (compiles from source)
8. GitHub Release `avl-binary-v1.0.0` exists with both platform wheels as assets

## Out of Scope

- Additional platforms (macOS x86_64, Linux arm64) — add later if needed
- Automated wheel rebuild on AVL updates — too infrequent for automation
- PyPI publication — unnecessary for an internal binary
