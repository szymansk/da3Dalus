---
canon: stall-onset-detection
kind: formula
shape: law
status: draft
output: stall-onset-index
source_status: PARTIAL
dimensional_check: PROCEDURAL
tags:
  - canon/formula
  - source/partial
  - dim/procedural
  - shape/law
---

# Stall onset from the shape of the computed polar

**Canonical form**

```
i_stall = first i > i(C_L,max) with C_L_i < C_L_(i-1) and C_D_i > C_D_(i-1)
```

**Produces** [[stall-onset-index]]  ·  **from** [[lift-coefficient]] · [[drag-coefficient]] · [[angle-of-attack]]

ℹ️ **Reclassified.** Was recorded as a second producer of another quantity. It produces its own: a design limit, not the actual value.

**Dimensional check.** ⚪ procedural — not an algebraic law

**Source.** 🟡 PARTIAL

> The PHYSICS is sourced: Anderson, Fundamentals of Aerodynamics 6e, §4.3 and §4.13 - past the stalling angle the lift coefficient "decreases precipitously" while there is a "large increase in drag", the two conditions the test encodes. The specific discrete two-condition criterion (first index past C_L,max with C_L falling and C_D rising) is an implementation; no source publishes it as a criterion.

**The source writes it as**

```
Anderson describes the mechanism qualitatively and distinguishes stall types rather than giving a detection rule.
```

**Validity at 0.5–15 kg.** Two RC-scale weaknesses. (1) Anderson §4.13 distinguishes leading-edge stall (thin 10-16% sections: sharp peaked maximum, rapid post-stall drop - the test fires cleanly) from trailing-edge stall (>16% thick: "gentle, gradual bending-over of the lift curve" - the test fires late and is sensitive to alpha step size). Thick sections are common on RC trainers, so the soft case is the normal case here. (2) Lennon records stall AoA falling from 17 deg to 10 deg at low model Rn, so a sweep grid tuned to full-scale stall angles can straddle the peak entirely. Deeper caveat: AeroBuildup/VLM does not model separation, so what this test detects is a feature of the underlying section data, not a computed stall - it must not be presented to the user as a predicted stall angle without stating the Re it came from.

## Implementations (1)

| node | claimed | verified | deviation |
|---|---|---|---|
| [[stall-point]] | EXACT | 🟢 |  |

## Approval

- [ ] **Source** — citation real, or absence stated and adopted on the maintainer's authority
- [ ] **Scale** — holds at 0.5–15 kg, or the limitation is written down (ADR 0023)
- [ ] **Dimensions** — the check balances
- [ ] **Implementations** — all agree, or each deviation is declared and justified
- [ ] **Preconditions** — every binding condition holds, or the violation is ticketed
- [ ] **Inputs approved** — no formula is approvable before its inputs are

> While `status: draft` this entry **cites nothing and decides nothing**.

