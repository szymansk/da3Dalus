---
canon: high-lift-clmax
kind: formula
shape: law
status: draft
output: max-lift-coefficient-config
source_status: PARTIAL
dimensional_check: BALANCES
tags:
  - canon/formula
  - source/partial
  - dim/balances
  - shape/law
  - flag/conflict
---

# Configuration C_L,max from the clean value and a flap factor

**Canonical form**

```
C_L,max,cfg = f_cfg * C_L,max,clean
```

**Produces** [[max-lift-coefficient-config]]  ·  **from** [[max-lift-coefficient]] · [[flap-clmax-factor]]

**Dimensional check.** 🟢 balances

**Source.** 🟡 PARTIAL

> Scholz, Flugzeugentwurf, 08_HighLift §8.2 (DATCOM 1978 method); Sadraey §4.3.4 Eq. 4.69c. Both sources exist and both write the relation ADDITIVELY, not multiplicatively.

**The source writes it as**

```
Scholz: C_L,max = C_L,max,clean + dC_L,max,f + dC_L,max,s, where the flap contribution is scaled dC_L,max,f = dc_l,max,f * (S_W,f/S_W) * K_Lambda (flapped-area ratio times a sweep factor, K_Lambda ~1.0 at 0 deg sweep), and the slat contribution uses (S_W,s/S_W)*cos(phi_HL) per Raymer 1992. Sadraey: C_L_TO = C_L_C + C_L_flap_TO with C_L_flap_TO ~ 0.3-0.8. A pure per-flap-type MULTIPLIER f_cfg in the range 1.0-1.6 has NO source in Scholz, Sadraey, Anderson or the RC vault.
```

**Validity at 0.5–15 kg.** The additive+area-scaled form is the sourced one and is the more defensible at RC scale, because RC flaps typically cover a smaller span fraction than transport flaps (where 0.60-0.75 of wing area is flapped), and the area ratio is exactly what the multiplier form throws away. A multiplier also makes the increment proportional to the clean C_L,max, which is backwards: flap increment is a property of the flap, not of the clean wing. Recommend recording this as a knowingly-simplified model with a DesignWarning, or switching to the additive form.

## ⚠️ Conflict

Two different laws for the same quantity. field_length_service applies a flap-type multiplier table (up to 1.3 takeoff, 1.6 landing) to the base C_L,max. matching_chart_service, for the same aircraft and the same two configurations, defaults C_L,max,TO and C_L,max,LDG to the clean value, i.e. f_cfg identically 1.0 -- no high-lift device is ever credited. The takeoff and landing constraints on the matching chart therefore sit at up to 60% lower C_L,max than the field-length service assumes for the identical configuration, and neither producer emits a warning about the substitution.

> Two or more implementations use **genuinely different laws** for this quantity.
> This is the entry that must be decided, not merely read.

## Implementations (4)

| node | claimed | verified | deviation |
|---|---|---|---|
| [[cl_max_ldg_fl]] | EXACT | 🔴 deviates, undeclared |  |
| [[cl_max_to_fl]] | EXACT | 🔴 deviates, undeclared |  |
| [[cl_max_l_mc]] | DEVIATES | 🟢 | No flap factor exists in this module: C_L,max,LDG defaults to the clean C_L,max (f_cfg = 1 |
| [[cl_max_to_mc]] | DEVIATES | 🟢 | Same as cl_max_l_mc for the takeoff configuration: C_L,max,TO defaults to the clean C_L,ma |

## Approval

- [ ] **Source** — citation real, or absence stated and adopted on the maintainer's authority
- [ ] **Scale** — holds at 0.5–15 kg, or the limitation is written down (ADR 0023)
- [ ] **Dimensions** — the check balances
- [ ] **Implementations** — all agree, or each deviation is declared and justified
- [ ] **Preconditions** — every binding condition holds, or the violation is ticketed
- [ ] **Inputs approved** — no formula is approvable before its inputs are

> While `status: draft` this entry **cites nothing and decides nothing**.

