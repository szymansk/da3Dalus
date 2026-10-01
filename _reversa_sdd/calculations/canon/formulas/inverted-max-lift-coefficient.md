---
canon: inverted-max-lift-coefficient
entry: formula
kind: procedure
shape: law
status: draft
output: inverted-max-lift-coefficient
source_status: PARTIAL
dimensional_check: PROCEDURAL
tags:
  - canon/formula
  - source/partial
  - dim/procedural
  - shape/law
  - kind/procedure
  - status/draft
---

# Negative maximum lift coefficient as the trough of the computed polar

**Canonical form**

```
C_L,min = min over alpha of C_L(alpha)
```

**Produces** [[inverted-max-lift-coefficient]]  ·  **from** [[lift-coefficient]] · [[angle-of-attack]]

**Kind: a procedure.** There is no closed form, so an algorithm stands in its place. Source and scale are asked as of any entry — a procedure is not source-free: it either implements a published standard or solves a stated equation. **On top of that** it must say **under which assumptions it holds** and **when it converges**, including what it returns when it does not.

**Dimensional check.** ⚪ procedural — an extremum of a sampled curve, not an expression.

## What this replaces, and why

**Decided 2026-09-30.** This entry previously read `C_L,min = -0.8 · C_L,max`. It is gone,
for two reasons, either sufficient:

**No source.** Searched Scholz, Sadraey, Anderson, Lennon, the RC-Network Wiki and
rcplanedesigner. 14 CFR 23.337 fixes a negative **load factor**, not a negative lift
coefficient. Nothing gives −0.8, or any other fixed ratio.

**No camber dependence, which is the whole of it.** The ratio between the upright and the
inverted maximum is essentially a function of camber. A symmetric aerobatic section flies
inverted at very nearly the same magnitude — a ratio near 1.0 — while a strongly cambered
trainer or glider section is far below 0.8. Both live inside 0.5–15 kg, so one constant
cannot serve both. It is the same defect as the deleted rule-of-thumb speeds: a number that
cannot tell a glider from an aerobatic model.

Reading the trough off the polar carries the camber automatically, because the polar was
computed for **this** section.

### The procedure

> A procedure is not invented here. It has **two origins**, and both are citable:
> the **relation** it solves, and the **method** it solves it with. Its assumptions and
> its convergence behaviour are then properties of that method — published, not chosen.

**Relation solved.** The definition of the lift-curve minimum, `C_L,min = min_alpha C_L(alpha)`
— the mirror of the stall optimisation's `C_L,max,stall` ([[stall-speed]]). No closed form exists, because `C_L(alpha)` comes from
a black-box solver.

**Method.** The same sweep that yields the positive peak, extended far enough into negative
angle of attack, with the minimum taken instead of the maximum. Reusing one sweep for both
extrema is deliberate: two sweeps would be two authorities for one polar.

**Assumptions.**

1. **The negative stall lies strictly inside the sampled range.** This is the assumption
   most at risk. The default sweep starts at −15°, and a cambered section can stall
   inverted beyond that — the trough would then sit on the boundary and the reported value
   would be the edge sample, not the minimum. Bracketing must be **checked**, not hoped for.
2. The spacing resolves the trough, as for the positive peak.
3. `C_L(alpha)` is single-troughed in the window.
4. **Same Reynolds caveat as the positive branch.** `C_L,min` depends on Reynolds number;
   taking it over a mixed velocity grid reports the value at the wrong speed. It must be
   evaluated at the condition it is used for, and carry that condition in its name (A2).

**On failure.** If the trough sits on the boundary, the value is **not** reported as a
minimum: the negative branch of the flight envelope is a placeholder and says so with a
`DesignWarning` (ADR 0020). A boundary sample silently passed off as `C_L,min` is exactly
the failure mode the positive counterpart already has.

## Preconditions on the bindings

**`alpha` range** — must extend past the inverted stall. A range chosen for the upright
polar is not automatically sufficient for the inverted one, and for a cambered section it
usually is not.

**Naming** — as the positive branch, the value belongs to an evaluation condition. A bare
`C_L,min` says nothing about the speed it holds at.

## Approval

- [ ] **Source** — citation real, or absence stated and adopted on the maintainer's authority
- [ ] **Scale** — holds at 0.5–15 kg, or the limitation is written down (ADR 0023)
- [ ] **Dimensions** — the check balances
- [ ] **Implementations** — all agree, or each deviation is declared and justified
- [ ] **Preconditions** — every binding condition holds, or the violation is ticketed
- [ ] **Inputs approved** — no formula is approvable before its inputs are

> While `status: draft` this entry **cites nothing and decides nothing**.
