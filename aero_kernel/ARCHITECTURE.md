# aero_kernel — Architecture (lean arc42)

> **Status: draft for approval (#1174).** Once the maintainer approves it, this document is the
> **binding template** for every ticket of Epic #1173 (#1174–#1178). Whoever changes something stated
> here changes this document first.
>
> **Precedence.** Where a ticket of the epic says something different (e.g. "manifest",
> `@formula(slug, inputs, outputs)`, graph from `scripts/canon_to_json.py`), this document wins and the
> ticket is corrected.
>
> **What is not in here:** the content of the formulas (→ the canon in `_reversa_sdd/calculations/canon/`)
> and the decisions (→ ADRs and register K, chapter 9). This document links; it does not repeat.

---

## 1. Goals and quality goals

**Task.** `aero_kernel` executes the calculation canon. It receives the complete data of one aircraft and
a list of requested quantities, and returns values, intervals, warnings and errors. Whether an input is
assumed or measured is irrelevant to it. It computes; it does not judge (canon rule A10).

**First purpose (Epic #1173).** Show that the canon computes stably before the canon is approved. Later it
becomes the app's single source of computation (register epic "implement the calculation canon").

| Prio | Quality goal | Measured by (→ ch. 10) |
|---|---|---|
| 1 | **Extensible without contradictions.** A new canon entry is an addition, not a redesign. | Q1, Q2 |
| 2 | **Traceable.** Every value leads back to its canon entry, application, tool and versions. | Q3 |
| 3 | **Stable and honest.** No silent substitutes; what cannot be computed is named. | Q4, Q5 |
| 4 | **AI-ready.** Errors are structured, machine- and human-readable, and carry a hint on what to do. | Q6 |
| 5 | **Efficient without state.** Identical inputs are never computed twice. | Q7 |

## 2. Constraints

- Python 3.11–3.12 with Poetry.
- Dependencies are limited to numpy, pydantic, aerosandbox and avl-binary.
- The fast CI tier runs **without** AeroSandbox and AVL.
- One unit per quantity, the canon's: SI-coherent, with the canon's declared exceptions (angles in
  `deg`, `deg/s`; `Wh`; `rpm/V`). No conversion inside the kernel except the geometry's millimetre fields.
- Everything in the source tree is English (ADR 0029).
- PEP 8, Pydantic v2 for all data types, full type annotations; enforced by `ruff` (strict rule set in
  `aero_kernel/ruff.toml`) and `pyright` in strict mode (module CLAUDE.md).
- The ADRs listed in chapter 9 are binding.

## 3. Context and boundary

**`aero_kernel` is a pure Python library with an asynchronous programming API**, not a service. It has no
REST endpoint, no HTTP and no server process. It offers **two interfaces** with the same request and
result types:

```python
from aero_kernel import compute, CachedKernel, MemoryCache, AircraftInput, ComputeRequest

# 1. stateless: a pure function, no cache, no state between calls
result = await compute(AircraftInput(...), ComputeRequest(quantities=["stall-speed"]))

# 2. cached: a facade object that holds a cache and puts it in front of the same computation
kernel = CachedKernel(cache=MemoryCache(max_entries=10_000))     # or DiskCache(path=...)
async with kernel:
    result = await kernel.compute(AircraftInput(...), ComputeRequest(quantities=["stall-speed"]))
```

Both interfaces return the same values for the same input (Q7). Which one a caller uses is its choice: tests,
golden values and the robustness run use the stateless function; the app will use one long-lived
`CachedKernel`.

The input and output types are Pydantic models, so they also have a JSON form and a JSON Schema. That is
for data exchange (golden files, agents, a later REST or MCP layer), not a network interface. Exposing the
kernel over REST or MCP is the app's job, through the register epic: the app's services `await compute()`
and the existing `app/api/v2` and MCP layers stay where they are (ADR 0019, ADR 0025).

```
        tests (aero_kernel/tests)        robustness run (tools/robustness.py)
                     \                     /
                     compute(AircraftInput, ComputeRequest) ──→ ComputeResult
                     |   aero_kernel/   |
                     └──────────────────┘
          reads: its own canon model (canon/canon_model.json, shipped in the package)
   import: external canon document (_reversa_sdd/calculations/canon/) ──→ importer ──→ canon model
           (a deliberate, separate step; never at runtime)
          calls: AeroSandbox (AeroBuildup, Opti, atmosphere), AVL (subprocess)
   later:  app/services · copilot (#902) · MCP — through the register epic, not now
```

- **Inward boundary.** `aero_kernel/` **never** imports `app/`, `cad_designer/` or `scripts/`. The app calls
  the kernel, never the other way round.
- **No second producer (ADR 0022).** Until the register epic switches the app over, the app shows no values
  from the kernel.
- **Not inert (ADR 0021).** The kernel is still in use from day one: tests, the CI job and the robustness run
  all call it (Epic #1173).
- **No triggering, no storage.** When computation runs (K28, K29) and where results are kept (snapshot) is
  the caller's decision. The kernel supplies the dependency subtree (A1) and the cost class for that.

## 4. Solution strategy

1. **The kernel interprets its own machine-readable canon model.** The canon document in `_reversa_sdd/` is
   the human source. A structured **import process** (ch. 8.9) translates it into a versioned JSON **canon
   model** that ships inside the package. The model holds quantities, formulas, applications,
   preconditions, units, roles, worlds and cost class. At runtime the kernel reads only this model, never the
   external document. Code registers **implementations** per formula only; dependencies never come from
   code.
2. **The whole canon is declared,** including what is not implemented yet (`not_implemented`).
3. **Formula ≠ application.** One implementation per formula. Applications bind inputs and carry a
   condition (canon README, "One formula, several applications").
4. **Method worlds instead of interval arithmetic** (A11, ADR 0027). Each world runs through the whole
   subtree, and the interval is formed only at the end.
5. **Stateless core, cache as a facade.** `compute()` is a pure function without state. `CachedKernel` is a
   facade that owns a cache and the in-flight deduplication and delegates to the same engine (ch. 8.4).
   Cache keys come from content and versions, never from identities.
6. **Solvers behind thin adapters.** Formulas talk to adapters, never to AeroSandbox or AVL directly. That
   keeps them mockable in the fast tier, and capability errors arise in one place.

## 5. Building blocks

```
aero_kernel/
  api.py            async compute() — the stateless interface (pure function)
  cached.py         CachedKernel — the cached facade (owns cache, in-flight deduplication, resources)
  engine.py         walks the graph; takes an optional NodeStore (none = stateless)
  runtime.py        executor, concurrency limit, cancellation
  geometry.py       AirplaneGeometry and its sub-models (format mirror, mm → m at parse, ch. 8.11)
  schema.py         AircraftInput, ComputeRequest, ComputeResult, QuantityResult, Polar, KernelWarning,
                    Provenance (Pydantic, extra="forbid"); re-exports AirplaneGeometry and KernelError
  canon/            canon_model.json         the interpreted canon (versioned, committed)
                    canon_model.schema.json  JSON Schema of the canon model
                    IMPORT_REPORT.md         report of the last import (source commit, diff, findings)
                    model.py                 the canon-model types (Pydantic; the schema is generated from them)
                    load.py                  load + schema/version and reference check at runtime
  importer/         parse.py · normalise.py · validate.py · diff.py · write.py · __main__.py
                    external canon document → canon model (ch. 8.9); not imported at runtime
  graph.py          subtree, order, world expansion, upstream_failed
  registry.py       @formula(slug), @precondition(slug, id), @postcondition(slug, id) — implementations ↔ canon model (ch. 8.12)
  formulas/         one file per canon formula (file name = slug, with underscores)
  solvers/          aerobuildup.py · avl.py · opti.py · atmosphere.py · data.py (KAT, APC providers)
  cache.py          NodeStore protocol; MemoryCache (LRU), DiskCache
  validate.py       physical admissibility of the input and `values` against the canon (ch. 8.11)
  canonical.py      canonical JSON and the SHA-256 helper, shared by the canon model hash and the cache keys
  errors.py         error catalogue (ch. 8.1): `ErrorCategory`, `KernelError`, the closed code table
                    (code → category), `FormulaError`, upstream aggregation; imports no other module
  __init__.py       public API; adds the NullHandler to the `aero_kernel` logger (ch. 8.14)
  tools/            robustness.py (#1178)
  tests/            unit, property, golden, traceability and error tests
```

| Block | Responsible for | Must not |
|---|---|---|
| `api` | accept the request, validate, walk the graph, build the result | compute |
| `canon` (load) | load the canon model, check schema and version | read `_reversa_sdd/`; know formulas |
| `importer` | translate the external canon document into the canon model | run during `compute()` |
| `graph` | dependencies, worlds, error propagation | call tools |
| `formulas/*` | exactly one canon formula | compute a second formula; judge thresholds (A10) |
| `solvers/*` | call the tool, report its version, translate tool errors | know canon names |
| `cache` | map keys to results | change results |

## 6. Runtime view — one call

```
await compute(aircraft, request)
 1 validate(aircraft)                      → any finding: ComputeResult with input_errors, nothing computed
 2 resolve request.quantities              → unknown slug: that quantity error invalid_input, rest goes on
 3 canon_model.subtree(quantities)         → applications, topologically sorted (ch. 8.13)
 4 per application: evaluate its condition → not met → status not_applicable (+ dependents, ch. 8.13)
 5 per application and world assignment (A11), in graph order, concurrently where independent:
     cost class minutes and include_long_runs off → skipped (long_run_not_included)
     a predecessor failed/skipped/not applicable  → status by precedence (ch. 8.13)
     required input value missing                → error invalid_input, code missing_input
     [CachedKernel only] key from the direct input values → hit → reuse, from_cache = true
     else check preconditions, then await the implementation inside the time budget (ch. 8.10)
       success → outputs + warnings (regime warnings come from the solver adapters, ch. 8.2)
       FormulaError / other exception → KernelError (other exceptions → internal)
 6 per quantity: merge worlds → value, or interval {min, max, worlds}
 7 ComputeResult (ch. 8.3) with provenance
```

## 7. Deployment

A Python library inside the same repository (package `aero_kernel/`), imported in-process by its callers;
no server, no process of its own. AVL runs as a subprocess in a temporary
directory.

## 8. Cross-cutting concepts

### 8.1 Error model (AI-ready)

An error means **no value**. A value with a caveat is a **warning** (8.2), not an error.

`KernelError` fields:
- `code`, `category`, `retryable`, `escalate`
- `quantity`, `formula`, `application`, `world`, `input_path`
- `message`: the cause, in natural language
- `hint`: what to do
- `detail`: data

| Category | retryable | escalate | Meaning | Example hint |
|---|---|---|---|---|
| `invalid_input` | no | no | input is physically inadmissible | "Chord at `wings.W.x_secs[2].chord` must be > 0." |
| `unsupported_configuration` | no | no | the method does not cover this layout, or a target lies above what the method itself can reach (code `target_above_method_maximum`, `detail` = the maximum reached and the input at which it occurs, e.g. the roll rate and δ_a) | "The textbook neutral-point formula needs a horizontal tail." |
| `not_implemented` | no | no | the canon formula has no implementation yet | "`max-sustained-turn-rate` is in the canon, not in the kernel." |
| `not_converged` | yes | no | the solver found no solution | "Raise the accuracy tier or change the start value." |
| `timeout` | yes | no | the time budget was exceeded | "Raise the budget or request it as a long run." |
| `tool_unavailable` | no | yes | a tool is missing (AeroSandbox, AVL) | "Use an environment with the aero dependencies." |
| `upstream_failed` | as predecessor | as predecessor | a predecessor quantity has no value | "Fix `stall-speed` first." |
| `internal` | no | yes | programming error | "Report it; attach input and provenance." |

`escalate = true` means an agent cannot resolve this itself; a human has to act. `retryable` and `escalate`
follow from the category (the table), never set per error; for `upstream_failed` they are derived from the
root causes (below).

**The code table is closed.** Every `code` belongs to exactly one category and is listed in `errors.py`; a
new code is added there, never invented at the raise site. So an agent can rely on the codes, and a root
cause's flags follow from its code alone.

**`not_applicable` is no category.** It is a `QuantityResult.status` with a `reason` (ch. 8.3), not a
`KernelError`: the application does not exist (no separate flap and aileron → no butterfly approach), so
nothing failed. The category enum holds only the eight rows above.

- **`compute()` never raises for computational failure.** Everything is in the `ComputeResult`. It raises
  only `asyncio.CancelledError` and Pydantic `ValidationError` when the caller builds a malformed
  `AircraftInput` or `ComputeRequest` (wrong types, unknown fields). Physically inadmissible but well-typed
  input is not an exception: it is returned in `ComputeResult.input_errors`.
- **`upstream_failed` with several failed predecessors:** `retryable` is true only if every root cause is
  retryable; `escalate` is true if any root cause escalates. `detail.causes` lists the root
  `KernelError`s (quantity, code), never the chain in between.
- **Violated precondition or postcondition:** the canon entry says per check `on_violation: warning | error`.
  `warning` → a `defect` warning and the value is returned. `error` → `unsupported_configuration`, code
  `precondition_violated` / `postcondition_violated`, `detail.precondition` / `detail.postcondition` = its
  id; for a postcondition **all outputs of that application** (in that world) are discarded, never
  returned (ADR 0020): they come from one evaluation, so a failed check on one invalidates the others.

### 8.2 Warnings

`KernelWarning` (not `Warning`, which would shadow the builtin), the `DesignWarning` shape of ADR 0020:
`severity` (`practice` | `defect`), `code`, `message`, plus `origin` (the quantity where it arose; `None`
until the engine sets it, since adapters know no canon names), `world` (the method world it arose in, or
`None`) and `detail` (the values it carries, e.g. the default taken or NeuralFoil's confidence). There is
no separate `quantity` field: the reporting quantity is the `QuantityResult` that lists it.

Warning codes are a **closed table** like error codes (ch. 8.1), each with its fixed severity; a source
adds its codes when it is built. A quantity's result lists its own warnings and those of its subtree,
deduplicated by their **full content** (`code`, `origin`, `world`, `message`, `detail`): a warning that
reaches a quantity along several subtree paths is one warning, while two warnings that differ only in
`detail` (`geometry_deflection_ignored` for two devices, both with origin `airplane`) stay two. The engine
collects and deduplicates; the result type only rejects exact duplicates. A V_S evaluated at Re 2·10⁴ thus warns on V_S and on everything computed from it.

Sources:
- the regime (ADR 0028): chord Re band 3·10⁴–1·10⁶, "bubble-sensitive" below 7·10⁴, Mach ≤ 0.3, warned up
  to 0.6. **Checked where Re and Mach become known:** in the aerodynamic solver adapters, per evaluation,
  from the section chords in metres, the evaluated V and the speed of sound at the altitude. Not in input
  validation, which does not know V.
- violated or unchecked preconditions
- a design target taken from its canon default (`default_target_used`, ch. 8.11)
- the route an `optional:` parameter selected (ch. 8.5)
- tool validity conditions, raised in the adapters (ch. 8.8), and reference points an entry cites
- active bounds in the optimiser

The A11 "not validated" marker is the field `QuantityResult.validated`, not a warning.

### 8.3 Result contract

`ComputeResult` fields:
- `quantities`: one `QuantityResult` per requested slug, in request order. Only requested quantities are
  returned, not the intermediate nodes of the subtree.
- `input_errors[]`: `KernelError`s of category `invalid_input` from validation (step 1). Non-empty means
  nothing was computed and `quantities` is empty.
- `provenance` (ch. 8.4).

`QuantityResult` fields:
- `slug` and `unit` (the quantity's canon unit, ch. 8.11)
- `status`: `ok`, `not_applicable`, `skipped` or `error`
- `reason` for every status other than `ok`: machine-readable `code` plus natural-language `message`
  (`not_applicable`: `condition_not_met`, `not_given` or `depends_on_not_applicable`, ch. 8.5; `skipped`: `long_run_not_included` or
  `depends_on_skipped`; `error`: see `error`)
- `value` **or** `interval {min, max, worlds{assignment: value}}` (ch. 8.13), exactly one when `ok`, neither
  otherwise. `value` is a float in the quantity's canon unit, or a structured value of the quantity's `type`
  (ch. 8.12). **v1 returns floats only**; the union widens with the first non-scalar formula, no placeholder
  type before that (ADR 0021). Numbers are **strict and finite**: `value`, the interval bounds and world
  values accept an `int` or `float`, never a `bool` or a numeric string, and never NaN or ±inf. The same holds inside every free JSON field
  (`detail` of errors and warnings, `solver_settings`): a non-finite number anywhere in the tree is
  rejected — one shared recursive check in `errors.py` — because JSON would silently turn it into `null`
  (ADR 0020).
- `ok` requires `tool` and `application` (Q3: every value leads back to its application and tool). A **requested** quantity whose `type` is not `scalar` (`polar-stall`,
  `airplane-landing`, a `curve`) is therefore, per quantity, `error` with category `not_implemented`, code
  `non_scalar_result`, decided at request time before anything is computed; the rest of the request is
  computed. The canon model is not touched: such quantities are requestable by the canon, only the v1
  result type cannot carry them. **Internal node values are not constrained by this:** the engine passes
  polars, configured geometry and curves between nodes as the structured types of ch. 8.12; only what
  enters a `QuantityResult` is float-only.
- `reason` codes are a closed enum of their own, separate from error codes; `ok` has neither `reason` nor
  `error`, `error` has `error` and no `reason`, the other two have `reason` and no `error`.
- `tool` and `application`
- `validated`: `false` — no value is validated against flight data (canon A11: "not validated")
- `warnings[]` and `error`
- `from_cache`: whether the value was served from the cache (ch. 8.4)

No internal paths or mechanisms in any field (ADR 0019).

### 8.4 Provenance, cache key and the two interfaces

`Provenance`:
- kernel version (`aero_kernel.__version__`, a constant bumped by hand: the repository is not an installed
  package) **and the build digest** (below), which identifies the exact code even when nobody bumped the
  version (Q3)
- canon model hash and its source commit (the canon state)
- tool versions (aerosandbox, NeuralFoil model, AVL): one non-empty version string per tool **the call actually
  used**; empty when only pure formulas ran
- accuracy tier (A3) and solver settings
- `defaults_used`: every canon default the call took, as `{slug, value, unit, source}` (ch. 8.11)

**Cache key** = SHA-256 over the canonical JSON of:
- the scope (see below), the application id and the world assignment
- the **direct input values** of the node: the values bound to its parameters, i.e. the outputs of its
  predecessors or the caller's input values. A node's key thus changes exactly when something in its
  subtree changes value (A1), without tracking leaf inputs.
- the **build digest**: one hash over the `.py` files of the installed `aero_kernel` package except
  `tests/`, `tools/` and `importer/`, plus `canon_model.json`; computed lazily on first use. Any code or canon change invalidates every entry. That wastes hits after an
  upgrade but can never serve a stale value; no hand-maintained implementation version exists that could be
  forgotten.
- the tool versions (aerosandbox, NeuralFoil model, AVL), the accuracy tier, and the `content_hash()` of every
  provider the node reads (ch. 8.8). There are no other solver settings in v1; one that is added later
  goes into `ComputeRequest`, the key and the provenance together.

**Canonicalisation:** sorted keys; floats as their exact shortest round-trip representation (`repr`),
`-0.0` as `0.0`; NaN and infinity cannot occur because validation rejects them. Numbers are **not**
rounded: rounding would let two different inputs share a key.

**What is stored:** the node's outputs (all output parameters of the application in that world) and its
own warnings, **including its pre- and postcondition warnings**. A hit returns them unchanged; both depend
only on the direct input values (which are part of the key) and on the outputs computed from them, so they
need not run again. Errors, `skipped` and `not_applicable` are never stored; a `timeout` or `not_converged` is
recomputed next time.

**No object is shared between calls.** `frozen=True` stops attribute assignment, not in-place mutation of
a `dict` field (`Interval.worlds`, `detail`) or of an array inside a structured value; that is a Pydantic
limit, accepted rather than worked around with custom immutable types. The guarantee is structural
instead: a store keeps entries in a **serialised form** (canonical JSON / bytes) and every hit
deserialises a fresh object, and every `compute()` builds a fresh `ComputeResult`. A caller who mutates
its result can corrupt only its own copy. Kernel code never mutates a model after construction; results
need not be hashable.

**Two interfaces, one engine.**

- **`compute()`, stateless.** A pure function. It keeps nothing between calls: no cache and no
  deduplication. Two calls with the same input compute twice.
- **`CachedKernel`, stateful facade.** An object that owns a `NodeStore` (`MemoryCache` or `DiskCache`) and
  the in-flight deduplication.
  - Its `compute()` has the same signature and the same result type.
  - It delegates to the same engine and passes in its store.
- **Why node level.** Caching happens **per graph node**, not per whole request. That way, a change to one
  input expires only its subtree (A1). The facade therefore injects the store into the engine instead of
  wrapping the whole call. Seen from outside it is still a facade: a separate object, put in front of the
  same computation, with no influence on the values.

**Per call on the facade:** `await kernel.compute(aircraft, request, cache="use" | "refresh")`.

| Mode | Reads | Writes | In-flight dedup | Use |
|---|---|---|---|---|
| `use` (default) | yes | yes | yes | normal operation |
| `refresh` | no | yes | no | force a recomputation and replace the stored entries, e.g. after a tool upgrade |

A call without the cache is simply the stateless `compute()`, so the facade needs no "off" mode.

Cache settings (size, disk location) are passed when the facade is created, never read from the environment.
Each `QuantityResult` reports `from_cache`, which is always `false` from the stateless interface.

**Cache scopes (multi-user callers).** A caller serving several users or aircraft can partition the cache.

```python
await kernel.compute(aircraft, request, scope="aircraft/3f2c…")   # default: scope="shared"
await kernel.drop_scope("aircraft/3f2c…")                          # e.g. the aircraft was deleted
```

- **Correctness never depends on scopes.** Keys are content hashes over everything that affects a value, so a
  hit can never return a value for different inputs. That holds in every scope, including `shared`.
- **Isolation.**
  - The scope is part of the key. An entry in one scope is never visible from another.
  - In-flight deduplication works only within a scope, so there is no cross-scope timing side channel.
- **Deletion.** `drop_scope(scope)` removes every entry of a scope, in memory and on disk.
- **Limits.** `MemoryCache` and `DiskCache` accept an optional limit per scope in addition to the global one,
  so one scope cannot evict the others.
- **Pluggable store.** `NodeStore` is an **async** protocol: `await get(scope, key) -> Entry | None`,
  `await put(scope, key, entry)`, `await drop_scope(scope)`. `Entry` is the JSON form of the stored outputs and
  warnings. A caller may supply its own store, e.g. a database or Redis per tenant.
- **`MemoryCache`:** one LRU over all scopes (`max_entries`), plus an optional `max_entries_per_scope`
  that evicts the least recently used entry **of that scope**.
- **`DiskCache`:** one SQLite file (stdlib `sqlite3`) at `path`; values as JSON, never pickle; limits
  `max_bytes` and optional `max_bytes_per_scope`, evicting by last access time.
- **One pool for all scopes.** One `CachedKernel` serves many scopes with one process pool, so no per-aircraft
  kernel objects are needed.
- **The caller assigns scopes.** What a scope stands for (aircraft, user, version snapshot K28, or `shared`)
  is the caller's decision. The kernel knows neither users nor aircraft; it only separates by name.
- **Not in the stateless `compute()`.** It has no cache and therefore no scope.

### 8.5 Applications and preconditions

An **application** is a formula plus the bindings of its inputs, a condition and the name of the output
quantity.

- Every input parameter of the formula is bound either to a **quantity** or to a **constant with source**
  (ADR 0028). Every output parameter is bound to a quantity, or explicitly to `null` in `produce`: the
  implementation still returns it (ch. 8.12), the application does not expose it. Example: `stall-speed`
  returns its α sweep as `polar`; only the clean application produces `polar-stall`, the take-off,
  landing and inverted applications write `polar: null`. A forgotten output is an import finding, an
  unexposed one is a declaration.
- An application has at most two kinds of condition; without either it exists always:
  - `when`: one term of the closed vocabulary over facts of the aircraft geometry (`has_vertical_tail`,
    `has_aileron`, …). The canon `README.md` defines the vocabulary; each term is implemented once in
    `graph.py`. Terms over control devices go by the **role** a surface acts in, not by its name (maintainer:
    "a flap is every surface that acts like a flap"): `has_aileron` holds for a surface acting as aileron,
    flaperon or elevon; the butterfly condition needs a flap-acting surface **and a distinct**
    aileron-acting one, because crow deflects both at once (a flaperon alone cannot). Without ailerons the roll quantities are `not_applicable`, code `condition_not_met`.
  - `given`: a list of input quantities (`role: input` or `target`, no `default`). The application exists
    only if every one of them is supplied in `AircraftInput.values`. A target the designer did not set is
    not a missing input but no requirement (ch. 8.11).
  Unmet, the application's outputs are `not_applicable` with `reason.code` `condition_not_met` (`when`) or
  `not_given` (`given`). Both kinds are declared in the entry; the importer never infers a condition.
- **A named condition is a quantity, never a mechanism** (A2, ch. 8.13). A configured aircraft
  (`airplane-landing`) or a speed (`approach-speed`) is its own quantity, produced by its own
  application. There is no per-application override of an input, no operating-point and no configuration
  field.
- **An embedded relation is not an edge** (`embeds:`, a list of formula slugs). Where a formula's
  canonical form evaluates another canon formula's relation *inside* itself, over its own variables, it
  reads that relation's inputs, not its output quantity. Example: the climb, turn, level-speed, dive and
  mass-envelope problems carry `V` and `n_prop` as decision variables with `T(V, n_prop)` and the torque
  balance as constraints, and `static-thrust-to-weight` evaluates `T(V = 0)`; all of them embed the
  propulsion relations (`motor-propeller-equilibrium`, `advance-ratio-from-speed`, `propeller-table-lookup`,
  `thrust-at-airspeed-from-coefficient`) and bind motor, battery and propeller inputs directly. A solver
  tool (AeroBuildup inside `stall-speed`) is named by `tool:`, not by `embeds:`. An embedded formula may
  itself be an optimisation: `mass-envelope` solves the stall-speed, max-level-speed and
  best-rate-of-climb problems at each mass of its own sweep.
  - **What is listed:** every formula the canonical form names **directly**, as `<slug>` or, for a formula
    with several applications, `<slug>.<application-id>` per application whose checks apply
    (`stall-speed.clean`, `stall-speed.landing`); a bare slug of a multi-application formula is an import
    finding. Embedding is transitive; the importer computes the closure (embedding `max-level-speed`
    brings in its propulsion relations), so a relation the form also names directly is listed again, and
    nothing else needs to be repeated. **An item embeds that application as written** — its bindings
    (quantities and `{const, source}`, e.g. `stall-speed.landing`: `airplane: airplane-landing`, `n_load: 1`)
    and its checks; a bare slug means the formula's single (default) application. One meaning of
    "application" everywhere, nothing bound twice.
  - **Variables** (`variables:`, a list of quantity slugs on the embedder): the quantities the embedder
    solves for or sweeps itself **and that the closure reads as quantities** (`mass-envelope`:
    `variables: [aircraft-mass, flight-speed]` — mass swept, speed solved). Internal decision variables
    are not listed: α, which is no quantity of the closure, and `propeller-speed`, which the closure
    produces. Inside the closure a listed quantity is **always** the
    embedder's variable, even if the embedder also reads that quantity as an input for another purpose
    (`m_current: aircraft-mass`, the current mass on the sweep). Nothing is implied: a quantity is a
    variable only if listed.
  - **Not embedding — a varied configuration.** A form that re-solves another formula's problem under a
    configuration it varies itself (`butterfly-approach`: the stall problem in crow configuration, swept
    over the mix `s`) cannot embed the fixed application. It states the same guard as its **own**
    postcondition on its output (`optimum_at_first_cl_peak` on every point of the curve, K32); the check
    function is shared with `stall-speed`'s (one implementation per check, as per formula; module
    `CLAUDE.md`). No embed with a varied
    configuration exists in the format.
  - **Inputs:** every quantity an embedded application binds is a `variables:` entry (then the embedder's
    variable takes its place), produced inside the closure (`propeller-speed`, `thrust-coefficient`), or an
    input of the embedder — that input is the value edge through which it arrives (`airplane_ldg:
    airplane-landing`). Constants come with the application and are never re-bound.
  - **Importer checks:** every slug and application id exists; the closure is acyclic; the input rule
    above; every `variables:` entry is read somewhere in the closure; no formula in the closure has
    `uncertainty: interval` (worlds are per node, ch. 8.13; an uncertain embedded relation needs a decision
    first).
  - **Engine:** an embedded formula is no node — no cache entry and no preconditions of its own (its inputs
    are the embedder's variables or inputs; the embedder's preconditions apply). **Its postconditions do
    run**, on every embedded evaluation — they guard what the relation returns (e.g. `stall-speed`'s
    `optimum_at_first_cl_peak` at each mass of the sweep, K32): the unscoped ones always, a scoped one when
    its application is listed. A violation is the embedder's: `on_violation: error` makes it
    `postcondition_violated` with `detail.embedded` = `<slug>.<application-id>`, `detail.postcondition` = the
    id and the variable values of the failing evaluation; `warning` becomes the embedder's `defect` warning
    with the same detail. The embedder node is cached as a whole; the build digest covers the shared code
    (ch. 8.4). Approval of the embedder follows approval of its closure.
- **Optional parameters** (`optional:`, a list of input parameter names). The formula receives `None`
  when the bound quantity has neither a value nor a default, and selects its route by data. Unlike
  `given`, the application exists either way. The entry states, per route, which of three outcomes holds:
  - **a declared method limitation** → a `practice` warning naming the route (ADR 0020). Example: `r_m`
    of `motor-propeller-equilibrium`, route A without it (Q-PT-6).
  - **the canon's own definition for that data** → no warning. Example: `flap_deflection` of
    `airplane-configuration` on an aircraft without flaps: there is no configuration, the aircraft is
    unchanged (stall-speed, 2026-10-02); this is not a substitute.
  - **the value is needed after all** → the formula raises `FormulaError(invalid_input, missing_input)`
    with `input_path = values.<slug>`, exactly as the engine would (ch. 8.11). Example: `flap_deflection` absent
    on an aircraft that has flaps.
  Every absent optional parameter is logged at `INFO` with the route (ch. 8.14).
- An entry without `applications:` has exactly one application: every parameter bound to its default
  quantity from `inputs:` / `outputs:`, condition "always".
- **Keys are always parameter names** (snake_case), in the canon fields, in `x` and in the return value of
  an implementation (ch. 8.12). Quantity slugs (kebab-case) appear only as binding targets.

A **precondition** is an executable check per application, scoped by its optional `applications: [<id>, …]`
in the canon entry (absent = every application of the formula; e.g. `alpha_range_past_inverted_stall`
of `stall-speed` only for `inverted`). The engine runs it only for the listed applications; for the
others it is neither run nor reported as unchecked. It is registered with `@precondition(slug, id)`
(ch. 8.12) and run before the implementation, so its `parameter` must be an **input** parameter.

A **postcondition** (`postconditions:`, same shape `{id, parameter, on_violation, applications}`) checks
what a computed value claims — that `cl_max` really is the C_L,max at the stall Reynolds number, that the
sweep bracketed the inverted stall. It runs **after** the implementation, on the inputs and all its
outputs (also the ones an application does not expose), registered with `@postcondition(slug, id)`. Its
`parameter` must be an **output** parameter. The importer rejects an output parameter in
`preconditions:` and an input parameter in `postconditions:`.

Both kinds return one of three states:
- 🟢 held
- 🔴 violated: a `defect` warning or an error, as `on_violation` in the canon entry says (ch. 8.1)
- ⚪ unchecked, including "no check registered yet": a `practice` warning

### 8.6 Consistency rules (checked by the importer)

- One producer per quantity; a second path only as a probe (A7).
- Unique symbols and slugs (A8).
- Targets only as `role: target` (A9).
- Units consistent across bindings (A4); dimensional check of law entries. **The importer is the
  authority** for model validity; it ports the logic of `scripts/check_canon.py` (it may not import
  `scripts/`). `check_canon.py` remains an authoring aid for the canon document (#1181) until
  `importer --check` runs in CI, then it is removed (ADR 0021).
- Every reference (inputs, bindings, worlds) resolves to a quantity in the model.

- Separate namespaces: the calculation canon now, the sizing canon (K31) later (ch. 8.9).

At load time the kernel additionally checks that every registered implementation and precondition has its
slug and id in the model.

Violations are **canon findings**, not runtime errors: the importer reports them, writes no model, and the
canon document is corrected.

### 8.7 Cost class

Each formula has a cost class: `instant`, `seconds` or `minutes`, carried in the canon model.

**Where it comes from (interim, O14 question 3 open).** The importer takes the canon field `cost:` where it
is set (#1181), otherwise derives it from the tool: APP, ATM, GEO, KAT, APC → `instant`; AB, AVL, OPT →
`seconds`. `minutes` is never derived, only declared. Should O14 assign the class to the app instead, the
field leaves the canon and the kernel only reports it.

**Long runs are opt-in per request.** `ComputeRequest.include_long_runs` (default `false`) switches on
formulas of cost class `minutes`. The caller decides beforehand; the kernel neither asks back nor defers.
- Flag off: a requested `minutes` quantity is returned with `status: skipped`, no value, and
  `reason.code = long_run_not_included`. Quantities depending on it are `skipped` with
  `reason.code = depends_on_skipped`. Everything else in the request is computed normally.
- Flag on: the quantity is computed like any other; the time budget of the request applies.
- **Documentation:** every `minutes` quantity is marked as long-running in the generated Python API reference (docstrings and the JSON Schema of the Pydantic types) and
  in `IMPORT_REPORT.md` (Appendix A, column "cost class"), so a caller knows before calling.
- `skipped` is not an error: nothing failed, the caller chose not to include it.

When the app turns the flag on (K28: on explicit user request, on an immutable version snapshot) is the
caller's responsibility.

### 8.8 Tools and data sources

- Tools: APP (pure), ATM, GEO, AB, AVL, OPT.
- **Solver adapters** (`solvers/`) are split between two tickets:
  - **#1174 builds the base**: `SolverAdapter` with `available() -> bool` and `version() -> str`
    (capability check → `tool_unavailable`, Q10), `run_cpu(fn, *args)` (process pool), `run_avl(files,
    commands)` (async subprocess in a temp dir, killed and cleaned up on cancellation, Q17), and
    `regime(chords_m, v, altitude) -> list[Warning]` (ADR 0028 check, ch. 8.2). Tested with a stub solver.
  - **Tool validity warnings belong to the adapter**, like the regime: they hold for every formula that uses
    the tool, so no canon entry repeats them and they are no precondition. Each names its source. AVL:
    `|p·b/2V| > 0.10`, the documented range of the primer (`defect`). AeroBuildup with a deflected
    control surface: NeuralFoil's `analysis_confidence` at `α_eff` of the deflected strips as a value, and
    "δ range of the τ fit unknown" (`practice`). A reference point a specific entry cites (Sadraey's
    20–25°) is emitted by that formula via `ctx.warn`, `practice`, and stated in the entry text.
  - **#1175 adds the domain methods** (`aerobuildup.sweep`, `avl.stability`, `opti.solve` …), each built on
    the base, alongside the first formula that needs it.
  - Adapters know no canon names. They return warnings without `quantity`; the engine sets `origin` to
    the quantity of the node whose call produced them.
- Data: KAT (component catalogue) and APC (propeller tables).
- Data comes **from the caller**, either inline in the input or as a provider with a content hash. The
  kernel loads nothing on its own.
- A provider is an async protocol in `solvers/data.py`: `content_hash() -> str` (part of the cache key of
  every node that reads it) and one lookup method per source. The lookup signatures are defined with the
  first formula that uses them (the probes `airplane-components`, `propeller-table-lookup`); the core chain
  reads no provider.

### 8.9 Canon import — from the canon document to the canon model

The kernel does not read the canon document. It interprets **its own canon model**. Changes to the canon
reach the kernel **only through an import**, a deliberate, reviewable step:

```
python -m aero_kernel.importer <canon-document-dir> [--check]
```

| Stage | Does | Fails when |
|---|---|---|
| 1 Parse | reads the front matter of every formula and quantity entry (fields above); never prose | a required field is missing or malformed |
| 2 Normalise | slugs, unit spellings to one closed symbol set (`1` for dimensionless, `—` folded into it), roles, kinds, tools to closed vocabularies; resolves `[[…]]` references | an unknown unit, kind, tool or role |
| 3 Validate | JSON Schema of the canon model; consistency rules (ch. 8.6); dimensional check | any rule is violated |
| 4 Diff | compares with the committed canon model: entries added, removed or changed; marks **breaking** changes (inputs, units, outputs, applications) and lists the affected implementations and golden tests | — (only reports) |
| 5 Write | writes `canon_model.json` (sorted, stable formatting), its content hash, the source commit of the canon document and the importer version; writes `IMPORT_REPORT.md` (diff, findings, Appendix A table) | — |

**What the importer reads (maintainer decision 2026-10-14, migration in #1181).** Every entry carries its
structure in the front matter; the prose explains, the importer never reads it. **The definition of the
fields, the `when` vocabulary and the quantity types is the canon `README.md`, section "Machine-readable
fields"** (in the canon document, #1181). This document does not repeat them, so the two cannot drift
apart; the importer's JSON Schema is written against that section. What the importer adds on top:

- **Formula entries** are recognised by `entry: formula`, **quantity entries** by `kind: quantity`.
- **Parsing.** Plain YAML with PyYAML `safe_load`. The canon uses no key or value that YAML 1.1 reads as a
  boolean (`on`, `off`, `yes`, `no`, `y`, `n`); a precondition names its parameter with `parameter:`.
  A boolean where the schema expects a string is a stage-1 finding.
- **`# ESCALATED:` comments** mark an undecided field. An entry that carries one is a stage-1 finding: the
  importer imports nothing until the maintainer has decided it (all or nothing, below).
- **`cost:`** is taken only where the entry sets it; otherwise derived from `tool` (ch. 8.7).

**The model** (`canon_model.json`, JSON Schema `canon_model.schema.json`) holds, per namespace, `quantities`
and `formulas` with **every field the canon README section "Machine-readable fields" defines, 1:1**, same
names and nesting — this document does not re-list them, so a new field cannot be forgotten here. The
fields the README keeps for readers and for approval are dropped, and this is the **complete** list —
any other README field is carried: `canon` (it becomes the dict key, the slug), `entry` and the quantity's
`kind: quantity` (document-structure markers; the container says which it is), `output` (a readable copy
of `outputs` / `produce`, checked equal by `check_canon.py`), `status` (the approval state; it changes no
value, every result is `validated: false`), `shape` (an approval classification), `tags`, `tex`,
`source_status` and `dimensional_check`. A new README field is carried unless this list is extended.
Normalisation adds nothing but: `bind` values become a quantity reference or `{const, source}`; absent
optional fields get their stated default (`when`/`given` absent = always, precondition `applications`
absent = all, `cost` derived, ch. 8.7); the default application is written out explicitly; the `embeds`
closure (ch. 8.5) is stored alongside the listed embeds. Fixture models in
`tests/fixtures/` follow exactly this shape and are validated against `canon_model.schema.json`. The model
also holds `schema_version`, `content_hash`, `source_commit` and
`importer_version`. References are slugs; namespaces are written `<namespace>:<slug>` (`calc:stall-speed`,
later `sizing:…`), and a bare slug in a request means `calc:`.

**Shape and identity of the model file** (decided for #1174, unit 6):
- **Types first, schema generated.** `canon/model.py` holds the Pydantic types (frozen, `extra="forbid"`,
  invariants in the model, ch. 8.11). `canon_model.schema.json` is generated from them (`python -m aero_kernel.canon.schema_file [path]`) and committed; a
  test fails when the committed schema differs from the generated one. Never hand-written.
- **Layout.** `{schema_version, content_hash, source_commit, importer_version, namespaces: {"calc":
  {quantities: {<slug>: …}, formulas: {<slug>: …}}}}`, dict keys bare slugs. **Every reference inside the
  model is fully qualified** (`calc:stall-speed`, embeds items `calc:stall-speed.clean`); application ids
  and parameter names stay bare. Every `embeds` and `embeds_closure` item is normalised to
  `<ns>:<slug>.<application-id>` (a single-application formula as `.default`); a bare item does not load.
  Absent `when`, `given` and check `applications` are stored as `null` (= always / all). Only a request's bare slug means `calc:`.
- **`schema_version`** is the integer `1` (`Literal[1]`), raised on every change of the model's shape. The
  loader reads it **before** type validation, so a newer model reports its version, not a cascade of
  unknown fields; any other version is `internal`, escalate. The loader raises `CanonLoadError` carrying
  that `KernelError`; turning it into per-quantity results is the api's job (`compute()` never raises,
  ch. 8.1). `source_commit` is a 40-hex git SHA, `importer_version` a non-empty string.
- **`content_hash`** is `"sha256:" + hex` of the canonical JSON of `namespaces` only — the canon's content,
  not its provenance (`source_commit`, `importer_version` and the hash itself are outside it), so two
  imports of identical content from different commits hash alike. Canonical JSON is the one used for
  cache keys (ch. 8.4): sorted keys, separators `,` `:`, UTF-8 without ASCII escaping, floats as `repr`;
  one helper in `canonical.py`, shared with the cache. The model's validator recomputes it: a hand-edited model does not
  load.
- **Closed vocabularies live in the model types**, so the importer's stage 2 and 3 check against them:
  `kind` (law, procedure, optimization, fit, rating), `tool` (APP, ATM, GEO, AB, AVL, OPT, KAT, APC),
  `role`, `type`, the `when` terms, `on_violation`, `cost` and **`unit`** (the canon's symbols after
  normalisation, `—` folded into `1`).
- **The model checks its own structural integrity** (a fixture or a file that breaks it does not load):
  every reference resolves; every application binds every input and produces every output (`null` =
  unexposed); a precondition names an input, a postcondition an output; `worlds` (≥ 2, unique, snake_case)
  exactly with `uncertainty: interval`; `given` slugs are bound by their application, role input/target,
  without default; `positive` only on input/target, a default then > 0; `variables` exactly with `embeds`;
  `embeds` ⊆ `embeds_closure` and every closure item resolves. **Cross-formula rules stay with the
  importer** (ch. 8.6): one producer per quantity, unit consistency, closure correctness and acyclicity,
  cost derivation. The implicit application is written out with id `default`.
- **The embeds closure** is a field of each embedder, `embeds_closure`: the sorted, de-duplicated items
  reachable through `embeds` (the direct ones included), computed by the importer.
- **Loader** (`canon/load.py`): version pre-check, Pydantic validation (the JSON Schema is generated from
  the same types; `jsonschema` is a test dependency only, used to validate fixtures against the committed
  schema), and — once a registry exists — that every registered implementation and check has its slug and
  id in the model (ch. 8.6).
- **`values` against the canon** — `unknown_quantity`, `not_an_input`, `non_positive_value` (ch. 8.11) —
  are `validate.validate_values(values, model)`, built with the model types (unit 6), called next to
  `validate_aircraft` in step 1.

Rules:
- **All or nothing.** Any failure in stages 1–3 writes nothing. The importer lists the findings with file,
  field and message; they are fixed in the canon document, not in the model.
- **The model is never edited by hand.** It is only produced by the importer, so model and document cannot
  drift apart unnoticed.
- **Idempotent.** Importing the same canon document twice yields a byte-identical model.
- **`--check`** writes nothing and reports whether the committed model still matches the canon document.
  CI runs it and reports drift; whether drift fails the build follows #1177. The canon is still `draft`,
  so drift is expected.
- **A breaking change** in the diff requires the affected implementations and golden values to be updated in
  the same change set (the traceability test, Q11, enforces it).
- **Schema version.** `canon_model.json` carries the schema version. The kernel refuses to load a model with
  an unknown schema version (`internal`, escalate).
- **Several canons.** The calculation canon and, later, the sizing canon (K31) are imported into separate
  namespaces of the same model format.

### 8.10 Asynchronous API and concurrency

The kernel behaves like an asynchronous Python API: `compute()` is a coroutine, it never blocks the
caller's event loop, it can be cancelled, and it limits its own resource use.

- **Non-blocking.** All heavy work runs off the event loop:
  - CPU-bound solver work (AeroBuildup, NeuralFoil, IPOPT via `asb.Opti`) runs in a **process pool**. The
    spawn context mirrors `app/services/cad_service.py`, because CasADi/IPOPT and numpy do not reliably
    release the GIL.
  - AVL runs through `asyncio.create_subprocess_exec`.
  - Formula code itself runs on the loop; it is cheap by contract (ch. 8.12). Only the solver adapters
    leave the loop. There is no size threshold.
- **Concurrency from the graph.** Independent nodes of the subtree and world assignments (A11) run
  concurrently (`asyncio.TaskGroup`). The dependency graph decides what may run in parallel, never the
  formula code.
- **Bounded.** Execution resources are passed in, never global:
  - an executor (process pool) and a concurrency limit.
  - The **stateless `compute()`** takes them as optional keyword arguments (`executor=`,
    `max_concurrency=`, default `os.cpu_count()`). The limit counts concurrent **solver calls** (pool tasks
    and AVL subprocesses); graph nodes waiting on them cost nothing. Without an executor it creates a pool on the first
    solver call and shuts it down before returning, so it stays free of state. Spawning costs about a
    second; callers that compute often pass an executor or use `CachedKernel`.
  - **`CachedKernel`** owns one pool and one limit for its lifetime. They are created lazily and closed by
    `async with` or `aclose()`.
  - Nothing starts at import. Resources are not results: they never change a value.
- **Cancellation.**
  - Cancelling the `compute()` task cancels all child tasks.
  - It kills running AVL subprocesses and removes their temporary directories.
  - Work already running in the process pool is allowed to finish but its result is discarded, because
    pool workers cannot be interrupted safely.
  - `asyncio.CancelledError` is always re-raised, never turned into a result.
- **Time budget.** `ComputeRequest.time_budget_s` (default `None` = no budget) is one wall-clock budget for
  the whole request, enforced with `asyncio.timeout`. Quantities still open when it expires get
  `error.category = timeout`; quantities already finished are returned.
- **Cache under concurrency (`CachedKernel` only).** The store is safe for concurrent use. **In-flight
  deduplication** (mode `use`): when two concurrent requests need the same key, the second awaits the first
  one's future instead of computing it again.
- **No hidden loop.** The kernel never calls `asyncio.run`, never creates or closes the caller's loop and
  keeps no loop-bound global state. It works inside FastAPI, in pytest-asyncio and in plain
  `asyncio.run(compute(...))` from scripts.
- **Not in v1: `compute_iter()`** (maintainer, 2026-10-14). An async generator yielding each
  `QuantityResult` as soon as it is final can be added later without changing `compute()`; first the canon
  is built and checked against real calculations.

### 8.11 Input and request

```python
class AircraftInput(BaseModel):          # extra="forbid"
    airplane: AirplaneGeometry           # docs/geometry-format/airplane-geometry.schema.json
    values: dict[str, float]             # canon slug → value in the quantity's canon unit

class ComputeRequest(BaseModel):
    quantities: list[str]                # canon quantity slugs, not formula slugs
    include_long_runs: bool = False      # ch. 8.7
    time_budget_s: float | None = None   # ch. 8.10
    accuracy: Literal["xxsmall", "xsmall", "small", "medium", "large", "xlarge", "xxlarge", "xxxlarge"] = "xxxlarge"
                                         # NeuralFoil model size; A3 / O10: a solver setting
```

**Providers** (KAT, APC; ch. 8.8) are runtime objects, not data, and therefore **not** part of
`AircraftInput`: they are passed as `compute(aircraft, request, providers={"KAT": …})`. `AircraftInput` and
`ComputeRequest` stay pure data with a JSON form and a JSON Schema.

**Binding of canon input quantities to the input:**
- **Units.** A value is given, and a result returned, in the unit the canon model declares for the
  quantity — SI-coherent, with the canon's declared exceptions: angles in `deg` (and `deg/s`), energy in
  `Wh`, the motor constant in `rpm/V`. The kernel converts none of them; a formula converts internally
  where a tool needs radians or SI base units.
- **What `values` may hold.** Only slugs of **scalar** canon quantities with `role: input` or `role:
  target`. An unknown slug is an `input_errors` entry, code `unknown_quantity`; a slug of a derived or
  output quantity (no override of a computed value), or of a non-scalar input (`airplane`, which arrives as
  `AircraftInput.airplane`), is `not_an_input` — "not an input of `values`", the message naming where the
  quantity comes from instead; both with `input_path = values.<slug>`.
- **What a request may name.** Only quantities with `role: derived` or `output`. An unknown slug is, per
  quantity, `error` / `invalid_input` / `unknown_quantity`; an input or target slug is `not_requestable`
  (its value is the caller's own); the rest of the request is computed.
- The quantity `airplane` (type `airplane`) is `AircraftInput.airplane`.
- Every other quantity with `role: input` or `role: target` is `AircraftInput.values[<slug>]`. Today these
  are `aircraft-mass`, `centre-of-gravity`, `altitude`, `flight-speed`, `angle-of-attack`, `load-factor`,
  `gravity`, `sea-level-air-density`, the control-device angles (`flap-deflection-takeoff` /
  `-landing`, `aileron-deflection`, `elevator-deflection-up` / `-down`, `crow-flap-deflection` /
  `crow-aileron-deflection`; deg, geometry sign convention, no default) and the `*-target` quantities. Assumptions are values like any
  other (R1); whether a value is assumed or measured is not the kernel's concern.
- A missing value falls back to the quantity's `default` in the canon model. Every default taken is
  listed in `provenance.defaults_used` and **logged** (maintainer, 2026-10-14; ch. 8.14). Whether it is
  also a result warning depends on the role:
  - **`role: input`** (physical constants such as `gravity` 9.80665 m/s², `sea-level-air-density`; A5):
    no warning. The constant is the value, sourced in the canon, not a substitute for a caller's choice.
    Logged at `INFO`.
  - **`role: target`** (e.g. the stall margins `approach-/touchdown-/takeoff-speed-margin-target`): a
    `practice` warning `default_target_used`, `origin` = the target slug, message with value and source,
    inherited by every quantity whose subtree reads it (ch. 8.2). A target is the designer's decision; a
    default stands in for one the designer did not make, which is a declared substitution in the sense of
    ADR 0020, and domain practice because it carries a source. Logged at `WARNING`.
  Without a default, the quantities that need it get `invalid_input`, code `missing_input`, with
  `input_path = values.<slug>`; the rest of the request is computed. **Exception:** an application whose
  `given` names the missing slug does not exist, so its outputs are `not_applicable`, code `not_given`
  (ch. 8.5); an application that reads the same slug without `given` still gets `missing_input`. A
  parameter listed in `optional:` receives `None` instead (ch. 8.5).
- **The passed mass always wins** (maintainer, 2026-10-14). Mass comes only from
  `values["aircraft-mass"]`; the geometry's `total_mass_kg` is not used. Otherwise no "what if?"
  calculation at a different mass would be possible. If both are set and differ, the call is **not**
  aborted, but a warning is issued: code `conflicting_mass`, severity `practice`, `origin` =
  `aircraft-mass`, message with both values. Like every warning it is inherited by all quantities whose
  subtree reads the mass (ch. 8.2).
- **Airfoils are inline.** The kernel loads nothing on its own (ch. 8.8), so `airfoil` in
  `AirplaneGeometry` is a NACA designation or inline coordinates. A file path is `invalid_input`, code
  `unresolved_airfoil`; resolving paths is the caller's job (the test fleet uses a test helper).

**Units.** The format is metres and degrees (AIRPLANE-GEOMETRY.md §2); the spar fields `spare_*` are
**metres** in the format (millimetres only in the app's database, which the kernel never sees). The
format's real millimetre fields are `hinge_spacing`, `side_spacing_root` / `side_spacing_tip`,
`turbulator.height_mm` and every field of `servo`. Parsing `AirplaneGeometry` converts exactly these to
metres: the JSON key stays the format's (alias), the Python attribute carries the SI unit in its name
(`height_mm` → `height_m`, `hinge_spacing` → `hinge_spacing_m`); the format key is a `validation_alias` only, so a dumped
model has SI keys that a re-parse rejects (`extra="forbid"`) instead of scaling a second time. That validator is the only place where
units are converted; after parsing everything is SI. `AirplaneGeometry` mirrors the format's JSON Schema
(`docs/geometry-format/airplane-geometry.schema.json`); a test checks that every schema field is
accepted.

**Input models carry types, not physics.** `AircraftInput`, `AirplaneGeometry` and `ComputeRequest`
declare structure and types only: `extra="forbid"`, required vs optional, enums, strict numbers (a `bool`
or a string where a number belongs is a `ValidationError`). They carry **no physical constraint** — no
`gt=0`, no `allow_inf_nan=False`, no minimum section count — because physically inadmissible but
well-typed input must come back as `input_errors` with an `input_path` (ch. 8.1), produced by
`validate.py`, not raised. Result and canon-model types are the opposite: their invariants live in the
model (ch. 8.3).

**Validation (step 1, physical admissibility only).** `validate.validate_aircraft(aircraft: AircraftInput) ->
Validation` returns `errors` (`KernelError`s of category `invalid_input`, all of them, not the first) and
`warnings` (input facts the engine attaches to every dependent: `conflicting_mass`, origin
`aircraft-mass`; `geometry_deflection_ignored`, origin `airplane`). It needs no canon model; the checks
of `values` slugs against the canon (`unknown_quantity`, `not_an_input`) are a second function added with
the canon loader, not a stub now (ADR 0021). **A rule exists only for a field the kernel reads**;
CAD-only fields (`number_interpolation_points`, servo geometry, step paths) are not validated. One rule,
one code, one test:

| code | rule |
|---|---|
| `non_finite_number` | NaN or ±inf anywhere in the geometry fields the kernel reads or in `values` (exact leaf path, tuple elements as `[i]`) |
| `non_positive_length` | a chord ≤ 0; fuselage semi-axes `a`, `b` ≤ 0; a wing whose span — the summed Euclidean length of its `xyz_le` chain — is 0 (path: its `x_secs`) |
| `non_positive_exponent` | a fuselage super-ellipse exponent `n` or `n_lower` ≤ 0 |
| `non_positive_thickness` | an airfoil of thickness ≤ 0 (inline contour, or NACA thickness digits `00`) |
| `too_few_sections` | a wing or a fuselage with fewer than two `x_secs` |
| `invalid_airfoil_contour` | inline coordinates with fewer than 3 points, or whose first and last point do not both lie at the contour's largest `x` (a blunt trailing edge is allowed; no tolerance is invented) |
| `unresolved_airfoil` | an airfoil string that is not a NACA 4-digit designation (`^naca\d{4}$`, case-insensitive, no spaces): the only kind a solver builds without loading data; a 5-digit or 6-series section is passed inline |
| `segment_on_last_section` | the last `x_sec` carries a `trailing_edge_device`, `spare_list` or `turbulator`: there is no segment for it, so the kernel would silently drop it |
| `control_surface_without_device` | a `control_surface` without the `trailing_edge_device` it is a projection of: its role would be unknown |

`values` are checked here for finiteness only. **Their admissibility comes from the canon model, never
from a slug written in code:** a quantity entry may declare `positive: true` (strictly > 0 by definition —
a mass, a density, gravity; a fact, not a design judgement, A10), and the canon-loader unit checks every
supplied value of such a quantity, code `non_positive_value`, `input_path = values.<slug>`, together with
`unknown_quantity` and `not_an_input`. `validate_aircraft` names no quantity slug except in the two
input-fact warnings, whose origins §8.11 fixes (`aircraft-mass`, `airplane`). A dict key is the identity of a wing or fuselage (paths use
it); a differing `name` is a label and no finding. The geometry's `total_mass_kg` is never used, so only its
finiteness is checked. `detail` carries `{"value": …}`: the number, or `"nan"` / `"inf"` / `"-inf"` as a
string (free JSON fields stay finite, ch. 8.3). Findings come section by section in document order (within a section in rule order), then `values` by
slug.

The kernel never reads `control_surface` (a derived projection; role and hinge come from the device,
angles from `values`), so a disagreement between the two is no finding. From a `trailing_edge_device` it
reads exactly `role`, `rel_chord_root`, `rel_chord_tip` (the hinge line), `symmetric`, `mix_gain_primary`,
`mix_gain_secondary` (AVL mixing of dual roles), and `deflection_deg` only to report it ignored; its span is
the segment it sits on. Every other device field is unread and not validated.

`input_path` is a path into `AircraftInput`: attribute names joined by `.`, list indices as `[i]`, dict
keys as `["…"]` with JSON string escaping (`airplane.wings["Main wing"].x_secs[2].chord`), except that a
`values` key matching the slug pattern is written dotted (`values.aircraft-mass`) and any other `values`
key bracketed. Paths use the **format's** field names (the JSON keys, e.g. `hinge_spacing`), not the SI
attribute names, so the caller can find the field in its document. Regime is not validated (ch. 8.2).

**Control devices are angles; stops are not limits** (maintainer, 2026-10-14). For **every** control device
— flap, aileron, elevator, rudder, crow — the canon works with deflection **angles in degrees**, given as
design inputs (`flap-deflection-landing`, `aileron-deflection`, `elevator-deflection-up`, the full-crow
angles, …) or solved for as results
(`aileron-deflection-required-approach`); never with a fraction or percentage of a stop. The geometry's
`positive_deflection_deg` / `negative_deflection_deg` are the designer's construction data, possibly a
first draft; the canon is used to find out which stop a wanted performance needs. The kernel therefore
**never reads, checks, clamps or warns** about a stop — not in validation, not in a formula, not in an
adapter — and `not_applicable` never follows from a stop. A deflection value is only validated for being
finite. **No fixed angle range bounds a deflection** (D6, 2026-10-14): a number would be invented, since
neither tool documents one. What remains is per method world (ch. 8.13):
- **A method that saturates** (AeroBuildup: clean airfoil at `α_eff = α + τ·δ`, no flap separation) is
  searched upward from 0 until its result stops increasing. That computed maximum is the method's own
  limit; a target above it is `target_above_method_maximum` (ch. 8.1) in that world — never a clipped
  angle (ADR 0020), never a judgement (A10).
- **A linear method** (AVL, linear in δ) is solved directly; it always has a solution.
- Everything else is a **warning carrying values**, no pass/fail: tool validity conditions from the adapter
  (ch. 8.8) and labelled reference points the entry cites (Sadraey §12.4.3, separation onset about
  20–25°, transport/GA, not checked at model Reynolds numbers; ADR 0028).

**The geometry's current deflections are not read either** (2026-10-15). `deflection_deg` on a
trailing-edge device and `deflection` on its `control_surface` are the state an editor last computed in,
not a design input. The kernel's aircraft is the geometry with **every control device at 0°**; a
configuration or a formula sets the angles it needs from `values` (`flap-deflection-landing`,
`aileron-deflection`, …) or solves for them (trim, `aileron-deflection-required-*`). `values` always
wins, as with the mass: a non-zero geometry deflection is ignored and reported once per device as a
`practice` warning `geometry_deflection_ignored` (`origin` = `airplane`, `detail` = device and angle),
inherited like `conflicting_mass`. From the device the kernel reads its **role** (which surface acts as
flap, aileron, elevon, …), its hinge geometry and its span, never an angle.

**Requests name quantities.** A formula with several outputs runs once per application and world; each
requested output is its own `QuantityResult`. Requesting two outputs of the same formula calls it once.

### 8.12 Formula implementation contract

```python
@formula("stall-speed")
async def stall_speed(x: Inputs, ctx: Context) -> dict[str, Value]:
    polar = await ctx.solvers.aerobuildup.sweep(x["airplane"], ...)   # leaves the loop
    ...
    return {"stall_speed": v_s, "cl_max": cl_max}       # output parameter names, snake_case
```

- **One coroutine per formula.** `x` maps the formula's **parameter names** (canon `inputs:`) to values, as
  bound by the application; the formula never sees which application or quantity it serves. It returns a
  dict over its **output parameter names**, every one of them. Values are floats in the quantity's canon unit (ch. 8.11) or instances of
  the structured types in `schema.py`, one per quantity `type` of the canon `README.md`: `scalar` → `float`,
  `airplane` → `AirplaneGeometry`, `curve` → `Curve`, `curve_pair` → `CurvePair`, `polar` → `Polar`. A new
  type is a canon decision first, then a type here.
- **`ctx`** carries: `solvers` (the adapters), `world` (the active world of this formula, if it has
  worlds), `accuracy`, `warn(code, message, severity)` and `embedded(item)` (ch. 8.5, below). Nothing else:
  no cache, no request, no global.
- **Formula code is cheap.** It runs on the event loop. Anything heavy goes through an adapter; adapters
  run CPU work in the process pool and AVL as an async subprocess (ch. 8.10).
- **Picklability** concerns only adapters: what they send to the pool is a module-level function and plain
  data. Formulas themselves never cross a process boundary.
- **Failure.** Raise `FormulaError(category, code, message, hint, detail=None, input_path=None)` for an
  expected failure. Formulas and adapters may raise only `invalid_input` (e.g. `missing_input` for an
  optional parameter that is needed after all, with `input_path`), `unsupported_configuration`,
  `not_converged` and `tool_unavailable`; `timeout`, `upstream_failed`, `not_implemented` and `internal`
  belong to the engine. The engine turns a `FormulaError` into a `KernelError`, adding `quantity`,
  `formula`, `application`, `world` and `retryable`/`escalate` from the category. Any other exception
  becomes `internal`. Never return a substitute value (ADR 0020).
- **Preconditions** are separate functions, `@precondition("stall-speed", "<check-id>")`, run only for the
  applications the canon scopes them to (ch. 8.5), taking the same
  `x` and returning `held | violated | unchecked` with a message. **Postconditions**,
  `@postcondition("stall-speed", "<check-id>")`, take `x` and the implementation's full return dict `y`
  and return the same three states.
- **Embedded relations** (ch. 8.5). The module of an embedded formula exposes its relation as a plain,
  module-level function over parameter names (numpy- and CasADi-compatible where an OPT formula embeds
  it); its `@formula` coroutine and every embedder call that one function, so there is one implementation
  per relation (ADR 0022). For an embedded optimisation the function is its problem (built into a given
  `asb.Opti` or solved at given values of the embedder's variables); the formula's module decides which and
  documents it. An embedder obtains it **only** through `ctx.embedded("<slug>.<application-id>")`, which
  returns the relation with that application's constants and quantity bindings already applied (the values
  arrive through the embedder's inputs) and its postconditions; the embedder passes only its `variables:`.
  Evaluated as a whole, the handle runs the postconditions on every call; built into an outer problem,
  the embedder passes the solved values to the handle's `check(...)`. The traceability test (Q11) checks that every `embeds:` item has that function and that the
  embedder requests each listed item through `ctx.embedded` (static check).
- **Registration** is by decorator at import of `aero_kernel.formulas`.
  - **Shape.** `registry.Registry` holds, per qualified formula slug, one implementation, its embeddable
    relation if any, and per `(slug, kind, check id)` one check function. The decorators `formula`,
    `relation`, `precondition` and `postcondition` are methods of a registry; the module-level names are
    those of the **default registry**, which `aero_kernel.formulas` fills at import and then **freezes**
    (any later registration raises). A frozen registry is a static table of code, not call state, so the
    stateless rule (ch. 8.4) holds; the engine takes the registry as a parameter (default: the frozen
    default), and tests build their own `Registry()` instead of touching the default.
  - **Signatures.** `@formula(slug, interface="sha256:…")` on an `async def f(x, ctx) -> dict`;
    `@relation(slug)` on the module-level relation function (ch. 8.5); `@precondition(slug, id)` on a
    plain `def check(x) -> CheckResult`, `@postcondition(slug, id)` on `def check(x, y) -> CheckResult`
    (`CheckResult`: `held | violated | unchecked` plus a message). Decorators stack, so one check function
    serves several `(slug, id)` pairs — one implementation per check (`optimum_at_first_cl_peak` for
    `stall-speed` and `butterfly-approach`). A duplicate registration or a non-coroutine `formula` is a
    `RegistryError` at import — a programming error, never a result.
  - **Parameter names are not repeated in code** (precedence note at the top). The decorator carries the
    formula's **interface fingerprint** instead: `sha256_of` the formula's sorted input names, output names
    and `optional` in the canon model. The traceability check computes it from the loaded model and compares
    (Q11): a changed parameter fails it until the implementation is updated and its fingerprint with it. It
    also checks that every registered slug and check id exists in the model, that every embedded item has
    a registered relation, and that every embedder requests each of its items through `ctx.embedded`
    (static check). It runs as a test in CI and once when a kernel is built; at runtime a formula whose
    fingerprint does not match is `internal`, code `stale_implementation`, escalate, for its quantities
    only. A model formula without an implementation is `not_implemented` (Q1).

### 8.13 Graph semantics

**Operating points.** A named condition is part of the quantity's name (A2): `stall-speed`,
`minimum-drag-speed` and `approach-speed` are separate quantities, each produced by its own application.
They need no operating point from the caller. The generic inputs (`flight-speed`, `altitude`,
`angle-of-attack`, `load-factor`) are ordinary input values (O10, A2: a generic quantity may be an input,
never an output), so one call evaluates one operating point. Several operating points are several calls;
`CachedKernel` makes the shared subtree free. There is no operating-point expansion in the graph.

**Named conditions inside one call** follow the same rule, quantity by quantity. Where a formula needs a
value at a fixed condition, the chain up to it has an application per condition, each producing a
quantity that names it: the take-off and landing stall speeds read `airplane-takeoff` /
`airplane-landing` (type `airplane`, produced by `airplane-configuration` from the design inputs
`flap-deflection-takeoff` / `flap-deflection-landing`; without flaps it is the unchanged aircraft, not a
fallback). `airplane-configuration` sets the given deflection as the flaps' state (`deflection_deg`)
exactly, **also beyond the stops** (ch. 8.11). Its `flap_deflection` is `optional:`: without flaps an absent
deflection gives the unchanged aircraft (no warning); with flaps it is `missing_input`, and its dependents
`upstream_failed`. A deflection given for an aircraft without flaps has nothing to act on: unchanged
aircraft plus a `practice` warning `deflection_without_flap`, because a supplied value is not used. A sampled curve over angle of attack is a quantity of type `polar`
whose slug names its evaluation condition (A2): `polar-stall`, the clean sweep at `V_S` with solver
drag, an output of `stall-speed` read by `stall-onset-detection`. The negative extremum `C_L,min` is not
read off that polar but is `stall-speed`'s `inverted` application (`n` bound to `{const: -1, source}`)
at its own Reynolds number. The engine needs nothing beyond applications for any of
these.

**Functions of a variable the formula solves for** are not quantities. Thrust over airspeed is not a curve
`T(V)` handed to the optimisers: they solve for `V` and `n_prop` themselves and embed the propulsion
relations (ch. 8.5). `thrust-at-airspeed` stays a scalar at the given `flight-speed`; the static value is
`static-thrust-to-weight` embedding the same relations at `V = 0`. One relation, one implementation, no
sampled grid and no `-static` chain.

**Worlds (A11, ADR 0027).**
- A formula with `uncertainty: interval` declares its worlds in the canon. Each world is a run of the same
  implementation with `ctx.world` set; worlds are not separate formulas (A7).
- A **world assignment** fixes one world per uncertain formula in the subtree, written
  `neutral-point=avl,roll-rate=aerobuildup`, formulas sorted by slug, so JSON and cache keys are
  deterministic. **This format is binding** wherever a world appears (`Interval.worlds` keys, the `world`
  of a warning or error): non-empty `<formula-slug>=<world>` pairs, slug kebab-case
  (`[a-z][a-z0-9]*(-[a-z0-9]+)*`), world snake_case as in the canon's `worlds:` (`[a-z][a-z0-9]*(_[a-z0-9]+)*`):
  lowercase letters and digits, the first character a letter, unique slugs, sorted by slug, joined by `,` without spaces. A single formula's
  world is one pair (`neutral-point=avl`), never a bare world name. One parse/format helper in `errors.py`
  (which imports no other kernel module) validates it; `schema.py` imports it from there. The engine runs the **Cartesian product** over the
  uncertain formulas in a quantity's subtree (A11 rule 3); a node outside an uncertain formula's subtree
  runs once and is shared by all assignments.
- The interval of a quantity is min and max over its assignments; `worlds` lists every assignment with its
  value. Never interval arithmetic. For `curve` and `curve_pair` min and max are pointwise over the swept
  variable, which must be the same grid in every world (else `internal`); for `airplane` and `polar` there is
  no min/max, only `worlds`.
- Worlds follow **value edges**, not `embeds:`. A formula that reads an uncertain quantity (`mass-envelope`
  reads `neutral-point`) is in its subtree and runs once per assignment like any node; all its outputs
  carry the interval, also those that do not depend on it numerically (zero width). Splitting such
  outputs into separate formulas is a canon decision, not an engine rule.
- **A failed assignment** makes the quantity an error, not a narrower interval: the error of the failed
  assignment, with `detail.worlds_ok` holding the values that did compute. A silently narrowed interval
  would be an undeclared fallback (ADR 0020). Example: `aileron-deflection-required-approach` with the target above the
  AeroBuildup maximum is an error even though AVL, linear in δ, returns an angle; the AVL value is in
  `detail.worlds_ok`.
- **Continuous causes** (a parameter evaluated at its bounds, A11 rule 2) and the **monotonicity check**
  (rule 4) are declared in the canon model but not in v1: such a formula returns `not_implemented`, code
  `continuous_uncertainty`. The core chain has only method worlds.

**Status propagation.** A node whose predecessors are not all `ok` takes the status by precedence:

| Predecessors (any of) | Node | reason / category |
|---|---|---|
| `error` | `error` | `upstream_failed` (ch. 8.1 for retryable/escalate) |
| `skipped`, none `error` | `skipped` | `depends_on_skipped` |
| `not_applicable`, none of the above | `not_applicable` | `depends_on_not_applicable` |

Every error propagates the same way, `missing_input` included: the quantity that reads the missing value
directly gets `missing_input`, its dependents `upstream_failed` with the cause in `detail.causes`.

An error dominates: computing the long run would not help a node whose other input failed. A predecessor
counts only if the node actually needs it; an unused output of a multi-output formula does not propagate.

### 8.14 Logging

Logs are **diagnostics**, not the contract: values, warnings and errors reach the caller only through the
`ComputeResult` (ch. 8.3). Logs answer a different question: *did the code run the way it was meant to?*
They are the first thing a developer or an agent reads to check a change and to trace an error.

**Library rules.**
- One logger per module, `logger = logging.getLogger(__name__)`, all below `aero_kernel`. The package root
  adds only a `logging.NullHandler`. The kernel never configures handlers, levels or formats and never
  calls `basicConfig`; that is the caller's job (app, pytest, scripts).
- Messages are English (ADR 0029), lazily formatted (`logger.debug("cache hit %s", key)`), and carry the
  context as `extra`: `call_id` (a short id per `compute()` call), `quantity`, `formula`, `application`,
  `world`, `scope`. With `call_id` the lines of one call can be followed through concurrent tasks.

**Levels.**

| Level | What | Examples |
|---|---|---|
| `DEBUG` | every step of the engine, to check the code runs as intended | subtree and order; per node: start, end, duration, status; cache hit/miss with key prefix; world assignment; solver call with its settings and duration; precondition result |
| `INFO` | one line per `compute()` call and per import | request (slugs, `include_long_runs`, budget), result counts per status, total duration, cache hits; importer: entries added/changed/removed |
| `WARNING` | the kernel ran, but in a degraded way an operator should know about, or it decided something on the designer's behalf | tool unavailable, time budget exceeded, a process-pool worker died, a disk-cache entry unreadable and recomputed; **a design target taken from its default** |
| `ERROR` | a programming error | every `internal` error with its traceback, logged exactly once where it is translated (`internal_error_from_exception`, `exc_info=exc`); the exception text goes only here, never into the result (ADR 0019) |

- **Every default taken is logged** (maintainer, 2026-10-14), once per `compute()` call and slug, when
  the input is resolved, so also on a full cache hit: `"default used: %s = %s %s (%s)"` with slug, value,
  unit and source, `extra` = `call_id`, `quantity` (the slug), `role`. Level by role: `input` (physical
  constants) → `INFO`, `target` → `WARNING` (ch. 8.11). The same applies to an `optional:` parameter that
  is absent: one `INFO` line per call and parameter, `"optional input absent: %s.%s, route %s"` (formula,
  parameter, route), alongside its result warning (ch. 8.5).
- **Otherwise not logged as `WARNING`:** domain warnings (regime, preconditions, `conflicting_mass`) and
  expected outcomes (`not_applicable`, `skipped`, `not_converged`). They are in the result; at most `DEBUG`.
- **No bulk data.** Geometry and polars are never logged in full, only their hash, size and the values that
  matter for the step. No user data above `DEBUG`.
- **Process-pool workers do not log.** A worker returns its diagnostics (duration, iterations, solver status)
  with its result; the adapter logs them in the parent process. That avoids lost or interleaved lines
  from spawned processes.
- **Tests use the logs.** Engine tests assert key `DEBUG` events with `caplog` (e.g. "cache hit", "node
  skipped") where the log is the cheapest proof of behaviour, such as Q7 and Q18.

## 9. Decisions (references only)

- **ADRs:**
  - 0003: ASB is the default, AVL an exception
  - 0019: no internals in the interface
  - 0020: one warning channel
  - 0021: nothing inert
  - 0022: one producer per quantity
  - 0026: solver drag
  - 0027: intervals over worlds
  - 0028: regime by flow physics
  - 0029: English source tree
- **Register entries:**
  - K26: neutral-point worlds
  - K27: lateral stability from AVL
  - K28/K29: triggering
  - K30: ISA
  - K32: stall up to the first C_L peak
- **Canon rules** A1–A11 in `ANFORDERUNGEN.md` §4.

## 10. Quality scenarios (= test cases)

| No. | Scenario | Test |
|---|---|---|
| Q1 | A new canon formula without implementation | The request returns `not_implemented` with the slug; no code changed |
| Q2 | All 57 canon entries mapped onto the model | Appendix A complete; the import succeeds without a schema change |
| Q3 | Every value is traceable | The result carries slug, application, tool, canon model hash and source commit |
| Q4 | The solver does not converge | `not_converged`; successors `upstream_failed`; other quantities still compute |
| Q5 | Layout without a separate flap and aileron | `butterfly-max-mix` is `not_applicable`, code `condition_not_met`: no error, no substitute value. `stall-speed-landing` computes and equals `stall-speed` (no configuration, not a fallback) |
| Q6 | Every error category | Serialises to JSON with `message` and `hint` |
| Q7 | Second identical call | `CachedKernel` (`use`): no formula call, `from_cache` true; `refresh` and stateless `compute()`: formula called; values bit-identical across all three |
| Q8 | Input mass ≤ 0 | `invalid_input` with `input_path`; Re < 3·10⁴ only warns |
| Q9 | Boundary to `app/` | Test: no import from `app/`, `cad_designer/`, `scripts/` |
| Q10 | No AeroSandbox installed | `tool_unavailable`, no ImportError |
| Q11 | A canon change with a changed input of an implemented formula | the import diff marks it breaking; the traceability test fails until the implementation is updated |
| Q12 | Runtime independence | `compute()` works with `_reversa_sdd/` absent; only `canon/canon_model.json` is read |
| Q13 | Import twice | byte-identical `canon_model.json` |
| Q14 | A canon entry with an unknown unit | the import fails at stage 2 with file and field; no model written |
| Q15 | A `minutes` quantity requested without `include_long_runs` | `status: skipped`, `reason.code = long_run_not_included`, dependents `depends_on_skipped`, all other quantities computed |
| Q16 | Event loop stays responsive | while a `seconds` computation runs, a concurrent `asyncio.sleep(0.01)` task is delayed by < 50 ms |
| Q17 | Cancellation | cancelling `compute()` during an AVL run kills the subprocess and leaves no temp directory; `CancelledError` propagates |
| Q18 | In-flight deduplication | on one `CachedKernel`, two concurrent identical requests cause exactly one formula call |
| Q19 | Time budget | budget exceeded → open quantities `timeout`, finished ones returned |
| Q20 | Stateless interface leaves no state | after `compute()` returns, no cache entry, pool or other object created by it remains; a second call computes again |
| Q21 | Cache scopes | an entry written in scope A is never a hit in scope B; `drop_scope(A)` leaves B untouched; a per-scope limit evicts only within its scope |
| Q22 | Multi-output formula | requesting two outputs of one application calls the implementation once |
| Q23 | One world fails | the quantity is `error` with `detail.worlds_ok`; no narrowed interval |
| Q24 | Missing input value | only the quantities needing it get `missing_input`; the rest compute |
| Q25 | Pre-/postcondition violated | `on_violation: warning` → value plus `defect` warning; `error` → `precondition_violated` (implementation not called) / `postcondition_violated` (value discarded); the importer rejects an output in `preconditions:` and an input in `postconditions:` |
| Q26 | Status precedence | mixed failed/skipped/not-applicable predecessors give the status of ch. 8.13 |
| Q27 | Cache key | inputs differing in the last bit of a float give different keys; a changed source file changes every key |
| Q28 | Mass differs from the geometry's `total_mass_kg` | computed with the passed mass; `conflicting_mass` warning on every quantity that depends on the mass, none on the others |
| Q29 | Target not set | `roll-rate-cruise` (`given: [cruise-speed-target]`) is `not_applicable`, code `not_given`; a quantity reading `cruise-speed-target` without `given` gets `missing_input` |
| Q30 | Embedded relation and optional parameter | with `flight-speed` = 0, `thrust-at-airspeed` equals the thrust inside `static-thrust-to-weight` bit for bit (one relation function); without `motor-circuit-resistance` both run route A with a `practice` warning naming the route, no `missing_input` |
| Q31 | Defaults taken | without `gravity` and without `approach-speed-margin-target`: `approach-speed` computes; `provenance.defaults_used` lists both with value and source; `caplog` has one `INFO` line for `gravity` and one `WARNING` line for the target, each with `call_id`, also on a second, cached call; the result carries `default_target_used` (`practice`) on `approach-speed` and its dependents, and no warning for `gravity` |
| Q32 | Embedding | `importer --check` rejects an embedding cycle, an embedded formula with worlds, and an embedded input that is neither bound, produced in the closure nor generic; the traceability test fails when an embedder does not call the embedded relation function; `mass-envelope` with `neutral-point` in three worlds runs three times and returns `cg-envelope-over-mass` as a pointwise interval |
| Q33 | Flap deflection: beyond the stop, flapless, missing | `flap-deflection-landing` larger than the flap's `positive_deflection_deg`: `airplane-landing` carries exactly the given deflection, `stall-speed-landing` computes, no error, no clamp and no warning about the stop. Flapless, no deflection given: `airplane-landing` is the unchanged aircraft, `stall-speed-landing` equals `stall-speed`, no warning, one `INFO` line. Flapless with a deflection: same values plus `deflection_without_flap`. Flaps, no deflection: `stall-speed-landing` is `missing_input` (`values.flap-deflection-landing`), `approach-speed` `upstream_failed`; `stall-speed` still computes |
| Q34 | Angles, not stops | `roll-rate-approach` at a given `aileron-deflection` beyond the aileron's stop computes, no stop warning; `aileron-deflection-required-approach` for a target above the AeroBuildup maximum: that world fails with `unsupported_configuration`, code `target_above_method_maximum` (maximum roll rate and its δ_a in `detail`), the AVL world computes, the quantity is `error` with the AVL value in `detail.worlds_ok` — no clipped angle, no narrowed interval. AVL at `|p·b/2V| > 0.10` carries the `defect` warning from the adapter |
| Q35 | Roll without ailerons; crow from the landing configuration | an aircraft without a surface acting as aileron, flaperon or elevon: `roll-rate-approach` and `aileron-deflection-required-approach` are `not_applicable` (`condition_not_met`), no `missing_input` for `aileron-deflection`; a flaperon-only wing has `has_aileron` but not the butterfly condition (crow needs a flap-acting and a distinct aileron-acting surface at once), so the butterfly quantities are `not_applicable`; with separate flaps and ailerons the butterfly curves start from `airplane-landing` (maintainer E2, 2026-10-15): at mix `s` the flap is at `flap-deflection-landing + s · (crow-flap-deflection − flap-deflection-landing)` and the aileron at `s · crow-aileron-deflection` (absolute end angles at `s = 1`, independent of the stops); at `s = 0` the stall speed agrees with `stall-speed-landing` to solver tolerance and `butterfly-approach-speed-curve(0)` equals `approach-speed` exactly (normalised by `V_S0(0)` of the same sweep) |
| Q36 | Embedded postcondition and variables | a stub `stall-speed` whose optimum is not the first C_L peak at one sweep mass: `mass-envelope` is `error`, `postcondition_violated`, `detail.embedded = stall-speed.clean` with that mass; with `m_current` set, the embedded `m` still takes every sweep value (`variables:`), never the current mass; the importer rejects a bare `stall-speed` in `embeds:` and a closure input that is neither variable, input nor produced |
| Q37 | Postcondition on a curve | a stub stall solve that lands on the post-stall peak at one mix `s`: `butterfly-approach` is `error`, `postcondition_violated` (`optimum_at_first_cl_peak`, the failing `s` in `detail`); all four butterfly outputs are discarded, none returned; the check function is the one `stall-speed` uses |
| Q38 | Non-scalar quantity requested in v1 | requesting `polar-stall` together with `stall-speed`: `polar-stall` is `error`, `not_implemented`, code `non_scalar_result`, no formula called for it; `stall-speed` computes and its formula, which also returns the polar internally, runs once |

## 11. Risks and technical debt

| Risk | Consequence | Handling |
|---|---|---|
| **The canon format is new.** #1181 made every entry machine-readable (PR #1182); the importer is the first program to read it in full. | Format gaps surface only when the importer runs against the real canon. | The importer is built and tested against the real canon document (`importer --check` in CI); its findings are fixed in the canon (ch. 8.9). Loader, graph and engine unit tests keep small hand-written fixture models in `tests/fixtures/`, validated against `canon_model.schema.json`. No entry carries an `# ESCALATED` field any more. |
| 55 of 57 canon entries are `draft` | Tests run against unapproved entries | Intended (Epic #1173); golden values are called "regression" |
| CI has no aero dependencies | Solver formulas are untested in the fast tier | Mock the adapters; job `aero-kernel-aero` (#1177) |
| Solver convergence (stall plateau, bounds) | `not_converged` occurs often | Robustness run (#1178), K32 procedure |
| The `stall-speed` prose still carries register-era context (implementation tables, conflict notes) next to the structured fields | A reader may take the prose for the binding | Resolved by #1181 for the importer: the applications are front-matter fields with canon slugs, and the importer never reads prose (ch. 8.9). The prose is for approval only. |

## 12. Glossary

| Term | Meaning | German (canon) |
|---|---|---|
| **Quantity** | named physical quantity with unit and role (`input`, `derived`, `output`, `target`) | Größe |
| **Formula** | one relation between quantities; `kind`: law, procedure, optimization, fit, rating | Formel |
| **Application** | a formula with bound inputs and a condition (`when`, `given`); produces one or more named quantities | Anwendung |
| **Binding** | which quantity is bound to an input of a formula | Bindung |
| **Precondition** | what must hold for the inputs so that the application means what it claims; checked before the call | Vorbedingung |
| **Postcondition** | what a computed output must satisfy to mean what it claims; checked after the call, also inside an embedder (ch. 8.5) | Nachbedingung |
| **Embedding** | a formula evaluating another formula's relation inside itself, over its own `variables` (`embeds:`, ch. 8.5); not a value edge | Einbettung |
| **World** | one method that runs through the whole chain for an uncertain quantity (A11) | Welt |
| **Probe** | a second path to a quantity, only as a check (A7) | Probe |
| **Canon document** | the human-readable canon in `_reversa_sdd/calculations/canon/` (external source) | Rechenkanon |
| **Canon model** | the machine-readable, versioned JSON image of the canon inside the package, interpreted by the kernel | — |
| **Import** | the deliberate step that translates the canon document into the canon model (ch. 8.9) | — |
| **Cost class** | `instant` / `seconds` / `minutes` | Kostenklasse |
| **Operating point** | mass, altitude, speed and controls of one flight condition (O10); one call evaluates one (ch. 8.13) | Betriebspunkt |
| **Parameter** | the name of a formula input or output inside the formula; applications bind it to a quantity | — |
| **World assignment** | one world chosen per uncertain formula of a subtree (ch. 8.13) | — |

---

## Appendix A — mapping of all 57 canon formulas

How the columns are filled:
- **in → out:** counted from the "Produces … from" line.
- **applications:** the number of bindings, from the entry's `applications:` (1 without). Hand-kept until
  the importer generates this table; only the rows touched by #1181 decisions are current.
- **preconditions:** whether the entry has them in structured form.
- **cost class:** derived from the tool (ch. 8.7), unless the entry declares `cost:` (marked *declared*). Only
  `mass-envelope` declares one: `minutes`, the long run of the approved plan of epic #1173 (K28).

Generated from the canon files. The importer (#1174 or its follow-up) replaces this table with one generated from the canon
model (part of `IMPORT_REPORT.md`).

| Formula | kind | tool | shape | in → out | applications | preconditions | worlds | cost class | v1 |
|---|---|---|---|---|---|---|---|---|---|
| `advance-ratio-from-speed` | law | APP | law | 3 → 1 | 1 | – | – | instant | later |
| `aerobuildup-evaluation` | procedure | AB | law | 4 → 4 | 1 | – | – | seconds | core chain |
| `aileron-deflection-required` | procedure | OPT | law | 8 → 2 | 1 | – | A11 | seconds | core chain |
| `air-density-isa` | law | ATM | law | 1 → 1 | 1 | – | – | instant | core chain |
| `airplane-components` | procedure | KAT | law | 1 → 9 | 1 | – | – | instant | probe |
| `airplane-configuration` | procedure | GEO | law | 2 → 1 | 2 | – | – | instant | core chain |
| `airplane-geometry` | procedure | GEO | law | 1 → 4 | 1 | – | – | instant | core chain |
| `aspect-ratio` | law | APP | law | 2 → 1 | 1 | – | – | instant | core chain |
| `battery-mass-from-capacity` | law | APP | law | 2 → 1 | 1 | – | – | instant | later |
| `best-angle-of-climb` | optimization | OPT | law | 5 → 2 | 1 | – | – | seconds | later |
| `best-rate-of-climb` | optimization | OPT | law | 5 → 2 | 1 | – | – | seconds | later |
| `butterfly-approach` | optimization | OPT | law | 6 → 4 | 1 | – | – | seconds | later |
| `cg-for-target-margin` | law | APP | law | 3 → 1 | 1 | – | – | instant | core chain |
| `cruise-target-performance` | procedure | OPT | law | 7 → 2 | 1 | – | – | seconds | later |
| `dive-speed` | procedure | OPT | law | 5 → 1 | 1 | – | – | seconds | later |
| `drag-polar` | law | APP | approximation | 3 → 1 | 1 | – | – | instant | later |
| `dynamic-pressure` | law | APP | law | 2 → 1 | 1 | – | – | instant | core chain |
| `endurance-and-range` | procedure | OPT | law | 8 → 2 | 1 | – | – | seconds | later |
| `glide-distance-from-ratio` | law | APP | law | 2 → 1 | 1 | yes | – | instant | later |
| `induced-drag-factor` | law | APP | law | 2 → 1 | 1 | – | – | instant | later |
| `lateral-static-stability-app` | procedure | AVL | law | 6 → 4 | 1 | – | – | seconds | core chain |
| `lateral-static-stability-md` | procedure | AVL | law | 6 → 4 | 1 | – | – | seconds | core chain |
| `lift-coefficient-required` | law | APP | law | 5 → 1 | 1 | – | – | instant | core chain |
| `lift-to-drag-ratio` | law | APP | law | 2 → 1 | 1 | – | – | instant | core chain |
| `linear-lift-curve-inverse` | law | APP | law | 3 → 1 | 1 | – | – | instant | later |
| `maneuvering-speed` | optimization | OPT | law | 5 → 1 | 1 | – | – | seconds | later |
| `mass-envelope` | optimization | OPT | law | 7 → 5 | 1 | – | – | minutes (declared) | core chain |
| `max-level-speed` | optimization | OPT | law | 5 → 1 | 1 | – | – | seconds | probe |
| `max-lift-to-drag-parabolic` | law | APP | law | 3 → 1 | 1 | – | – | instant | later |
| `max-mass-structure` | law | APP | law | 2 → 1 | 1 | – | – | instant | later |
| `roll-rate-cruise-target` | procedure | OPT | law | 5 → 1 | 1 | – | A11 | seconds | later |
| `roll-rate` | procedure | OPT | law | 5 → 2 | 1 | – | A11 | seconds | core chain |
| `max-sustained-turn-rate` | optimization | OPT | law | 6 → 2 | 1 | – | – | seconds | later |
| `mean-geometric-chord` | law | APP | law | 2 → 1 | 1 | – | – | instant | core chain |
| `min-sustained-turn-radius` | optimization | OPT | law | 6 → 2 | 1 | – | – | seconds | later |
| `minimum-drag-speed-closed-form` | law | APP | approximation | 4 → 1 | 1 | – | – | instant | later |
| `minimum-drag-speed-from-polar` | optimization | OPT | route | 5 → 2 | 1 | – | – | seconds | core chain |
| `minimum-sink-speed-from-polar` | optimization | OPT | law | 5 → 1 | 1 | – | – | seconds | core chain |
| `motor-propeller-equilibrium` | procedure | APP | route | 9 → 1 | 1 | – | – | instant | probe |
| `neutral-point` | procedure | AVL | law | 5 → 1 | 1 | – | A11 | seconds | core chain |
| `parabolic-polar-fit` | fit | OPT | law | 6 → 2 | 1 | – | – | seconds | probe |
| `propeller-table-lookup` | procedure | APC | law | 2 → 1 | 1 | – | – | instant | probe |
| `relative-mass-deviation` | law | APP | law | 2 → 1 | 1 | – | – | instant | later |
| `sink-rate` | law | APP | law | 3 → 1 | 1 | – | – | instant | core chain |
| `spar-break-load-factor` | procedure | APP | law | 3 → 2 | 1 | – | – | instant | later |
| `speed-from-stall-margin` | rating | APP | approximation | 2 → 3 | 3 | – | – | instant | probe |
| `spiral-parameter` | law | APP | law | 5 → 1 | 1 | – | – | instant | core chain |
| `stall-onset-detection` | procedure | AB | law | 3 → 1 | 1 | – | – | seconds | core chain |
| `stall-speed` | optimization | OPT | law | 5 → 4 | 4 | yes | – | seconds | core chain |
| `stall-wing-loading-limit` | law | APP | law | 3 → 1 | 1 | – | – | instant | later |
| `static-margin-probe` | procedure | AB | law | 6 → 2 | 1 | – | – | seconds | core chain |
| `static-margin` | law | APP | law | 3 → 1 | 1 | – | – | instant | core chain |
| `static-thrust-to-weight` | law | APP | law | 2 → 1 | 1 | – | – | instant | later |
| `thrust-at-airspeed-from-coefficient` | law | APP | law | 4 → 1 | 1 | – | – | instant | later |
| `vertical-tail-volume` | law | APP | law | 1 → 1 | 1 | – | – | instant | core chain |
| `weight-from-mass` | law | APP | law | 2 → 1 | 1 | – | – | instant | core chain |
| `wing-loading` | law | APP | law | 3 → 1 | 1 | – | – | instant | core chain |

*57 entries; core chain 27, probes 6, later 24. `airplane-configuration` added, `inverted-max-lift-coefficient` removed (its output is `stall-speed`'s `inverted` application).*

**Finding from the mapping.** All 57 entries fit the model (five `kind`s, eight tools, three `shape`s,
worlds, cost classes). The missing piece was not a concept but **machine-readability** in the canon; #1181
delivered it (PR #1182), so the importer generates this table from now on.
