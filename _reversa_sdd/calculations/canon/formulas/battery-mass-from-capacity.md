---
canon: battery-mass-from-capacity
kind: formula
status: draft
output: predicted-battery-mass
source_status: PARTIAL
dimensional_check: BALANCES
tags:
  - canon/formula
  - source/partial
  - dim/balances
---

# Battery mass implied by capacity and specific energy

**Canonical form**

```
m_bat,pred = E_bat / E_star
```

**Produces** [[predicted-battery-mass]]  ·  **from** [[battery-capacity]] · [[battery-specific-energy]]

**Dimensional check.** 🟢 balances

**Source.** 🟡 PARTIAL

> Definitional (energy divided by specific energy). The VALUE of E* is the citable part: RC-Network Wiki, "Energiedichte" (Antriebstechnik) - LiPo 0.55 MJ/kg, which converts to 152.8 Wh/kg.

**The source writes it as**

```
RC-Network tabulates MJ/kg; the app uses Wh/kg. 1 MJ = 0.2778 kWh, so 0.55 MJ/kg = 152.8 Wh/kg.
```

**Validity at 0.5–15 kg.** The critical qualification: 0.55 MJ/kg is a CELL-level figure. Pack-level specific energy after wiring, connectors, balance leads, shrink and case is materially lower - typically 100-140 Wh/kg for RC packs in this class. The skeleton correctly names the quantity 'pack specific energy', so if the cell number is used as the default the predicted mass is systematically light and the deviation warning downstream fires spuriously on correctly-specified packs. Record E* with its source and its cell-vs-pack basis per ADR 0023.

## Implementations (1)

| node | claimed | verified | deviation |
|---|---|---|---|
| [[end_battery_mass_predicted]] | EXACT | 🟢 |  |

## Approval

- [ ] **Source** — citation real, or absence stated and adopted on the maintainer's authority
- [ ] **Scale** — holds at 0.5–15 kg, or the limitation is written down (ADR 0023)
- [ ] **Dimensions** — the check balances
- [ ] **Implementations** — all agree, or each deviation is declared and justified
- [ ] **Inputs approved** — no formula is approvable before its inputs are

> While `status: draft` this entry **cites nothing and decides nothing**.

