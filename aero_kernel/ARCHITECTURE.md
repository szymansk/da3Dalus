# aero_kernel — Architecture (lean arc42)

> **Status: draft for approval (#1174).** Once the maintainer approves it, this document is the
> **binding template** for every ticket of Epic #1173 (#1174–#1179). Whoever changes something stated
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

```
        tests (aero_kernel/tests)        robustness run (tools/robustness.py)
                     \                     /
   calibration ───── compute(AircraftInput, ComputeRequest) ──→ ComputeResult
   (calibration/)    |   aero_kernel/   |
                     └──────────────────┘
          reads: canon manifest (generated from _reversa_sdd/calculations/canon/)
          calls: AeroSandbox (AeroBuildup, Opti, atmosphere), AVL (subprocess)
   later:  app/services · copilot (#902) · MCP — through the register epic, not now
```

- **Inward boundary.** `aero_kernel/` **never** imports `app/`, `cad_designer/` or `scripts/`. The app calls
  the kernel, never the other way round.
- **No second producer (ADR 0022).** Until the register epic switches the app over, the app shows no values
  from the kernel.
- **Not inert (ADR 0021).** The kernel is still in use from day one: tests, the CI job, the robustness run
  and the calibration all call it (Epic #1173).
- **No triggering, no storage.** When computation runs (K28, K29) and where results are kept (snapshot) is
  the caller's decision. The kernel supplies the dependency subtree (A1) and the cost class for that.

## 4. Solution strategy

1. **The canon is the structural source.** A generator turns the canon files into a versioned **manifest**:
   quantities, formulas, applications, preconditions, units, roles, worlds and cost class. Code registers
   **implementations** per formula only. Dependencies never come from code.
2. **The whole canon is declared,** including what is not implemented yet (`not_implemented`).
3. **Formula ≠ application.** One implementation per formula. Applications bind inputs and carry a
   condition (canon README, "One formula, several applications").
4. **Method worlds instead of interval arithmetic** (A11, ADR 0027). Each world runs through the whole
   subtree, and the interval is formed only at the end.
5. **Stateless outside, cache inside.** Cache keys come from content and versions, never from identities.
6. **Solvers behind thin adapters.** Formulas talk to adapters, never to AeroSandbox or AVL directly. That
   keeps them mockable in the fast tier, and capability errors arise in one place.

## 5. Building blocks

```
aero_kernel/
  api.py            compute() — the only public entry point
  schema.py         AircraftInput, OperatingPoint, ComputeRequest, ComputeResult, QuantityResult,
                    KernelError, Warning, Provenance (Pydantic, extra="forbid")
  manifest/         generate.py  canon .md → manifest.json (shipped with the package, versioned)
                    load.py      load + consistency rules (ch. 8.6)
  graph.py          subtree, order, world expansion, upstream_failed
  registry.py       @formula(slug) — implementations ↔ manifest
  formulas/         one file per canon formula (file name = slug, with underscores)
  solvers/          aerobuildup.py · avl.py · opti.py · atmosphere.py · data.py (KAT, APC)
  cache.py          in-memory LRU, optionally on disk
  validate.py       physical admissibility; regime warnings (ADR 0028)
  errors.py         error catalogue (ch. 8.1)
  calibration/      FlightObservation, comparison (#1179)
  tools/            robustness.py (#1178)
  tests/            unit, property, golden, traceability and error tests
```

| Block | Responsible for | Must not |
|---|---|---|
| `api` | accept the request, validate, walk the graph, build the result | compute |
| `manifest` | read and check the canon structure | know formulas |
| `graph` | dependencies, worlds, error propagation | call tools |
| `formulas/*` | exactly one canon formula | compute a second formula; judge thresholds (A10) |
| `solvers/*` | call the tool, report its version, translate tool errors | know canon names |
| `cache` | map keys to results | change results |

## 6. Runtime view — one call

```
compute(aircraft, request)
 1 validate(aircraft)                      → invalid_input with input_path; the only abort
 2 manifest.subtree(request.quantities)    → formulas + applications, topologically sorted
 3 per application: check its condition    → not met → status "not_applicable"
 4 per world (A11) and per operating point:
     cost class "minutes" without approval → needs_confirmation
     build key → cache hit?                → reuse
     else call the implementation (time budget)
       success → value + warnings (incl. regime ADR 0028, preconditions)
       failure → KernelError; successors → upstream_failed
 5 merge worlds → [min, max] with the list of worlds
 6 ComputeResult with provenance
```

## 7. Deployment

A library inside the same repository, with no process of its own. AVL runs as a subprocess in a temporary
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
| `needs_confirmation` | yes, after approval | yes | long run (K28) | "The user must start this computation." |
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
- `status`: `ok`, `not_applicable` or `error`
- `value` **or** `interval {min, max, worlds{name: value}}`
- `tool` and `application`
- `validated`: always `false` until calibration (#1179)
- `warnings[]` and `error`

No internal paths or mechanisms in any field (ADR 0019).

### 8.4 Provenance and cache key

`Provenance`:
- kernel version
- manifest hash (the canon state)
- tool versions (aerosandbox, NeuralFoil model, AVL)
- accuracy tier (A3) and solver settings

**Cache key** = hash of:
- the formula slug, application and world
- the canonicalised **relevant** inputs
- the manifest hash of the entry
- the implementation version and the tool versions

Canonicalisation means sorted keys and numbers at a fixed number of significant digits. When a formula
changes, only its subtree expires (A1).

### 8.5 Applications and preconditions

An **application** is a formula plus the bindings of its inputs, a condition and the name of the output
quantity.

A **precondition** is an executable check per application. It returns one of three states:
- 🟢 held
- 🔴 violated: a `defect` warning or an error, as the canon entry says
- ⚪ unchecked: a `practice` warning

### 8.6 Consistency rules when loading the manifest

- One producer per quantity; a second path only as a probe (A7).
- Unique symbols and slugs (A8).
- Targets only as `role: target` (A9).
- Units of implementation signatures equal the manifest (A4).
- Every implementation has a slug in the manifest.
- Separate namespaces: the calculation canon now, the sizing canon (K31) later.

Violations are **canon findings**, not runtime errors: the generator reports them and the canon is
corrected.

### 8.7 Cost class

Each formula has a cost class: `instant`, `seconds` or `minutes`. A `minutes` formula only runs with
`request.allow_long_runs` (K28). Which layer sets the class is still open (O14, question 3). The kernel
carries the attribute from the manifest.

### 8.8 Tools and data sources

- Tools: APP (pure), ATM, GEO, AB, AVL, OPT.
- Data: KAT (component catalogue) and APC (propeller tables).
- Data comes **from the caller**, either inline in the input or as a provider with a content hash. The
  kernel loads nothing on its own.

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
| Q2 | All 57 canon entries mapped onto the model | Appendix A complete; the manifest loads without a model change |
| Q3 | Every value is traceable | The result carries slug, application, tool, manifest hash |
| Q4 | The solver does not converge | `not_converged`; successors `upstream_failed`; other quantities still compute |
| Q5 | Layout without flaps | `stall-speed-landing` is `not_applicable`: no error, no substitute value |
| Q6 | Every error category | Serialises to JSON with `message` and `hint` |
| Q7 | Second identical call | No formula call; result bit-identical with and without cache |
| Q8 | Input mass ≤ 0 | `invalid_input` with `input_path`; Re < 3·10⁴ only warns |
| Q9 | Boundary to `app/` | Test: no import from `app/`, `cad_designer/`, `scripts/` |
| Q10 | No AeroSandbox installed | `tool_unavailable`, no ImportError |

## 11. Risks and technical debt

| Risk | Consequence | Handling |
|---|---|---|
| **The canon is only half machine-readable.** Inputs sit in the prose line "Produces … from". Only `stall-speed` has an application table, and only 3 of 57 entries have structured preconditions. | The manifest cannot derive applications and preconditions completely. | **Decision needed** (see below). |
| 55 of 57 canon entries are `draft` | Tests run against unapproved entries | Intended (Epic #1173); golden values are called "regression" |
| CI has no aero dependencies | Solver formulas are untested in the fast tier | Mock the adapters; job `aero-kernel-aero` (#1177) |
| Solver convergence (stall plateau, bounds) | `not_converged` occurs often | Robustness run (#1178), K32 procedure |
| The `stall-speed` application table uses old register names (`v_stall_clean_mps`) instead of canon slugs | Names do not match the manifest | Switch to canon slugs when extending the format |

**Open decision for the maintainer: the canon format.** So that the manifest does not have to guess
applications and preconditions from prose, every formula entry needs machine-readable fields in its front
matter, for example:
- `inputs:`
- `applications:` (name, bindings, condition)
- `preconditions:` (check, status, test)

Proposal: extend the format once and update all 57 entries mechanically, keeping the prose, **before** the
generator is built.

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
| **Manifest** | machine-readable, versioned image of the canon that the kernel loads | — |
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

Generated from the canon files. The manifest generator (#1174) replaces this table with an automatically
generated one.

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
