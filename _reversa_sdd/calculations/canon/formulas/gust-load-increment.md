---
canon: gust-load-increment
entry: formula
kind: law
shape: law
status: draft
output: gust-load-increment
source_status: SOURCED
dimensional_check: MISMATCH
tags:
  - canon/formula
  - source/sourced
  - dim/mismatch
  - shape/law
  - kind/law
  - status/draft
---

# Load-factor increment from a discrete vertical gust

**Canonical form**

```
delta_n = 0.5 * rho * V * C_Lalpha * U_de * K_g / (W/S)
```

**Produces** [[gust-load-increment]]  ·  **from** [[air-density]] · [[flight-speed]] · [[lift-curve-slope]] · [[gust-velocity]] · [[gust-alleviation-factor]] · [[wing-loading]]

**Kind: a law.** A closed-form relation. Approval asks for its **source** and its **validity at 0.5–15 kg**.

**Dimensional check.** 🔴 does not balance

> right-hand side → `1 / ANG`, declared `1`. **Resolve before approval.**

**Source.** 🟢 SOURCED

> 14 CFR 23.341(c): n = 1 + K_g*U_de*V*a/(498*W/S), with V in knots equivalent airspeed, W/S in psf, U_de in ft/s, a per radian; 498 is the unit-conversion constant embedding rho_0/2. The proposal's delta_n = 0.5*rho*V*C_Lalpha*U_de*K_g/(W/S) is the SI form of the same relation. Un-alleviated core independently in Scholz, 07_WingDesign §7.3: n_alpha = dn/dalpha = 0.5*rho*v^2*C_L,alpha/(W/S).

**The source writes it as**

```
Two substantive differences from the proposal. (1) The regulation's V is EQUIVALENT airspeed and the density implied by the 498 constant is SEA-LEVEL rho_0 - using local rho together with true airspeed double-counts altitude. (2) The regulation gives the total n = 1 + delta_n; the proposal returns the increment alone.
```

**Validity at 0.5–15 kg.** Inherits every caveat of gust-mass-ratio, gust-alleviation-factor and gust-velocity-schedule. Scholz §7.3 gives the qualitative direction and it is the right one: load factor per gust is inversely proportional to wing loading, so a low-wing-loading RC model is the MOST gust-sensitive case - Scholz notes small GA aircraft at 50-100 lbf/ft^2 already require "continuous pilot attention in turbulent conditions". The direction is sourced and correct; the magnitude at 0.5-15 kg is an extrapolation of a 1933-1950 transport fit and must be labelled as such.

## Implementations (1)

| node | claimed | verified | deviation |
|---|---|---|---|
| [[fe_delta_n]] | EXACT | 🟢 |  |

## Approval

- [ ] **Source** — citation real, or absence stated and adopted on the maintainer's authority
- [ ] **Scale** — holds at 0.5–15 kg, or the limitation is written down (ADR 0023)
- [ ] **Dimensions** — the check balances
- [ ] **Implementations** — all agree, or each deviation is declared and justified
- [ ] **Preconditions** — every binding condition holds, or the violation is ticketed
- [ ] **Inputs approved** — no formula is approvable before its inputs are

> While `status: draft` this entry **cites nothing and decides nothing**.

