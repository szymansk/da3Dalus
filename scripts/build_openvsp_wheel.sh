#!/usr/bin/env bash
# Build an OpenVSP Python wheel from source for the active Poetry env.
#
# Background: the official `openvsp` PyPI package is a placeholder
# with no installable wheel for current CPython releases. The repo
# ships pre-built wheels via GitHub Releases, but if you need to
# (re)build for a different Python / OpenVSP version, this script
# automates the process documented in `docs/md/openvsp-import-setup.md`.
#
# Usage:
#   scripts/build_openvsp_wheel.sh                  # build OpenVSP_3.50.4 (default)
#   scripts/build_openvsp_wheel.sh 3.49.0           # build a specific version
#
# Requirements:
#   - macOS (Apple Silicon tested) or Linux
#   - clang / gcc with C++17 support
#   - SWIG 4.0+   (brew install swig)
#   - CMake **3.x**  (NOT 4.x — see "Pitfalls" below)
#   - Internet access (fetches OpenVSP + third-party deps)
#   - ~3 GB free disk in /tmp, ~30 min build time
#
# Output: a `.whl` in `vendor/openvsp/` ready to be `pip install`ed.
#
# Pitfalls:
#   - CMake 4.x removed compatibility with cmake_minimum_required(VERSION <3.5),
#     which two of OpenVSP's bundled dependencies (CODEELI, STEPCODE) still use.
#     The script installs CMake 3.31 into an isolated venv if `cmake --version`
#     reports 4.x.

set -euo pipefail

OPENVSP_VERSION="${1:-3.50.4}"
BUILD_DIR="${BUILD_DIR:-/tmp/openvsp-build}"
REPO_ROOT="$(cd "$(dirname "$0")/.." && pwd)"

echo "==> Building OpenVSP ${OPENVSP_VERSION} for $(poetry run python --version)"

# ---------------------------------------------------------------------------
# Step 1 — Verify and (if needed) pin CMake 3.x
# ---------------------------------------------------------------------------

CMAKE_BIN="$(command -v cmake || true)"
CMAKE_MAJOR="$($CMAKE_BIN --version 2>/dev/null | head -1 | awk '{print $3}' | cut -d. -f1 || echo 0)"

if [[ -z "$CMAKE_BIN" || "$CMAKE_MAJOR" -ge 4 ]]; then
  echo "==> System cmake is $CMAKE_MAJOR.x or missing — installing 3.31 in isolated venv"
  if [[ ! -x /tmp/cmake-old-env/bin/cmake ]]; then
    python3 -m venv /tmp/cmake-old-env
    /tmp/cmake-old-env/bin/pip install --quiet cmake==3.31.6
  fi
  CMAKE_BIN=/tmp/cmake-old-env/bin/cmake
  export PATH="/tmp/cmake-old-env/bin:$PATH"
fi
echo "==> Using cmake: $($CMAKE_BIN --version | head -1)"

# ---------------------------------------------------------------------------
# Step 2 — Verify SWIG
# ---------------------------------------------------------------------------

if ! command -v swig >/dev/null; then
  echo "ERROR: swig not found. Install via:  brew install swig"
  exit 1
fi
echo "==> Using swig: $(swig -version | grep -i version | head -1 | tr -s ' ')"

# ---------------------------------------------------------------------------
# Step 3 — Resolve Python paths (point at the Poetry venv)
# ---------------------------------------------------------------------------

PYBIN="$(poetry run which python)"
PYINC="$(poetry run python -c 'import sysconfig; print(sysconfig.get_paths()["include"])')"
PYVER="$(poetry run python -c 'import sysconfig; print(sysconfig.get_config_var("LDVERSION") or sysconfig.get_python_version())')"
PYLIBDIR="$(poetry run python -c 'import sysconfig; print(sysconfig.get_config_var("LIBDIR"))')"
PYLIB="$(find "$PYLIBDIR" -maxdepth 1 -name "libpython${PYVER}*.dylib" -o -name "libpython${PYVER}*.so" 2>/dev/null | head -1)"

if [[ -z "$PYLIB" ]]; then
  echo "ERROR: could not locate libpython${PYVER} in $PYLIBDIR"
  exit 1
fi
echo "==> Python bin:     $PYBIN"
echo "==> Python headers: $PYINC"
echo "==> Python library: $PYLIB"

# ---------------------------------------------------------------------------
# Step 4 — Clone (or reuse) OpenVSP source
# ---------------------------------------------------------------------------

mkdir -p "$BUILD_DIR"
SOURCE_DIR="$BUILD_DIR/OpenVSP_${OPENVSP_VERSION}"

if [[ ! -d "$SOURCE_DIR" ]]; then
  echo "==> Cloning OpenVSP_${OPENVSP_VERSION}..."
  git clone --depth 1 --branch "OpenVSP_${OPENVSP_VERSION}" \
    https://github.com/OpenVSP/OpenVSP.git "$SOURCE_DIR"
else
  echo "==> Reusing existing source: $SOURCE_DIR"
fi

# ---------------------------------------------------------------------------
# Step 5 — Configure SuperProject + headless build
# ---------------------------------------------------------------------------

BUILD_OUT="$BUILD_DIR/build_${OPENVSP_VERSION}"
rm -rf "$BUILD_OUT"
mkdir -p "$BUILD_OUT"
cd "$BUILD_OUT"

echo "==> Configuring..."
# VSP_NO_VSPAERO   — skip VSPAERO solver (uses OpenMP; clang on macOS lacks it by default)
# VSP_NO_PYDOC     — skip Sphinx-based Python doc generation
# VSP_NO_HELP/DOC  — skip help/manual generation (not needed for the wheel)
"$CMAKE_BIN" \
  -DCMAKE_BUILD_TYPE=Release \
  -DVSP_NO_GRAPHICS=ON \
  -DVSP_NO_VSPAERO=ON \
  -DVSP_NO_PYDOC=ON \
  -DVSP_NO_HELP=ON \
  -DVSP_NO_DOC=ON \
  -DPYTHON_EXECUTABLE="$PYBIN" \
  -DPYTHON_INCLUDE_DIR="$PYINC" \
  -DPYTHON_LIBRARY="$PYLIB" \
  "$SOURCE_DIR/SuperProject"

# ---------------------------------------------------------------------------
# Step 6 — Build (long — uses all CPU cores)
# ---------------------------------------------------------------------------

NPROC="$(sysctl -n hw.ncpu 2>/dev/null || nproc)"
echo "==> Building with $NPROC parallel jobs (this takes 30-60 min)..."
"$CMAKE_BIN" --build . --parallel "$NPROC"

# ---------------------------------------------------------------------------
# Step 7 — Locate the wheel and vendor it
# ---------------------------------------------------------------------------

WHEEL_PATH="$(find "$BUILD_OUT" -name 'openvsp-*.whl' | head -1)"
if [[ -z "$WHEEL_PATH" ]]; then
  echo "==> No wheel produced by the build — falling back to manual wheel build"
  PYAPI_DIR="$(find "$BUILD_OUT" -type d -name openvsp -path '*python_api/packages*' | head -1)"
  if [[ -z "$PYAPI_DIR" ]]; then
    PYAPI_DIR="$(find "$SOURCE_DIR" -type d -name openvsp -path '*python_api/packages*' | head -1)"
  fi
  if [[ -z "$PYAPI_DIR" ]]; then
    echo "ERROR: could not find python_api/packages/openvsp directory"
    exit 1
  fi
  echo "==> Building wheel from: $PYAPI_DIR"
  poetry run python -m pip install --quiet --upgrade build
  ( cd "$PYAPI_DIR" && poetry run python -m build --wheel )
  WHEEL_PATH="$(find "$PYAPI_DIR/dist" -name 'openvsp-*.whl' | head -1)"
fi

if [[ -z "$WHEEL_PATH" ]]; then
  echo "ERROR: wheel not found after build"
  exit 1
fi

mkdir -p "$REPO_ROOT/vendor/openvsp"
cp "$WHEEL_PATH" "$REPO_ROOT/vendor/openvsp/"
echo "==> Vendored wheel: $REPO_ROOT/vendor/openvsp/$(basename "$WHEEL_PATH")"

# ---------------------------------------------------------------------------
# Step 8 — Smoke test
# ---------------------------------------------------------------------------

echo "==> Installing wheel into Poetry venv..."
poetry run pip install --force-reinstall "$REPO_ROOT/vendor/openvsp/$(basename "$WHEEL_PATH")"

echo "==> Smoke test..."
poetry run python -c "import openvsp; print('OpenVSP version:', openvsp.GetVSPVersion())"

echo
echo "==> Build complete."
echo "==> Next: upload to a GitHub Release for sharing:"
echo "    gh release create openvsp-wheels-${OPENVSP_VERSION} \\"
echo "        '$REPO_ROOT/vendor/openvsp/$(basename "$WHEEL_PATH")' \\"
echo "        --title 'OpenVSP ${OPENVSP_VERSION} Python wheels' \\"
echo "        --notes 'See docs/md/openvsp-import-setup.md'"
