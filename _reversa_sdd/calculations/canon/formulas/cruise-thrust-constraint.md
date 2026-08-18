---
canon: cruise-thrust-constraint
entry: formula
kind: law
shape: law
status: draft
output: thrust-to-weight-required-cruise
source_status: SOURCED
dimensional_check: BALANCES
tags:
  - canon/formula
  - source/sourced
  - dim/balances
  - shape/law
  - kind/law
---

# Thrust-to-weight required for level flight at a given speed

**Canonical form**

```
T/W = q * C_D0 / (W/S) + k * (W/S) / q
```

**Produces** [[thrust-to-weight-required-cruise]]  ·  **from** [[dynamic-pressure]] · [[zero-lift-drag-coefficient]] · [[wing-loading]] · [[induced-drag-factor]]

**Kind: a law.** A closed-form relation. Approval asks for its **source** and its **validity at 0.5–15 kg**.

ℹ️ **Reclassified.** Was recorded as a second producer of another quantity. It produces its own: a design limit, not the actual value.

**Dimensional check.** 🟢 balances

**Source.** 🟢 SOURCED

> Sadraey, Aircraft Design: A Systems Engineering Approach, §4.3.3.1, Eq. 4.47 (boxed): (T/W)_Vmax = (1/sigma)*[rho_0*V_max^2*C_Do/(2*(W/S)) + (2K/(rho*V_max^2))*(W/S)], compactly Eq. 4.48: T/W = a*V^2/(W/S) + (b/V^2)*(W/S). Substituting q = 0.5*rho*V^2 at sigma = 1 reproduces the proposal exactly.

**The source writes it as**

```
Sadraey writes it against V_max with the density ratio sigma carried explicitly for altitude; the proposal writes it against q. Algebraically identical. Sadraey notes the structure: a parasite term decreasing in W/S plus an induced term increasing in W/S, with a minimum in between.
```

**Validity at 0.5–15 kg.** Valid - but this is the JET form. Sadraey gives the prop-driven counterpart at §4.3.3.2, Eq. 4.56, in W/P with V_max CUBED in the parasite term, and warns explicitly that "a 10% increase in V_max requires roughly 33% more power" and that this is "a key driver of why prop aircraft cruise much closer to (L/D)max speed than jets do". For an electric RC model the V^3 power form is the sourced one and carries different sensitivity. Using the T/W form is not wrong physics, but it hides the cubic sensitivity that dominates RC powertrain sizing.

## Implementations (1)

| node | claimed | verified | deviation |
|---|---|---|---|
| [[tw_cruise_constraint]] | SPECIALISED | 🟢 | Sea-level only: the 1/sigma density-ratio factor of the general form is dropped, so the co |

## Approval

- [ ] **Source** — citation real, or absence stated and adopted on the maintainer's authority
- [ ] **Scale** — holds at 0.5–15 kg, or the limitation is written down (ADR 0023)
- [ ] **Dimensions** — the check balances
- [ ] **Implementations** — all agree, or each deviation is declared and justified
- [ ] **Preconditions** — every binding condition holds, or the violation is ticketed
- [ ] **Inputs approved** — no formula is approvable before its inputs are

> While `status: draft` this entry **cites nothing and decides nothing**.

