---
canon: reynolds-scheduled-polar
kind: formula
shape: law
status: draft
output: zero-lift-drag-coefficient
source_status: PARTIAL
dimensional_check: PROCEDURAL
tags:
  - canon/formula
  - source/partial
  - dim/procedural
  - shape/law
---

# Polar coefficient interpolated against speed through the Reynolds number

**Canonical form**

```
C_D0(V), e(V) = interp( table, Re(V) ),  Re = rho * V * c_MAC / mu
```

**Produces** [[zero-lift-drag-coefficient]]  ·  **from** [[flight-speed]] · [[air-density]] · [[mean-aerodynamic-chord]] · [[zero-lift-drag-coefficient]] · [[oswald-efficiency]]

**Dimensional check.** ⚪ procedural — not an algebraic law

**Source.** 🟡 PARTIAL

> The Reynolds number itself is exactly sourced: Anderson, Fundamentals of Aerodynamics 6e, §1.7, Re = rho*V*c/mu, with chord as the characteristic length for airfoils. The MANDATE to schedule polar coefficients against Re is strongly sourced (Anderson §4.3: the lift slope a_0 is Re-independent but "c_l,max is strongly dependent on Re because stall is governed by viscous flow separation"). The specific table-interpolation of C_D0 and e against Re(V) is an implementation, published nowhere as a formula.

**The source writes it as**

```
RC-scale sanity-check forms of the same quantity: Lennon Ch. 1-3, Rn = speed(mph) * chord(in) * K with K = 780 at sea level, 690 at 5000 ft, 610 at 10000 ft; RC-Network Wiki "Re-Zahl", Re = v[m/s] * t[mm] * 70.
```

**Validity at 0.5–15 kg.** Re-scheduling is MORE necessary at 0.5-15 kg than at transport scale, not less - this is the one formula in the register whose RC justification is stronger than its transport justification. RC-Network "Re-Zahl" states that model aircraft "often operate near or around the critical Reynolds number", so "flow conditions on wings and tail surfaces can change dramatically with relatively small changes in airspeed and angle of attack", and that even in supercritical regions lift and drag coefficients change significantly with Re. Lennon quantifies the drag half: profile drag nearly doubles at low Rn. Two cautions: (1) linear interpolation assumes smooth variation, which RC-Network explicitly denies near Re_crit - the table needs enough resolution there; (2) Lennon notes a tapered wing's root and tip fly at different Re, so a single MAC-based Re is already an average.

## Implementations (3)

| node | claimed | verified | deviation |
|---|---|---|---|
| [[cd0_at_v]] | EXACT | 🔴 deviates, undeclared |  |
| [[e_at_v]] | EXACT | 🔴 deviates, undeclared |  |
| [[end_e_at_v]] | EXACT | 🔴 deviates, undeclared |  |

## Approval

- [ ] **Source** — citation real, or absence stated and adopted on the maintainer's authority
- [ ] **Scale** — holds at 0.5–15 kg, or the limitation is written down (ADR 0023)
- [ ] **Dimensions** — the check balances
- [ ] **Implementations** — all agree, or each deviation is declared and justified
- [ ] **Preconditions** — every binding condition holds, or the violation is ticketed
- [ ] **Inputs approved** — no formula is approvable before its inputs are

> While `status: draft` this entry **cites nothing and decides nothing**.

