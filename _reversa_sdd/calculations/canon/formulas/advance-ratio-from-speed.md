---
canon: advance-ratio-from-speed
entry: formula
kind: law
tool: APP
shape: law
status: draft
output: advance-ratio
source_status: SOURCED
dimensional_check: BALANCES
tags:
  - canon/formula
  - source/sourced
  - dim/balances
  - shape/law
  - kind/law
  - status/draft
inputs: {v: flight-speed, n_prop: propeller-speed, d_prop: propeller-diameter}
outputs: {j: advance-ratio}
---

# Advance ratio

**Canonical form**

```
J = V / (n_prop * D_prop)
```

**Produces** [[advance-ratio]]  ·  **from** [[flight-speed]] · [[propeller-speed]] · [[propeller-diameter]]

**Kind: a law.** A closed-form relation. Approval asks for its **source** and its **validity in the RC/UAV regime (ADR 0028)**.

**Dimensional check.** 🟢 balances — (m/s) / ((1/s)·m) is dimensionless.

**Source.** 🟢 SOURCED

> Standard propeller notation: the forward distance per revolution relative to the diameter. Used verbatim by the APC data files the tables come from.

**Validity in the RC/UAV regime (ADR 0028).** Exact.

## Implementations (0)

None in aero_kernel yet; no register node is mapped to this entry.

## Approval

- [ ] **Source** — citation real, or absence stated and adopted on the maintainer's authority
- [ ] **Regime** — holds in the RC/UAV regime (Reynolds, Mach, equipment), or the limitation is written down (ADR 0028)
- [ ] **Dimensions** — the check balances
- [ ] **Implementations** — all agree, or each deviation is declared and justified
- [ ] **Preconditions** — every binding condition holds, or the violation is ticketed
- [ ] **Inputs approved** — no formula is approvable before its inputs are

> While `status: draft` this entry **cites nothing and decides nothing**.
