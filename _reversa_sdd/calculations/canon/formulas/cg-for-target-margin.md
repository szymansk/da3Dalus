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
  - source/sourced
  - dim/balances
  - shape/law
  - kind/law
  - status/draft
tex: x_{CG,SM} = x_{NP} - SM_{target}\,c_{MAC}
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
