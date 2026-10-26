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
  `deg`, `deg/s`; `Wh`; `rpm/V`; `mAh`, `1/h` for the battery as the catalogue holds it). No conversion inside the kernel except the geometry's millimetre fields.
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
kernel = CachedKernel(cache=MemoryCache(max_entries=10_000))
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

### 4.1 Build order — a vertical slice first (maintainer, 2026-10-16)

"A good slice first, then broaden by KISS." Each step adds only what its formulas need:
1. **Slice:** `weight-from-mass`, `air-density-isa` (the ATM adapter), `dynamic-pressure` — importer on the
   real canon, the `Build`, a lean engine, an end-to-end test against hand-computed values (`aero` tier).
2. **Geometry:** `wing-loading` via `airplane-geometry` (`S_ref`).
3. **Solver path:** `stall-speed` — AeroBuildup/Opti adapters, applications, `when`, postconditions,
   configured airplanes, polar values.
4. **Method worlds:** `minimum-drag-speed` first (it sets the lift coefficient of the AVL world, #1204), then
   `neutral-point` (A11 intervals, AVL) with `static-margin-measured` (#1203) and `centre-of-gravity-design` (#1214).
5. **Embedding:** the propulsion relations and the optimisers; `mass-envelope` last (embedding, worlds and
   long runs together).
Engine features named "built with the first embedder" (or with a later step) are specified here but not
built before that step (ADR 0021). Appendix A's last column predates this order.

## 5. Building blocks

```
aero_kernel/
  api.py            async compute(aircraft, request) — the stateless interface
  build.py          the internal Build (shipped model + digest + checked registry), loaded once on first use
  cached.py         CachedKernel — the cached facade (owns cache, in-flight deduplication, resources)
  engine.py         walks the graph; takes an optional MemoryCache (none = stateless)
  runtime.py        executor, concurrency limit, cancellation
  geometry.py       AirplaneGeometry and its sub-models (format mirror, mm → m at parse, ch. 8.11)
  schema.py         AircraftInput, ComputeRequest, ComputeResult, QuantityResult, Polar, KernelWarning,
                    Provenance (Pydantic, extra="forbid"); re-exports AirplaneGeometry and KernelError
  canon/            canon_model.json         the interpreted canon (versioned, committed)
                    canon_model.schema.json  JSON Schema of the canon model
                    IMPORT_REPORT.md         report of the last import (content hash, findings, the formula table)
                    model.py                 the canon-model types (Pydantic; the schema is generated from them)
                    load.py                  load + schema/version and reference check at runtime
  importer/         parse.py · normalise.py · validate.py · diff.py · write.py · __main__.py
                    external canon document → canon model (ch. 8.9); not imported at runtime
  graph.py          subtree, order, world expansion, upstream_failed
  registry.py       @formula(slug), @precondition(slug, id), @postcondition(slug, id) — implementations ↔ canon model (ch. 8.12)
  formulas/         one file per canon formula (file name = slug, with underscores)
  solvers/          aerobuildup.py · avl.py · opti.py · atmosphere.py
  cache.py          MemoryCache (LRU), Entry, cache_key, build_digest
  validate.py       physical admissibility of the input and `values` against the canon (ch. 8.11)
  canonical.py      canonical JSON and the SHA-256 helper, shared by the canon model hash and the cache keys
  errors.py         error catalogue (ch. 8.1): `ErrorCategory`, `KernelError`, the closed code table
                    (code → category), `FormulaError`, upstream aggregation; imports no other module
  __init__.py       public API; adds the NullHandler to the `aero_kernel` logger (ch. 8.14)
  evaluation/       rules.py (rule table, shipped `rule_table.json`, check against the canon model) · evaluator.py (result + rule table → verdicts with a self-contained `text`, `summarize_verdicts`, red/yellow verdicts logged at INFO on `aero_kernel.evaluation`; #1289)
                    the judgement the canon never makes (A10); pure; not called by `compute()` (#1276)
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
| `evaluation` | judge computed values against a rule table: inside, below, above, partly (interval), not applicable, not available | compute a physical quantity; hold a band in code (bands are data, `_reversa_sdd/calculations/evaluation/`); read YAML (Q12; `importer/rule_table.py` generates the shipped `evaluation/rule_table.json` from the YAML at dev time, `shipped_rule_table()` loads it) |
| `cache` | map keys to results | change results |

## 6. Runtime view — one call

```
await compute(aircraft, request)
 0 the shipped Build (loaded once on first use) → missing or broken: every quantity internal, escalate
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
directory. **POSIX only** (macOS, Linux, the Linux containers): external processes run in their own
session and are killed as a process group (`os.killpg`). Windows is not supported; there is no untested
fallback path (ADR 0021).

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
| `unsupported_configuration` | no | no | the method does not cover this layout, or a target lies above what the method itself can reach (code `target_above_method_maximum`, `detail` = the maximum reached and the input at which it occurs, e.g. the roll rate and δ_a), or every method world of a quantity declared itself outside its validity (code `all_worlds_outside_validity`, `detail.worlds_excluded`, ch. 8.13) | "The textbook neutral-point formula needs a horizontal tail." |
| `not_implemented` | no | no | the canon formula has no implementation yet | "`max-sustained-turn-rate` is in the canon, not in the kernel." |
| `not_converged` | yes | no | the solver found no solution | "Change the start value or the operating point." |
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
- **Refused layouts and tool limits** (`unsupported_configuration`): `unsupported_layout` — the neutral point
  is defined for one `main_wing` with one `horizontal_tail` (any `vertical_tail` and `winglet`), decided from
  `surface_type` only, before any world runs (`detail.surface_types`, ch. 8.5); `avl_array_limit` — the
  declared AVL mesh overflows AVL's vortex array (`detail`: the mesh), never retried on a coarser mesh;
  `roll_device_on_unmirrored_surface` — a device acting as aileron sits on a wing that is not mirrored (no
  fleet aircraft has one, ADR 0021; `detail`: wing key, device label, role); `missing_hinge`
  (`invalid_input`) — a driven roll device without `rel_chord_root`, the tool's default hinge is never used;
  `hinge_line_discontinuous` — two driven segments meet at a rib with different hinge lines (AVL holds one
  value per section; `detail`: wing key, y).
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
adds its codes when it is built. `severity` stays a **required** field, so the public JSON schema and every
dump always carry it (ADR 0019); code builds warnings through the named constructor
`KernelWarning.of(code, message, …)`, which takes the severity from the table, and a given severity that
contradicts the table is rejected. A quantity's result lists its own warnings and those of its subtree,
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
- a method world outside its stated range (`world_outside_validity`, `practice`, ch. 8.13): the world leaves the interval and the warning carries its value and the limit
- the missing fuselage (`fuselage_not_modelled`, `practice`, origin `neutral-point`, once per world): none of the
  three neutral-point worlds models a fuselage, whose contribution is destabilising, so the interval is biased
  aft and a static margin computed from it is over-reported (`static-margin-measured` inherits it). `practice`: a
  deliberate, declared simplification (maintainer 2026-10-24, #1205): USAF DATCOM 1978 §4.2.2.1 Method 1
  gives about 1.5-2.1 % MAC forward (BRYAN) and 0.7-1.0 % (JAGUAR), inside Sadraey's "about ±5 % c̄"
- AVL mesh validity (ch. 8.8): `avl_mesh_not_converged` (`defect`; `detail`: both values and meshes) and
  `avl_refinement_unchecked` (`defect`)
- the averaged hinge line of a roll device (`hinge_line_averaged`, `practice`, ch. 8.8): AeroBuildup holds one
  hinge per segment, so a tapered hinge line is replaced by the mean of its root and tip (`detail`: wing key,
  device, `root`, `tip`, `used`)
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
- `slug` and `unit` (the quantity's canon unit, ch. 8.11); `unit` is `None` exactly when the kernel knows no
  quantity of that slug (an unknown or malformed slug, or no loadable model) — required whenever `status` is `ok`
- `status`: `ok`, `not_applicable`, `skipped` or `error`
- `reason` for every status other than `ok`: machine-readable `code` plus natural-language `message`
  (`not_applicable`: `condition_not_met`, `not_given` or `depends_on_not_applicable`, ch. 8.5; `skipped`: `long_run_not_included` or
  `depends_on_skipped`; `error`: see `error`)
- `value` **or** `interval {min, max, worlds{assignment: value}}` (ch. 8.13), exactly one when `ok`, neither
  otherwise. `value` is a float in the quantity's canon unit, or a structured value of the quantity's `type`
  (ch. 8.12). **v1 returns floats only**; the union widens with the first non-scalar formula, no placeholder
  type before that (ADR 0021). The `per_control_surface` value (keyed by surface and application, with
  `application` then `None`) and the handling of duplicate surface keys are specified with the first such
  formula implementation (ch. 8.5). Numbers are **strict and finite**: `value`, the interval bounds and world
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
- the **build digest** (below), which identifies the exact code and canon model file (Q3); there is no
  hand-bumped version (the repository is not an installed package)
- the canon model hash (the canon state; the commit that shipped it is found with
  `git log -S <content_hash> -- aero_kernel/canon/canon_model.json`); `None` only when the shipped model
  could not be loaded (every quantity is then `internal`)
- tool versions (aerosandbox, NeuralFoil model, AVL): one non-empty version string per tool **the call actually
  used**; empty when only pure formulas ran. The tool of a node with method worlds is the tool of its **world**
  (`taxonomy.yaml` maps each world to a tool; `CanonModel.tool_of`), not the `tool` of the formula: the AVL world
  of `roll-rate` lists the AVL binary, the AeroBuildup world the optimiser's tools (#1221)
- solver settings (e.g. the NeuralFoil model size the adapters use: `xlarge` in v1, the author's default at the knee
  of speed versus accuracy, Sharpe 2024, PhD thesis ch. 7, Table 7.1; maintainer 2026-10-22. It is a named constant of the
  OPT adapter, recorded in `solver_settings` together with its alpha sweep (`opt_alpha_min_deg`, `opt_alpha_max_deg`,
  `opt_alpha_step_deg`, `opt_bracket_cl`), its speed bounds, iteration limit and active-bound fraction: every constant that shapes a result; a caller-selectable accuracy level comes only when a caller needs it. The
  airfoil scoring, #821, uses `xxxlarge` on purpose: it is precomputed)
- `defaults_used`: every canon default the call took, as `{slug, value, unit, source}` (ch. 8.11)

**Cache key** = SHA-256 over the canonical JSON of:
- the application id and the world assignment
- the **direct input values** of the node: the values bound to its parameters, i.e. the outputs of its
  predecessors or the caller's input values. A node's key thus changes exactly when something in its
  subtree changes value (A1), without tracking leaf inputs.
- the **build digest**: one hash over the `.py` files of the installed `aero_kernel` package except
  `tests/`, `tools/` and `importer/`, plus `canon_model.json`; computed once, with the `Build`. Any code or canon change invalidates every entry. That wastes hits after an
  upgrade but can never serve a stale value; no hand-maintained implementation version exists that could be
  forgotten.
- the tool versions (aerosandbox, NeuralFoil model, AVL) and the solver settings of the tool of the node's
  world (`Solvers.tool_versions_of` / `settings_of` of `CanonModel.tool_of(formula, world)`). The settings are
  module constants, so a change of one is a code change and the build digest already expires every entry;
  they are in the key as a guard, and as the record of what the result was computed with. Per-world expiry
  happens only when a tool or its binary changes version: a new AVL binary expires the AVL world and leaves
  the AeroBuildup world cached. Every datum a node reads —
  components and propeller tables included — is part of its direct input values, so nothing else enters
  the key (ch. 8.11, D14). There are no request-level solver settings in v1 (no accuracy knob, S10:
  A3 asks for one declared level per quantity, not per request, and the NeuralFoil size names are an
  implementation detail, ADR 0019); one that is added later goes into `ComputeRequest`, the key and the
  provenance together.

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
instead: the cache keeps entries in a **serialised form** (canonical JSON / bytes) and every hit
deserialises a fresh object, and every `compute()` builds a fresh `ComputeResult`. A caller who mutates
its result can corrupt only its own copy. Kernel code never mutates a model after construction; results
need not be hashable.

**Two interfaces, one engine.**

- **The `Build`** — a frozen value of the validated canon model, its `CanonGraph` (built once; a
  `GraphModelError` is a load failure), the build digest and the registry with its
  traceability report — is **the kernel's own responsibility** (maintainer, 2026-10-17): `canon_model.json`
  is a package artefact, not caller data, so D14 (external data is pushed) does not apply to it. The kernel
  loads its shipped Build **itself, once, lazily on first use**, memoised in `build.py` — never at import.
  This one memo is an immutable package artefact, not call state, so the stateless rule holds. A missing or
  broken shipped model is **our** defect: every requested quantity is `internal`, escalate. The memo stores
  only a successful load, so a failed load is retried on every call — **deliberately**: after the file is
  fixed the kernel recovers without a restart. Each failing call logs one `ERROR` (with `exc_info`). Prevention lives in CI, not at runtime: the packaged model loads and
  matches the canon (`importer --check`), and a packaging test checks that the file ships. Internally the
  engine keeps an explicit seam, `evaluate(build, aircraft, request)`, which tests use with small test
  canons; it is not exported. A second canon (K31) will be a second namespace of the same shipped model —
  still ours, never passed in by the caller.
- **`compute(aircraft, request)`, stateless.** A pure function. It keeps nothing between calls: no
  cache and no deduplication. Two calls with the same input compute twice.
- **`CachedKernel`, stateful facade.** An object that owns a `MemoryCache` and
  the in-flight deduplication.
  - Its `compute()` has the same signature and the same result type.
  - It delegates to the same engine and passes in its cache.
- **Why node level.** Caching happens **per graph node**, not per whole request. That way, a change to one
  input expires only its subtree (A1). The facade therefore injects the cache into the engine instead of
  wrapping the whole call. Seen from outside it is still a facade: a separate object, put in front of the
  same computation, with no influence on the values.

**Per call on the facade:** `await kernel.compute(aircraft, request)` — one mode: read, write, in-flight
deduplication. There is no `refresh`: every reason to recompute (tool versions, build digest) is already in
the key, and errors are never stored. A forced recomputation is the stateless `compute()`.

Cache settings (the size) are passed when the facade is created, never read from the environment.
Each `QuantityResult` reports `from_cache`, which is always `false` from the stateless interface.

**One in-memory cache, no scopes, no persistence** (maintainer, 2026-10-17: S2 = b, D13). `MemoryCache` is
one LRU over all entries (`max_entries`). There are no cache scopes, no per-scope limits, no `drop_scope`,
no pluggable store and no disk cache: correctness never depended on them (keys are content hashes), and no
caller needs them before the register epic. All of it is restorable from `2dc55f19`. `MemoryCache.get`
and `put` are plain synchronous methods (no awaits, no I/O); the in-flight deduplication lives in
`CachedKernel`, with `asyncio` futures keyed by the cache key.
- **Entries are lossless; keys are canonical.** The canonicalisation above (`-0.0` → `0.0`, sorted keys)
  builds **keys** only. A stored value round-trips exactly, `-0.0` included, so a hit is bit-identical to a
  recomputation (Q7). The cache knows only JSON values; converting structured outputs (polar, airplane,
  curves) to JSON and back by the quantity's `type` is the engine's. Every hit
  deserialises a fresh object (no object is shared between calls).

### 8.5 Applications and preconditions

An **application** is a formula plus the bindings of its inputs, a condition and the name of the output
quantity.

- Every input parameter of the formula is bound either to a **quantity** or to a **constant with source**
  (ADR 0028). Every output parameter is bound to a quantity, or explicitly to `null` in `produce`: the
  implementation still returns it (ch. 8.12), the application does not expose it. Example: `stall-speed`
  returns its α sweep as `polar`; only the clean application produces `polar-stall`, the take-off,
  landing and inverted applications write `polar: null`. A forgotten output is an import finding, an
  unexposed one is a declaration.
- **One producer per quantity, with one keyed exception** (canon README, maintainer 2026-10-19, #1174): a
  quantity of type `per_control_surface` (`hinge-moment`) may be produced by several applications of **one**
  formula — one tool, one unit — and is the union of the applicable applications' entries; two formulas
  never produce it (ADR 0022). Such a quantity is bound by no application, so no value edge ever has to
  choose a producer: `graph._index_producers` admits the same exception, and a read of a quantity with
  several producers is a `GraphModelError`. Resolving a requested quantity to all its producers, their
  closures and the engine's union come with the first `per_control_surface` formula implementation.
- An application has at most two kinds of condition; without either it exists always:
  - `when`: one term of the closed vocabulary over facts of the aircraft geometry (`has_vertical_tail`,
    `has_aileron`, …). The canon `README.md` defines the vocabulary; each term is implemented once in
    `graph.py`. Terms over control devices go by the **role** a surface acts in, not by its name (maintainer:
    "a flap is every surface that acts like a flap"): `has_aileron` holds for a surface acting as aileron,
    flaperon or elevon; the butterfly condition needs a **pure flap** (role `flap`) **and** an aileron-acting
    surface (role `aileron` or `elevon`) — flaperons never count toward it (maintainer, 2026-10-17, D10). Without ailerons the roll quantities are `not_applicable`, code `condition_not_met`.
    **Evaluation** (`graph.facts_from_geometry`), from `trailing_edge_device.role` only (never
    `control_surface`, never a name); a device is one `(wing key, x_sec index)`:
    - `has_aileron`: some device has role `aileron`, `flaperon` or `elevon`.
    - `has_separate_flap_and_aileron`: some device has role `flap` and some device has role `aileron` or
      `elevon`. Flaperons are ignored for it; a mixed set (flaps, ailerons and flaperons) needs no special
      rule (KISS, D10).
    - `has_elevator`: some device has role `elevator`, `elevon` or `ruddervator`; `has_flap`: role `flap`
      or `flaperon`; `has_rudder`: role `rudder` or `ruddervator` (the rudder role set is shared). A
      `stabilator` counts for none of them.
    - **Surface terms** (maintainer, 2026-10-17, D9 = C) read each wing's required **`surface_type`** —
      never a geometric inference (the provisional planform rule is dropped); the geometry-format change
      gets its own ticket. The type follows the **function**, not the position:
      - `main_wing` — exactly one (biplanes are out of v1; a second `main_wing` is `main_wing_count`);
        `S_ref`, `b_ref`, `c_MAC` come from it alone, chosen by type and never by list position, and are
        AeroSandbox's own values of that wing (maintainer 2026-10-25, superseding the own integration of
        2026-10-22): `Wing.area(type="planform", include_centerline_distance=True)`,
        `Wing.span(type="yz", include_centerline_distance=True)` and `Wing.mean_aerodynamic_chord()`; area and
        span both include the centreline gap, and the flags are set in code, never left to ASB's defaults
        (#1262). The GEO adapter (`solvers/geometry.py`) measures them on the wing the one conversion
        `to_asb_airplane` builds; its tool versions are AeroSandbox's;
      - `horizontal_tail`;
      - `vertical_tail` — also tip fins and centre fins that carry a rudder or serve directional stability;
      - `v_tail` — counts as **both** a horizontal and a vertical tail;
      - `canard`;
      - `tandem_wing` — `S_ref` still from the main wing only (the tandem rule is a later domain question);
      - `winglet` — only when modelled as a separate wing (winglet sections of the main wing stay part of it).
    - `has_horizontal_tail`: some wing has `surface_type` `horizontal_tail` or `v_tail`.
    - A vocabulary term whose fact is not computed yet (e.g. `has_horizontal_tail` until #1187) makes its
      applications a declared `not_implemented`, never a `KeyError`.
    - `has_vertical_tail`: some wing has `surface_type` `vertical_tail` or `v_tail`.
    - **Ontology rule** (maintainer, 2026-10-17): terms that describe the aircraft's ontology — the surface
      types and the facts derived from them — are defined complete whether or not a canon entry uses them
      yet; ADR 0021 applies to mechanisms, not to the domain vocabulary.
    - **Layout check of `neutral-point`** (#1203): decided from `surface_type`, never from the planform, in every
      world, before AVL is started. Supported: exactly one `main_wing` and one `horizontal_tail`, plus any
      `vertical_tail` and `winglet`. Tailless, canard, tandem and V-tail layouts are
      `unsupported_configuration` / `unsupported_layout` (open: #1206 tailless, #1207 canard and tandem, #1208
      V-tail). A tail-shaped surface typed `main_wing` is the main wing: the type decides.
  - `given`: a list of input quantities (`role: input` or `target`, without an entry in `defaults.yaml`). The application exists
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
  - **Engine** (built with the first embedder, like `@relation`): an embedded formula is no node — no cache entry and no preconditions of its own (its inputs
    are the embedder's variables or inputs; the embedder's preconditions apply). **Its postconditions do
    run**, on every embedded evaluation — they guard what the relation returns (e.g. `stall-speed`'s
    `optimum_at_first_cl_peak` at each mass of the sweep, K32): the unscoped ones always, a scoped one when
    its application is listed. A violation is the embedder's: `on_violation: error` makes it
    `postcondition_violated` with `detail.embedded` = `<slug>.<application-id>`, `detail.postcondition` = the
    id and the variable values of the failing evaluation; `warning` becomes the embedder's `defect` warning
    with the same detail. The embedder node is cached as a whole; the build digest covers the shared code
    (ch. 8.4). Approval of the embedder follows approval of its closure. Evaluating one embedded
    formula several times at different variable values (`spar-break-load-factor`: `spanwise-loads` at
    `n = +1` and `n = −1`) is specified with this embed engine.
- **Optional parameters** (`optional:`, a list of input parameter names). The formula receives `None`
  when the bound quantity has neither a value nor a default, and selects its route by data. Unlike
  `given`, the application exists either way. The entry states, per route, which of three outcomes holds:
  - **a declared method limitation** → a `practice` warning naming the route (ADR 0020). Example: `r_m`
    of `motor-propeller-equilibrium`, route A without it (Q-PT-6).
  - **the canon's own definition for that data** → no warning. Example: `flap_deflection` of
    `airplane-configuration` on an aircraft without flaps: there is no configuration, the aircraft is
    unchanged (stall-speed, 2026-10-02); this is not a substitute.
  - **the value is needed after all** → the formula raises `FormulaError(invalid_input, missing_input,
    parameter=<name>)`; the **engine** fills `input_path = values.<slug>` from the application's binding, so
    the formula never sees a slug (ch. 8.12). Example: `flap_deflection` absent on an aircraft that has
    flaps.
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

- One producer per quantity; a second path only as a probe (A7). Exception: a `per_control_surface`
  quantity may have several producers, all applications of the same formula — the finding names the reason,
  one tool and one unit; and a `per_control_surface` quantity is bound by no application (one finding, which
  covers `given`, `variables` and embedded inputs).
- Unique symbols and slugs (A8).
- Targets only as `role: target` (A9, as its text says): every `role: target` quantity has a `target` kebab
  segment in its slug (anywhere: `stall-speed-target`, `roll-rate-target-approach`), except the one A9 names
  (`limit-load-factor`); no input or target slug contains `requirement`, `goal` or `req`; and an input or
  target quantity is produced by no formula. The reverse — a `target` segment implies role `target` — is
  not a rule: outputs computed at a target (`range-at-cruise-target`) are named after it.
- Units consistent across bindings (A4); dimensional check of law entries (later, report-only).
- **One home per rule.** The importer is the authority for model validity: every **structural** rule
  (front-matter fields, vocabularies, references, the rules above) lives in the importer, which ports them
  from `scripts/check_canon.py` (it may not import `scripts/`). Porting and deleting happen in **one**
  change (S13): the importer unit adds `importer --check` and its CI step and deletes the structural rules
  from `check_canon.py` in the same change; there is never a second copy, so no differential test exists.
  `check_canon.py` keeps only the **prose/authoring checks** the importer never does, because it never
  reads prose — the "Produces / from" and "Used by" lines and the README examples — as the canon
  document's own authoring check.
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
field leaves the canon and the kernel only reports it. An embedder whose closure runs a slower tool than
its own (`spar-break-load-factor`: `tool: APP`, embeds AVL) is settled by O14 or a declared `cost:`, not
by a derivation rule here.

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
  - **#1174 builds the base**: `SolverAdapter(runtime)` declaring its `tool` and `requirements` (distribution →
    module), with `available() -> bool` (capability check → `tool_unavailable`, Q10) and
    `tool_versions() -> {distribution: version}` (what `Provenance.tool_versions` and the cache key take;
    it replaces a single `version()`); `runtime.SolverRuntime` owns the spawn-context pool
    and the concurrency limit and offers `run_cpu(fn, *args)` and `run_process(files, commands, …)` (an
    async subprocess in its own process group and temp dir, killed and cleaned up on cancellation or
    timeout, Q17; the AVL adapter is its first user); and `regime(chords_m, v, speed_of_sound,
    kinematic_viscosity) -> list[KernelWarning]` (ADR 0028 check, ch. 8.2; the atmosphere values come from
    the caller, the ISA is the ATM formula's: `air-density-isa` outputs `rho`, `mu` and `a`, the solver entries
    bind them, and the kinematic viscosity is `mu / rho` of the bound values, never recomputed from the altitude). Regime codes: `reynolds_outside_band` (defect, Re < 3·10⁴
    or > 10⁶), `reynolds_bubble_sensitive` (practice, 3·10⁴ ≤ Re < 7·10⁴; below the band `reynolds_outside_band`
    alone applies), `mach_above_limit` (practice,
    0.3 < M ≤ 0.6), `mach_beyond_validity` (defect, M > 0.6). A worker function returns a `WorkerOutcome`
    (value plus diagnostics, logged by the parent at `DEBUG`) or a `WorkerFailure` the parent re-raises as
    `FormulaError`; a dead worker discards the pool and becomes `internal`. Tested with a stub solver.
  - **`minimum_sink_stall_limited`** (`practice`, #1268): the OPT adapter adds it to a minimum-sink solution whose optimum is the stall boundary (the sink power still falling at the first C_L peak); the value is returned there, with the boundary alpha and C_L in `detail`.
  - **Tool validity warnings belong to the adapter**, like the regime: they hold for every formula that uses
    the tool, so no canon entry repeats them and they are no precondition. Each names its source. AVL:
    `|p·b/2V| > 0.10`, the documented range of the primer (`defect`). AeroBuildup with a deflected
    control surface: NeuralFoil's `analysis_confidence` at `α_eff` of the deflected strips as a value, and
    "δ range of the τ fit unknown" (`practice`). A reference point a specific entry cites (Sadraey's
    20–25°) is emitted by that formula via `ctx.warn`, `practice`, and stated in the entry text.
  - **The ATM tool is an adapter too** (`solvers/atmosphere.py`): `asb.Atmosphere(altitude=h,
    method="isa")`, the canonical model the maintainer fixed (O5, 2026-10-05; ASB first). There is no
    second, hand-written ISA in the kernel. Its `requirements` include aerosandbox, so a missing ASB is
    `tool_unavailable`; fast-tier tests stub the adapter, the hand-computed COESA check runs against the
    real adapter in the `aero` tier.
  - **#1175 adds the domain methods** (`opti.stall` with `stall-speed`; `aerobuildup.sweep` arrives with
    `aerobuildup-evaluation`, the first formula that calls AeroBuildup itself; `avl.stability` …), each built
    on the base, alongside the first formula that needs it. Until then AeroBuildup is reached only inside
    the stall worker, through `solvers.aerobuildup.sweep_polar`, the one place that evaluates it.
  - **Implementation note, `stall-speed` (#1201).** The procedure always makes two bracketing sweeps: one at
    the speed a first lift-coefficient estimate implies (`BRACKET_CL`), one at the speed the first sweep's own
    extremum implies. The first C_L extremum moves with the Reynolds number; at the estimate alone the
    inverted trough lay about three sweep steps outside IPOPT's window. It is unconditional (never
    triggered by a failure) and not a fixed point; an optimum on the edge of the window is still an error.
  - **The AVL adapter** (`solvers/avl.py`, #1203): `neutral_point(airplane, cl)`. One own writer
    (`avl_writer.py`) emits the `.avl` text: no BODY (no fuselage is modelled), no CONTROL, Mach 0, `SREF`,
    `CREF`, `BREF` from the kernel's projected geometry function (one authority, ADR 0022), the reference
    point at the geometry origin. The aligned mesh (`avl_mesh.py`): one uniform spanwise distribution over
    the main wing's semi-span, the horizontal tail on the wing's stations over its span plus its tip (a
    station within 0.3 strip widths of the tip is dropped), a fin at the wing's strip width; a mirrored
    surface starts at the centreline, its y exactly 0 with the root chord held (a root stored at −0.25 mm gave
    a strip across its own mirror image and moved BRYAN's neutral point by 3 % MAC; one stored at +1.1 mm
    left a slit between the halves and made JAGUAR's neutral point drift 1.9 % MAC per span doubling). Section positions are not stations. `CLAF = 1 + 0.77 t/c` with
    the thickness from AeroSandbox `max_thickness`, computed in a pool worker. Every contour is repanelled to
    `avl_airfoil_points_per_side` (80) cosine-spaced points per side by `solvers/avl_contour.py`, always and
    not only when too large (AVL stops at 399 contour points; a conditional substitution would be undeclared,
    ADR 0020); AeroSandbox's own `repanel` is not used, it leaves the chord on BRYAN's contour. The chain of
    each surface is read through `surface_chain.oriented_chain`, the same rule as the planform values
    (root first, a surface stored on −y or tip first gives the same mesh, ADR 0022). AVL runs through
    `run_process`; the lift coefficient is constrained (`a c`), not trimmed. AVL exit or output that is not
    understood, or a `CLtot` that misses the request by more than 1e-4, is `internal` (a defect of ours); a
    vortex array overflow of the declared mesh is `avl_array_limit` (AVL signals it either by its overflow message or, on a very fine mesh, by a LAPACK "illegal value" with exit 0; both count). One AVL run never takes longer than `AVL_MAX_RUN_S` (120 s, far above the measured 15 s refined run; AVL can spin forever on a geometry it cannot solve): expiry kills the process group and is a `timeout` error of the quantity (`detail.run_limit_s`), distinct from the request's time budget. A deflected control device is refused (`unsupported_configuration`, the refusal shared with the AeroBuildup adapter), because no CONTROL is written. **Refinement check:** the adapter runs
    the declared mesh and the same mesh refined by `avl_refine_factor` (both counts), returns the declared
    value, and declares `avl_mesh_not_converged` if the two differ by more than
    `avl_refinement_tolerance_mac` of the mean chord, `avl_refinement_unchecked` if the refined mesh
    overflows. Settings (`Provenance.solver_settings`, public keys): `avl_nchord` 10, `avl_nspan` 24,
    `avl_airfoil_points_per_side` 80, `avl_core_ratio` 0.25, `avl_refine_factor` 2, `avl_refinement_tolerance_mac` 0.005, `avl_roll_refinement_tolerance` 0.01, `avl_roll_nchord_front` 12, `avl_roll_nchord_aft` 8, `avl_roll_branch_tolerance` 0.10; tool versions
    `avl-binary` and `aerosandbox`. The AVL world adds no regime warning: those come with the
    minimum-drag speed and are inherited. The reference value for BRYAN under these conditions is in
    `scripts/sim_export/crrcsim/AVL_CONVERGENCE.md`.
  - **The steady roll** (`opti.steady_roll`, `avl.steady_roll`, #1211). Both worlds solve the same roll: rotation
    about the stability x axis through the airplane's reference point, the stability-axis rolling moment zero,
    positive to the right.
    - *One orientation rule.* `to_asb_airplane` builds a mirrored surface from `surface_chain.oriented_chain`
      (y ≥ 0, root first), as the AVL writer does, so the sign helper sees the written side +1 in both tools.
      Before #1211 ASB received the surface as stored, and a mirrored wing stored on −y or tip first was a
      different wing to AeroBuildup (BRYAN, clean: C_D 0.246 against 0.070): a latent defect, fixed here and
      pinned by an aero test on the clean airplane.
      Scope change: every consumer of `to_asb_airplane` (the GEO properties, AeroBuildup) now refuses a mirrored
      surface whose sections fold back along y as `unsupported_configuration`, as the AVL mesh already did.
    - *Validity of the AVL world (#1243).* AVL is linear in δ and its primer gives `|pb/2V| <= 0.10` as the
      practical limit. Outside it (`ROLL_RATE_LIMIT`, tested with `>`: 0.10 itself is inside) the `roll-rate`
      formula declares `world_outside_validity` in the `avl` world (`detail`: `p_hat`, `p_deg_s`, `limit`) and
      the interval is the AeroBuildup world alone (ch. 8.13). The adapter's own `defect` warning
      `avl_roll_rate_beyond_range` stays: it is the tool's statement, the exclusion is the canon's decision.
    - *AeroBuildup.* IPOPT over α and the stability-axis rate. The window of α and the start value come from
      one sweep on the **clean** (unrolled) airplane: with the deflection the curve has kinks and its first
      local maximum lies far below the stall (trainer: C_L 0.364 at 1° against a clean peak of 1.233 at 16°),
      so a sweep on the rolled airplane brackets nothing. The window only keeps IPOPT on the physical branch;
      local stall under the deflection is reported by the diagnostics of the deflected evaluation. The
      `α + τδ` it reports is the shift before NeuralFoil's 360° blend (which uses the unshifted angle for its
      post-stall weight); the τ pin uses `include_360_deg_effects=False` for that reason.
      The start of the roll rate is the zero of the secant of the stability-axis rolling moment at the
      weight-carrying α (two numeric runs: without roll and at a quarter of the window): IPOPT started from a
      fixed fraction of the window ended in `Infeasible_Problem_Detected` on BRYAN at 20° (fraction 0.1; 0.25
      failed on other cases) although the equilibrium exists. A start is no result; if the secant has no
      damping the fixed fraction 0.1 is the start.
    - *AVL.* The controlled wing is split at the hinge line into a front and an aft SURFACE of one COMPONENT on
      the same span stations (Drela's rule 3, `avl_doc.txt:1110-1117`): front `AFIL 0..x_h`, aft `AFIL x_h..1`,
      the CONTROL on the aft piece with its hinge at the aft leading edge (`amake.f:418-423`), so the deflected
      part is the whole aft strip. The aft leading edge is at `x_le + x_h c` with z unchanged (AVL tilts the
      normals, it never rotates the lattice). Off the device the cut is the hinge fraction of the nearest
      controlled station. Declared chordwise counts: front 12, aft 8 (`SPLIT_N_CHORD`); the refinement check
      doubles them and the spanwise count. Reason: on one full-chord surface the control derivative at the
      hinge carries an O(1/N_chord) discretisation error (a camber-slope jump), 4.5 % (BRYAN) and 7.5 %
      (JAGUAR) between the declared and the refined mesh, and aligning the hinge with a panel edge does not
      cure it. The clean file (neutral point) is unchanged. AVL's chordwise limit is 50 vortices per surface
      (`KCMAX`, `amake.f:55`); above it AVL prints an array overflow and returns zero: the adapter refuses
      it as `avl_array_limit` (a refined mesh beyond it is `avl_refinement_unchecked`).
      A refined run that is beyond the arrays or ends in `avl_roll_branch_inconsistent` leaves the declared
      value standing (the declared run passed every check) and declares `avl_refinement_unchecked` with the
      `reason`; a declared run off the branch is an error.
      The other fixed arrays count too: 500 strips (`NSMAX`, mirror images and both pieces of the split
      wing included), 100 surfaces, 6000 vortices; each overflow message is `avl_array_limit`.
    - *Driven stations.* The main wing of a driven run has one sine-to-tip distribution over the half span,
      `y = (b/2) sin(π/2 t)` (AVL's `Sspace` −2 from root to tip, `avl_doc.txt:1043-1048`), the device ends
      exact: their `t` is rounded to a strip count and `t` runs evenly inside each of the three pieces
      (inboard, device, outboard), so the strip widths stay continuous across the ends (Rule 2,
      `avl_doc.txt:1100`); front and aft piece have the same stations, the tail takes the wing's stations
      inside its span. Reason: with uniform strips the roll damping `Clp` has an O(1/N) error at the tip
      (it halves on every doubling; the aileron effectiveness `Cld01` is within 0.5 % at 24 strips);
      bunching at the device ends is no remedy (cosine inside each piece is worse than uniform).
      Declared mesh: 24 strips, refined 48, chordwise (12, 8) and (24, 16); the 6000-vortex limit allows a
      refined mesh of 64 strips, not one of 80. Doubling check, p̂ at C_L 0.7, δ 20°:

      | N declared → refined 2N | BRYAN | JAGUAR |
      |---|---|---|
      | 12 → 24 | −0.88 % | +0.24 % |
      | 16 → 32 | +0.92 % | +0.43 % |
      | 20 → 40 | −0.09 % | +0.73 % |
      | **24 → 48** | **+0.15 %** | **+0.69 %** |
      | 28 → 56 | +0.20 % | +0.66 % |
      | 32 → 64 | +0.37 % | +0.67 % |
      | 40 → 80 | refined run beyond `NVMAX` (`avl_refinement_unchecked`) | same |

      p̂ of the declared mesh is 0.28643 (BRYAN) and 0.27927 (JAGUAR). Caveat: from 48 to 96 strips `Clp` and
      `Cld01` still move by about 0.5 % each, in opposite directions, so p̂ is flat partly by cancellation.
      The check is on p̂, the canon output; `Clp` and `Cld01` of these runs are never exposed as converged
      values. 24 strips was kept over 16 because 16 → 32 is within 0.1 % of the 1 % bound for BRYAN.
    - *Branch consistency.* In the same AVL session, after the trimmed roll, the run holds `p'b/2V` and the
      aileron at zero and prints the stability derivatives; the linearised rate `-Cld01 δ / Clp` must agree
      with the trimmed one to 10 % (plus the print floor 2·10⁻⁴), otherwise the adapter raises
      `avl_roll_branch_inconsistent` (`not_converged`, both values in the `detail`). A numerical sanity check
      of the solver, no domain threshold: the nonlinearity measured on the fleet is 0.2–0.4 % (BRYAN 0.27932
      against 0.28005; the unsplit file 0.2623 against 0.2634), whereas BRYAN at 96 spanwise strips lands
      on a spurious branch (0.825 against 0.347, the state without roll at 7.1° instead of 4.2°) with no
      AVL message, and every other check of the run (`C_L`, residual moment, control echo) passes.
  - Adapters know no canon names. They return warnings without `quantity`; the engine sets `origin` to
    the quantity of the node whose call produced them.
- Data: KAT (the fitted components) and APC (the fitted propeller's measured table) are **plain reads of
  `AircraftInput.components`** (ch. 8.11), like GEO reads the geometry. The tool codes classify the
  formulas; they are no data sources. The kernel loads nothing on its own and calls nothing back (D14).

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
| 5 Write | writes `canon_model.json` (sorted, stable formatting), its content hash and the importer version; writes `IMPORT_REPORT.md` (diff, findings, Appendix A table, stage-2 approval table and unmapped inputs) | — |

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
value, every result is `validated: false`), `shape` (an approval classification), `tags` (except the six taxonomy families, below), `tex`,
`source_status` and `dimensional_check`. A new README field is carried unless this list is extended.
Normalisation adds nothing but: `bind` values become a quantity reference or `{const, source}`; absent
optional fields get their stated default (`when`/`given` absent = always, precondition `applications`
absent = all, `cost` derived, ch. 8.7); the default application is written out explicitly; the `embeds`
closure (ch. 8.5) is stored alongside the listed embeds. **Taxonomy (#1218).** The tags of the families `module/`, `point/`, `stage/`, `group/`, `discipline/`
(quantities) and `direction/` (formulas) are carried as the structured fields `module`, `point`, `stage`,
`group`, `discipline` and `direction`, and a probe quantity's `checks: <slug>`. The values of the families
are stated once, in `taxonomy.yaml` (label, explanation, order, properties; tool codes with names; the
world-to-tool mapping), and the model carries it as the namespace's `taxonomy`. Stage 3 validates the tags
against it (`importer/tag_rules.py`): an unknown value, a missing tag where the quantity's place in the
calculation requires one, a target outside a target module, a group that disagrees with its stage or
module, an undeclared tool or world, a probe that checks nothing. A quantity has at most one tag per family
(stage 2). The navigator and the kernel read the vocabulary from the model.
Fixture models in
`tests/fixtures/` follow exactly this shape and are validated against `canon_model.schema.json`. The model
also holds `schema_version`, `content_hash` and `importer_version`. References are slugs; namespaces are written `<namespace>:<slug>` (`calc:stall-speed`,
later `sizing:…`), and a bare slug in a request means `calc:`.

**Shape and identity of the model file** (decided for #1174, unit 6):
- **Types first, schema generated.** `canon/model.py` holds the Pydantic types (frozen, `extra="forbid"`,
  invariants in the model, ch. 8.11). `canon_model.schema.json` is generated from them (`python -m aero_kernel.canon.schema_file [path]`) and committed; a
  test fails when the committed schema differs from the generated one. Never hand-written.
- **Layout.** `{schema_version, content_hash, importer_version, namespaces: {"calc":
  {quantities: {<slug>: …}, formulas: {<slug>: …}}}}`, dict keys bare slugs. **Every reference inside the
  model is fully qualified** (`calc:stall-speed`, embeds items `calc:stall-speed.clean`); application ids
  and parameter names stay bare. Every `embeds` and `embeds_closure` item is normalised to
  `<ns>:<slug>.<application-id>` (a bare slug of a single-application formula as that application's id, `.default` when it is the implicit one); a bare item does not load.
  Absent `when`, `given` and check `applications` are stored as `null` (= always / all). Only a request's bare slug means `calc:`. **Outside the model** — results, errors (`formula`,
  `quantity`), messages and world assignments — a `calc:` slug is written bare, a slug of any other
  namespace qualified — except a requested quantity's own slug (`QuantityResult.slug` and its error's
  `quantity`), which echoes the request's spelling exactly, so the caller can match it (an unknown slug
  cannot be normalised anyway). Two request entries that name the same quantity in different spellings
  (`stall-speed`, `calc:stall-speed`) are a duplicate: qualifying a slug is syntactic (bare = `calc:`), so
  `ComputeRequest` compares the qualified forms and rejects the request as malformed; the graph never sees
  a duplicate and keeps request order. World assignments key formulas by bare slug, so two uncertain formulas of the same
  bare slug in different namespaces are a model error (`GraphModelError`) until a second namespace needs
  them.
- **`schema_version`** is the integer `2` (`Literal[2]`; 2 since the taxonomy and the tag fields, #1218), raised on every change of the model's shape. The
  loader reads it **before** type validation, so a newer model reports its version, not a cascade of
  unknown fields; any other version is `internal`, escalate. The loader raises `CanonLoadError` carrying
  that `KernelError`; turning it into per-quantity results is the api's job (`compute()` never raises,
  ch. 8.1). `importer_version` is a non-empty string. **There is no source-commit pointer** (maintainer,
  2026-10-18, decision e): the model names no git commit, and the importer runs no git at all. Which commit
  shipped a model is found from its content: `git log -S <content_hash> --
  aero_kernel/canon/canon_model.json`. The blocking `--check` keeps model and canon in step, whatever merge
  strategy lands them.
- **`content_hash`** is `"sha256:" + hex` of the canonical JSON of `namespaces` only — the canon's content,
  not its provenance (`importer_version` and the hash itself are outside it), so two imports of identical
  content from different commits hash alike. Canonical JSON is the one used for
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
  and have no entry in `defaults`; `positive` and `at_most` only on input/target scalars, `positive` with an `at_most` > 0, and a default
  is > 0 for a `positive` quantity and not above `at_most`; `variables` exactly with `embeds`;
  `embeds` ⊆ `embeds_closure` and every closure item resolves. **Cross-formula rules stay with the
  importer** (ch. 8.6): one producer per quantity, unit consistency, closure correctness and acyclicity,
  cost derivation, and the two-stage approval (#1251): a quantity's `data:` sources (`<kind>:<location>`, five closed kinds) belong to quantities no formula produces and their locations are looked up in the repository files (`importer/data_sources.py`); stage 2 is derived in `importer/approval.py` and reported in `IMPORT_REPORT.md`. The implicit application is written out with id `default`.
- **The embeds closure** is a field of each embedder, `embeds_closure`: the sorted, de-duplicated items
  reachable through `embeds` (the direct ones included), computed by the importer.
- **Loader** (`canon/load.py`): version pre-check, Pydantic validation (the JSON Schema is generated from
  the same types; `jsonschema` is a test dependency only, used to validate fixtures against the committed
  schema), and — once a registry exists — that every registered implementation and check has its slug and
  id in the model (ch. 8.6).
- **`values` against the canon** — `unknown_quantity`, `not_an_input`, `non_positive_value`, `value_above_maximum` (ch. 8.11) —
  are `validate.validate_values(values, model)`, built with the model types (unit 6), called next to
  `validate_aircraft` in step 1.

Rules:
- **All or nothing.** Any failure in stages 1–3 writes nothing. The importer lists the findings with file,
  field and message; they are fixed in the canon document, not in the model.
- **The model is never edited by hand.** It is only produced by the importer, so model and document cannot
  drift apart unnoticed.
- **Idempotent.** Importing the same canon document twice yields a byte-identical model.
- **`--check`** runs stages 1–3 in memory, writes nothing, needs no git, and compares the result with the
  committed model by `content_hash`, `schema_version` and `importer_version`. A finding **or** a mismatch exits 1, and the CI step **fails the build**: the
  shipped model is the kernel's own artefact (ch. 8.4), so a canon change re-imports the model in the same
  change. Canon authors run it instead of the structural part of `check_canon.py`.
- **Vocabulary drift.** The canon README defines the `when` vocabulary and the quantity types; the model's
  Literals copy them. An importer test reads those two README tables and fails when they differ from the
  Literals, so the two cannot drift apart unnoticed.
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
  - AVL runs as a plain `subprocess.Popen` (pipes, `start_new_session=True`); its `communicate()` runs in a
    thread pool the runtime owns. There is no asyncio subprocess transport (#1188: cancelling asyncio's
    start task can hang the shutdown forever, CPython gh-103847, not fixed for 3.11/3.12).
  - Formula code itself runs on the loop; it is cheap by contract (ch. 8.12). Only the solver adapters
    leave the loop. There is no size threshold.
- **Concurrency from the graph.** Independent nodes of the subtree and world assignments (A11) run
  concurrently (`asyncio.TaskGroup`). The dependency graph decides what may run in parallel, never the
  formula code.
- **Bounded.** Execution resources are never global. The kernel always **owns** its process pool (maintainer
  D12, 2026-10-16: no injected executor; restorable from `a2825d72` if the app ever needs one):
  - The **stateless `compute()`** takes one optional keyword argument, `max_concurrency=` (default
    `os.cpu_count()`). The limit counts concurrent **solver calls** (pool tasks and AVL subprocesses); graph
    nodes waiting on them cost nothing. It creates its pool on the first solver call and shuts it down before
    returning, so it stays free of state (Q20). Spawning costs about a second; callers that compute often
    use `CachedKernel`.
  - **`CachedKernel`** owns one pool and one limit for its lifetime. They are created lazily and closed by
    `async with` or `aclose()`.
  - **Submissions are gated** by a second semaphore equal to the pool's resolved worker count, so every
    submitted item has a free worker and nothing waits in the pool's own call queue.
  - **Closing.** Once `aclose()` has begun, the runtime refuses work: a call not yet running in a worker
    fails with `RuntimeError("… closed")`, never with a `CancelledError` nobody asked for, and no new pool is
    ever created; no call starts after closing began. `aclose()` drains this runtime's running jobs off the
    loop, then shuts the pool down in `asyncio.to_thread` (waiting for the workers, cancelling what is
    pending): when it returns, no work of this runtime is running.
  - **Threads for AVL.** The runtime also owns one `ThreadPoolExecutor` (`max_workers = max_concurrency`)
    for the subprocesses' `communicate()`, created with the runtime and shut down in `aclose()`; the loop's
    default executor is never used.
  - Nothing starts at import. Resources are not results: they never change a value.
- **Cancellation.**
  - Cancelling the `compute()` task cancels all child tasks.
  - It kills running AVL subprocesses (their whole process group) and removes their temporary directories.
    The spawn is synchronous, so there is no start to interrupt. On a cancel or timeout the kernel sends
    `SIGKILL` to the group (`os.killpg`), then waits a bounded 5 s for `communicate()` to reap the child,
    ignoring further cancels during that wait only, and re-raises. Past the bound, one `WARNING`
    `process not reaped (<tool>)` (ADR 0020); the stuck `communicate()` thread then holds one slot of the
    runtime's thread pool for the rest of its life, and `aclose()` still returns (`shutdown(wait=False)`),
    but if a descendant escaped the process group, interpreter exit waits until it exits, because
    `concurrent.futures` joins its workers at exit (AVL forks nothing: rare, accepted). The pid-reuse race between exit and `killpg` is not closed
    (no `WNOWAIT`; KISS).
  - Work already running in the process pool is allowed to finish but its result is discarded, because
    pool workers cannot be interrupted safely.
  - `asyncio.CancelledError` is always re-raised, never turned into a result.
- **Time budget** (built with the solver path, #1201). `ComputeRequest.time_budget_s` (default `None` = no budget) is one wall-clock budget for
  the whole request, enforced with `asyncio.timeout` around the graph run. A budget that is not a finite number > 0 is an
  input error (`non_finite_number` / `non_positive_value`, `input_path` `request.time_budget_s`). Quantities still open when it expires, and
  those waiting for them, get `error.category = timeout`; quantities already finished are returned, also when their
  layer did not complete. The running tasks are cancelled; pool jobs finish and are discarded.
- **Cache under concurrency (`CachedKernel` only).** The cache is used from the event loop only, so it needs no lock. **In-flight
  deduplication** (mode `use`): when two concurrent requests need the same key, the second awaits the first
  one's future instead of computing it again.
- **No hidden loop.** The kernel never calls `asyncio.run`, never creates or closes the caller's loop and
  keeps no loop-bound global state. It works inside FastAPI, in pytest-asyncio and in plain
  `asyncio.run(compute(...))` from scripts.
- **Not in v1: `compute_iter()`** (maintainer, 2026-10-14). An async generator yielding each
  `QuantityResult` as soon as it is final can be added later without changing `compute()`; first the canon
  is built and checked against real calculations.

### 8.11 Input and request

**Everything is pushed** (maintainer D14, 2026-10-16): *the kernel is given all the data it needs, then it
computes; if something is missing, that was the caller's mistake or intent.* There is no runtime callback out
of the kernel of any kind — no provider, no lookup, no database access, no file read.

```python
class AircraftInput(BaseModel):          # extra="forbid"
    airplane: AirplaneGeometry           # docs/geometry-format/airplane-geometry.schema.json
    components: Components | None = None # the fitted components, a contract of its own (below)
    values: dict[str, float]             # canon slug → value in the quantity's canon unit

class ComputeRequest(BaseModel):
    quantities: list[str]                # canon quantity slugs, not formula slugs
    include_long_runs: bool = False      # ch. 8.7
    # time_budget_s: added with the solver path (ch. 8.10)
```

`AircraftInput` and `ComputeRequest` are pure data with a JSON form and a JSON Schema.

**`Components` — the fitted parts, pushed** (D14). The app resolves the parts fitted to the aircraft from
its component tree and catalogue and passes them as data; selecting a part from the catalogue is the app's
(or a later design canon's), never the kernel's. Rules:
1. **A contract of its own**, separate from the geometry format (which has no components, D11), with its own
   JSON Schema and `schema_version`; the kernel accepts only the version it was built for.
2. **The full measured propeller table**: the fitted propeller's diameter plus `C_T(J)` **and** `C_P(J)`
   for **every** RPM block of the APC data, because the propeller speed is a solver variable (torque
   balance, the thrust optimisers) and is interpolated across blocks; never a single reduced curve.
3. **Absence survives the push**: a value the catalogue does not have (e.g. the motor resistance `R_m`,
   #1149) arrives **absent**, never filled, estimated or defaulted by the app. Route selection by data
   (`optional:`, Q-PT-6) and the warning that declares the route depend on it (ADR 0020).
4. **The cache key comes from the input only**: the components are direct input values of the nodes that
   read them (ch. 8.4); no provider hash exists.
5. **KAT and APC are plain input reads** (ch. 8.8): `airplane-components` and `propeller-table-lookup` read
   `AircraftInput.components` as `airplane-geometry` reads the geometry.
The canon quantity `airplane` (type `airplane`) is **geometry only**: `AircraftInput.airplane`. The fitted
parts are the separate canon input quantity **`components`** (type `components`, S15, on the canon's main
since `84599128`), bound to `AircraftInput.components`; only the formulas that read parts bind it, so a
change of parts expires only their subtree (A1). A missing `components` is the ordinary `missing_input` of
that one quantity (ch. 8.11, 8.13). Its exact field list is defined with the first KAT / APC formula
implementation, not before (ADR 0021).

**Binding of canon input quantities to the input:**
- **Units.** A value is given, and a result returned, in the unit the canon model declares for the
  quantity — SI-coherent, with the canon's declared exceptions: angles in `deg` (and `deg/s`), energy in
  `Wh`, the battery charge in `mAh` and its C-rate in `1/h`, the motor constant in `rpm/V`. The kernel converts none of them; a formula converts internally
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
  are `aircraft-mass`, `centre-of-gravity-measured`, `altitude`, `flight-speed`, `angle-of-attack`, `load-factor`,
  `gravity`, the control-device angles (`flap-deflection-takeoff` /
  `-landing`, `aileron-deflection`, `elevator-deflection-up` / `-down`, `crow-flap-deflection` /
  `crow-aileron-deflection`; deg, geometry sign convention, no default) and the `*-target` quantities. Assumptions are values like any
  other (R1); whether a value is assumed or measured is not the kernel's concern.
- **The frame of position quantities** (#1203): `neutral-point` and `centre-of-gravity-measured` are x coordinates in
  the geometry frame of `airplane`, x aft positive, in metres. The app's own CG field follows in #1209.
- **Validation rules** (maintainer, 2026-10-25, #1260). A requirement on the input data or a limit of a tool is a
  canon rule in `rules.yaml` (README, "Validation rules"); its thresholds are parameters, not literals. The
  importer carries them into `namespaces.calc.rules`. `aero_kernel/rules.py` resolves a threshold for one call
  (the canon value, or the caller's `AircraftInput.rule_overrides`) and remembers what it handed out;
  `provenance.rules_used` declares it. The geometry rules run once in `validate_aircraft`, on every path.
  A model that lacks a rule the kernel reads is a defect (`KeyError`), never a silent skip.
- **Defaults** (maintainer, 2026-10-17, S5). A missing value is computed with its **default**, and the
  caller can set or override every value. Defaults are never hard-coded and never in a quantity entry:
  - **One settings file in the canon document**, `_reversa_sdd/calculations/canon/defaults.yaml`: a mapping
    `<quantity slug>: {value, unit, basis, source, regime}` — `value` in the quantity's canon unit, `basis` what kind of value it is (`definition`, `standard`, `sourced`, `convention` or `start`; a `convention` is a chosen value without a published source, adopted on the maintainer's word, #1219; a `start` is a starting value the designer is expected to change, #1258), `source` the citation,
    `regime` the RC/UAV check (ADR 0028: why the value holds for chord Re 3·10⁴–1·10⁶ and Mach ≤ 0.3, or
    that it is regime-independent, e.g. standard gravity). The quantity entries carry no `default:` field.
  - **The importer** validates it (stage 3: every slug exists, has role `input` or `target` and type
    `scalar`; `value` finite, for a `positive` quantity > 0 and not above its `at_most`; `basis` one of the five terms, `source` and `regime` non-empty; no slug
    twice) and writes it **into the one model artefact**, `canon_model.json`, as
    `namespaces.calc.defaults: {<slug>: {value, unit, basis, source, regime}}`. There is no second file and no
    second loader: the defaults load, hash and check with the model (`content_hash`, the build digest,
    `importer --check`), and the model's own validators cover them (ch. 8.9).
  - **When a default counts as taken:** a node whose implementation is actually **called** binds a supplied
    input or target that has no value but a default (an absent `optional:` parameter with a default takes
    the default, not `None`). A node that stops at rows 1–7 of ch. 8.13 — not applicable, an error, or
    skipped — takes none: provenance never claims a default for a result whose formula was not called. A
    called formula that then fails still took it (it may be the cause of the failure, ADR 0020).
  - **Reporting.** Every default taken is in `provenance.defaults_used` (`{slug, value, unit, source}`,
    sorted by display slug) and
    logged once per call at `INFO` (ch. 8.14). A **target** default additionally gives the `practice`
    warning `default_target_used` (`origin` = the target slug), inherited by every quantity that reads it
    (ch. 8.2); a physical-constant default (`role: input`, e.g. `gravity`) gives none.
  - **ADR 0020.** A target default stands in for a decision the designer did not make, so it is a
    substitution; the `practice` warning declares it (domain practice, because it is sourced and
    regime-checked). A constant's default is the constant's value, not a substitution, so the provenance
    entry is its declaration. The log level is not the declaration: ADR 0020 asks for the result warning,
    which exists; `INFO` only keeps the operator log free of design choices.
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
| `non_positive_length` | a chord ≤ 0; a fuselage semi-axis `a`, `b` < 0 at the first or last section, ≤ 0 at an interior section (a lofted fuselage closes to a point or a line at its ends; team-lead 2026-10-22, BRYAN nose/tail points); a wing whose span — the summed Euclidean length of its `xyz_le` chain — is 0 (path: its `x_secs`) |
| `non_positive_exponent` | a fuselage super-ellipse exponent `n` or `n_lower` ≤ 0 |
| `non_positive_thickness` | an airfoil of thickness ≤ 0 (inline contour, or NACA thickness digits `00`) |
| `too_few_sections` | a wing or a fuselage with fewer than two `x_secs` |
| `invalid_airfoil_contour` | inline coordinates with fewer than 3 points, or whose first and last point do not both lie at the contour's largest `x` (a blunt trailing edge is allowed; no tolerance is invented) |
| `unresolved_airfoil` | an airfoil string that is not a NACA 4-digit designation (`^naca\d{4}$`, case-insensitive, no spaces): the only kind a solver builds without loading data; a 5-digit or 6-series section is passed inline |
| `segment_on_last_section` | the last `x_sec` carries a `trailing_edge_device`, `spare_list` or `turbulator`: there is no segment for it, so the kernel would silently drop it |
| `control_surface_without_device` | a `control_surface` without the `trailing_edge_device` it is a projection of: its role would be unknown |
| `missing_surface_type` | a wing without its `surface_type` (D9: required, never inferred) |
| `main_wing_count` | not exactly one wing of `surface_type` `main_wing` |

`values` are checked here for finiteness only. **Their admissibility comes from the canon model, never
from a slug written in code:** a quantity entry may declare `positive: true` (strictly > 0 by definition —
a mass, a density, gravity; a fact, not a design judgement, A10), and the canon-loader unit checks every
supplied value of such a quantity, code `non_positive_value`, `input_path = values.<slug>`, together with
`unknown_quantity` and `not_an_input`. A quantity may also declare `at_most: <number>` (an efficiency is at
most 1); a supplied value above it is `value_above_maximum`, same path. `validate_aircraft` names no quantity slug except in the two
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
    stall = await ctx.solvers.opti.stall(x["airplane"], ...)   # leaves the loop
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
  worlds), `warn(code, message, detail=None)` — the severity follows from the closed warning table, as an
  error's flags follow from its category — and `embedded(item)` (built with the first embedder). Nothing
  else: no cache, no request, no global.
- **Formula code is cheap.** It runs on the event loop. Anything heavy goes through an adapter; adapters
  run CPU work in the process pool and AVL as an async subprocess (ch. 8.10).
- **Picklability** concerns only adapters: what they send to the pool is a module-level function and plain
  data. Formulas themselves never cross a process boundary.
- **Failure.** Raise `FormulaError(category, code, message, hint, detail=None, parameter=None)` for an
  expected failure. Formulas and adapters may raise only `invalid_input` (e.g. `missing_input` for an
  optional parameter that is needed after all, naming its `parameter`; the engine derives `input_path`), `unsupported_configuration`,
  `not_converged` and `tool_unavailable`; `timeout`, `upstream_failed`, `not_implemented` and `internal`
  belong to the engine. The engine turns a `FormulaError` into a `KernelError`, adding `quantity`,
  `formula`, `application`, `world` and `retryable`/`escalate` from the category. Any other exception
  becomes `internal`. Never return a substitute value (ADR 0020).
- **Preconditions** are separate functions, `@precondition("stall-speed", "<check-id>")`, run only for the
  applications the canon scopes them to (ch. 8.5), taking the same
  `x` and returning `held | violated | unchecked` with a message. **Postconditions**,
  `@postcondition("stall-speed", "<check-id>")`, take `x` and the implementation's full return dict `y`
  and return the same three states.
- **Embedded relations** (ch. 8.5; built with the first embedder). The module of an embedded formula exposes its relation as a plain,
  module-level function over parameter names (numpy- and CasADi-compatible where an OPT formula embeds
  it); its `@formula` coroutine and every embedder call that one function, so there is one implementation
  per relation (ADR 0022). For an embedded optimisation the function is its problem (built into a given
  `asb.Opti` or solved at given values of the embedder's variables); the formula's module decides which and
  documents it. An embedder obtains it **only** through `ctx.embedded("<slug>.<application-id>")`, which
  returns the relation with that application's constants and quantity bindings already applied (the values
  arrive through the embedder's inputs) and its postconditions; the embedder passes only its `variables:`.
  Evaluated as a whole, the handle runs the postconditions on every call; built into an outer problem,
  the embedder passes the solved values to the handle's `check(...)`. The engine **records** the items each
  run requests through `ctx.embedded`; the embedding tests assert that they equal the formula's `embeds`
  (S7: no static source scan).
- **Registration** is by decorator at import of `aero_kernel.formulas`.
  - **Shape.** `registry.Registry` holds, per qualified formula slug, one implementation, its embeddable
    relation if any, and per `(slug, kind, check id)` one check function. The decorators `formula`,
    `relation`, `precondition` and `postcondition` are methods of a registry; the module-level names are
    those of the **default registry**, which `aero_kernel.formulas` fills at import and then **freezes**
    (any later registration raises). A frozen registry is a static table of code, not call state, so the
    stateless rule (ch. 8.4) holds; the shipped `Build` holds the frozen default, and tests build their own
    `Registry()` and `Build` for `evaluate` instead of touching the default.
  - **Signatures.** `@formula(slug)` on an `async def f(x, ctx) -> dict`;
    `@relation(slug)` on the module-level relation function (ch. 8.5); `@precondition(slug, id)` on a
    plain `def check(x) -> CheckResult`, `@postcondition(slug, id)` on `def check(x, y) -> CheckResult`
    (`CheckResult`: `held | violated | unchecked` plus a message). Decorators stack, so one check function
    serves several `(slug, id)` pairs — one implementation per check (`optimum_at_first_cl_peak` for
    `stall-speed` and `butterfly-approach`). A duplicate registration or a non-coroutine `formula` is a
    `RegistryError` at import — a programming error, never a result.
  - **Parameter names are not repeated in code** (precedence note at the top). Considered and rejected,
    because each is a second, hand-kept copy of what the model owns: names in the decorator
    (`inputs=…, outputs=…`), a typed `Inputs` model per formula, keyword parameters in the signature; and an
    AST scan of `x["…"]`, which is fragile; and a hand-kept interface fingerprint (S6), which could only
    fire if CI was bypassed, since model and code ship together. The body still *reads* `x["name"]` — use,
    not a declaration. **Q11 instead:** every formula's unit test builds `x` **from the model** (a test
    helper maps the bound quantities' values to the formula's parameter names), so a renamed or added
    parameter fails that test; the engine's check that an implementation returns exactly the output
    parameters (otherwise `internal`) covers the output side.
  - **Traceability.** `Registry.check_traceability(model) -> TraceabilityReport(findings, not_implemented,
    ok)` reports a registered slug or check id the model does not have (`unknown_formula`,
    `unknown_check`) and a check registered on the wrong side (`check_kind_mismatch`); loading the `Build`
    runs it, and the formulas unit asserts it is `ok` on the shipped model. A model formula without an implementation
    is no finding but `not_implemented` at runtime (Q1). `@relation` and the embedding checks arrive with the
    first embedded formula (ADR 0021); a working version exists in commit `13dde61b` to restore from.

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
drag, an output of `stall-speed` read by `stall-break`. The negative extremum `C_L,min` is not
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
- **A world outside its validity** (ADR 0027 point 8, maintainer 2026-10-25, #1243). A world whose method states a
  range and whose result lies outside it declares that with `ctx.warn("world_outside_validity", …)` and still
  returns its values; the warning (`practice`, the world on it, `detail`: the value and the limit) *is* the
  exclusion. The merge drops an assignment from `min`, `max` and `Interval.worlds` when a
  `world_outside_validity` warning is anywhere in the subtree of that assignment (a dependent of an excluded
  world is excluded with it); the warnings of the dropped assignment stay on the quantity. This is not a
  failure: a failed assignment is still never dropped, and with a failed and an excluded assignment the
  failure is reported. One remaining assignment gives an interval with `min == max`. **Every assignment
  excluded** gives an error, `unsupported_configuration`, code `all_worlds_outside_validity`, no world,
  `detail.worlds_excluded` (assignment → value); like every error it carries no warnings. `detail.worlds_ok`
  of another failure lists the excluded assignments too, since they computed. The roll rate is the first
  user (ch. 8.8).
- **Which failure is reported.** When several assignments fail, the quantity's error is that of the failed
  assignment whose run has the lowest row in the status order below, then the lexicographically smallest
  assignment key. The row is the run's, not the error code's: a failure the formula raises while computing
  is row 8 whatever its code (a `missing_input` raised by a formula is not the engine's row 5).
  `detail.worlds_ok` holds the values that did compute. A failure that is the same in every assignment — a
  failed node shared by all of them (outside every uncertain subtree), or a refusal every world raises
  alike, such as the neutral point's unsupported layout — has its cause in no world: the error carries no
  `world` and `worlds_ok` is `{}`. `upstream_failed` is decided per assignment: a dependent inside an
  uncertain subtree is `upstream_failed` in exactly the assignments where its predecessor failed.
- **Continuous causes** (a parameter evaluated at its bounds, A11 rule 2) and the **monotonicity check**
  (rule 4) are declared in the canon model but not in v1: such a formula returns `not_implemented`, code
  `continuous_uncertainty`. The core chain has only method worlds.

**Status of a node — one order** (2026-10-17, replacing the predecessor-only table). A node takes the
**first** status that applies:

| # | Applies when | Node | reason / code |
|---|---|---|---|
| 1 | its own `when` / `given` is unmet | `not_applicable` | `condition_not_met` / `not_given` |
| 2 | a read predecessor is `not_applicable` | `not_applicable` | `depends_on_not_applicable` |
| 3 | in this order: its `when` term has no fact yet; it reads a value whose type v1 cannot carry; it has no implementation | `error` | `not_implemented` (`unsupported_value_type` for the read) |
| 4 | a read predecessor is `error` | `error` | `upstream_failed` (ch. 8.1 for retryable/escalate) |
| 5 | a read input has no value and no default | `error` | `missing_input` |
| 6 | it is a `minutes` formula and `include_long_runs` is off | `skipped` | `long_run_not_included` |
| 7 | a read predecessor is `skipped` | `skipped` | `depends_on_skipped` |

The principle: report first what **no change by the caller would alter**. A quantity that does not exist
for this aircraft (1, 2) is not applicable whatever else fails; a kernel gap (3) remains even if the
caller supplies more; a failure (4, 5) is what the caller can fix; a skip (6, 7) is only the caller's
choice, and reporting it first would promise a value that turning long runs on would not deliver.

Every error propagates the same way, `missing_input` included: the quantity that reads the missing value
directly gets `missing_input`, its dependents `upstream_failed` with the cause in `detail.causes`. A
predecessor counts only if the node actually reads it; an unused output of a multi-output formula does not
propagate. `Subtree.propagate` is the one home of rows 2, 4 and 7; the engine applies the order. How the
statuses of several producers of one `per_control_surface` quantity combine is specified with the first
such formula implementation (ch. 8.5).

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
  `world`. With `call_id` the lines of one call can be followed through concurrent tasks.

**Levels.**

| Level | What | Examples |
|---|---|---|
| `DEBUG` | every step of the engine, to check the code runs as intended | subtree and order; per node: start, end, duration, status; cache hit/miss with key prefix; world assignment; solver call with its settings and duration; precondition result |
| `INFO` | one summary line per `compute()` call and per import, plus one line per default taken (S5) | request (slugs, `include_long_runs`), result counts per status, total duration, cache hits; importer: entries added/changed/removed |
| `WARNING` | the kernel ran, but in a degraded way an operator should know about | tool unavailable, time budget exceeded, a process-pool worker died |
| `ERROR` | a programming error | every `internal` error with its traceback, logged exactly once where it is translated (`internal_error_from_exception`, `exc_info=exc`); the exception text goes only here, never into the result (ADR 0019) |

- **Every default taken is logged** (maintainer, 2026-10-14), once per `compute()` call and slug, as its
  own `INFO` line in addition to the summary line, so also on a full cache hit: `"default used: %s = %s %s (%s)"` with slug, value,
  unit and source, `extra` = `call_id`, `quantity` (the slug), `role`. Always `INFO` (maintainer,
  2026-10-17), whatever the role (ch. 8.11). The same applies to an `optional:` parameter that
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
| Q3 | Every value is traceable | The result carries slug, application, tool and canon model hash; the shipping commit follows from the hash (`git log -S`) |
| Q4 | The solver does not converge | `not_converged`; successors `upstream_failed`; other quantities still compute |
| Q5 | Layout without a separate flap and aileron | `butterfly-max-mix` is `not_applicable`, code `condition_not_met`: no error, no substitute value. `stall-speed-landing` computes and equals `stall-speed` (no configuration, not a fallback) |
| Q6 | Every error category | Serialises to JSON with `message` and `hint` |
| Q7 | Second identical call | `CachedKernel`: no formula call, `from_cache` true; stateless `compute()`: formula called; values bit-identical across both |
| Q8 | Input mass ≤ 0 | `invalid_input` with `input_path`; Re < 3·10⁴ only warns |
| Q9 | Boundary to `app/` | Test: no import from `app/`, `cad_designer/`, `scripts/` |
| Q10 | No AeroSandbox installed | `tool_unavailable`, no ImportError |
| Q11 | A canon change with a changed input of an implemented formula | the import diff marks it breaking; that formula's unit test, which builds `x` from the model, fails until the implementation is updated |
| Q12 | Runtime independence | `compute()` works with `_reversa_sdd/` absent; only `canon/canon_model.json` is read |
| Q13 | Import twice | byte-identical `canon_model.json` |
| Q14 | A canon entry with an unknown unit | the import fails at stage 2 with file and field; no model written |
| Q15 | A `minutes` quantity requested without `include_long_runs` | `status: skipped`, `reason.code = long_run_not_included`, dependents `depends_on_skipped`, all other quantities computed |
| Q16 | Event loop stays responsive | while a `seconds` computation runs, a concurrent `asyncio.sleep(0.01)` task is delayed by < 50 ms |
| Q17 | Cancellation | cancelling `compute()` during an AVL run kills the subprocess and leaves no temp directory; `CancelledError` propagates |
| Q18 | In-flight deduplication | on one `CachedKernel`, two concurrent identical requests cause exactly one formula call |
| Q19 | Time budget (with the solver path) | budget exceeded → open quantities `timeout`, finished ones returned |
| Q20 | Stateless interface leaves no state | after `compute()` returns, no cache entry, pool or other object created by it remains; a second call computes again |
| Q21 | — | removed with the cache scopes (S2 = b, 2026-10-17); the number is kept so the others stay stable |
| Q22 | Multi-output formula | requesting two outputs of one application calls the implementation once |
| Q23 | One world fails | the quantity is `error` with `detail.worlds_ok`; no narrowed interval |
| Q24 | Missing input value | only the quantities needing it get `missing_input`; the rest compute |
| Q25 | Pre-/postcondition violated | `on_violation: warning` → value plus `defect` warning; `error` → `precondition_violated` (implementation not called) / `postcondition_violated` (value discarded); the importer rejects an output in `preconditions:` and an input in `postconditions:` |
| Q26 | Status precedence | mixed failed/skipped/not-applicable predecessors give the status of ch. 8.13 |
| Q27 | Cache key | inputs differing in the last bit of a float give different keys; a changed source file changes every key |
| Q28 | Mass differs from the geometry's `total_mass_kg` | computed with the passed mass; `conflicting_mass` warning on every quantity that depends on the mass, none on the others |
| Q29 | Target not set | `roll-rate-cruise` (`given: [cruise-speed-target]`) is `not_applicable`, code `not_given`; a quantity reading `cruise-speed-target` without `given` gets `missing_input` |
| Q30 | Embedded relation and optional parameter | with `flight-speed` = 0, `thrust-at-airspeed` equals the thrust inside `static-thrust-to-weight` bit for bit (one relation function); without `motor-circuit-resistance` both run route A with a `practice` warning naming the route, no `missing_input` |
| Q31 | Defaults taken | without `gravity` and without `approach-speed-margin-target`: `approach-speed` computes; `provenance.defaults_used` lists both with value and source; `caplog` has one `INFO` line for `gravity` and one `INFO` line for the target, each with `call_id`, also on a second, cached call; the result carries `default_target_used` (`practice`) on `approach-speed` and its dependents, and no warning for `gravity` |
| Q32 | Embedding (engine half built with the first embedder) | `importer --check` rejects an embedding cycle, an embedded formula with worlds, and an embedded input that is neither bound, produced in the closure nor generic; the traceability test fails when an embedder does not call the embedded relation function; `mass-envelope` with `neutral-point` in three worlds runs three times and returns `cg-envelope-over-mass` as a pointwise interval |
| Q33 | Flap deflection: beyond the stop, flapless, missing | `flap-deflection-landing` larger than the flap's `positive_deflection_deg`: `airplane-landing` carries exactly the given deflection, `stall-speed-landing` computes, no error, no clamp and no warning about the stop. Flapless, no deflection given: `airplane-landing` is the unchanged aircraft, `stall-speed-landing` equals `stall-speed`, no warning, one `INFO` line. Flapless with a deflection: same values plus `deflection_without_flap`. Flaps, no deflection: `stall-speed-landing` is `missing_input` (`values.flap-deflection-landing`), `approach-speed` `upstream_failed`; `stall-speed` still computes |
| Q34 | Angles, not stops | `roll-rate-approach` at a given `aileron-deflection` beyond the aileron's stop computes, no stop warning; `aileron-deflection-required-approach` for a target above the AeroBuildup maximum: that world fails with `unsupported_configuration`, code `target_above_method_maximum` (maximum roll rate and its δ_a in `detail`), the AVL world computes, the quantity is `error` with the AVL value in `detail.worlds_ok` — no clipped angle, no narrowed interval. AVL at `|p·b/2V| > 0.10` carries the `defect` warning from the adapter and, since #1243, leaves the interval (`world_outside_validity`, ch. 8.13): with BRYAN and JAGUAR at 20° the roll rate is the AeroBuildup world alone |
| Q35 | Roll without ailerons; crow from the landing configuration | an aircraft without a surface acting as aileron, flaperon or elevon: `roll-rate-approach` and `aileron-deflection-required-approach` are `not_applicable` (`condition_not_met`), no `missing_input` for `aileron-deflection`; a wing whose devices are flaperons only has `has_aileron` but not the butterfly condition — flaperons never count toward it (D10), with one flaperon or several; butterfly needs a device of role `flap` and one of role `aileron` or `elevon`, otherwise the butterfly quantities are `not_applicable`; with separate flaps and ailerons the butterfly curves start from `airplane-landing` (maintainer E2, 2026-10-15): at mix `s` the flap is at `flap-deflection-landing + s · (crow-flap-deflection − flap-deflection-landing)` and the aileron at `s · crow-aileron-deflection` (absolute end angles at `s = 1`, independent of the stops); at `s = 0` the stall speed agrees with `stall-speed-landing` to solver tolerance and `butterfly-approach-speed-curve(0)` equals `approach-speed` exactly (normalised by `V_S0(0)` of the same sweep) |
| Q36 | Embedded postcondition and variables (engine half built with the first embedder) | a stub `stall-speed` whose optimum is not the first C_L peak at one sweep mass: `mass-envelope` is `error`, `postcondition_violated`, `detail.embedded = stall-speed.clean` with that mass; with `m_current` set, the embedded `m` still takes every sweep value (`variables:`), never the current mass; the importer rejects a bare `stall-speed` in `embeds:` and a closure input that is neither variable, input nor produced |
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
| `airplane-components` | procedure | KAT | law | 1 → 11 | 1 | – | – | instant | probe |
| `airplane-configuration` | procedure | GEO | law | 2 → 1 | 2 | – | – | instant | core chain |
| `airplane-geometry` | procedure | GEO | law | 1 → 3 | 1 | – | – | instant | core chain |
| `aspect-ratio` | law | APP | law | 2 → 1 | 1 | – | – | instant | core chain |
| `battery-mass-from-capacity` | law | APP | law | 2 → 1 | 1 | – | – | instant | later |
| `best-angle-of-climb` | optimization | OPT | law | 5 → 2 | 1 | – | – | seconds | later |
| `best-rate-of-climb` | optimization | OPT | law | 5 → 2 | 1 | – | – | seconds | later |
| `butterfly-approach` | optimization | OPT | law | 6 → 4 | 1 | – | – | seconds | later |
| `cg-for-target-margin` | law | APP | law | 3 → 1 | 1 | – | – | instant | core chain |
| `cruise-target-performance` | procedure | OPT | law | 14 → 2 | 1 | – | – | seconds | later |
| `dive-speed` | procedure | OPT | law | 5 → 1 | 1 | – | – | seconds | later |
| `drag-polar` | law | APP | approximation | 3 → 1 | 1 | – | – | instant | later |
| `dynamic-pressure` | law | APP | law | 2 → 1 | 1 | – | – | instant | core chain |
| `endurance-and-range` | procedure | OPT | law | 15 → 2 | 1 | – | – | seconds | later |
| `endurance-and-range-optimum` | optimization | OPT | law | 15 → 2 | 1 | – | – | seconds | later |
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
| `motor-propeller-equilibrium` | procedure | APP | law | 9 → 1 | 1 | – | – | instant | probe |
| `motor-propeller-part-load` | procedure | OPT | law | 13 → 4 | 1 | – | – | seconds | later |
| `neutral-point` | procedure | AVL | law | 5 → 1 | 1 | – | A11 | seconds | core chain |
| `parabolic-polar-fit` | fit | OPT | law | 6 → 2 | 1 | – | – | seconds | probe |
| `propeller-table-lookup` | procedure | APC | law | 2 → 1 | 1 | – | – | instant | probe |
| `sink-rate` | law | APP | law | 3 → 1 | 1 | – | – | instant | core chain |
| `spar-break-load-factor` | procedure | APP | law | 3 → 2 | 1 | – | – | instant | later |
| `speed-from-stall-margin` | rating | APP | approximation | 2 → 3 | 3 | – | – | instant | probe |
| `spiral-parameter` | law | APP | law | 5 → 1 | 1 | – | – | instant | core chain |
| `stall-break` | procedure | OPT | law | 7 → 2 | 1 | – | – | seconds | later |
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
