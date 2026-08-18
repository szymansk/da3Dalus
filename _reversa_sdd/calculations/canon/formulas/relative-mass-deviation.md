---
canon: relative-mass-deviation
kind: formula
status: draft
output: battery-mass-deviation
source_status: NO_SOURCE_FOUND
dimensional_check: BALANCES
tags:
  - canon/formula
  - source/no-source-found
  - dim/balances
---

# Relative deviation between predicted and entered battery mass

**Canonical form**

```
dev = |m_bat,pred - m_bat| / m_bat
```

**Produces** [[battery-mass-deviation]]  ·  **from** [[predicted-battery-mass]] · [[battery-mass]]

**Dimensional check.** 🟢 balances

**Source.** 🔴 NO SOURCE FOUND

> None, and none is needed - this is a plain relative error |predicted - actual|/actual, not an engineering relation. No aircraft-design authority states it because it is not a domain formula.

**The source writes it as**

```
n/a.
```

**Validity at 0.5–15 kg.** Not scale-dependent. Two implementation notes rather than validity notes: (1) the denominator m_bat is zero whenever the battery mass is unset, and the chain's own convention that 0.0 means 'not configured' makes that state reachable, so the division is undefined on a realistic input; (2) the warning it drives is only as meaningful as E* (see battery-mass-from-capacity) - with a cell-level E* the deviation measures the cell-to-pack overhead rather than a user error, which would make the warning fire on correct data and train users to ignore it.

## Implementations (1)

| node | claimed | verified | deviation |
|---|---|---|---|
| [[end_battery_deviation]] | EXACT | 🟢 |  |

## Approval

- [ ] **Source** — citation real, or absence stated and adopted on the maintainer's authority
- [ ] **Scale** — holds at 0.5–15 kg, or the limitation is written down (ADR 0023)
- [ ] **Dimensions** — the check balances
- [ ] **Implementations** — all agree, or each deviation is declared and justified
- [ ] **Inputs approved** — no formula is approvable before its inputs are

> While `status: draft` this entry **cites nothing and decides nothing**.

