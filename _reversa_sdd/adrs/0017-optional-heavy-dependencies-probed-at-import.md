# ADR 0017 — Heavy native dependencies are optional, probed once, and degrade to 503

- **Status:** Accepted — in force
- **Decided:** incrementally; the platform probe module and the conditional router mounting are the crystallised form
- **Deciders:** Marc Szymanski (maintainer)
- **Confidence:** 🟢 CONFIRMED (code, `pyproject.toml` env markers, module docstrings)

## Context

Three native stacks are hostile to portable packaging: **CadQuery / cadquery-ocp**
(the OCCT kernel), **AeroSandbox** (CasADi, NumPy/SciPy, NeuralFoil, VTK) and
**OpenVSP** (a SWIG binding with no compatible wheel, installed by hand).
Environment markers **exclude CadQuery and AeroSandbox on `linux/aarch64`**, where
no usable wheels exist, and the Docker image force-installs a *different* version
set than `poetry.lock` resolves. A naive `import cadquery` at module scope would
make the whole service unstartable on a platform where only the geometry features
are unavailable — health checks, the airfoil catalogue, the component library, mass
and CG, mission sizing and versioning have no reason to require OCCT.

## Decision

**Treat CadQuery, AeroSandbox and OpenVSP as optional capabilities. Probe them once
at import time, mount the dependent routers conditionally, and turn a missing
capability into a clean 503 rather than a crash.**

1. **`app/core/platform.py`** exposes `cad_available()` / `aerosandbox_available()`,
   both `@lru_cache(maxsize=1)` — *"a broken install detected once stays broken for
   the life of the process"* — plus `require_cad` / `require_aerosandbox` FastAPI
   dependencies that raise a **503 with an explanatory message**.
2. **`main.py` probes before `create_app` is even defined** and conditionally
   imports five routers (`cad`, `aeroanalysis`, `operating_points`, `airfoils`,
   `section_aoa`), each inside its own `try/except ImportError` that logs a warning.
   On aarch64 the service still starts; the affected paths simply 404.
3. **`/health` is forbidden from importing CadQuery or AeroSandbox**, stated in its
   module header, and always returns **HTTP 200** — deliberately, *"so that a load
   balancer can tell the difference between 'service is down' (HTTP error) and
   'service is up but degraded'"*.
4. **Service-level lazy imports.** Modules that mostly work without the heavy stack
   import it *inside* the function that needs it and degrade with a logged warning —
   `fuselage_slice_service` (→ `InternalError`), `airfoil_low_re_service` (→ `[]`),
   `section_geometry` (→ `SectionGeometryUnavailableError`),
   `construction_plan_service.list_creators` (→ empty list), and three more.
5. **OpenVSP gets a dedicated shim.** `openvsp_adapter` memoises the import in three
   module globals with `reset_for_tests()` as the only reset, and `get_vsp()` raises
   an `ImportError` naming the three supported install paths.
6. **A container smoke test.** `docker_smoke_test.py` runs inside the Docker build,
   with an `ldd` check on the AVL binary, so a broken native install fails the build
   rather than the first request.

## Consequences

- The service runs where the geometry and aero stacks cannot be installed at all;
  failure is *legible*; cheap module import matters because the MCP server is built
  at **import time**; and the same discipline is what made the CI tiering possible
  ([ADR 0015](0015-tiered-ci-fast-full-nightly.md)).
- 🔴 **The capability state is invisible.** `/health` reports
  `{status, version, database}` and **not** `cad_available` /
  `aerosandbox_available`. There is no readiness probe, no Alembic-head check, and
  its version string matches neither of the other two
  ([ADR 0022](0022-one-authority-per-user-facing-quantity.md) / `Q-CC-4`).
- **Two failure shapes for the same cause**: an unmounted router gives 404, a
  mounted endpoint with `Depends(require_*)` gives 503. A client cannot tell "not
  built" from "not installed".
- **`lru_cache` means no recovery** — if a dependency becomes importable later, the
  process never notices.
- 🔴 **Process-level module state makes hot reload lie.** The OpenVSP adapter's
  memoised globals, the importer's `_HANDLERS`/`_POST_PASSES` registries and the
  SWIG module's native global VSP model mean `uvicorn --reload` does **not** pick up
  importer changes — the process must be restarted.
- **Version drift between environments is real and unmanaged** — a geometry result
  reproduced locally is not guaranteed in the container.
- **Every consumer must remember to guard.** A new top-level `import cadquery`
  anywhere in `app/` silently breaks aarch64 startup, and no test covers that
  platform.

**Rejected:** hard dependencies without aarch64 support (aarch64 is the maintainer's
own container/dev target); feature flags instead of probes (a probe reflects
reality, a flag reflects intent, and the fact being guarded is an *installation*
fact).

## Related

[ADR 0005](0005-cad-in-a-spawned-process-pool.md) ·
[ADR 0015](0015-tiered-ci-fast-full-nightly.md) ·
[ADR 0018](0018-openvsp-import-scope-is-rc-scaling-inspiration.md) ·
domain rule BR-81.
Evidence: `app/core/platform.py`, `app/main.py:1-95, 222-223`,
`app/api/v2/endpoints/health.py` (module header),
`app/converters/openvsp_adapter.py:53-97`; `pyproject.toml` (env markers + the
OpenVSP install note); `Dockerfile`; `docker_smoke_test.py`; project memory
`feedback_backend_restart_after_importer_merge`.
