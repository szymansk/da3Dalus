# OpenVSP `.vsp3` Importer — Setup Guide

The OpenVSP importer (gh-637) is an **optional feature**. It depends
on the official [`openvsp` Python package][openvsp-pkg] published by
the OpenVSP team. That package is built against a specific CPython
version — the version OpenVSP itself was built with — so the wheel
on PyPI does not always match our Python 3.11/3.12 runtime.

This guide documents the three supported install paths, in
preference order. **Pick the first one that works in your
environment.**

[openvsp-pkg]: https://pypi.org/project/openvsp/

> **Quick path for da3Dalus contributors on macOS arm64 / Python 3.11:**
> a pre-built wheel is published on the project's GitHub Releases. See
> **Option A.1** below.

---

## Option A — Pre-built wheel from GitHub Releases (preferred)

Pre-built wheels for the configurations we actively support are
attached as assets on releases tagged `openvsp-wheels-<version>` of
this repository.

### A.1 Install the pre-built wheel

```bash
# Replace VERSION + PYTAG + PLATTAG with the asset matching your env.
poetry run pip install \
  https://github.com/szymansk/da3Dalus/releases/download/openvsp-wheels-3.50.4/openvsp-3.50.4-cp311-cp311-macosx_14_0_arm64.whl

# Smoke test:
poetry run python -c "import openvsp; print(openvsp.GetVSPVersion())"
```

Supported wheel matrix (as of writing):

| OpenVSP | Python | Platform                     | Notes                          |
|---------|--------|------------------------------|--------------------------------|
| 3.50.4  | 3.11   | `macosx_14_0_arm64`          | Apple Silicon, headless build |

If your combination is not listed, fall back to **Option B**.

### A.2 If/when PyPI publishes a matching wheel

```bash
poetry run pip install openvsp
```

> **Why not `poetry add`?** The `openvsp` PyPI entry has historically
> been a placeholder with no installable distribution for any
> currently supported Python. Declaring it in `pyproject.toml` —
> even in an optional group — breaks `poetry lock` for everyone. We
> therefore treat it as an out-of-tree install, manually applied
> after `poetry install`.

---

## Option B — Build from source (when no wheel matches your env)

Run the helper script (`scripts/build_openvsp_wheel.sh`) which
automates the steps below:

```bash
scripts/build_openvsp_wheel.sh                  # OpenVSP_3.50.4 (default)
scripts/build_openvsp_wheel.sh 3.49.0           # specific version
```

The script handles everything: install pinned CMake, configure
SuperProject, build, vendor the wheel, install into Poetry env, smoke
test.

### Manual build steps (for reference)

If you prefer to drive it by hand or are debugging the script:

```bash
# 1. Build dependencies
brew install swig
# CMake 3.x — NOT 4.x; see "Pitfalls" below. Quick install:
python3 -m venv /tmp/cmake-old-env
/tmp/cmake-old-env/bin/pip install cmake==3.31.6
export PATH="/tmp/cmake-old-env/bin:$PATH"

# 2. Clone OpenVSP at the version you want.
git clone --depth 1 --branch OpenVSP_3.50.4 \
  https://github.com/OpenVSP/OpenVSP.git /tmp/openvsp-build/OpenVSP

# 3. Resolve Python paths (point at the Poetry venv).
PYBIN=$(poetry run which python)
PYINC=$(poetry run python -c 'import sysconfig; print(sysconfig.get_paths()["include"])')
PYLIBDIR=$(poetry run python -c 'import sysconfig; print(sysconfig.get_config_var("LIBDIR"))')
PYLIB="$PYLIBDIR/libpython3.11.dylib"   # adjust suffix for Linux (.so)

# 4. Configure SuperProject (unified Libraries + main build).
mkdir -p /tmp/openvsp-build/build && cd /tmp/openvsp-build/build
cmake -DCMAKE_BUILD_TYPE=Release \
      -DVSP_NO_GRAPHICS=ON \
      -DVSP_NO_VSPAERO=ON \
      -DVSP_NO_PYDOC=ON \
      -DVSP_NO_HELP=ON \
      -DVSP_NO_DOC=ON \
      -DPYTHON_EXECUTABLE="$PYBIN" \
      -DPYTHON_INCLUDE_DIR="$PYINC" \
      -DPYTHON_LIBRARY="$PYLIB" \
      /tmp/openvsp-build/OpenVSP/SuperProject

# 5. Build (30-60 min on Apple Silicon).
cmake --build . --parallel $(sysctl -n hw.ncpu)

# 6. Locate the wheel and vendor it.
find . -name 'openvsp-*.whl' -exec cp {} vendor/openvsp/ \;
poetry run pip install vendor/openvsp/openvsp-*.whl
poetry run python -c "import openvsp; print(openvsp.GetVSPVersion())"
```

### Build-time options we use

| Flag | Why |
|---|---|
| `-DVSP_NO_GRAPHICS=ON` | Skip FLTK / OpenGL — we never render the OpenVSP GUI. |
| `-DVSP_NO_VSPAERO=ON` | Skip VSPAERO solver. Uses OpenMP, which Apple clang lacks by default. Our import only needs geometry parsing. |
| `-DVSP_NO_PYDOC=ON` | Skip Sphinx-based Python docs (Sphinx is not in our Poetry venv). |
| `-DVSP_NO_HELP=ON` / `-DVSP_NO_DOC=ON` | Skip user-manual generation. |

### Pitfalls

#### CMake 4.x breaks the build

CMake 4.x removed compatibility with `cmake_minimum_required(VERSION
<3.5)`. Two of OpenVSP's bundled third-party dependencies (CODEELI,
STEPCODE) still declare older minimums and fail to configure:

```
CMake Error at CMakeLists.txt:13 (cmake_minimum_required):
  Compatibility with CMake < 3.5 has been removed from CMake.
```

**Fix:** use CMake 3.x. Easiest install method that doesn't touch
the system:

```bash
python3 -m venv /tmp/cmake-old-env
/tmp/cmake-old-env/bin/pip install cmake==3.31.6
export PATH="/tmp/cmake-old-env/bin:$PATH"
```

Then re-run the configure step. CMake 3.31 happily handles both
modern (OpenVSP 3.50) and old (CODEELI 0.0.0) projects.

The helper script `scripts/build_openvsp_wheel.sh` auto-detects
this case and installs the pinned CMake when it sees CMake 4+ on the
PATH.

#### Anaconda Python vs system Python

`poetry env info --path` may show an anaconda-rooted venv. Make sure
`PYTHON_LIBRARY` points at the **anaconda** `libpython3.x.dylib`,
not the macOS framework Python. Mismatched library → wheel imports
but segfaults on any C call.

#### Sphinx, VSPAERO, and other optional pieces

If you DON'T pass `VSP_NO_PYDOC`, the build will fail at the
documentation step unless `sphinx` is in the active Python env. If
you DON'T pass `VSP_NO_VSPAERO`, the build will fail on macOS
because Apple clang doesn't bundle OpenMP. We skip both because the
importer only needs the geometry-parsing API.

---

## Option C — Docker microservice (last-resort fallback)

When neither A nor B is feasible (e.g. CI runner with no compiler,
or platform mismatch), run OpenVSP in a separate container with its
own compatible Python, and call it over HTTP.

### Architecture

```
+-------------------+        HTTP        +--------------------+
| da3Dalus backend  |  -- POST /parse -->|  openvsp-service   |
| (Python 3.11/12)  |  <-- AeroplaneJSON | (Python 3.x, vsp.) |
+-------------------+                    +--------------------+
```

The microservice exposes a single endpoint that accepts a `.vsp3`
upload and returns the same `ImportResult` payload that the in-process
importer would produce. The adapter shim
(`app/converters/openvsp_adapter.py`) is forward-compatible with this
pattern — we can swap the local `import openvsp` for an HTTP client
without touching the rest of the importer.

A reference Dockerfile is **not** part of Phase 1 (gh-637 MVP). When
Options A and B both fail in production, file a ticket against EPIC
B (#638) to add the microservice fallback.

---

## Publishing a built wheel to a GitHub Release (for redistribution)

Once you have a working wheel in `vendor/openvsp/`, share it with
the team via a GitHub Release:

```bash
# Tag format: openvsp-wheels-<OpenVSP version>
gh release create openvsp-wheels-3.50.4 \
  vendor/openvsp/openvsp-3.50.4-cp311-cp311-macosx_14_0_arm64.whl \
  --title "OpenVSP 3.50.4 Python wheels" \
  --notes "Pre-built wheels for the OpenVSP 3.50.4 Python bindings.

Built headless (no GUI, no VSPAERO, no Sphinx). See
docs/md/openvsp-import-setup.md for the build commands.

Install:
  poetry run pip install <asset-url>"
```

Other developers (or this repo's CI in the future) can then install
the wheel via Option A.1.

License note: OpenVSP is **NASA Open Source Agreement (NOSA) 1.3**
— redistribution of built binaries is explicitly permitted. No
attribution headers required in the wheel itself.

---

## Verifying installation

After any successful install path:

```bash
poetry run pytest app/tests/test_openvsp_adapter.py -v
```

All non-`SKIP` tests must pass. The smoke test
`TestSmoke::test_real_openvsp_smoke` will run instead of being
skipped — verifying that `vsp.ClearVSPModel` and `vsp.GetVSPVersion`
both resolve.

End-to-end via the REST endpoint:

```bash
curl -X POST http://localhost:8001/api/v2/import/openvsp \
  -F "file=@some-model.vsp3"
# Expect: 200 with {"aeroplane_uuid": "...", ...} (not 503)
```

---

## Troubleshooting

### `ImportError: No module named 'openvsp'`

You have not yet installed any of A/B/C. The adapter shim shows the
same hint when something calls `get_vsp()` without the dependency.

### `ImportError: dlopen … wrong architecture`

The wheel is built for the wrong CPU (e.g. x86_64 wheel on Apple
Silicon). Either find the right wheel or fall back to Option B.

### `ImportError: incompatible library version`

The wheel was built against a different Python version. Force a
rebuild via Option B.

### `vsp.ClearVSPModel()` segfaults

Likely a Python-library mismatch — the SWIG wheel was linked against
a different `libpython3.x.dylib` than the one running. Common cause:
mixing anaconda and macOS framework Python. Rebuild from source
pointing `PYTHON_LIBRARY` at the same `libpython` the Poetry env
uses.

### Endpoint returns 503

The `openvsp` package isn't visible to the FastAPI worker. Restart
the server after installing the wheel — Python caches imported
modules at process start.

---

## Related

- Issue: gh-639 — install-strategy ticket
- Epic: gh-637 — OpenVSP `.vsp3` importer Phase 1 (MVP, merged)
- Adapter shim: `app/converters/openvsp_adapter.py`
- Build script: `scripts/build_openvsp_wheel.sh`
- Vendor dir: `vendor/openvsp/`
- Scope note: `~/.claude/projects/.../memory/feedback_openvsp_import_rc_scope.md`
