---
canon: thrust-to-weight
kind: formula
shape: law
status: draft
output: thrust-to-weight
source_status: SOURCED
dimensional_check: BALANCES
tags:
  - canon/formula
  - source/sourced
  - dim/balances
  - shape/law
---

# Thrust-to-weight ratio

**Canonical form**

```
T/W = T_mean / W
```

**Produces** [[thrust-to-weight]]  ·  **from** [[mean-thrust]] · [[weight]]

**Dimensional check.** 🟢 balances

**Source.** 🟢 SOURCED

> Sadraey §4.3.3.1 Eq. 4.47 and §4.3.4 Eq. 4.71; Scholz 05_PreliminarySizing §5.2 - both use T_TO/(m_MTO*g) as the ordinate of the matching chart throughout. Definitional, universally used.

**The source writes it as**

```
Scholz writes it as T_TO/(m_MTO*g) rather than T/W, keeping mass explicit.
```

**Validity at 0.5–15 kg.** Exact as a definition, but the METHODOLOGICAL fit to RC is poor and this is a sourced objection, not a preference. Sadraey §4.3.5.2 and §4.3.3.2 are explicit that PROP-DRIVEN aircraft are sized on power loading W/P, not thrust loading T/W (Eq. 4.56 and 4.89 are both W/P forms), because for a propeller thrust is not a design constant. Every 0.5-15 kg electric model is prop-driven. RC practice agrees: Lennon Ch. 26 tracks power loading (oz per cubic inch of displacement) as his go/no-go metric, and the electric RC community uses W/kg. Building the matching chart on T/W departs from the sourced prop methodology.

## Implementations (1)

| node | claimed | verified | deviation |
|---|---|---|---|
| [[t_over_w_fl]] | EXACT | 🟢 |  |

## Approval

- [ ] **Source** — citation real, or absence stated and adopted on the maintainer's authority
- [ ] **Scale** — holds at 0.5–15 kg, or the limitation is written down (ADR 0023)
- [ ] **Dimensions** — the check balances
- [ ] **Implementations** — all agree, or each deviation is declared and justified
- [ ] **Preconditions** — every binding condition holds, or the violation is ticketed
- [ ] **Inputs approved** — no formula is approvable before its inputs are

> While `status: draft` this entry **cites nothing and decides nothing**.

