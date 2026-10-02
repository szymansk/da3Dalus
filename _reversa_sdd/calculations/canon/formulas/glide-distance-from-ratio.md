---
canon: glide-distance-from-ratio
entry: formula
kind: law
tool: APP
shape: law
status: draft
output: glide-distance
source_status: SOURCED
dimensional_check: BALANCES
tags:
  - canon/formula
  - source/sourced
  - dim/balances
  - shape/law
  - kind/law
  - status/draft
---

# Glide distance from the glide ratio

**Canonical form**

```
R_glide = E * h
```

**Produces** [[glide-distance]]  ·  **from** [[lift-to-drag-ratio]] · [[altitude]]

**Kind: a law.** A closed-form relation. Approval asks for its **source** and its **validity at 0.5–15 kg**.

**Dimensional check.** 🟢 balances — dimensionless * m = m.

**Source.** 🟢 SOURCED

> Definitional from the steady glide: the glide angle satisfies tan(gamma) = C_D/C_L = 1/E, so the ground distance covered from height h is h/tan(gamma) = E*h. Anderson, Fundamentals of Aerodynamics 6e, §6.6, derives the same relation for the unpowered equilibrium glide. The small-angle step is the one already declared in [[sink-rate]].

**Validity at 0.5–15 kg.** Exact for a **steady** glide at the stated glide ratio. It
assumes the aircraft is already at that speed and stays there; the height lost while
settling into the glide after a motor stops is not in it, and at model scale that
transient is a real fraction of a low-altitude engine-out.

## Preconditions on the bindings

**`E` must come from the same configuration the aircraft is actually in.** Best glide is
reached only at the minimum-drag speed; at any other speed `E` is smaller and so is the
distance. A glide distance computed from `E_max` while the model flies at some other speed
overstates what it can reach.

**The propeller is not in the polar.** Unpowered flight here uses the clean polar. A
windmilling propeller adds substantial drag, a stopped one less, a folded one almost none
— the qualitative ordering is established but no figure is sourced at this scale, so none
is applied. The distance this formula gives is therefore an **upper bound** for a model
whose propeller keeps turning.

## Approval

- [ ] **Source** — citation real, or absence stated and adopted on the maintainer's authority
- [ ] **Scale** — holds at 0.5–15 kg, or the limitation is written down (ADR 0023)
- [ ] **Dimensions** — the check balances
- [ ] **Implementations** — all agree, or each deviation is declared and justified
- [ ] **Preconditions** — every binding condition holds, or the violation is ticketed
- [ ] **Inputs approved** — no formula is approvable before its inputs are
