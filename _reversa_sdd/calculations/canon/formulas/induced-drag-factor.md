---
canon: induced-drag-factor
kind: formula
status: draft
output: induced-drag-factor
source_status: SOURCED
dimensional_check: BALANCES
tags:
  - canon/formula
  - source/sourced
  - dim/balances
---

# Induced-drag factor of the parabolic polar

**Canonical form**

```
k = 1 / (pi * e * AR)
```

**Produces** [[induced-drag-factor]]  ·  **from** [[oswald-efficiency]] · [[aspect-ratio]]

**Dimensional check.** 🟢 balances

**Source.** 🟢 SOURCED

> Anderson, Fundamentals of Aerodynamics 6e, §5.3.3: C_D,i = C_L^2/(pi*e*AR), with e = 1/(1+delta) the span efficiency factor; §6.7.2 for the complete-airplane form. Sadraey Eq. 4.41: K = 1/(pi*e*AR). Scholz 05_PreliminarySizing §5.7 same.

**The source writes it as**

```
Anderson §6.7.2 draws a distinction the app must not lose: the SPAN efficiency e in C_D,i = C_L^2/(pi*e*AR) is 0.9-1.0 for a clean wing, whereas the OSWALD factor e_tilde = 1/(1 + r*pi*e*AR) in the total-airplane polar is 0.70-0.85 and additionally absorbs the lift-dependent part of parasite drag (C_D,e = C_D,0 + r*C_L^2). They are different numbers; Anderson says so explicitly.
```

**Validity at 0.5–15 kg.** Prandtl lifting-line: valid for moderate-to-high AR unswept wings, which covers RC well. The RC-specific weakness is the constant-e assumption: at Re 5e4-3e5 the lift-dependent parasite term r*C_L^2 is LARGER than at transport scale (laminar separation bubble drag rises steeply outside the drag bucket), so a single e fitted over the whole polar is a worse approximation for a model than for an airliner. The 0.8 literal fallback is an Oswald-band number (Anderson's 0.70-0.85) being used where a span efficiency may be meant - state which one it is.

## Implementations (2)

| node | claimed | verified | deviation |
|---|---|---|---|
| [[end_k_induced]] | EXACT | 🟢 |  |
| [[induced_drag_factor_k]] | EXACT | 🟢 |  |

## Approval

- [ ] **Source** — citation real, or absence stated and adopted on the maintainer's authority
- [ ] **Scale** — holds at 0.5–15 kg, or the limitation is written down (ADR 0023)
- [ ] **Dimensions** — the check balances
- [ ] **Implementations** — all agree, or each deviation is declared and justified
- [ ] **Inputs approved** — no formula is approvable before its inputs are

> While `status: draft` this entry **cites nothing and decides nothing**.

