---
canon: turn-load-factor
entry: formula
kind: law
shape: law
status: draft
output: load-factor
source_status: SOURCED
dimensional_check: BALANCES
tags:
  - canon/formula
  - source/sourced
  - dim/balances
  - shape/law
  - kind/law
---

# Load factor of a steady coordinated level turn

**Canonical form**

```
n = 1 / cos(phi)
```

**Produces** [[load-factor]]  ·  **from** [[bank-angle]]

**Kind: a law.** A closed-form relation. Approval asks for its **source** and its **validity at 0.5–15 kg**.

**Dimensional check.** 🟢 balances

**Source.** 🟢 SOURCED

> Lennon, Basics of R/C Model Aircraft Design (1996), Ch. 21: for a steady coordinated level turn in which horizontal CF equals 1 g and weight equals 1 g, the wing load is sqrt(1^2 + 1^2) = 1.414 g at a bank angle of 45 deg. That is exactly n = 1/cos(45 deg) = 1.4142, i.e. the RC authority states the relation in worked-instance form.

**The source writes it as**

```
Lennon writes it as a Pythagorean vector sum of weight and centrifugal force rather than as n = 1/cos(phi); the two are identical for a coordinated level turn. Neither Anderson's Fundamentals of Aerodynamics 6e (which has no turning-flight chapter - that material is in his Introduction to Flight) nor the Scholz/Sadraey vault states n = 1/cos(phi) as a display equation.
```

**Validity at 0.5–15 kg.** Exact for a steady, coordinated, level turn; assumes no sideslip and negligible thrust-vector contribution. Lennon adds an RC-specific warning the app should not lose: horizontal turns are LESS demanding than vertical loops of the same radius and speed, because a loop adds CF directly to weight rather than vectorially. So n from bank angle is not the envelope-defining case for an aerobatic model - the pull-out is. Reporting only the banked-turn n understates the real RC load case.

## Implementations (1)

| node | claimed | verified | deviation |
|---|---|---|---|
| [[turn_load_factor_n]] | EXACT | 🟢 |  |

## Approval

- [ ] **Source** — citation real, or absence stated and adopted on the maintainer's authority
- [ ] **Scale** — holds at 0.5–15 kg, or the limitation is written down (ADR 0023)
- [ ] **Dimensions** — the check balances
- [ ] **Implementations** — all agree, or each deviation is declared and justified
- [ ] **Preconditions** — every binding condition holds, or the violation is ticketed
- [ ] **Inputs approved** — no formula is approvable before its inputs are

> While `status: draft` this entry **cites nothing and decides nothing**.

