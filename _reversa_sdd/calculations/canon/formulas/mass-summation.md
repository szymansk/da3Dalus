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

**Kind: a procedure.** There is no closed form, so an algorithm stands in its place. Approval asks two different questions: **under which assumptions does it hold**, and **when does it converge** — including what it returns when it does not.

### Assumptions and convergence

> A procedure exists because no closed solution does. What replaces the source is the
> statement of **what must hold for it to be valid** and **when it terminates**. Both
> are required before approval.

**Assumptions.** 🔴 not yet stated — required for approval.

**Convergence.** 🔴 not yet stated — required for approval.

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

- [ ] **Assumptions** — the conditions under which the procedure is valid are stated
- [ ] **Convergence** — the criterion, and what is returned and declared on failure
- [ ] **Dimensions** — the check balances
- [ ] **Implementations** — all agree, or each deviation is declared and justified
- [ ] **Preconditions** — every binding condition holds, or the violation is ticketed
- [ ] **Inputs approved** — no formula is approvable before its inputs are

> While `status: draft` this entry **cites nothing and decides nothing**.

