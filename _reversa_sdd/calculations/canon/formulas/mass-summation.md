---
canon: mass-summation
entry: formula
kind: procedure
shape: law
status: draft
output: aircraft-mass
source_status: SOURCED
dimensional_check: UNPARSEABLE
tags:
  - canon/formula
  - source/sourced
  - dim/unparseable
  - shape/law
  - kind/procedure
---

# Aircraft mass as the sum of component masses

**Canonical form**

```
m = sum_i m_i
```

**Produces** [[aircraft-mass]]  ·  **from** [[component-mass]]

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

**Dimensional check.** ⚪ not machine-checkable as written

**Source.** 🟢 SOURCED

> Scholz, Flugzeugentwurf, 02_DesignSequence §2.2 (design step 13, take-off mass iteration): m_TO = m_OE + m_F + m_PL. Sadraey Ch. 10 builds MTOW from the same component summation. RC: Lennon, Basics of R/C Model Aircraft Design, Ch. 26 tracks gross weight, wing area, wing loading, engine, prop and power loading as a coherent six-number design point.

**The source writes it as**

```
Scholz sums three mass GROUPS (operating empty, fuel, payload) rather than an arbitrary component tree; the tree is the app's generalisation.
```

**Validity at 0.5–15 kg.** Exact - summation is scale-free. One RC-specific note from Lennon Ch. 26: the discipline that matters is recording the design point as a SET (gross weight, wing area, wing loading, power loading, prop) rather than a single total, because the total alone does not tell you whether the airframe/propulsion combination will fly the mission. Also relevant to this project's stated design philosophy that mass starts as a manual estimate: the summation is only an authority once the tree is populated, so it must not silently override a user-supplied design mass (ADR 0022 - two producers of aircraft mass).

## Implementations (1)

| node | claimed | verified | deviation |
|---|---|---|---|
| [[aircraft-total-weight-kg]] | DEVIATES | 🟢 | Sums only what the user actually placed in the component tree. There is no closed enumerat |

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

