---
canon: stall-speed-in-turn
entry: formula
kind: law
shape: law
status: draft
output: stall-speed-in-turn
source_status: SOURCED
dimensional_check: BALANCES
tags:
  - canon/formula
  - source/sourced
  - dim/balances
  - shape/law
  - kind/law
  - status/draft
---

# Stall speed in a banked turn

**Canonical form**

```
V_S,turn = V_S1 * sqrt(n)
```

**Produces** [[stall-speed-in-turn]]  ·  **from** [[stall-speed]] · [[load-factor]]

**Kind: a law.** A closed-form relation. Approval asks for its **source** and its **validity at 0.5–15 kg**.

**Dimensional check.** 🟢 balances

**Source.** 🟢 SOURCED

> Follows algebraically from Sadraey §4.3.2 Eq. 4.30 with L = n*W. RC-authority confirmation: Lennon, Basics of R/C Model Aircraft Design (1996), Ch. 21 (Centrifugal Force / CF, turn radius and speed) - "If the demanded CL exceeds CL_max, a high-speed (accelerated) stall results", with worked g-loadings for model pull-outs.

**The source writes it as**

```
Neither source writes V_S,turn = V_S*sqrt(n) as a display equation; both state the accelerated-stall mechanism and the load factor, from which the sqrt(n) scaling is one line of algebra on the lift balance.
```

**Validity at 0.5–15 kg.** Exact - no empiricism. Directly RC-relevant and arguably the most useful safety number in the set for this audience: Lennon Ch. 4 identifies centrifugal load during "tight turns, sharp pull-ups, dive-recoveries" as the most serious consequence of raising wing loading, and Ch. 21 gives concrete model numbers (55 mph at 200 ft radius = 2 g total; 90 mph at 100 ft radius = 6.4 g; 100 mph at 100 ft radius = 7.7 g). Inherits the C_L,max uncertainty of V_S.

## Implementations (1)

| node | claimed | verified | deviation |
|---|---|---|---|
| [[v_stall_turn]] | EXACT | 🟢 |  |

## Approval

- [ ] **Source** — citation real, or absence stated and adopted on the maintainer's authority
- [ ] **Scale** — holds at 0.5–15 kg, or the limitation is written down (ADR 0023)
- [ ] **Dimensions** — the check balances
- [ ] **Implementations** — all agree, or each deviation is declared and justified
- [ ] **Preconditions** — every binding condition holds, or the violation is ticketed
- [ ] **Inputs approved** — no formula is approvable before its inputs are

> While `status: draft` this entry **cites nothing and decides nothing**.

