# aero_kernel/ — module instructions

**Read [`ARCHITECTURE.md`](ARCHITECTURE.md) before changing anything in this package. It is binding.**
If a change contradicts it, change the architecture document first and get the maintainer's approval,
then the code. Epic: #1173.

## Rules that are easy to get wrong

- **Boundary.** Never import from `app/`, `cad_designer/` or `scripts/`. The app calls the core, never
  the other way round (ARCHITECTURE §3, test Q9).
- **The kernel interprets its own canon model** (`canon/canon_model.json`). Quantities, applications,
  dependencies and units come from it. Code only registers implementations via `@formula("<slug>")` and
  checks via `@precondition("<slug>", "<id>")`. Never hard-code a dependency, a unit or a quantity name that
  the model owns.
- **Formula contract (ARCHITECTURE §8.12).** A formula is a cheap coroutine over its canon parameter names,
  returns every output parameter, and raises `FormulaError` instead of returning a substitute. Heavy work
  only through a solver adapter. It never sees the application, the request or the cache.
- **Until #1181 is merged** the canon document is not machine-readable: build and test against hand-written
  fixture models in `tests/fixtures/`, never against a hand-written `canon/canon_model.json`.
- **Canon changes only through the import** (`python -m aero_kernel.importer`, ARCHITECTURE §8.9). Never
  edit `canon_model.json` by hand, and never read `_reversa_sdd/` at runtime. A canon finding is fixed in
  the canon document, then re-imported. A breaking diff means: update the affected implementations and
  golden values in the same change.
- **One file per canon formula** in `formulas/`, file name = slug with underscores (`stall_speed.py`). One implementation per formula;
  applications are bindings, not copies (ARCHITECTURE §8.5).
- **Formulas compute, they do not judge** (canon A10): no thresholds, bands or pass/fail in this package.
- **Solvers only through `solvers/`.** Formulas never import aerosandbox or call AVL directly, so they stay
  mockable and missing tools become `tool_unavailable`.
- **Errors vs warnings.** No value → `KernelError` with category, `message`, `hint` (ARCHITECTURE §8.1).
  Value with a caveat → warning with `severity` (ADR 0020). Never a silent substitute.
- **Validation** rejects only physically inadmissible input. Mass is always the passed
  `values["aircraft-mass"]` (what-if calculations); a differing `total_mass_kg` in the geometry gives a
  `conflicting_mass` warning, never an abort. Regime (Re, Mach; ADR 0028) is a warning, raised in the solver adapters.
- **Parameter names vs. slugs.** Inside a formula and in its canon fields, keys are parameter names
  (snake_case); quantity slugs (kebab-case) appear only as binding targets (ARCHITECTURE §8.5).
  Mass is not a criterion.
- **Uncertain quantities** (A11, ADR 0027): run each method world through the whole subtree; intervals
  only at the end; never interval arithmetic. A failed world makes the quantity an error, never a
  narrower interval (ARCHITECTURE §8.13).
- **Cache keys** hash exact values (`repr` of floats), never rounded ones; a rounded key can serve a value
  for a different input (ARCHITECTURE §8.4).
- **English only (ADR 0029).** Identifiers, file names, comments, docstrings, error `message`/`hint`
  and docs in this package are English. Canon slugs are used as they are.
- **Async API (ARCHITECTURE §8.10).** `compute()` is a coroutine and must never block the event loop:
  solver work goes through `runtime.py` (process pool), AVL through `asyncio.create_subprocess_exec`.
  Never call `asyncio.run` inside the package; always re-raise `CancelledError`; clean up subprocesses and
  temp dirs on cancellation.
- **Two interfaces, one engine (ARCHITECTURE §8.4).** `compute()` is stateless: no cache, no module-level
  mutable state, no global pool. `CachedKernel` is the stateful facade that owns the cache, in-flight
  dedup and resources, and injects its `NodeStore` into the same engine. Never add state to `compute()`;
  never let the cache change a value. Cache scopes (`scope=`, `drop_scope`) isolate tenants; a hit
  must never cross scopes.

## Tests

| Marker | Runs | Needs |
|---|---|---|
| (none) | fast tier, mocked solvers | numpy, pydantic |
| `@pytest.mark.aero` | real AeroBuildup/AVL, golden values | aerosandbox, avl-binary |

Every formula: a unit test against a hand-computed value. Golden values of the reference fleet are
**regression, not validation**. Run slow tests sequentially.

```bash
poetry run pytest aero_kernel/tests            # fast (pytest-asyncio)
poetry run pytest aero_kernel/tests -m aero    # solvers, golden values
```
