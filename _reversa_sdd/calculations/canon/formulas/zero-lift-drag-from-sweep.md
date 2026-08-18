---
canon: zero-lift-drag-from-sweep
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
  - flag/conflict
---

# Drag coefficient at zero lift, read off the computed sweep

**Canonical form**

```
C_D0 := C_D at the C_L = 0 crossing, by linear interpolation between the two bracketing sweep points
```

**Produces** [[zero-lift-drag-coefficient]]  ·  **from** [[lift-coefficient]] · [[drag-coefficient]] · [[angle-of-attack]]

**Dimensional check.** ⚪ procedural — not an algebraic law

**Source.** 🟡 PARTIAL

> Anderson, Fundamentals of Aerodynamics 6e, §6.7.2 defines C_D,0 as "the zero-lift drag coefficient (parasite drag at C_L = 0)" within the polar C_D = C_D,0 + r*C_L^2 + C_L^2/(pi*e*AR), rewritten as C_D,0 + C_L^2/(pi*e_tilde*AR). Reading C_D at the C_L = 0 crossing is the definition; interpolating between two bracketing sweep points is the implementation.

**The source writes it as**

```
Anderson's definition and the parabolic-fit intercept coincide ONLY for a strictly parabolic polar. Anderson is explicit that parasite drag is not truly lift-independent (C_D,e = C_D,0 + r*C_L^2), which is why the Oswald factor exists at all - so a real polar's value at C_L = 0 and its fitted intercept are different numbers by construction.
```

**Validity at 0.5–15 kg.** This is a genuine correctness finding at RC scale, not just the naming collision the skeleton already flags. Scholz/Sadraey §5.4.3 give the polar form that actually applies to airfoils at these Reynolds numbers: Cd = Cd_min + K*(Cl - Cl_min)^2 - an OFFSET parabola whose minimum sits at a POSITIVE Cl (the laminar drag bucket, with Cd_min ~0.003-0.006 for laminar sections). For a cambered RC section, C_D at C_L = 0 is therefore neither the minimum drag nor the parabolic C_D0; it is a point on the rising left branch of the bucket, and it overstates C_D0. The two producers of C_D0 in this chain will disagree by more at 0.5-15 kg than they would on a transport, and the C_L=0 one is the wrong one. ADR 0022 applies; resolve toward the fitted intercept over the operating C_L range.

## ⚠️ Conflict

Two genuinely different laws produce a number labelled C_D0. Here it is the solver's TOTAL C_D interpolated at the C_L sign change, which still contains induced drag from the residual (non-zero) lift distribution, trim drag and any spanwise-loading offset -- it is C_D(C_L=0), not the parasite term. Everywhere else in the chain (v_md, tw_cruise_constraint, power-required-electrical, max-lift-to-drag-parabolic) C_D0 means the lift-independent term of a fitted parabolic polar C_D = C_D0 + k C_L^2. The two are different quantities that differ by the induced drag at the zero-net-lift condition. Substituting the first into the second's formulas biases V_md high, the cruise T/W constraint high and E_max low, and the diagram labels the first one 'CD0' to the user.

> Two or more implementations use **genuinely different laws** for this quantity.
> This is the entry that must be decided, not merely read.

## Implementations (1)

| node | claimed | verified | deviation |
|---|---|---|---|
| [[drag-at-zero-lift-point]] | DEVIATES | 🟢 | Reports total C_D at C_L = 0, not the parasite term of the polar, while carrying the C_D0  |

## Approval

- [ ] **Source** — citation real, or absence stated and adopted on the maintainer's authority
- [ ] **Scale** — holds at 0.5–15 kg, or the limitation is written down (ADR 0023)
- [ ] **Dimensions** — the check balances
- [ ] **Implementations** — all agree, or each deviation is declared and justified
- [ ] **Inputs approved** — no formula is approvable before its inputs are

> While `status: draft` this entry **cites nothing and decides nothing**.

