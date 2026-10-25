---
canon: battery-mass-from-capacity
entry: formula
kind: law
tool: APP
shape: law
status: draft
output: predicted-battery-mass
source_status: PARTIAL
dimensional_check: BALANCES
tags:
  - canon/formula
  - source/partial
  - dim/balances
  - shape/law
  - kind/law
  - status/draft
inputs: {e_bat: battery-capacity, e_star: battery-specific-energy}
outputs: {m_bat_pred: predicted-battery-mass}
---

# Battery mass implied by capacity and specific energy

**Canonical form**

```
m_bat,pred = E_bat / E_star
```

**Produces** [[predicted-battery-mass]]  ·  **from** [[battery-capacity]] · [[battery-specific-energy]]

**Kind: a law.** A closed-form relation. Approval asks for its **source** and its **validity in the RC/UAV regime (ADR 0028)**.

**Dimensional check.** 🟢 balances

**`E*` is a design assumption, not a component read** (maintainer, 2026-10-25, #1235). [[battery-specific-energy]] is an input of this entry only; it is no longer produced by [[airplane-components]], because a value derived from the real pack would make the plausibility check against the actual battery mass tautological. The input carries its **basis**: the formula divides a *pack* energy ([[battery-capacity]], pack nominal) and compares with a *pack* mass, so the consistent basis is the pack; a cell-level `E*` predicts the cell mass only, and the check then differs from a correct pack systematically.

**Default: 140 Wh/kg at pack level, a `convention`** (maintainer, 2026-10-25; `defaults.yaml`). Candidates were the catalogue packs 128–159 Wh/kg — placeholder 'Generic LiPo' entries, not datasheets —, the app default 180 Wh/kg and the canon's cited source 152.8 Wh/kg, which is cell level (below). A published pack value would replace the convention.

**Source.** 🟡 PARTIAL

> Definitional (energy divided by specific energy). The VALUE of E* is the citable part: RC-Network Wiki, "Energiedichte" (Antriebstechnik) - LiPo 0.55 MJ/kg, which converts to 152.8 Wh/kg.

**The source writes it as**

```
RC-Network tabulates MJ/kg; the app uses Wh/kg. 1 MJ = 0.2778 kWh, so 0.55 MJ/kg = 152.8 Wh/kg.
```

**Validity in the RC/UAV regime (ADR 0028).** The critical qualification: 0.55 MJ/kg is a CELL-level figure. Pack-level specific energy after wiring, connectors, balance leads, shrink and case is materially lower - typically 100-140 Wh/kg for RC packs in this class. The skeleton correctly names the quantity 'pack specific energy', so if the cell number is used as the default the predicted mass is systematically light and the deviation warning downstream fires spuriously on correctly-specified packs. Record E* with its source and its cell-vs-pack basis (ADR 0028; ADR 0023 is superseded). The catalogue packs in the database give 128–159 Wh/kg.

## Implementations (1)

| node | claimed | verified | deviation |
|---|---|---|---|
| [[end_battery_mass_predicted]] | EXACT | 🟢 |  |

## Approval

- [ ] **Source** — citation real, or absence stated and adopted on the maintainer's authority
- [ ] **Regime** — holds in the RC/UAV regime (Reynolds, Mach, equipment), or the limitation is written down (ADR 0028)
- [ ] **Dimensions** — the check balances
- [ ] **Implementations** — all agree, or each deviation is declared and justified
- [ ] **Preconditions** — every binding condition holds, or the violation is ticketed
- [ ] **Inputs approved** — no formula is approvable before its inputs are

> While `status: draft` this entry **cites nothing and decides nothing**.

