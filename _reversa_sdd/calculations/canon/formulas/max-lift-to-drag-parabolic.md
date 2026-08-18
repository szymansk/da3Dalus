---
canon: max-lift-to-drag-parabolic
kind: formula
shape: law
status: draft
output: max-lift-to-drag-ratio
source_status: SOURCED
dimensional_check: BALANCES
tags:
  - canon/formula
  - source/sourced
  - dim/balances
  - shape/law
  - flag/conflict
---

# Maximum glide ratio of a parabolic polar

**Canonical form**

```
E_max = 0.5 * sqrt(pi * e * AR / C_D0)
```

**Produces** [[max-lift-to-drag-ratio]]  ·  **from** [[oswald-efficiency]] · [[aspect-ratio]] · [[zero-lift-drag-coefficient]]

**Dimensional check.** 🟢 balances

**Source.** 🟢 SOURCED

> Anderson, Fundamentals of Aerodynamics 6e, §6.7.2, derived by setting d(C_L/C_D)/dC_L = 0: (L/D)_max = 0.5*sqrt(pi*e*AR/C_D,0). Independently Scholz, Flugzeugentwurf, 05_PreliminarySizing §5.7, Eq. 5.39, identical form. Sadraey (via Scholz aspect-ratio page §5.6) writes the equivalent (L/D)_max = 1/(2*sqrt(K*C_D0)) with K = 1/(pi*e*AR).

**The source writes it as**

```
Identical in all three. Both Anderson and Scholz also give the companion result C_L,md = sqrt(pi*e*AR*C_D,0), i.e. at maximum L/D the zero-lift drag exactly equals the induced drag - a cheap internal consistency assertion the app could make.
```

**Validity at 0.5–15 kg.** The derivation assumes a strictly parabolic polar with constant C_D0 and constant e. That assumption is materially weaker at Re 5e4-3e5 than at transport Re: the RC-scale polar has a drag bucket and a steep off-bucket rise (Scholz/Sadraey §5.4.3: Cd = Cd_min + K*(Cl - Cl_min)^2, an OFFSET parabola), so E_max from this closed form and E_max read off the computed polar will legitimately disagree. Anderson's note that (L/D)_max is independent of weight and size does hold - it is a configuration property. Two producers of E_max is an ADR 0022 risk; pick the computed-polar one as authority at RC scale and derive the closed form only for cross-check.

## ⚠️ Conflict

One user-visible number, two different laws behind it. mission_kpi_service reports the empirical max(C_L/C_D) taken from the AeroBuildup sweep when the polar fit produced an ld_max, and the parabolic closed form otherwise. These agree only if the real polar is parabolic. The formula string rendered next to the KPI is unconditionally the closed form, so in the common case the displayed derivation does not describe the displayed value.

> Two or more implementations use **genuinely different laws** for this quantity.
> This is the entry that must be decided, not merely read.

## Implementations (1)

| node | claimed | verified | deviation |
|---|---|---|---|
| [[mkpi_glide]] | DEVIATES | 🟢 | Prefers the empirical sweep maximum and only falls back to the closed form, while always l |

## Approval

- [ ] **Source** — citation real, or absence stated and adopted on the maintainer's authority
- [ ] **Scale** — holds at 0.5–15 kg, or the limitation is written down (ADR 0023)
- [ ] **Dimensions** — the check balances
- [ ] **Implementations** — all agree, or each deviation is declared and justified
- [ ] **Preconditions** — every binding condition holds, or the violation is ticketed
- [ ] **Inputs approved** — no formula is approvable before its inputs are

> While `status: draft` this entry **cites nothing and decides nothing**.

