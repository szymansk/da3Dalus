---
canon: drag-polar
entry: formula
kind: law
tool: APP
shape: approximation
status: draft
output: drag-coefficient-parabolic
source_status: SOURCED
dimensional_check: BALANCES
tags:
  - canon/formula
  - source/sourced
  - dim/balances
  - shape/approximation
  - kind/law
  - status/draft
---

# The drag polar

**Canonical form**

```
C_D,par = C_D0 + k * C_L^2
```

**Produces** [[drag-coefficient-parabolic]]  ·  **from** [[zero-lift-drag-coefficient]] · [[induced-drag-factor]] · [[lift-coefficient]]

**Kind: a law.** A closed-form relation. Approval asks for its **source** and its **validity at 0.5–15 kg**.

**Dimensional check.** 🟢 balances — all three terms are dimensionless.

**Source.** 🟢 SOURCED

> Anderson, Fundamentals of Aerodynamics 6e, §6.7.2, writes the polar as C_D = C_D,0 + r*C_L^2 with C_D,0 the zero-lift (parasite) drag coefficient. Scholz (Flugzeugentwurf) and Sadraey (§4.3) use the same parabolic form with k = 1/(pi*A*e).

**Why this entry exists.** Three formulas in this canon consume a drag coefficient —
[[lift-to-drag-ratio]], [[sink-rate]] and [[stall-onset-detection]] — and until this entry
none produced one. The relation was present exactly once, **inlined** inside
[[power-required-electrical]], where the other three cannot reach it. A producer hidden
inside a consumer is not a missing law; it is an unfactored one.

**Validity at 0.5–15 kg.** The parabolic form is a **model**, not an identity, and at model
Reynolds numbers it is weaker than the textbooks assume. Both `C_D0` and `k` vary with
Reynolds number (see [[reynolds-scheduled-polar]]), so the polar is a *family* of curves
indexed by speed, not one curve. Treating `C_D0` and `k` as constants across the speed
range is the same assumption that made the closed-form minimum-drag speed a Probe rather
than an authority.

## ⚠️ Route — two ways to a drag coefficient

The solver sweep (AeroBuildup) returns `C_D` **directly** at each evaluated point; this
entry computes it from the polar model. They are not two truths: at low Reynolds number
the swept value is the authority and the parabolic form is the model. Their difference is
a **test** of how well the parabolic model fits at this scale (A7), and it is the same
check that gave 2.9 % median and 33 % worst case on the stall.

The solver sweep has no canon entry of its own — it is a `procedure`, and writing it up is
outstanding.

## Approval

- [ ] **Source** — citation real, or absence stated and adopted on the maintainer's authority
- [ ] **Scale** — holds at 0.5–15 kg, or the limitation is written down (ADR 0023)
- [ ] **Dimensions** — the check balances
- [ ] **Implementations** — all agree, or each deviation is declared and justified
- [ ] **Preconditions** — every binding condition holds, or the violation is ticketed
- [ ] **Inputs approved** — no formula is approvable before its inputs are

**Renamed 2026-10-02 (A2).** The parabola's value is `C_D,par`, not `C_D`. `C_D` is the
coefficient the solver computes; the two shared one name, which is what made the graph
show the false cycle `C_D → C_D0 → C_D`. The parabola is an **approximation** — measured
non-parabolic at Re ≈ 1e5 (`V_mp/V_md` = 0.70 against 0.76) — kept where ADR 0004 and the
design direction use it.
