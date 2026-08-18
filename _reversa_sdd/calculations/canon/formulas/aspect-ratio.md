---
canon: aspect-ratio
kind: formula
shape: law
status: draft
output: aspect-ratio
source_status: SOURCED
dimensional_check: BALANCES
tags:
  - canon/formula
  - source/sourced
  - dim/balances
  - shape/law
---

# Aspect ratio from span and area

**Canonical form**

```
AR = b_ref^2 / S_ref
```

**Produces** [[aspect-ratio]]  ·  **from** [[wing-span]] · [[wing-reference-area]]

**Dimensional check.** 🟢 balances

**Source.** 🟢 SOURCED

> Anderson, Fundamentals of Aerodynamics 6e, §5.3.3: AR = b^2/S, used throughout the finite-wing induced-drag development. Sadraey §5.6 gives the primary definition AR = b/c_bar with b^2/S as the special case.

**The source writes it as**

```
Sadraey §5.6 is explicit that AR = b^2/S is "only valid when area equals span x chord" (rectangular or straight-tapered); for elliptic, delta or unusual planforms the AR = b/c_bar definition must be used.
```

**Validity at 0.5–15 kg.** Valid for the trapezoidal wings this app builds. Sadraey's caveat is live for RC flying wings and delta/elliptical planforms, which are common at model scale. The separate 7.0 literal fallback noted in the skeleton has no source in any of the three authorities and is an undeclared substitution (ADR 0020).

## Implementations (1)

| node | claimed | verified | deviation |
|---|---|---|---|
| [[fe_aspect_ratio]] | EXACT | 🟢 |  |

## Approval

- [ ] **Source** — citation real, or absence stated and adopted on the maintainer's authority
- [ ] **Scale** — holds at 0.5–15 kg, or the limitation is written down (ADR 0023)
- [ ] **Dimensions** — the check balances
- [ ] **Implementations** — all agree, or each deviation is declared and justified
- [ ] **Preconditions** — every binding condition holds, or the violation is ticketed
- [ ] **Inputs approved** — no formula is approvable before its inputs are

> While `status: draft` this entry **cites nothing and decides nothing**.

