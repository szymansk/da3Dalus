---
canon: stall-wing-loading-limit
kind: formula
shape: law
status: draft
output: wing-loading-limit-stall
source_status: SOURCED
dimensional_check: BALANCES
tags:
  - canon/formula
  - source/sourced
  - dim/balances
  - shape/law
---

# Maximum wing loading permitted by a stall-speed requirement

**Canonical form**

```
(W/S)_max,stall = 0.5 * rho * V_S,target^2 * C_L,max,clean
```

**Produces** [[wing-loading-limit-stall]]  ·  **from** [[air-density]] · [[stall-speed-target]] · [[max-lift-coefficient]]

ℹ️ **Reclassified.** Was recorded as a second producer of another quantity. It produces its own: a design limit, not the actual value.

**Dimensional check.** 🟢 balances

**Source.** 🟢 SOURCED

> Sadraey, Aircraft Design: A Systems Engineering Approach, §4.3.2, Eq. 4.31 verbatim: (W/S)_Vs = 0.5*rho*V_s^2*C_L,max. Boxed in the source as the stall-speed sizing constraint.

**The source writes it as**

```
Identical. Sadraey adds two binding usage rules the app should honour: (a) rho must be the SEA-LEVEL value (1.225 kg/m^3), because lowest density gives highest V_s and hence the conservative match; (b) the acceptable region is to the LEFT of the resulting vertical line (lower W/S is always acceptable). Sadraey also notes FAR 23 caps V_s at 61 kt and CS-VLA at 45 kt - FAR 25 has no V_s cap and uses landing field length instead.
```

**Validity at 0.5–15 kg.** Valid at RC scale, and it is the right constraint to use for RC (Scholz's Loftin landing-field-length alternative, s_LFL with k_L = 0.107 kg/m^3, is a statistical fit to 1980s jet transports and must NOT be used at 0.5-15 kg). Caveat under ADR 0023: Sadraey's C_L,max source tables 4.10/4.11 have no RC row. The nearest bands are Home-built 1.2-1.8 and Microlight 1.8-2.4. The app's 1.4 default sits inside the home-built band, which is a defensible provenance, but it is a manned-aircraft band, not an RC measurement.

## Implementations (1)

| node | claimed | verified | deviation |
|---|---|---|---|
| [[ws_stall_constraint]] | EQUIVALENT | 🟢 |  |

## Approval

- [ ] **Source** — citation real, or absence stated and adopted on the maintainer's authority
- [ ] **Scale** — holds at 0.5–15 kg, or the limitation is written down (ADR 0023)
- [ ] **Dimensions** — the check balances
- [ ] **Implementations** — all agree, or each deviation is declared and justified
- [ ] **Inputs approved** — no formula is approvable before its inputs are

> While `status: draft` this entry **cites nothing and decides nothing**.

