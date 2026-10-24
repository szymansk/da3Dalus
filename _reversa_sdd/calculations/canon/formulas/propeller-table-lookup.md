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
