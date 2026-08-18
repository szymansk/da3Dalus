---
canon: inverted-max-lift-coefficient
kind: formula
shape: law
status: draft
output: inverted-max-lift-coefficient
source_status: NO_SOURCE_FOUND
dimensional_check: BALANCES
tags:
  - canon/formula
  - source/no-source-found
  - dim/balances
  - shape/law
---

# Negative maximum lift coefficient

**Canonical form**

```
C_L,min = -0.8 * C_L,max
```

**Produces** [[inverted-max-lift-coefficient]]  ·  **from** [[max-lift-coefficient]]

**Dimensional check.** 🟢 balances

**Source.** 🔴 NO SOURCE FOUND

> No source. Searched Scholz (Flugzeugentwurf 05/07/08), Sadraey (Ch. 4, 5, 10), Anderson FoA 6e (Ch. 4, 5), Lennon, RC-Network Wiki and rcplanedesigner material. RC-Network "Rückenflug" describes inverted flight only qualitatively (most aircraft need down-elevator to hold altitude inverted). FAR 23.337 fixes the negative LOAD FACTOR limit, not a negative C_L,max. Nothing gives C_L,min = -0.8*C_L,max or any other fixed ratio.

**The source writes it as**

```
n/a.
```

**Validity at 0.5–15 kg.** Unattributed and, more seriously, structurally wrong for RC because it has no camber dependence. The ratio is essentially a function of camber: a symmetric aerobatic section flies inverted at very nearly the same C_L,max magnitude (ratio ~1.0), while a heavily cambered trainer or glider section is far below 0.8. RC covers both extremes within the same 0.5-15 kg class - symmetric pattern/3D models and cambered thermal gliders - so a single constant cannot serve. Either derive C_L,min from the section's negative-alpha polar (which the sweep can produce) or emit a DesignWarning that the negative branch of the V-n envelope is a placeholder.

## Implementations (1)

| node | claimed | verified | deviation |
|---|---|---|---|
| [[fe_cl_min_factor]] | EXACT | 🟢 |  |

## Approval

- [ ] **Source** — citation real, or absence stated and adopted on the maintainer's authority
- [ ] **Scale** — holds at 0.5–15 kg, or the limitation is written down (ADR 0023)
- [ ] **Dimensions** — the check balances
- [ ] **Implementations** — all agree, or each deviation is declared and justified
- [ ] **Inputs approved** — no formula is approvable before its inputs are

> While `status: draft` this entry **cites nothing and decides nothing**.

