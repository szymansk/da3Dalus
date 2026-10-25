---
canon: cg-for-target-margin
entry: formula
kind: law
tool: APP
shape: law
status: approved
output: centre-of-gravity-design
source_status: SOURCED
dimensional_check: BALANCES
tags:
  - canon/formula
  - direction/design
  - source/sourced
  - dim/balances
  - shape/law
  - kind/law
  - status/approved
tex: x_{cg,design} = x_{NP} - SM_{target}\,c_{MAC}
inputs: {x_np: neutral-point, sm_target: static-margin-target, c_mac: mean-aerodynamic-chord}
outputs: {x_cg_sm: centre-of-gravity-design}
---

# Centre of gravity that gives the target static margin

**Canonical form**

```
x_cg,design = x_NP - SM_target * c_MAC
```

**Produces** [[centre-of-gravity-design]]  ·  **from** [[neutral-point]] · [[static-margin-target]] · [[mean-aerodynamic-chord]]

**Kind: a law** — the design direction (§2.3, ADR 0011): the CG is a **target derived from
the wanted stability**, not a bottom-up result of the components. The designer then places
battery and parts so that the real CG lands here.

**Source.** 🟢 Definition of the static margin read the other way; ADR 0011.

**Validity in the RC/UAV regime (ADR 0028).** Regime-independent: the static-margin definition (Sadraey Eq. 11.18, §11.6.2) solved for the CG; the target margin is a caller parameter. The result inherits the limitations of [[neutral-point]], above all the aft bias from the missing fuselage: a CG placed from the aft end of the interval gives less real margin than the target.

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
