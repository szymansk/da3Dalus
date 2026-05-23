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

---

## Option A — PyPI wheel (preferred)

The cleanest path: a published wheel matches our Python version.

```bash
poetry run pip install openvsp
poetry run python -c "import openvsp; print(openvsp.GetVSPVersion())"
```

> **Why `pip` and not `poetry add`?** The `openvsp` PyPI entry is a
> placeholder with no installable distribution for any currently
> supported Python (as of 2026-05). Declaring it in `pyproject.toml`
> — even in an optional group — breaks `poetry lock` for everyone.
> We therefore treat it as an **out-of-tree** install, manually
> applied after `poetry install`, only when a wheel becomes
> available.

**When this works:** the OpenVSP release ships a wheel for CPython
3.11 or 3.12. As of writing (May 2026) this is **not** the case — the
latest published `openvsp` wheels target older Python versions.

**Verify:**

```bash
poetry run python -c "from app.converters.openvsp_adapter import is_available; print(is_available())"
# Expected: True
```

---

## Option B — Build from source against our Python (recommended fallback)

When no matching wheel is on PyPI, build the SWIG bindings against
our Python interpreter and vendor the resulting wheel.

### Prerequisites

- C++17 compiler (gcc 11+, clang 14+, or MSVC 2019+)
- CMake 3.24+
- SWIG 4.0+
- The Python development headers for **our** Python version (3.11.x
  or 3.12.x) — on macOS: `brew install python@3.11`; on Debian:
  `sudo apt install python3.11-dev`.

### Build steps

```bash
# 1. Clone OpenVSP at the version you want to track.
git clone --depth 1 --branch OpenVSP_3.41.2 https://github.com/OpenVSP/OpenVSP.git
cd OpenVSP

# 2. Configure for our Python interpreter — POINT IT EXPLICITLY.
mkdir build && cd build
cmake -DCMAKE_BUILD_TYPE=Release \
      -DVSP_USE_SYSTEM_PYTHON=ON \
      -DPython3_EXECUTABLE=$(poetry run which python) \
      -DVSP_NO_GRAPHICS=ON \
      ../Libraries
cmake --build . --parallel
cmake -DCMAKE_BUILD_TYPE=Release \
      -DVSP_USE_SYSTEM_PYTHON=ON \
      -DPython3_EXECUTABLE=$(poetry run which python) \
      -DCMAKE_INSTALL_PREFIX=../install \
      ../src
cmake --build . --parallel --target install

# 3. Build the Python wheel.
cd ../src/python_api/packages/openvsp
$(poetry run which python) -m build --wheel

# 4. Vendor the wheel into the da3Dalus repo.
cp dist/openvsp-*.whl /path/to/cad-modelling-service/vendor/openvsp/
```

### Install the vendored wheel

```bash
cd /path/to/cad-modelling-service
poetry run pip install vendor/openvsp/openvsp-*.whl
poetry run python -c "import openvsp; print(openvsp.GetVSPVersion())"
```

Do **not** add the vendored wheel to the Poetry `openvsp` group —
that group remains pointed at PyPI for the day a matching wheel
appears there. Vendored installs are tracked as a manual step in the
README setup checklist.

---

## Option C — Docker microservice (last-resort fallback)

When neither A nor B is feasible (e.g. CI runner with no compiler,
or platform mismatch), run OpenVSP in a separate container with its
own compatible Python, and call it over HTTP.

### Architecture

```
+-------------------+        HTTP        +--------------------+
| da3Dalus backend  |  -- POST /parse -->|  openvsp-service   |
| (Python 3.11/12)  |  <-- AeroplaneJSON | (Python 3.6, vsp.) |
+-------------------+                    +--------------------+
```

The microservice exposes a single endpoint that accepts a `.vsp3`
upload and returns the same `ImportResult` payload that the in-process
importer would produce. The adapter shim
(`app/converters/openvsp_adapter.py`) is forward-compatible with this
pattern — we can swap the local `import openvsp` for an HTTP client
without touching the rest of the importer.

A reference Dockerfile is **not** part of Phase 1 (gh-637 MVP). When
Option A or B both fail in production, file a ticket against EPIC B
(#638) to add the microservice fallback.

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

Likely a version mismatch between the SWIG bindings and the native
`libvsp.so` / `libvsp.dylib`. Rebuild both from the same source tree
via Option B.

---

## Related

- Issue: gh-639 — install-strategy ticket
- Epic: gh-637 — OpenVSP `.vsp3` importer Phase 1
- Adapter shim: `app/converters/openvsp_adapter.py`
- Scope note: `~/.claude/projects/.../memory/feedback_openvsp_import_rc_scope.md`
