---
canon: linear-lift-curve-inverse
entry: formula
kind: procedure
shape: law
status: draft
output: characteristic-angle-of-attack
source_status: SOURCED
dimensional_check: PROCEDURAL
tags:
  - canon/formula
  - source/sourced
  - dim/procedural
  - shape/law
  - kind/procedure
---

# Angle of attack from lift coefficient via the linear lift curve

**Canonical form**

```
alpha = alpha_0 + C_L / C_Lalpha   (converted to degrees)
```

**Produces** [[characteristic-angle-of-attack]]  ·  **from** [[lift-coefficient]] · [[lift-curve-slope]] · [[zero-lift-angle]]

**Kind: a procedure.** There is no closed form, so an algorithm stands in its place. Approval asks two different questions: **under which assumptions does it hold**, and **when does it converge** — including what it returns when it does not.

### Assumptions and convergence

> A procedure exists because no closed solution does. What replaces the source is the
> statement of **what must hold for it to be valid** and **when it terminates**. Both
> are required before approval.

**Assumptions.** 🔴 not yet stated — required for approval.

**Convergence.** 🔴 not yet stated — required for approval.

**On failure.** 🔴 not yet stated — what is returned when it does not converge, and is it declared? (ADR 0020)

**Dimensional check.** ⚪ procedural — not an algebraic law

**Source.** 🟢 SOURCED

> Anderson, Fundamentals of Aerodynamics 6e, §4.3 (linear region, alpha_L=0, lift slope a_0) and §5.3.3 (finite-wing C_L = a*(alpha - alpha_L=0)). Scholz 08_HighLift §8.2 / Sadraey §5.4.3 list alpha_o and C_l_alpha as defining features of the lift curve. RC: Lennon Ch. 3 performs exactly this inversion in worked form (C_L = 0.211 divided by the 0.08/deg slope gives 2.64 deg, then subtract the E197 section's -2 deg zero-lift angle).

**The source writes it as**

```
Sources write the forward relation C_L = a*(alpha - alpha_0); the proposal inverts it. Anderson §5.3.3 adds a fact worth keeping: alpha_L=0 is unaffected by aspect ratio (at zero lift there is no downwash), so the section zero-lift angle may be used for the finite wing - the slope, not the intercept, is what AR changes.
```

**Validity at 0.5–15 kg.** Valid ONLY inside the linear range, and that is a real restriction for two of the three quantities this formula is used for. Recovering alpha_stall by inverting the linear curve at C_L,max is wrong by construction, because the curve is non-linear precisely there - it will always understate the stall angle. The error is largest exactly at RC scale: Lennon records stall AoA dropping from 17 deg to 10 deg at low model Rn while the linear slope barely moves, so the linear extrapolation overshoots further the smaller the model. alpha at best glide and minimum sink are inside the linear range and are fine.

## Implementations (3)

| node | claimed | verified | deviation |
|---|---|---|---|
| [[alpha-stall-deg]] | SPECIALISED | 🟢 | Evaluated at C_L = C_L,max to report the stall angle. Because the relation is linear, it e |
| [[alpha-best-glide-deg]] | SPECIALISED | 🟢 | Evaluated at the C_L of the best-glide point. |
| [[alpha-min-sink-deg]] | SPECIALISED | 🟢 | Evaluated at the C_L of the minimum-sink point. |

## Approval

- [ ] **Assumptions** — the conditions under which the procedure is valid are stated
- [ ] **Convergence** — the criterion, and what is returned and declared on failure
- [ ] **Dimensions** — the check balances
- [ ] **Implementations** — all agree, or each deviation is declared and justified
- [ ] **Preconditions** — every binding condition holds, or the violation is ticketed
- [ ] **Inputs approved** — no formula is approvable before its inputs are

> While `status: draft` this entry **cites nothing and decides nothing**.

