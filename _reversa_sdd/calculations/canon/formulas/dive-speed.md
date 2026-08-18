---
canon: dive-speed
entry: formula
kind: law
shape: law
status: draft
output: dive-speed
source_status: PARTIAL
dimensional_check: BALANCES
tags:
  - canon/formula
  - source/partial
  - dim/balances
  - shape/law
  - kind/law
---

# Design dive speed from maximum level speed

**Canonical form**

```
V_D = 1.4 * V_max
```

**Produces** [[dive-speed]]  ·  **from** [[max-level-speed]]

**Kind: a law.** A closed-form relation. Approval asks for its **source** and its **validity at 0.5–15 kg**.

**Dimensional check.** 🟢 balances

**Source.** 🟡 PARTIAL

> 14 CFR 23.335(b)(2)(i) (FAR Part 23, Design airspeeds): V_D may not be less than 1.40*V_C_min for normal and commuter category; 1.50*V_C for utility; 1.55*V_C for acrobatic. The factors may be decreased linearly with W/S to 1.35 at W/S = 100 psf.

**The source writes it as**

```
The regulation multiplies the DESIGN CRUISING SPEED V_C, not the maximum level speed V_max. The proposal applies 1.4 to V_max. Since V_max > V_C in general (Sadraey §4.3.3.1/4.3.3.2: V_max ~ 1.2-1.3 V_C), applying the factor to V_max yields a larger, more conservative V_D than the regulation requires - a safe direction, but a different quantity, and the register should not claim FAR 23.335 as the source of the proposed form without saying so.
```

**Validity at 0.5–15 kg.** FAR Part 23 governs manned GA aircraft; no airworthiness code assigns a V_D to a 0.5-15 kg model. RC practice has no certified equivalent: RC-Network Wiki ("Manövergeschwindigkeit") treats V_A and V_NE qualitatively and observes that high-performance models are marketed as "full-throttle capable" with "dive from 500 m and pull to full deflection" claims - i.e. the RC community operates well outside a certified envelope. Adopting 1.4 is a reasonable conservative import, but note the category coupling: an aerobatic RC model under the same rule would take 1.55, not 1.4. Flag under ADR 0023 as a transport/GA-category constant used at model scale.

## Implementations (3)

| node | claimed | verified | deviation |
|---|---|---|---|
| [[fe_dive_factor]] | EXACT | 🟢 |  |
| [[fe_v_dive]] | EXACT | 🟢 |  |
| [[kpi_dive_speed]] | EXACT | 🟢 |  |

## Approval

- [ ] **Source** — citation real, or absence stated and adopted on the maintainer's authority
- [ ] **Scale** — holds at 0.5–15 kg, or the limitation is written down (ADR 0023)
- [ ] **Dimensions** — the check balances
- [ ] **Implementations** — all agree, or each deviation is declared and justified
- [ ] **Preconditions** — every binding condition holds, or the violation is ticketed
- [ ] **Inputs approved** — no formula is approvable before its inputs are

> While `status: draft` this entry **cites nothing and decides nothing**.

