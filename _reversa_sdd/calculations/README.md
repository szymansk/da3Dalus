# Calculation graph — the design computations, their formulas and their provenance

> **Purpose: making this application testable.** Not helping anyone design an
> aircraft. This register exists so that *fachliche* tests — tests that assert a
> domain truth rather than a code path — can be written at all, and so that a
> defect in a computation chain can be found by inspection instead of by
> accident.

## Why it exists

The audit of 2026-08-17 found six defects in a single computation chain (the spar
chain, gh-1136 … gh-1141). **Not one of them was an arithmetic error.** Every one
was a defect *between* the computations:

| defect | what it is, in graph terms |
|---|---|
| `shear_N` computed by gh-1002, never read by spar sizing | a node with **no outgoing edge** |
| where the spar ends — topology *and* a strength threshold | **two producers** of one fact |
| the telescoping relation, discarded by stock snapping | an edge **invalidated by a later transform** |
| `utilisation` = containment-band fit, not strength | a name that **contradicts its definition** |
| `g_limit` consumed pre-multiplied by `j·k ≈ 3.75` | a name that **contradicts its magnitude** |

None of these is visible when reading a function. All of them are visible when
looking at the graph. That is the whole argument for this directory.

It also explains a recurring frustration: four ADRs are already *rules about this
graph* —

- **ADR 0022** — one authority per user-facing quantity → *no node with two producers*
- **ADR 0020** — no undeclared fallbacks → *every substitution is an annotated edge*
- **ADR 0023** — constants carry their source, validated at 0.5–15 kg → *every leaf
  node has a citation, and the citation has a scale*
- **ADR 0019** — no implementation leaks in the public API → *public node names name
  the quantity, not the mechanism*

Four rules about an object that did not exist. That is why they are violated
without anyone noticing.

## Scope

**In:** calculations that size, analyse or judge the aircraft — structure, aerodynamics,
stability, performance, mass, powertrain.

**Out:** the CAD construction in `cad_designer/airplane/creator/` (the Creators build
geometry, they do not compute design quantities), tessellation, export, CRUD, import,
and copilot plumbing. The spar **solver** is in scope because it sizes; the wing
**Creators** are not because they build.

## Node format

One file per quantity, named `<slug>.md`, in the cluster directory. Every file:

```markdown
---
name: required-section-modulus
symbol: erf_W
kind: quantity            # quantity | constant | parameter
unit: mm³
cluster: structure
user_visible: true
---

# Required section modulus

**Definition.** The section modulus a spar cross-section must reach at a station
so the design bending moment does not exceed the allowable stress.

**Formula (as the code writes it).**

    erf_W = M_design · 1000 / σ_allow

The factor `1000` is exactly the N·m → N·mm conversion — not a fudge.

**Inputs.** [[design-bending-moment]] · [[allowable-bending-stress]]

**Produced by.** `app/services/spar_sizing.py:78-88` — `required_section_modulus()`
🟢 CONFIRMED

**Consumed by.** [[spar-outer-diameter]] · [[stock-snapping]]

**Source.** 🟢 SOURCED — Sadraey, *Aircraft Design: A Systems Engineering Approach*
(Wiley 2013), Eq. (10.x); consulted via `/aircraft-design-scholz`.

**Notes.** — anything that does not fit above: divergence between code and source,
scale warnings, observed anomalies.
```

### Links are the point

Inputs and consumers are **Obsidian wikilinks** (`[[slug]]`). Opening this directory
as an Obsidian vault gives a navigable dependency graph — follow an edge to see what a
number is built from and who reads it. A link to a note that does not exist yet is
fine; it marks a node still to be written, not an error.

## Markers

Two independent axes, per [`../MARKERS.md`](../MARKERS.md).

**Confidence** — how well the *code* claim is established:
🟢 CONFIRMED (read from the code, with `file:line`) · 🟡 INFERRED · 🔴 GAP.

**Source status** — how well the *formula* is attributed:

| marker | meaning |
|---|---|
| 🟢 **SOURCED** | a specific citable reference: author, work, chapter/equation/page |
| 🟡 **PARTIAL** | the general method is standard, but this exact form or value is not attributable |
| 🔴 **NO SOURCE FOUND** | nothing found — **stated as such, never filled with a plausible guess** |

🔴 is a legitimate and useful result. A fabricated citation is the worst possible
entry here, because everything downstream cites it. The same rule that governs the
confidence markers governs these: **inventing an anchor is worse than having none.**

Two further annotations appear only when they apply:

- **Divergence** — the code's formula differs from the source's. What differs, and
  whether it matters.
- **Scale warning** — the source is transport-category while this application targets
  **0.5–15 kg** RC/UAV aircraft (ADR 0023). A constant is not justified by being
  standard in airliner literature.

## How this stays true

A hand-maintained graph rots, and a rotted graph is **worse than none** because it
gets cited. Two mechanisms:

1. **Mechanical check.** Every node names its producer as `file:line` *plus a symbol
   name*. A script asserts the symbol still exists at or near that line. That catches
   the common decay — renamed, moved, deleted — for almost nothing.
2. **Review gate.** A change that adds a user-visible number adds a node. A change
   that alters a formula updates its node in the same commit.

Neither catches every semantic drift. Both catch the drift that actually happens.

## State — first full pass, 2026-08-18

**1112 nodes** extracted from 30 service modules by a 22-agent team, in two stages per
domain: read the code, then ask the domain experts for a citable source.

| | |
|---|---|
| nodes | **1112** — 285 constants, 697 reaching an API response or the UI |
| provenance | 🟢 443 sourced · 🟡 358 partial · 🔴 **310 with no attributable source** |
| citation check | **1007 of 1007 file:line references exist**; 96 % also resolve to the named symbol's scope |
| flagged | 639 anomalies · 834 divergences · 147 scale warnings — **all 🟡, none independently verified** |

Two things about those numbers.

**The provenance check is the strong result.** Not one fabricated path, not one line
outside its file. The extraction can be trusted about *where* things are.

**The flags are not findings yet.** 639 anomalies across 1112 nodes is an over-reporting
rate, not a defect rate; 834 divergences is implausible as "the code contradicts the
literature" and mostly means "the source writes it differently". Every one is marked
🟡 *reported, not verified* in its note, and must be confirmed against the code before it
is cited. Removing that marker turns a lead into a claim.

What **is** confirmed already lives in the tickets it belongs to — the root cause of
gh-1132 was found this way.

## The provenance audit — 2026-08-18

Every node was re-checked by an independent reviewer swarm (25 agents, one per source
file), instructed to **refute rather than confirm**: read the cited line, compare the
formula character by character, check the unit and the literal value.

| verdict | nodes |
|---|---|
| 🟢 CONFIRMED | **1043** |
| 🟠 corrected — wrong line | 26 |
| 🟠 corrected — wrong formula | 6 |
| 🟠 corrected — wrong unit | 4 |
| 🟠 misdescribed | 2 |
| ⚪ not verified | 30 |

**96 % stood; the 38 defects were all small** — a guard line cited instead of the return
line beneath it, an assignment cited instead of its condition, a load factor labelled `g`
instead of dimensionless. All corrections are applied, and every note now carries
`code_audit:` in its frontmatter plus the original value where it was changed.

**What this audit did NOT establish.** It confirmed *where* things are and *what* they
compute. Of the 639 anomaly claims it refuted exactly one — which is not a plausible
confirmation rate, it means the anomalies were largely not tested. They remain 🟡, and
**refactoring must not be derived from them until they have their own adversarial pass.**

## The solver boundary

Roughly a seventh of the graph's nodes are **not computed here at all** — they come out of
AeroBuildup, VLM, LiftingLine, NeuralFoil or AVL. Those have no formula to source and no
arithmetic to test: the solver is trusted.

That trust is exactly why [`_solver-boundaries.md`](_solver-boundaries.md) exists. It records
every call site with its **complete input set**, each input classified by origin —
`app-derived` (the bug-prone class: this application did arithmetic before handing over),
`user-input`, `hardcoded`, `passed-through`, or `solver-default` (**never passed at all**, so
the solver's own default silently applies).

44 call sites, 417 inputs, 142 of them app-derived and 104 never passed.

## Layout

```
calculations/
  README.md          this file — format and rules
  graph.md           the whole graph as a diagram
  structure/         spar sizing and layout
  aero/              polars, spanwise loads, drag build-up
  stability/         static margin, tail volume, control authority
  performance/       matching chart, field length, endurance, envelope
  mass/              mass build-up, CG, assumptions
  powertrain/        motor, battery, propeller
```
