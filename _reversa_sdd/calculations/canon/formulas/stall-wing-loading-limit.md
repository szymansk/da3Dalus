---
canon: stall-wing-loading-limit
entry: formula
kind: law
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
  - kind/law
  - status/draft
---

# Maximum wing loading permitted by a stall-speed requirement

**Canonical form**

```
(W/S)_max,stall = 0.5 * rho_0 * V_S,target^2 * C_L,max,clean
```

**Produces** [[wing-loading-limit-stall]]  ·  **from** [[sea-level-air-density]] · [[stall-speed-target]] · [[max-lift-coefficient]]

**Kind: a law.** A closed-form relation. Approval asks for its **source** and its **validity at 0.5–15 kg**.

ℹ️ **Reclassified.** Was recorded as a second producer of another quantity. It produces its own: a design limit, not the actual value.

**Dimensional check.** 🟢 balances

**Source.** 🟢 SOURCED

> Sadraey, Aircraft Design: A Systems Engineering Approach, §4.3.2, Eq. 4.31 verbatim: (W/S)_Vs = 0.5*rho*V_s^2*C_L,max. Boxed in the source as the stall-speed sizing constraint.

**The source writes it as**

```
Identical. Sadraey adds two usage rules: (a) rho is the SEA-LEVEL value (1.225 kg/m^3). Corrected 2026-10-02: the earlier gloss called this the conservative choice because lowest density gives highest V_s — that is backwards, sea level is the densest air and gives the LOWEST V_s. It is a convention (stall speeds stated as equivalent airspeed), and the maintainer adopts it for simplicity: RC models are flown by feel, almost never with an airspeed sensor, so V_S,target is meant at sea level. (b) the acceptable region is to the LEFT of the resulting vertical line (lower W/S is always acceptable). Sadraey also notes FAR 23 caps V_s at 61 kt and CS-VLA at 45 kt - FAR 25 has no V_s cap and uses landing field length instead.
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
- [ ] **Preconditions** — every binding condition holds, or the violation is ticketed
- [ ] **Inputs approved** — no formula is approvable before its inputs are

> While `status: draft` this entry **cites nothing and decides nothing**.

## Design direction — what this entry is for (maintainer, 2026-10-02)

It turns a **mission target** into a **requirement on the construction** before the airplane
exists: the highest wing loading that still meets `V_S,target`. That is the purpose of the
design direction, not a defect — the system is meant to help the designer (a person or an AI
agent) judge the aircraft's properties and steer the construction. Once an airplane exists,
the analysis computes `V_S` and the comparison with `V_S,target` closes the loop in the Ablauf.

Open: where `C_L,max` comes from while there is no airplane yet (O12).
