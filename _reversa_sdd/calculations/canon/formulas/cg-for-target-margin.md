---
canon: cg-for-target-margin
entry: formula
kind: law
tool: APP
shape: law
status: draft
output: cg-for-target-margin
source_status: SOURCED
dimensional_check: BALANCES
tags:
  - canon/formula
  - direction/design
  - source/sourced
  - dim/balances
  - shape/law
  - kind/law
  - status/draft
tex: x_{CG,SM} = x_{NP} - SM_{target}\,c_{MAC}
inputs: {x_np: neutral-point, sm_target: static-margin-target, c_mac: mean-aerodynamic-chord}
outputs: {x_cg_sm: cg-for-target-margin}
---

# Centre of gravity that gives the target static margin

**Canonical form**

```
x_CG,SM = x_NP - SM_target * c_MAC
```

**Produces** [[cg-for-target-margin]]  ·  **from** [[neutral-point]] · [[static-margin-target]] · [[mean-aerodynamic-chord]]

**Kind: a law** — the design direction (§2.3, ADR 0011): the CG is a **target derived from
the wanted stability**, not a bottom-up result of the components. The designer then places
battery and parts so that the real CG lands here.

**Source.** 🟢 Definition of the static margin read the other way; ADR 0011.

## Implementations (1)

| node | claimed | verified | deviation |
|---|---|---|---|
| `aero_kernel/formulas/cg_for_target_margin.py` | EXACT | 🟢 |  |

## Approval

- [ ] **Source** — citation real, or absence stated and adopted on the maintainer's authority
- [ ] **Regime** — holds in the RC/UAV regime (Reynolds, Mach, equipment), or the limitation is written down (ADR 0028)
- [ ] **Dimensions** — the check balances
- [ ] **Implementations** — all agree, or each deviation is declared and justified
- [ ] **Preconditions** — every binding condition holds, or the violation is ticketed
- [ ] **Inputs approved** — no formula is approvable before its inputs are

> While `status: draft` this entry **cites nothing and decides nothing**.
