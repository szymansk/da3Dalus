---
canon: range-from-endurance
entry: formula
kind: law
shape: law
status: draft
output: range
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

# Range from endurance

**Canonical form**

```
R = V_cruise * t
```

**Produces** [[range]]  ·  **from** [[cruise-speed]] · [[endurance-time]]

**Kind: a law.** A closed-form relation. Approval asks for its **source** and its **validity at 0.5–15 kg**.

**Dimensional check.** 🟢 balances — (m/s) * s = m.

**Source.** 🟢 SOURCED

> Definitional for steady flight at constant speed. The Breguet range equation, which the textbook treatment of range rests on, does **not** apply to an electric aircraft: it integrates a weight change as fuel burns, and a battery does not lose mass. Raymer 6e treats the electric case through a battery mass fraction instead, and endurance follows from stored energy over power required — see [[endurance-from-battery]].

**Validity at 0.5–15 kg.** Exact for steady flight at one speed. It says nothing about
climb-out or reserve, which at model scale are a large fraction of a short flight.

## Precondition on the binding

**Both factors must come from the SAME operating point.** Endurance is largest at the
speed of minimum power required; range is largest at the speed of minimum drag, and the two
speeds differ by roughly a factor 0.76 for a parabolic polar. Multiplying a
maximum-endurance time by a maximum-range speed produces a number that no aircraft can
fly — it would be a binding error of exactly the kind A2 exists to prevent.

## Approval

- [ ] **Source** — citation real, or absence stated and adopted on the maintainer's authority
- [ ] **Scale** — holds at 0.5–15 kg, or the limitation is written down (ADR 0023)
- [ ] **Dimensions** — the check balances
- [ ] **Implementations** — all agree, or each deviation is declared and justified
- [ ] **Preconditions** — every binding condition holds, or the violation is ticketed
- [ ] **Inputs approved** — no formula is approvable before its inputs are
