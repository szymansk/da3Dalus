---
canon: lift-coefficient-required
kind: formula
shape: law
status: draft
output: lift-coefficient
source_status: SOURCED
dimensional_check: BALANCES
tags:
  - canon/formula
  - source/sourced
  - dim/balances
  - shape/law
---

# Lift coefficient demanded by the level-flight balance at a load factor

**Canonical form**

```
C_L,req = n * m * g / (q * S_ref)
```

**Produces** [[lift-coefficient]]  ·  **from** [[aircraft-mass]] · [[gravity]] · [[load-factor]] · [[dynamic-pressure]] · [[wing-reference-area]]

**Dimensional check.** 🟢 balances

**Source.** 🟢 SOURCED

> Anderson, Fundamentals of Aerodynamics 6e, §1.5: C_L = L/(q_inf*S), with L = n*W from the manoeuvre force balance. Scholz 05_PreliminarySizing §5.6.2 Eq. 5.30 gives the level-flight instance m_MTO/S_W = C_L*q/g. Sadraey §4.3.4 uses the same pattern for rotation: C_LR = 2*m*g/(rho*S*V_R^2).

**The source writes it as**

```
Sources write the n = 1 case and introduce n separately; the combined n*m*g/(q*S) is the app's composition. Scholz's Eq. 5.30 is in mass form (m/S = C_L*q/g), which is where the g placement differs.
```

**Validity at 0.5–15 kg.** Exact. Only caution is interpretive: the C_L this returns is a DEMAND, and the app must compare it against C_L,max at the correct Reynolds number before reporting the point as flyable - Lennon Ch. 21 is explicit that exceeding C_L,max here is precisely the accelerated stall.

## Implementations (1)

| node | claimed | verified | deviation |
|---|---|---|---|
| [[gravity_g]] | EXACT | 🟢 |  |

## Approval

- [ ] **Source** — citation real, or absence stated and adopted on the maintainer's authority
- [ ] **Scale** — holds at 0.5–15 kg, or the limitation is written down (ADR 0023)
- [ ] **Dimensions** — the check balances
- [ ] **Implementations** — all agree, or each deviation is declared and justified
- [ ] **Preconditions** — every binding condition holds, or the violation is ticketed
- [ ] **Inputs approved** — no formula is approvable before its inputs are

> While `status: draft` this entry **cites nothing and decides nothing**.

