---
canon: stall-margin-ratio
kind: formula
status: draft
output: stall-margin-ratio
source_status: PARTIAL
dimensional_check: BALANCES
tags:
  - canon/formula
  - source/partial
  - dim/balances
---

# Stall safety ratio

**Canonical form**

```
V_cruise / V_S1
```

**Produces** [[stall-margin-ratio]]  ·  **from** [[cruise-speed]] · [[stall-speed]]

**Dimensional check.** 🟢 balances

**Source.** 🟡 PARTIAL

> The idea of a speed-over-stall-speed ratio as a safety measure is regulatory and well sourced (CS 25.125 V_APP >= 1.3*V_S; CS 25.111 V_2 >= 1.2*V_S; Sadraey Eq. 4.72 V_TO = 1.1-1.3*V_s; FAR 23.51). But V_cruise/V_S1 SPECIFICALLY, reported as a KPI, has no source in Scholz, Sadraey, Anderson or the RC literature - the regulations set margins on approach and takeoff speeds, not on cruise.

**The source writes it as**

```
Sources state one-sided minima on named certification speeds; the proposal reports a continuous ratio on a mission speed.
```

**Validity at 0.5–15 kg.** Meaningful in principle and useful for the RC audience, but it inherits two problems that compound. It carries the full C_L,max uncertainty of V_S1 (30-45% at model Reynolds number per Lennon, which is ~20% on V_S1), and because V_cruise is itself derived rather than given (see cruise-speed-resolution), the ratio can silently become V_md/V_S1 - a ratio of two quantities both computed from the same polar, then displayed as if it were an independent design margin. That is circular and should either be blocked when V_cruise is substituted, or labelled with which cruise-speed resolution produced it.

## Implementations (1)

| node | claimed | verified | deviation |
|---|---|---|---|
| [[mkpi_stall_safety]] | EXACT | 🟢 |  |

## Approval

- [ ] **Source** — citation real, or absence stated and adopted on the maintainer's authority
- [ ] **Scale** — holds at 0.5–15 kg, or the limitation is written down (ADR 0023)
- [ ] **Dimensions** — the check balances
- [ ] **Implementations** — all agree, or each deviation is declared and justified
- [ ] **Inputs approved** — no formula is approvable before its inputs are

> While `status: draft` this entry **cites nothing and decides nothing**.

