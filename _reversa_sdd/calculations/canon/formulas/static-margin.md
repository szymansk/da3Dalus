---
canon: static-margin
entry: formula
kind: law
tool: APP
shape: law
status: draft
output: static-margin
source_status: SOURCED
dimensional_check: BALANCES
tags:
  - canon/formula
  - source/sourced
  - dim/balances
  - shape/law
  - kind/law
  - status/draft
tex: SM = \frac{x_{NP} - x_{CG}}{c_{MAC}}
inputs: {x_np: neutral-point, x_cg: centre-of-gravity, c_mac: mean-aerodynamic-chord}
outputs: {sm: static-margin}
---

# Static margin

**Canonical form**

```
SM = 1 / c_MAC * (x_NP - x_CG)
```

**Produces** [[static-margin]]  ·  **from** [[neutral-point]] · [[centre-of-gravity]] · [[mean-aerodynamic-chord]]

**Kind: a law** — the analysis direction: given where the CG is, how stable is the aircraft.
Positive is stable. Decided in §2.3.

**Source.** 🟢 Standard definition (Anderson; Scholz, *Flugmechanik*; RC practice uses the same
measure in % MAC).

**Validity in the RC/UAV regime (ADR 0028).** Regime-independent: a definition, the non-dimensional distance between two points (Sadraey Eq. 11.18, §11.6.2), with no aerodynamic model in it. Its value inherits every limitation of [[neutral-point]]: the interval, the missing fuselage that biases x_NP aft (`fuselage_not_modelled`), and the low-Re limits of the three worlds.

## Implementations (1)

| node | claimed | verified | deviation |
|---|---|---|---|
| `aero_kernel/formulas/static_margin.py` | EXACT | 🟢 |  |

## Approval

- [ ] **Source** — citation real, or absence stated and adopted on the maintainer's authority
- [ ] **Regime** — holds in the RC/UAV regime (Reynolds, Mach, equipment), or the limitation is written down (ADR 0028)
- [ ] **Dimensions** — the check balances
- [ ] **Implementations** — all agree, or each deviation is declared and justified
- [ ] **Preconditions** — every binding condition holds, or the violation is ticketed
- [ ] **Inputs approved** — no formula is approvable before its inputs are

> While `status: draft` this entry **cites nothing and decides nothing**.
