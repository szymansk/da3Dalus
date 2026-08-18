---
canon: weight-from-mass
kind: formula
shape: law
status: draft
output: weight
source_status: SOURCED
dimensional_check: BALANCES
tags:
  - canon/formula
  - source/sourced
  - dim/balances
  - shape/law
---

# Weight from mass

**Canonical form**

```
W = m * g
```

**Produces** [[weight]]  ·  **from** [[aircraft-mass]] · [[gravity]]

**Dimensional check.** 🟢 balances

**Source.** 🟢 SOURCED

> Definitional (Newton). The value of g is the load-bearing part: Scholz, 05_PreliminarySizing, unit bookkeeping of the take-off constraint, states explicitly "SI: ... g = 9.81 m/s^2" (British: 32.17 ft/s^2). The 9.80665 m/s^2 value is standard gravity as fixed by the 3rd CGPM (1901) and adopted in the U.S. Standard Atmosphere 1976.

**The source writes it as**

```
Scholz and Sadraey almost always carry the mass form m*g inline rather than a separate symbol W (e.g. T_TO/(m_MTO*g), m_ML/S_W), so the 'weight' node is an app-level construct, not a source-level one.
```

**Validity at 0.5–15 kg.** Exact at any scale. The two literals differ by 0.15%, which is far below every other uncertainty in this chain (C_L,max at model Reynolds number is uncertain by 30-45%, see stall-speed). So the 9.81 / 9.80665 split is an ADR 0022 single-authority defect, not an accuracy defect - do not justify it as a precision improvement. Scholz's own choice is 9.81.

## Implementations (4)

| node | claimed | verified | deviation |
|---|---|---|---|
| [[fe_weight]] | EXACT | 🟢 |  |
| [[weight-force-n]] | EXACT | 🟢 |  |
| [[weight-n]] | EXACT | 🟢 |  |
| [[weight_n_fl]] | EXACT | 🟢 |  |

## Approval

- [ ] **Source** — citation real, or absence stated and adopted on the maintainer's authority
- [ ] **Scale** — holds at 0.5–15 kg, or the limitation is written down (ADR 0023)
- [ ] **Dimensions** — the check balances
- [ ] **Implementations** — all agree, or each deviation is declared and justified
- [ ] **Inputs approved** — no formula is approvable before its inputs are

> While `status: draft` this entry **cites nothing and decides nothing**.

