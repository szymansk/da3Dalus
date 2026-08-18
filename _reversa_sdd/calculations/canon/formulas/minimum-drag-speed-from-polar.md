---
canon: minimum-drag-speed-from-polar
entry: formula
kind: procedure
shape: route
status: draft
output: minimum-drag-speed
source_status: SOURCED
dimensional_check: PROCEDURAL
tags:
  - canon/formula
  - source/sourced
  - dim/procedural
  - shape/route
  - kind/procedure
---

# Minimum-drag speed as the argmax of the computed glide ratio

**Canonical form**

```
V_md = V( argmax_i (C_L_i / C_D_i) )
```

**Produces** [[minimum-drag-speed]]  ·  **from** [[flight-speed]] · [[lift-to-drag-ratio]]

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

**Shape: a route.** This is one of several ways to the same quantity. The canon does not choose between them — it requires that they **agree**.

**Test that follows.** Both routes claim the same quantity by different means; they must agree. Where they do not, the polar is not parabolic — which is a statement about the aircraft, not a defect.

**Dimensional check.** ⚪ procedural — not an algebraic law

**Source.** 🟢 SOURCED

> Anderson, Fundamentals of Aerodynamics 6e, §6.7.2 defines (L/D)_max as the maximum of the C_L/C_D curve over angle of attack. RC-Network Wiki "Gleitzahl": the best glide ratio "occurs at a specific airspeed called the best glide speed", and glide ratio is explicitly a function of airspeed with a single interior optimum.

**The source writes it as**

```
Sources define the condition; the discrete argmax over sweep points is the implementation.
```

**Validity at 0.5–15 kg.** Valid, and at 0.5-15 kg this is the PREFERRED route over the closed form, precisely because the low-Re polar is not parabolic. RC-Network also gives the weight dependence that validates the app's behaviour: heavier aircraft reach best glide ratio at higher speed (the ballast argument). Resolution caveat: the argmax is only as good as the alpha/speed grid - a coarse sweep will quantise V_md.

## Implementations (2)

| node | claimed | verified | deviation |
|---|---|---|---|
| [[i-best-glide]] | EXACT | 🟢 |  |
| [[v-best-glide]] | EXACT | 🟢 |  |

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

