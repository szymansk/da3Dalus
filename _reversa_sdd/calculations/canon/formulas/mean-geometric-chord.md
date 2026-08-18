---
canon: mean-geometric-chord
entry: formula
kind: law
shape: law
status: draft
output: mean-geometric-chord
source_status: SOURCED
dimensional_check: BALANCES
tags:
  - canon/formula
  - source/sourced
  - dim/balances
  - shape/law
  - kind/law
---

# Mean geometric chord

**Canonical form**

```
c_bar = S_ref / b_ref
```

**Produces** [[mean-geometric-chord]]  ·  **from** [[wing-reference-area]] · [[wing-span]]

**Kind: a law.** A closed-form relation. Approval asks for its **source** and its **validity at 0.5–15 kg**.

**Dimensional check.** 🟢 balances

**Source.** 🟢 SOURCED

> 14 CFR 23.341(c) (and CS-25.341 / 14 CFR 25.341) symbol list: "C = Mean geometric chord (ft.)" - this is the chord the gust regulation prescribes for the mass ratio. Sadraey §5.6 gives AR = b/c_bar, hence c_bar = S/b when S = b*c_bar.

**The source writes it as**

```
The regulation names it only as a symbol definition inside the gust-load paragraph; it does not write c_bar = S/b as a standalone equation. That algebraic step comes from Sadraey's AR definition.
```

**Validity at 0.5–15 kg.** Valid. The deliberate choice of MGC over MAC is correct and matches the regulation - keep it, and keep the comment saying why, because it will otherwise be 'fixed' to MAC by a future reviewer. For a rectangular RC wing MGC and MAC coincide, so the distinction only bites on tapered wings.

## Implementations (1)

| node | claimed | verified | deviation |
|---|---|---|---|
| [[fe_c_mgc]] | EXACT | 🟢 |  |

## Approval

- [ ] **Source** — citation real, or absence stated and adopted on the maintainer's authority
- [ ] **Scale** — holds at 0.5–15 kg, or the limitation is written down (ADR 0023)
- [ ] **Dimensions** — the check balances
- [ ] **Implementations** — all agree, or each deviation is declared and justified
- [ ] **Preconditions** — every binding condition holds, or the violation is ticketed
- [ ] **Inputs approved** — no formula is approvable before its inputs are

> While `status: draft` this entry **cites nothing and decides nothing**.

