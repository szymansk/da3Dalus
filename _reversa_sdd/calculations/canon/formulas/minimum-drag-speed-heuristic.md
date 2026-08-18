---
canon: minimum-drag-speed-heuristic
kind: formula
shape: approximation
status: draft
output: minimum-drag-speed
source_status: NO_SOURCE_FOUND
dimensional_check: BALANCES
tags:
  - canon/formula
  - source/no-source-found
  - dim/balances
  - shape/approximation
---

# Minimum-drag speed as a fixed multiple of the stall speed

**Canonical form**

```
V_md = 1.4 * V_S
```

**Produces** [[minimum-drag-speed]]  ·  **from** [[stall-speed]]

⚠️ **Shape: an approximation.** A rule of thumb standing where a law belongs. It may be the right thing to show, but it is never approved *as* the law for this quantity.

> V_md = 1.4·V_S carries no polar information — no C_D0, no e, no AR — so it cannot tell a glider from an aerobatic model.

**Dimensional check.** 🟢 balances

**Source.** 🔴 NO SOURCE FOUND

> No source. Checked Scholz (Flugzeugentwurf 05/07/08), Sadraey (Ch. 4, 5), Anderson FoA 6e, Lennon (Basics of R/C Model Aircraft Design), RC-Network Wiki and rcplanedesigner material. None gives V_md = 1.4*V_S. The nearest sourced speed-to-stall ratios are all for other quantities: Sadraey Eq. 4.72 V_TO = 1.1-1.3 V_s; CS 25.111 V_2 >= 1.2 V_S; CS 25.125 V_APP >= 1.3 V_S.

**The source writes it as**

```
What the sources DO fix is the physics: V_md/V_S = sqrt(C_L,max/C_L,md) with C_L,md = sqrt(pi*e*AR*C_D0) (Anderson §6.7.2). A factor of 1.4 implies C_L,md = 0.51*C_L,max, which is configuration-specific, not a constant. Scholz's own table (05 §5.7) tabulates V/V_md, never V/V_S.
```

**Validity at 0.5–15 kg.** Unattributed at any scale, including RC. Note it is also mutually inconsistent with the sourced Sadraey ratio V_mp = V_md/3^0.25 = V_md/1.316: pairing V_md = 1.4 V_S with V_mp = 1.2 V_S implies V_md/V_mp = 1.167, where Sadraey requires 1.316. The two heuristics cannot both be right. Recommend deriving both from the polar and deleting the fixed multiples, or emitting a DesignWarning when the heuristic path is taken (ADR 0020).

## Implementations (2)

| node | claimed | verified | deviation |
|---|---|---|---|
| [[kpi_best_ld_heuristic]] | EXACT | 🟢 |  |
| [[kpi_best_ld_speed]] | DEVIATES | 🟢 | Not a law but a three-way selection across two different laws: a trimmed operating-point m |

## Approval

- [ ] **Source** — citation real, or absence stated and adopted on the maintainer's authority
- [ ] **Scale** — holds at 0.5–15 kg, or the limitation is written down (ADR 0023)
- [ ] **Dimensions** — the check balances
- [ ] **Implementations** — all agree, or each deviation is declared and justified
- [ ] **Inputs approved** — no formula is approvable before its inputs are

> While `status: draft` this entry **cites nothing and decides nothing**.

