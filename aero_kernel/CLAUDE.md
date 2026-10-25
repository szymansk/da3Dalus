# aero_kernel/ — module instructions

**Read [`ARCHITECTURE.md`](ARCHITECTURE.md) before changing anything in this package. It is binding.**
If a change contradicts it, change the architecture document first and get the maintainer's approval,
then the code. Epic: #1173.

## Rules that are easy to get wrong

- **Boundary.** Never import from `app/`, `cad_designer/` or `scripts/`. The app calls the core, never
  the other way round (ARCHITECTURE §3, test Q9).
- **The kernel interprets its own canon model** (`canon/canon_model.json`). Quantities, applications,
  dependencies and units come from it. Code only registers implementations via `@formula("<slug>")` and
  checks via `@precondition("<slug>", "<id>")` (inputs, before) and `@postcondition("<slug>", "<id>")` (outputs, after). Never hard-code a dependency, a unit or a quantity name that
  the model owns.
- **Formula contract (ARCHITECTURE §8.12).** A formula is a cheap coroutine over its canon parameter names,
  returns every output parameter, and raises `FormulaError` instead of returning a substitute. Heavy work
  only through a solver adapter. It never sees the application, the request or the cache.
- **The canon is machine-readable (#1181).** The importer is built and tested against the real canon
  document; loader, graph and engine unit tests use small hand-written fixture models in `tests/fixtures/`
  (validated against `canon_model.schema.json`), never a hand-written `canon/canon_model.json`.
- **Canon changes only through the import** (`python -m aero_kernel.importer`, ARCHITECTURE §8.9). Never
  edit `canon_model.json` by hand, and never read `_reversa_sdd/` at runtime. A canon finding is fixed in
  the canon document, then re-imported. A breaking diff means: update the affected implementations and
  golden values in the same change.
- **One file per canon formula** in `formulas/`, file name = slug with underscores (`stall_speed.py`). One implementation per formula;
  applications are bindings, not copies (ARCHITECTURE §8.5). Likewise one implementation per check: a
  postcondition stated by two entries (`optimum_at_first_cl_peak`) shares one check function.
- **Formulas compute, they do not judge** (canon A10): no thresholds, bands or pass/fail in this package.
- **Judgement lives in `evaluation/` only (#1276).** Bands, rule meanings and `when` conditions are data in the
  rule table (`_reversa_sdd/calculations/evaluation/`), never in code; the evaluator is a pure function of a
  rule table and a `ComputeResult`; an interval is judged per end (`partly` when it straddles the band). A rule
  for a quantity the canon lacks carries `planned: "#N"` and stays `not_available`.
- **Solvers only through `solvers/`.** Formulas never import aerosandbox or call AVL directly, so they stay
  mockable and missing tools become `tool_unavailable`.
- **Errors vs warnings.** No value → `KernelError` with category, `message`, `hint` (ARCHITECTURE §8.1).
  Value with a caveat → warning with `severity` (ADR 0020). Never a silent substitute.
- **Validation** rejects only physically inadmissible input. Mass is always the passed
  `values["aircraft-mass"]` (what-if calculations); a differing `total_mass_kg` in the geometry gives a
  `conflicting_mass` warning, never an abort. Regime (Re, Mach; ADR 0028) is a warning, raised in the solver adapters.
  Control devices are angles in degrees, never fractions of a stop; stops (`positive/negative_deflection_deg`)
  are never read, checked, clamped or warned about; `airplane-configuration` applies the given flap
  deflection even beyond the stop. No fixed angle range: a saturating method is
  searched to its own maximum, a linear one solved directly; tool validity is an adapter warning
  (ARCHITECTURE §8.11, §8.8).
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
  solver work goes through `runtime.py` (process pool), AVL through `subprocess.Popen` with `communicate()` in the runtime's thread pool (never an asyncio
  subprocess transport, #1188).
  Never call `asyncio.run` inside the package; always re-raise `CancelledError`; clean up subprocesses and
  temp dirs on cancellation.
- **Two interfaces, one engine (ARCHITECTURE §8.4).** `compute()` is stateless (the one exception is the memoised shipped `Build` in `build.py`, an immutable package artefact): no cache, no module-level
  mutable state, no global pool. `CachedKernel` is the stateful facade that owns the cache, in-flight
  dedup and resources, and injects its `MemoryCache` into the same engine. Never add state to `compute()`;
  never let the cache change a value. There is one in-memory cache, no scopes, no disk cache (ARCHITECTURE §8.4).

## Code style, types and linters

- **PEP 8** (https://peps.python.org/pep-0008/): naming (`snake_case` functions and variables,
  `PascalCase` classes, `UPPER_CASE` constants), imports at the top in standard / third-party / local
  order, one statement per line. Formatting is not discussed; `ruff format` decides (line length 100).
- **Pydantic v2 for every data type** that crosses a module boundary: input, request, result, errors,
  warnings, provenance, the canon model, cache entries. `model_config = ConfigDict(extra="forbid")`;
  results and canon-model types also `frozen=True`. `frozen` does not protect `dict` fields or arrays: never
  mutate a model after construction, and never hand the same object to two calls — the cache stores
  serialised entries and deserialises a fresh object per hit (ARCHITECTURE §8.4). **Where constraints live depends on the model:**
  result and canon-model types carry their invariants in the model (`Field(gt=0)`, validators), not in
  scattered `if` checks; **input models** (`AircraftInput`, `AirplaneGeometry`, `ComputeRequest`) carry
  types and structure only — physical admissibility (lengths > 0, finite numbers, ≥ 2 sections, inline
  airfoils) is `validate.py`'s, so it returns `input_errors` instead of raising (ARCHITECTURE §8.11). No `dict` as an ad-hoc record.
- **Types everywhere.** Every function, method and attribute is annotated, including return types and
  tests' helpers. Modern syntax (`X | None`, `list[float]`). `Any` only at a documented boundary (e.g. raw
  front matter in the importer), never as a shortcut; `cast` and `# type: ignore` need a comment saying why.
- **Docstrings** (Google style) on every public module, class and function: what it does, its units, and
  which canon slug it implements.
- **Linters are the gate, not a suggestion.** Before every commit, all three must be clean:

  ```bash
  poetry run ruff check aero_kernel          # strict rule set in aero_kernel/ruff.toml
  poetry run ruff format --check aero_kernel
  poetry run pyright aero_kernel             # strict mode (pyrightconfig.json)
  ```

  Never silence a finding to get green (`# noqa`, `# type: ignore`, relaxing `ruff.toml`) without a
  comment naming the reason; a finding usually points at a real problem.

## Logging (ARCHITECTURE §8.14)

Logs are how you check that your code runs as intended. Write them while you write the code, not after a
failure.
- `logger = logging.getLogger(__name__)` per module. Never configure handlers or levels in the package.
- **`DEBUG`** for every engine step (node start/end/duration/status, cache hit/miss, world, solver call and
  settings), **`INFO`** one line per `compute()` and per import, **`WARNING`** only for degraded operation
  (tool missing, timeout, dead worker), **`ERROR`** with the traceback for `internal` errors, logged once, in
  `errors.internal_error_from_exception` (`logger.error(..., exc_info=exc)`: it receives the exception
  outside an `except` block, so `logger.exception` does not apply).
- **Every default taken is logged** (maintainer, 2026-10-14), once per call and slug, with slug, value,
  unit, source and `call_id`, always at `INFO` (maintainer, 2026-10-17). A target default is declared by
  the `default_target_used` practice warning in the result; every default is in `provenance.defaults_used`. An absent `optional:` parameter: `INFO` line
  with the route taken.
- Other domain warnings and expected outcomes (`not_applicable`, `skipped`, `not_converged`) are in the
  result, not at `WARNING` level.
- Context in `extra` (`call_id`, `quantity`, `formula`, `world`); lazy `%s` formatting; English;
  never full geometry or polars, only hashes and the values that matter.
- Pool workers do not log; they return diagnostics and the adapter logs them.
- To see what your code did: `poetry run pytest aero_kernel/tests -k <test> -o log_cli=true --log-cli-level=DEBUG`.

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
