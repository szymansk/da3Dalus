# aero_kernel — Architecture (lean arc42)

> **Status: draft for approval (#1174).** Once the maintainer approves it, this document is the
> **binding template** for every ticket of Epic #1173 (#1174–#1178). Whoever changes something stated
> here changes this document first.
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
- SI units throughout.
- Everything in the source tree is English (ADR 0029).
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
  schema.py         AircraftInput, OperatingPoint, ComputeRequest, ComputeResult, QuantityResult,
                    KernelError, Warning, Provenance (Pydantic, extra="forbid")
  canon/            canon_model.json         the interpreted canon (versioned, committed)
                    canon_model.schema.json  JSON Schema of the canon model
                    IMPORT_REPORT.md         report of the last import (source commit, diff, findings)
                    load.py                  load + schema/version check at runtime
  importer/         parse.py · normalise.py · validate.py · diff.py · write.py · __main__.py
                    external canon document → canon model (ch. 8.9); not imported at runtime
  graph.py          subtree, order, world expansion, upstream_failed
  registry.py       @formula(slug) — implementations ↔ canon model
  formulas/         one file per canon formula (file name = slug, with underscores)
  solvers/          aerobuildup.py · avl.py · opti.py · atmosphere.py · data.py (KAT, APC)
  cache.py          NodeStore protocol; MemoryCache (LRU), DiskCache
  validate.py       physical admissibility; regime warnings (ADR 0028)
  errors.py         error catalogue (ch. 8.1)
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
 1 validate(aircraft)                      → invalid_input with input_path; the only abort
 2 canon_model.subtree(request.quantities)    → formulas + applications, topologically sorted
 3 per application: check its condition    → not met → status "not_applicable"
 4 per world (A11) and per operating point:
     cost class "minutes" and include_long_runs off → status "skipped" (reason long_run_not_included)
     [CachedKernel only] build key → cache hit? → reuse, from_cache = true
     else schedule the implementation (time budget); independent nodes run concurrently (ch. 8.10)
       success → value + warnings (incl. regime ADR 0028, preconditions)
       failure → KernelError; successors → upstream_failed
 5 merge worlds → [min, max] with the list of worlds
 6 ComputeResult with provenance
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
| `unsupported_configuration` | no | no | the method does not cover this layout | "The textbook neutral-point formula needs a horizontal tail." |
| `not_applicable` | — | — | **not an error**: the application does not exist (no flap → no V_S,landing) | — |
| `not_implemented` | no | no | the canon formula has no implementation yet | "`max-sustained-turn-rate` is in the canon, not in the kernel." |
| `not_converged` | yes | no | the solver found no solution | "Raise the accuracy tier or change the start value." |
| `timeout` | yes | no | the time budget was exceeded | "Raise the budget or request it as a long run." |
| `tool_unavailable` | no | yes | a tool is missing (AeroSandbox, AVL) | "Use an environment with the aero dependencies." |
| `upstream_failed` | as predecessor | as predecessor | a predecessor quantity has no value | "Fix `stall-speed` first." |
| `internal` | no | yes | programming error | "Report it; attach input and provenance." |

`escalate = true` means an agent cannot resolve this itself; a human has to act.

### 8.2 Warnings

Same shape as `DesignWarning` (ADR 0020): `severity` (`practice` | `defect`), `code`, `message`,
`quantity`.

Sources:
- the regime (ADR 0028): Re band 3·10⁴–1·10⁶, "bubble-sensitive" below 7·10⁴, Mach
- violated or unchecked preconditions
- active bounds in the optimiser
- the "not validated" marker of A11

### 8.3 Result contract

`QuantityResult` fields:
- `slug` and `unit` (SI)
- `status`: `ok`, `not_applicable`, `skipped` or `error`
- `reason` for every status other than `ok`: machine-readable `code` plus natural-language `message`
  (`not_applicable`: the application's unmet condition; `skipped`: `long_run_not_included` or
  `depends_on_skipped`; `error`: see `error`)
- `value` **or** `interval {min, max, worlds{name: value}}`
- `tool` and `application`
- `validated`: `false` — no value is validated against flight data (canon A11: "not validated")
- `warnings[]` and `error`
- `from_cache`: whether the value was served from the cache (ch. 8.4)

No internal paths or mechanisms in any field (ADR 0019).

### 8.4 Provenance, cache key and the two interfaces

`Provenance`:
- kernel version
- canon model hash and its source commit (the canon state)
- tool versions (aerosandbox, NeuralFoil model, AVL)
- accuracy tier (A3) and solver settings

**Cache key** = hash of:
- the formula slug, application and world
- the canonicalised **relevant** inputs
- the canon model hash of the entry
- the implementation version and the tool versions

Canonicalisation means sorted keys and numbers at a fixed number of significant digits. When a formula
changes, only its subtree expires (A1).

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

### 8.5 Applications and preconditions

An **application** is a formula plus the bindings of its inputs, a condition and the name of the output
quantity.

A **precondition** is an executable check per application. It returns one of three states:
- 🟢 held
- 🔴 violated: a `defect` warning or an error, as the canon entry says
- ⚪ unchecked: a `practice` warning

### 8.6 Consistency rules (checked by the importer)

- One producer per quantity; a second path only as a probe (A7).
- Unique symbols and slugs (A8).
- Targets only as `role: target` (A9).
- Units consistent across bindings (A4); dimensional check of law entries (`scripts/check_canon.py` logic).
- Every reference (inputs, bindings, worlds) resolves to a quantity in the model.

At load time the kernel additionally checks: every registered implementation has a slug in the model, and
its declared units equal the model's.
- Separate namespaces: the calculation canon now, the sizing canon (K31) later.

Violations are **canon findings**, not runtime errors: the importer reports them, writes no model, and the
canon document is corrected.

### 8.7 Cost class

Each formula has a cost class: `instant`, `seconds` or `minutes`, carried in the canon model.

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
caller's responsibility. Which layer *assigns* the cost class to a formula is still open (O14, question 3).

### 8.8 Tools and data sources

- Tools: APP (pure), ATM, GEO, AB, AVL, OPT.
- Data: KAT (component catalogue) and APC (propeller tables).
- Data comes **from the caller**, either inline in the input or as a provider with a content hash. The
  kernel loads nothing on its own.

### 8.9 Canon import — from the canon document to the canon model

The kernel does not read the canon document. It interprets **its own canon model**. Changes to the canon
reach the kernel **only through an import**, a deliberate, reviewable step:

```
python -m aero_kernel.importer <canon-document-dir> [--check]
```

| Stage | Does | Fails when |
|---|---|---|
| 1 Parse | reads every formula and quantity entry: front matter, the structured fields (`inputs`, `applications`, `preconditions`, `uncertainty`, …) and the canonical form; never prose | a required field is missing or malformed |
| 2 Normalise | slugs, units to SI symbols, roles, kinds, tools to closed vocabularies; resolves `[[…]]` references | an unknown unit, kind, tool or role |
| 3 Validate | JSON Schema of the canon model; consistency rules (ch. 8.6); dimensional check | any rule is violated |
| 4 Diff | compares with the committed canon model: entries added, removed or changed; marks **breaking** changes (inputs, units, outputs, applications) and lists the affected implementations and golden tests | — (only reports) |
| 5 Write | writes `canon_model.json` (sorted, stable formatting), its content hash, the source commit of the canon document and the importer version; writes `IMPORT_REPORT.md` (diff, findings, Appendix A table) | — |

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
  - Pure `law` formulas below a size threshold run inline; they are microseconds.
- **Concurrency from the graph.** Independent nodes of the subtree, method worlds (A11) and operating points
  run concurrently (`asyncio.TaskGroup`). The dependency graph decides what may run in parallel, never the
  formula code.
- **Bounded.** Execution resources are passed in, never global:
  - an executor (process pool) and a concurrency limit.
  - The **stateless `compute()`** takes them as optional keyword arguments. Without them it uses a
    per-call default, so it stays free of state.
  - **`CachedKernel`** owns one pool and one limit for its lifetime. They are created lazily and closed by
    `async with` or `aclose()`.
  - Nothing starts at import. Resources are not results: they never change a value.
- **Cancellation.**
  - Cancelling the `compute()` task cancels all child tasks.
  - It kills running AVL subprocesses and removes their temporary directories.
  - Work already running in the process pool is allowed to finish but its result is discarded, because
    pool workers cannot be interrupted safely.
  - `asyncio.CancelledError` is always re-raised, never turned into a result.
- **Time budget.** `ComputeRequest.time_budget_s` is enforced with `asyncio.timeout`. Quantities still open
  when it expires get `error.category = timeout`; quantities already finished are returned.
- **Cache under concurrency (`CachedKernel` only).** The store is safe for concurrent use. **In-flight
  deduplication** (mode `use`): when two concurrent requests need the same key, the second awaits the first
  one's future instead of computing it again.
- **No hidden loop.** The kernel never calls `asyncio.run`, never creates or closes the caller's loop and
  keeps no loop-bound global state. It works inside FastAPI, in pytest-asyncio and in plain
  `asyncio.run(compute(...))` from scripts.
- **Optional, decided at approval: `compute_iter()`.** An async generator yielding each `QuantityResult` as
  soon as it is final, for progressive display of long runs. Same request, same results as `compute()`.

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
| Q5 | Layout without flaps | `stall-speed-landing` is `not_applicable`: no error, no substitute value |
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
| Q20 | Stateless interface leaves no state | after `compute()` returns, no cache entry, pool or other object created by it remains; a second call computes again |
| Q19 | Time budget | budget exceeded → open quantities `timeout`, finished ones returned |

## 11. Risks and technical debt

| Risk | Consequence | Handling |
|---|---|---|
| **The canon document is only half machine-readable.** Inputs sit in the prose line "Produces … from". Only `stall-speed` has an application table, and only 3 of 57 entries have structured preconditions. | The importer cannot derive applications and preconditions completely. | **Decision needed** (see below). |
| 55 of 57 canon entries are `draft` | Tests run against unapproved entries | Intended (Epic #1173); golden values are called "regression" |
| CI has no aero dependencies | Solver formulas are untested in the fast tier | Mock the adapters; job `aero-kernel-aero` (#1177) |
| Solver convergence (stall plateau, bounds) | `not_converged` occurs often | Robustness run (#1178), K32 procedure |
| The `stall-speed` application table uses old register names (`v_stall_clean_mps`) instead of canon slugs | Names do not match the canon model | Switch to canon slugs when extending the format |

**Open decision for the maintainer: the canon format.** So that the importer does not have to guess
applications and preconditions from prose, every formula entry needs machine-readable fields in its front
matter, for example:
- `inputs:`
- `applications:` (name, bindings, condition)
- `preconditions:` (check, status, test)

Proposal: extend the format once and update all 57 entries mechanically, keeping the prose, **before** the
importer is built.

## 12. Glossary

| Term | Meaning | German (canon) |
|---|---|---|
| **Quantity** | named physical quantity with unit and role (`input`, `derived`, `output`, `target`) | Größe |
| **Formula** | one relation between quantities; `kind`: law, procedure, optimization, fit, rating | Formel |
| **Application** | a formula with bound inputs and a condition; produces one named quantity | Anwendung |
| **Binding** | which quantity is bound to an input of a formula | Bindung |
| **Precondition** | what must hold for the inputs so that the application means what it claims | Vorbedingung |
| **World** | one method that runs through the whole chain for an uncertain quantity (A11) | Welt |
| **Probe** | a second path to a quantity, only as a check (A7) | Probe |
| **Canon document** | the human-readable canon in `_reversa_sdd/calculations/canon/` (external source) | Rechenkanon |
| **Canon model** | the machine-readable, versioned JSON image of the canon inside the package, interpreted by the kernel | — |
| **Import** | the deliberate step that translates the canon document into the canon model (ch. 8.9) | — |
| **Cost class** | `instant` / `seconds` / `minutes` | Kostenklasse |
| **Operating point** | mass, altitude, speed and controls of one flight condition (O10) | Betriebspunkt |

---

## Appendix A — mapping of all 57 canon formulas

How the columns are filled:
- **in → out:** counted from the "Produces … from" line.
- **applications:** the number of bindings. Only `stall-speed` has a table today; otherwise 1, or the
  number of outputs for `rating`.
- **preconditions:** whether the entry has them in structured form.
- **cost class:** a proposal.

Generated from the canon files. The importer (#1174) replaces this table with one generated from the canon
model (part of `IMPORT_REPORT.md`).

| Formula | kind | tool | shape | in → out | applications | preconditions | worlds | cost class | v1 |
|---|---|---|---|---|---|---|---|---|---|
| `advance-ratio-from-speed` | law | APP | law | 3 → 1 | 1 | – | – | instant | later |
| `aerobuildup-evaluation` | procedure | AB | law | 4 → 4 | 1 | – | – | seconds | core chain |
| `aileron-throw-fraction` | procedure | OPT | law | 8 → 2 | 1 | – | A11 | seconds | core chain |
| `air-density-isa` | law | ATM | law | 1 → 1 | 1 | – | – | instant | core chain |
| `airplane-components` | procedure | KAT | law | 1 → 9 | 1 | – | – | instant | probe |
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
| `inverted-max-lift-coefficient` | procedure | AB | law | 2 → 1 | 1 | yes | – | seconds | later |
| `lateral-static-stability-app` | procedure | AVL | law | 6 → 4 | 1 | – | – | seconds | core chain |
| `lateral-static-stability-md` | procedure | AVL | law | 6 → 4 | 1 | – | – | seconds | core chain |
| `lift-coefficient-required` | law | APP | law | 5 → 1 | 1 | – | – | instant | core chain |
| `lift-to-drag-ratio` | law | APP | law | 2 → 1 | 1 | – | – | instant | core chain |
| `linear-lift-curve-inverse` | law | APP | law | 3 → 1 | 1 | – | – | instant | later |
| `maneuvering-speed` | optimization | OPT | law | 5 → 1 | 1 | – | – | seconds | later |
| `mass-envelope` | optimization | OPT | law | 6 → 5 | 1 | – | – | minutes | core chain |
| `max-level-speed` | optimization | OPT | law | 5 → 1 | 1 | – | – | seconds | probe |
| `max-lift-to-drag-parabolic` | law | APP | law | 3 → 1 | 1 | – | – | instant | later |
| `max-mass-structure` | law | APP | law | 2 → 1 | 1 | – | – | instant | later |
| `max-roll-rate-cruise-target` | procedure | OPT | law | 5 → 1 | 1 | – | A11 | seconds | later |
| `max-roll-rate` | procedure | OPT | law | 5 → 2 | 1 | – | A11 | seconds | core chain |
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
| `stall-speed` | optimization | OPT | law | 5 → 4 | 3 | yes | – | seconds | core chain |
| `stall-wing-loading-limit` | law | APP | law | 3 → 1 | 1 | – | – | instant | later |
| `static-margin-probe` | procedure | AB | law | 6 → 2 | 1 | – | – | seconds | core chain |
| `static-margin` | law | APP | law | 3 → 1 | 1 | – | – | instant | core chain |
| `static-thrust-to-weight` | law | APP | law | 2 → 1 | 1 | – | – | instant | later |
| `thrust-at-airspeed-from-coefficient` | law | APP | law | 4 → 1 | 1 | – | – | instant | later |
| `vertical-tail-volume` | law | APP | law | 1 → 1 | 1 | – | – | instant | core chain |
| `weight-from-mass` | law | APP | law | 2 → 1 | 1 | – | – | instant | core chain |
| `wing-loading` | law | APP | law | 3 → 1 | 1 | – | – | instant | core chain |

*57 entries; core chain 26, probes 6, later 25.*

**Finding from the mapping.** All 57 entries fit the model (five `kind`s, eight tools, three `shape`s,
worlds, cost classes). What is missing is not a concept but **machine-readability** in the canon (ch. 11).
