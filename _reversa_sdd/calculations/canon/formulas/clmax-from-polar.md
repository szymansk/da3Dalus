---
canon: clmax-from-polar
entry: formula
kind: procedure
shape: law
status: draft
output: max-lift-coefficient
source_status: PARTIAL
dimensional_check: PROCEDURAL
tags:
  - canon/formula
  - source/partial
  - dim/procedural
  - shape/law
  - kind/procedure
---

# Maximum lift coefficient as the peak of the computed polar

**Canonical form**

```
C_L,max = max over alpha of C_L(alpha)
```

**Produces** [[max-lift-coefficient]]  ·  **from** [[lift-coefficient]] · [[angle-of-attack]]

**Kind: a procedure.** There is no closed form, so an algorithm stands in its place. Source and scale are asked as of any entry — a procedure is not source-free: it either implements a published standard or solves a stated equation. **On top of that** it must say **under which assumptions it holds** and **when it converges**, including what it returns when it does not.

### The procedure

> A procedure is not invented here. It has **two origins**, and both are citable:
> the **relation** it solves, and the **method** it solves it with. Its assumptions and
> its convergence behaviour are then properties of that method — published, not chosen.

**Relation solved.** 🔴 not yet stated — which equation or standard does this implement?

**Method.** 🔴 not yet named — bisection, Brent, Newton, Picard, an interior-point solver, a tabulated standard?

**Assumptions.** 🔴 not yet stated — bracketing, continuity, monotonicity, validity range. These follow from the method; they are not a matter of taste.

**Convergence.** 🔴 not yet stated — tolerance, iteration cap, and the guarantee the method actually offers.

**On failure.** 🔴 not yet stated — what is returned when it does not converge, and is it declared? (ADR 0020)

**Dimensional check.** ⚪ procedural — not an algebraic law

**Source.** 🟡 PARTIAL

> Anderson, Fundamentals of Aerodynamics 6e, §4.3 and §4.13: c_l,max is defined as the maximum of the lift curve, occurring just prior to stall; "the maximum lift coefficient occurs just prior to stall". The definition is sourced; taking the discrete max over a sampled alpha array is an implementation of it, not a published method.

**Validity at 0.5–15 kg.** Valid as a definition. The RC problem is upstream: Anderson §4.3 states that the lift slope a_0 is Reynolds-independent but "c_l,max is strongly dependent on Re because stall is governed by viscous flow separation". A VLM/AeroBuildup sweep does not model separation - the peak it produces is entirely inherited from whatever section data sits underneath it. If that section data is not evaluated at the model's actual Re (5e4-3e5), the reported C_L,max is a different aircraft's number. Anderson §4.13 also warns the peak shape differs by stall type (sharp for 10-16% thick leading-edge stall, gentle bend-over above 16%), which changes how well a discrete max locates it.

## Implementations (2)

| node | claimed | verified | deviation |
|---|---|---|---|
| [[cl-max-speed-polar]] | EXACT | 🟢 |  |
| [[max-cl-point]] | EXACT | 🟢 |  |

## Approval

- [ ] **Source** — citation real, or absence stated and adopted on the maintainer's authority
- [ ] **Scale** — holds at 0.5–15 kg, or the limitation is written down (ADR 0023)
- [ ] **Relation and method** — which equation it solves, and by which named method
- [ ] **Assumptions** — the conditions the method requires (bracketing, continuity, range)
- [ ] **Convergence** — the criterion, and what is returned and declared on failure
- [ ] **Dimensions** — the check balances
- [ ] **Implementations** — all agree, or each deviation is declared and justified
- [ ] **Preconditions** — every binding condition holds, or the violation is ticketed
- [ ] **Inputs approved** — no formula is approvable before its inputs are

> While `status: draft` this entry **cites nothing and decides nothing**.

