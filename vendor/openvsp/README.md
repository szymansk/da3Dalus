# Vendored OpenVSP wheel

This directory holds locally-built `openvsp-*.whl` files for the
OpenVSP Python bindings. The wheel itself is NOT committed to git
(it's in `.gitignore` — wheels are too large and platform-specific).

## Getting a wheel

Three options, by ease:

### 1. Download from a GitHub Release (easiest)

The project publishes pre-built wheels for actively-supported
configurations as assets on releases tagged
`openvsp-wheels-<version>`. See **Option A** in
`docs/md/openvsp-import-setup.md`.

```bash
# Example — replace the URL with the asset matching your env:
poetry run pip install \
  https://github.com/szymansk/da3Dalus/releases/download/openvsp-wheels-3.50.4/openvsp-3.50.4-cp311-cp311-macosx_14_0_arm64.whl
```

### 2. Build via helper script

```bash
scripts/build_openvsp_wheel.sh
# Wheel ends up here in vendor/openvsp/, then auto-installed in the Poetry env.
```

### 3. Manual build

See `docs/md/openvsp-import-setup.md` Option B for step-by-step
commands.

## Install a wheel placed here manually

```bash
poetry run pip install vendor/openvsp/openvsp-*.whl
poetry run python -c "import openvsp; print(openvsp.GetVSPVersion())"
```

## Why is `*.whl` gitignored?

- Wheels are typically 30-200 MB — too large for git tree.
- Wheels are platform- and Python-version-specific (one wheel per
  combination); committing all of them would bloat the repo.
- We distribute via GitHub Releases instead — same artifacts,
  accessible via `pip install <url>`, without cluttering the repo.

If you produce a new wheel for a config that's not yet on a Release,
please upload it via:

```bash
gh release create openvsp-wheels-<version> \
  vendor/openvsp/openvsp-<version>-<pytag>-<plattag>.whl
```

See `docs/md/openvsp-import-setup.md` for the full publish workflow.
