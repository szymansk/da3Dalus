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
