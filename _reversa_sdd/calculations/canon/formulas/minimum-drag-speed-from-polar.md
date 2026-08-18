---
canon: minimum-drag-speed-from-polar
kind: formula
status: draft
output: minimum-drag-speed
source_status: SOURCED
dimensional_check: PROCEDURAL
tags:
  - canon/formula
  - source/sourced
  - dim/procedural
  - flag/conflict
---

# Minimum-drag speed as the argmax of the computed glide ratio

**Canonical form**

```
V_md = V( argmax_i (C_L_i / C_D_i) )
```

**Produces** [[minimum-drag-speed]]  ·  **from** [[flight-speed]] · [[lift-to-drag-ratio]]

**Dimensional check.** ⚪ procedural — not an algebraic law

**Source.** 🟢 SOURCED

> Anderson, Fundamentals of Aerodynamics 6e, §6.7.2 defines (L/D)_max as the maximum of the C_L/C_D curve over angle of attack. RC-Network Wiki "Gleitzahl": the best glide ratio "occurs at a specific airspeed called the best glide speed", and glide ratio is explicitly a function of airspeed with a single interior optimum.

**The source writes it as**

```
Sources define the condition; the discrete argmax over sweep points is the implementation.
```

**Validity at 0.5–15 kg.** Valid, and at 0.5-15 kg this is the PREFERRED route over the closed form, precisely because the low-Re polar is not parabolic. RC-Network also gives the weight dependence that validates the app's behaviour: heavier aircraft reach best glide ratio at higher speed (the ballast argument). Resolution caveat: the argmax is only as good as the alpha/speed grid - a coarse sweep will quantise V_md.

## ⚠️ Conflict

Second of three independent laws for V_md (see minimum-drag-speed-closed-form). This one is polar-shape-free and therefore correct for a non-parabolic polar, but its resolution is limited to the alpha grid of the sweep -- it can only return a speed that was actually sampled.

> Two or more implementations use **genuinely different laws** for this quantity.
> This is the entry that must be decided, not merely read.

## Implementations (2)

| node | claimed | verified | deviation |
|---|---|---|---|
| [[i-best-glide]] | EXACT | 🟢 |  |
| [[v-best-glide]] | EXACT | 🟢 |  |

## Approval

- [ ] **Source** — citation real, or absence stated and adopted on the maintainer's authority
- [ ] **Scale** — holds at 0.5–15 kg, or the limitation is written down (ADR 0023)
- [ ] **Dimensions** — the check balances
- [ ] **Implementations** — all agree, or each deviation is declared and justified
- [ ] **Inputs approved** — no formula is approvable before its inputs are

> While `status: draft` this entry **cites nothing and decides nothing**.

