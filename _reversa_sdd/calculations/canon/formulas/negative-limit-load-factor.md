---
canon: negative-limit-load-factor
entry: formula
kind: law
shape: law
status: draft
output: negative-limit-load-factor
source_status: PARTIAL
dimensional_check: BALANCES
tags:
  - canon/formula
  - source/partial
  - dim/balances
  - shape/law
  - kind/law
---

# Negative limit load factor

**Canonical form**

```
n_neg = -0.4 * n_lim
```

**Produces** [[negative-limit-load-factor]]  ·  **from** [[limit-load-factor]]

**Kind: a law.** A closed-form relation. Approval asks for its **source** and its **validity at 0.5–15 kg**.

**Dimensional check.** 🟢 balances

**Source.** 🟡 PARTIAL

> Sadraey, Aircraft Design: A Systems Engineering Approach, §10.4.1: "Aircraft regulations also specify negative load factors (push-over), typically about 0.4x the positive maximum for transports and as much as -3 g for acrobatic GA aircraft." Corroborated by 14 CFR 23.337(b): negative limit -0.4x positive for normal and utility, -0.5x positive for acrobatic category.

**The source writes it as**

```
Sadraey attaches the 0.4 factor specifically to TRANSPORTS and immediately contrasts it with acrobatic aircraft at up to -3 g absolute. It is not presented as a universal ratio. FAR 23.337 makes the category dependence explicit (-0.4 normal/utility, -0.5 acrobatic).
```

**Validity at 0.5–15 kg.** Report under ADR 0023. Sadraey's own Table 10.9 gives "Remote-controlled model: n_max = 1.5-2" as a SEPARATE category, and explains that this reflects designers choosing light structure - not that RC loads are low. Lennon Ch. 21 documents real RC pull-out loads of 6.4-7.7 g, and this project's own load-factor work puts real RC loads at 6-19 g. So the 0.4 ratio imports a transport-category convention into a class both Sadraey and the RC literature treat separately, and it sits on top of an n_lim default (3.0) that is already above Sadraey's RC band. The negative branch of the V-n envelope should either follow FAR 23.337 category selection (0.4 normal / 0.5 acrobatic) or be user-set.

## Implementations (1)

| node | claimed | verified | deviation |
|---|---|---|---|
| [[fe_neg_g_factor]] | EXACT | 🟢 |  |

## Approval

- [ ] **Source** — citation real, or absence stated and adopted on the maintainer's authority
- [ ] **Scale** — holds at 0.5–15 kg, or the limitation is written down (ADR 0023)
- [ ] **Dimensions** — the check balances
- [ ] **Implementations** — all agree, or each deviation is declared and justified
- [ ] **Preconditions** — every binding condition holds, or the violation is ticketed
- [ ] **Inputs approved** — no formula is approvable before its inputs are

> While `status: draft` this entry **cites nothing and decides nothing**.

