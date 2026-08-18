---
canon: sink-rate
entry: formula
kind: procedure
shape: law
status: draft
output: sink-rate
source_status: PARTIAL
dimensional_check: UNPARSEABLE
tags:
  - canon/formula
  - source/partial
  - dim/unparseable
  - shape/law
  - kind/procedure
---

# Steady-glide sink rate

**Canonical form**

```
w = V * C_D / C_L   (small glide-angle form of w = V * sin(gamma), tan(gamma) = C_D/C_L)
```

**Produces** [[sink-rate]]  ·  **from** [[flight-speed]] · [[lift-coefficient]] · [[drag-coefficient]]

**Kind: a procedure.** There is no closed form, so an algorithm stands in its place. Approval asks two different questions: **under which assumptions does it hold**, and **when does it converge** — including what it returns when it does not.

### Assumptions and convergence

> A procedure exists because no closed solution does. What replaces the source is the
> statement of **what must hold for it to be valid** and **when it terminates**. Both
> are required before approval.

**Assumptions.** 🔴 not yet stated — required for approval.

**Convergence.** 🔴 not yet stated — required for approval.

**On failure.** 🔴 not yet stated — what is returned when it does not converge, and is it declared? (ADR 0020)

**Dimensional check.** ⚪ not machine-checkable as written

**Source.** 🟡 PARTIAL

> RC-Network Wiki, "Gleitzahl" (Aerodynamik): tan(glide angle) = 1/E = altitude lost / horizontal distance, with E = C_L/C_D. Anderson's Fundamentals of Aerodynamics 6e does NOT cover glide performance - that material is in Anderson's Introduction to Flight / Aircraft Performance and Design, which are not the works this project's aerodynamics-expert authority covers. Scholz treats glide ratio only in the climb-gradient sense (18_Klausur SS19 §2.1).

**The source writes it as**

```
The sourced relation is the glide-angle one, tan(gamma) = C_D/C_L, from which w = V*sin(gamma). The proposal's w = V*C_D/C_L is its small-angle form (sin ~ tan), correctly labelled as such in the skeleton.
```

**Validity at 0.5–15 kg.** The small-angle step is benign for RC gliders (E = 10-20 gives gamma = 3-6 deg, error under 0.5%) but not for draggy powered models: at E = 5 the error is ~2%, at E = 3 it is ~5%, and 3-6 is a realistic E for a sport RC model at low Re. Second-order point: the exact steady glide has L = W*cos(gamma), so V itself is slightly overstated by the level-flight lift balance at low E. Both errors push sink rate the same way (optimistic). Acceptable with a stated E floor; below E ~ 5 report the trigonometric form.

## Implementations (1)

| node | claimed | verified | deviation |
|---|---|---|---|
| [[speed-polar-w]] | EXACT | 🟢 |  |

## Approval

- [ ] **Assumptions** — the conditions under which the procedure is valid are stated
- [ ] **Convergence** — the criterion, and what is returned and declared on failure
- [ ] **Dimensions** — the check balances
- [ ] **Implementations** — all agree, or each deviation is declared and justified
- [ ] **Preconditions** — every binding condition holds, or the violation is ticketed
- [ ] **Inputs approved** — no formula is approvable before its inputs are

> While `status: draft` this entry **cites nothing and decides nothing**.

