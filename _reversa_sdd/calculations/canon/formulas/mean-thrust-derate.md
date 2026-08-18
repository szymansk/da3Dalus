---
canon: mean-thrust-derate
kind: formula
status: draft
output: mean-thrust
source_status: PARTIAL
dimensional_check: UNKNOWN_SYMBOL
tags:
  - canon/formula
  - source/partial
  - dim/unknown_symbol
---

# Effective mean thrust over the ground roll

**Canonical form**

```
T_mean = f_T * T_static
```

**Produces** [[mean-thrust]]  ·  **from** [[static-thrust]]

**Dimensional check.** ⚪ symbol not in the register

**Source.** 🟡 PARTIAL

> The SIMPLIFICATION is sourced, the VALUE is not. Scholz, 05_PreliminarySizing §5.2, derives the simplified ground roll explicitly "assuming level runway with no wind, negligible drag and friction compared to thrust" - i.e. constant thrust over the roll. Sadraey §4.3.4 Eq. 4.66/4.71 declines the simplification and integrates the actual force balance with C_DG = C_D_TO - mu*C_L_TO, absorbing the roll plus obstacle-clearance segment in the constant 1.65. No source in Scholz, Sadraey, Anderson, Lennon or RC-Network gives a numeric static-to-mean thrust factor f_T.

**The source writes it as**

```
Sadraey's closed form (Eq. 4.71) is the accurate alternative and needs mu (Table 4.15: dry concrete/asphalt 0.03-0.05, turf 0.04-0.07, grass 0.05-0.1, soft ground 0.1-0.3) rather than a thrust derate.
```

**Validity at 0.5–15 kg.** Doubly weak at RC scale. (1) Lennon Ch. 18 documents the static-to-flight change from the propeller side using David Gierke's Real Performance Measurement tests: static-to-flight rpm gain is ~+10%, and advance per rev EXCEEDS nominal pitch by 7-18%. The thrust decay with airspeed is steep and prop-specific, so a single scalar f_T is a per-prop fudge, and the RC vault's low-Reynolds propeller material shows thrust degradation is itself Re-dependent at model scale. (2) Many models in this class are hand-launched and have no ground roll at all, making the whole quantity undefined for that launch mode. Declare f_T as an assumption with a DesignWarning (ADR 0020).

## Implementations (1)

| node | claimed | verified | deviation |
|---|---|---|---|
| [[t_mean_fl]] | DEVIATES | 🟢 | The de-rate factor f_T is currently 1.0, so the mean thrust over the ground roll is assert |

## Approval

- [ ] **Source** — citation real, or absence stated and adopted on the maintainer's authority
- [ ] **Scale** — holds at 0.5–15 kg, or the limitation is written down (ADR 0023)
- [ ] **Dimensions** — the check balances
- [ ] **Implementations** — all agree, or each deviation is declared and justified
- [ ] **Inputs approved** — no formula is approvable before its inputs are

> While `status: draft` this entry **cites nothing and decides nothing**.

