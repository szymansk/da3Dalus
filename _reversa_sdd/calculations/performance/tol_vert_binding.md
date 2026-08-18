---
name: tol_vert_binding
symbol: TOL_VERT
kind: constant
unit: fraction
cluster: perf-matching
user_visible: true
source_status: NO_SOURCE_FOUND
code_audit: CONFIRMED
node_class: unclassified-constant
tags:
  - cluster/perf-matching
  - class/unclassified-constant
  - source/no-source-found
  - surface/user-visible
  - audit/confirmed
  - flag/anomaly
  - flag/divergence
---

# Vertical-constraint binding tolerance

**Definition.** Relative W/S band within which a vertical constraint counts as binding.

⚪ **Unclassified constant.** Not yet decided whether this is a rule of thumb, a calibration or a physical value. Classifying it is open work — it is deliberately not guessed.

**Value.** `0.05`

**Formula — as the code writes it.**

```
TOL_VERT = 0.05
```

**Inputs.** — *(leaf: a constant or an external input)*

**Produced by.** `app/services/matching_chart_service.py:657` — `_check_feasibility`

🟢 **Verified against the code** — an independent reviewer read this line and confirmed the formula, unit and value (2026-08-18 audit).

**Consumed by.**

- in this graph: `Feasibility verdict`  
  *(these are backlinks — open the Backlinks pane to navigate them)*
- outside it: `_check_feasibility:680,682`

**Source.** 🔴 NO SOURCE FOUND

> No source (see tol_line_binding).
>
> — via `aircraft-design-scholz`
> No citable source was found. **This is recorded, not filled in.** The value is
> in the code without an attributable origin.

**⚠️ Divergence from the source.** A design 5% over the stall or landing W/S ceiling is still reported feasible, and the 5% vertical vs 3% line asymmetry has no justification in any source. For the stall constraint in particular this is a safety-relevant relaxation: Sadraey Eq. 4.31 is a hard limit with the acceptable region strictly to the left.

🟡 *Reported by the extraction pass, not independently verified.*

**⚠️ Anomaly.** A design 5% over the stall or landing W/S ceiling is still reported feasible — asymmetric with the 3% line tolerance, no source for either.

🟡 *Reported by the extraction pass, not independently verified. Do not cite as a
defect until confirmed against the code.*

**Cited in the code itself.** `# 5% W/S tolerance for "binding" vertical constraints`

---
*Cluster [[_index-perf-matching|perf-matching]] · generated from the 2026-08-18 extraction.*
