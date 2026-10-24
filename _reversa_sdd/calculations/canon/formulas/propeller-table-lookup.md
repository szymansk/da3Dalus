---
canon: propeller-table-lookup
entry: formula
kind: procedure
tool: APC
shape: law
status: draft
output: thrust-coefficient
source_status: SOURCED
dimensional_check: PROCEDURAL
tags:
  - canon/formula
  - source/sourced
  - dim/procedural
  - shape/law
  - kind/procedure
  - status/draft
inputs: {components: components, j: advance-ratio}
outputs: {c_t: thrust-coefficient}
---

# Thrust coefficient from the measured propeller table

**Canonical form**

```
C_T := interp( table of the chosen propeller, J )
```

**Produces** [[thrust-coefficient]]  ·  **from** [[components]] · [[advance-ratio]]

**Kind: a procedure — a table lookup.** The thrust coefficient of the propeller fitted to the
airplane, interpolated at the advance ratio. 454 APC propellers with 300 187 measured
points are in the database; extrapolation outside the measured `J` range is flagged.

**Source.** 🟢 Definitions `J = V/(n·D)`, `C_T = T/(ρ·n²·D⁴)`, `C_P = P/(ρ·n³·D⁵)`: Brandt & Selig 2011 §II.F. The data are APC PER3 performance files (v2022-0915); their header reads "Simulation Date" and "AIRFOIL AERO DATA GENERATED USING: POLAR DIAGRAMS" (`app/tests/fixtures/apc_props/PER3_7x4.dat:3-6`), so they are APC's own computation, not wind-tunnel measurement. 🔴 NO SOURCE FOUND for the accuracy of APC's computation at low Reynolds number.

**Validity in the RC/UAV regime (ADR 0028).** The tables are for the right class, APC model propellers, but the coefficients depend on the propeller's own Reynolds number and tip Mach, not only on `J`. Small propellers run at Re₀.₇₅ ≈ 15–100 k (ADR 0028; Brandt & Selig 2011 §IV), where `C_T` rises and efficiency improves with rpm (Deters, Ananda & Selig 2014 §V.A–B; Brandt & Selig 2011 §IV). Each rpm block of the table holds one Reynolds number (Brandt & Selig 2011 §II.F), and the implementation reads the nearest block, so the error between blocks is a Reynolds-number error. RC propeller tips typically run near Ma ≈ 0.5 (Roxxy Motoren-Fibel Ch. 1 pp. 9–10), above the M 0.3 at which Anderson treats a flow as compressible (§8.5): the propeller is the one part of the chain outside M ≤ 0.3. Static (`J = 0`) coefficients differ from those at small advance ratio (Brandt & Selig 2011 §II.B, §III). Outside the tabulated `J` range the lookup extrapolates, which is flagged.

## Implementations (0)

None in aero_kernel yet; no register node is mapped to this entry.

## Approval

- [ ] **Source** — citation real, or absence stated and adopted on the maintainer's authority
- [ ] **Regime** — holds in the RC/UAV regime (Reynolds, Mach, equipment), or the limitation is written down (ADR 0028)
- [ ] **Relation and method** — which equation it solves, and by which named method
- [ ] **Assumptions** — the conditions the method requires (bracketing, continuity, range)
- [ ] **Convergence** — the criterion, and what is returned and declared on failure
- [ ] **Dimensions** — the check balances
- [ ] **Implementations** — all agree, or each deviation is declared and justified
- [ ] **Preconditions** — every binding condition holds, or the violation is ticketed
- [ ] **Inputs approved** — no formula is approvable before its inputs are

> While `status: draft` this entry **cites nothing and decides nothing**.
