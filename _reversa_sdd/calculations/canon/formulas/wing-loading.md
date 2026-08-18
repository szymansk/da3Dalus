---
canon: wing-loading
entry: formula
kind: law
shape: law
status: draft
output: wing-loading
source_status: SOURCED
dimensional_check: BALANCES
tags:
  - canon/formula
  - source/sourced
  - dim/balances
  - shape/law
  - kind/law
---

# Wing loading

**Canonical form**

```
W/S = m * g / S_ref
```

**Produces** [[wing-loading]]  ·  **from** [[aircraft-mass]] · [[gravity]] · [[wing-reference-area]]

**Kind: a law.** A closed-form relation. Approval asks for its **source** and its **validity at 0.5–15 kg**.

**Dimensional check.** 🟢 balances

**Source.** 🟢 SOURCED

> Sadraey, Aircraft Design: A Systems Engineering Approach (Wiley 2013), §4.3.2, Eq. 4.30-4.31: L = W = 0.5*rho*V_s^2*S*C_L,max, divided by S. Scholz, 05_PreliminarySizing §5.1 uses the mass form m_ML/S_W. RC: RC-Network Wiki, "Flächenbelastung"; Lennon, Basics of R/C Model Aircraft Design (1996), Ch. 4 "Wing Loading Design".

**The source writes it as**

```
Scholz/Sadraey normally write the MASS loading m/S in kg/m^2 (or lb/ft^2), not the force loading N/m^2. RC writes g/dm^2 (Europe) or oz/ft^2 (Lennon: gliders <10-15, sport 15-20, pattern 23-26 oz/ft^2). Conversion, not disagreement - but it is where the second g enters.
```

**Validity at 0.5–15 kg.** Fully valid at 0.5-15 kg; wing loading is arguably the single most used RC design number. Caveat is presentational: RC users read g/dm^2 or oz/ft^2, and Lennon's mission bands are the ones they benchmark against. Producing this quantity in three places with two different g values (as the skeleton notes) is an ADR 0022 violation with no defence in either source.

## Implementations (3)

| node | claimed | verified | deviation |
|---|---|---|---|
| [[fe_wing_loading]] | EXACT | 🟢 |  |
| [[wing_loading_fl]] | EXACT | 🟢 |  |
| [[mkpi_wing_loading]] | EXACT | 🟢 |  |

## Approval

- [ ] **Source** — citation real, or absence stated and adopted on the maintainer's authority
- [ ] **Scale** — holds at 0.5–15 kg, or the limitation is written down (ADR 0023)
- [ ] **Dimensions** — the check balances
- [ ] **Implementations** — all agree, or each deviation is declared and justified
- [ ] **Preconditions** — every binding condition holds, or the violation is ticketed
- [ ] **Inputs approved** — no formula is approvable before its inputs are

> While `status: draft` this entry **cites nothing and decides nothing**.

