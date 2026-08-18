---
canon: gust-mass-ratio
entry: formula
kind: law
shape: law
status: draft
output: gust-mass-ratio
source_status: SOURCED
dimensional_check: MISMATCH
tags:
  - canon/formula
  - source/sourced
  - dim/mismatch
  - shape/law
  - kind/law
---

# Gust mass ratio

**Canonical form**

```
mu_g = 2 * (W/S) / (rho * c_bar * C_Lalpha * g)
```

**Produces** [[gust-mass-ratio]]  ·  **from** [[wing-loading]] · [[air-density]] · [[mean-geometric-chord]] · [[lift-curve-slope]] · [[gravity]]

**Kind: a law.** A closed-form relation. Approval asks for its **source** and its **validity at 0.5–15 kg**.

**Dimensional check.** 🔴 does not balance

> right-hand side → `ANG`, declared `1`. **Resolve before approval.**

**Source.** 🟢 SOURCED

> 14 CFR 23.341(c) (FAR Part 23, Gust load factors), symbol definition verbatim: "mu_g = 2(W/S)/(rho*C*a*g) = airplane mass ratio", with C = mean geometric chord (ft), a = slope of the airplane normal force coefficient curve C_NA per radian, W/S = wing loading (psf), g = acceleration due to gravity. Identical definition in 14 CFR 25.341 / CS-25.341.

**The source writes it as**

```
The regulation uses a = slope of the AIRPLANE normal-force coefficient curve, and adds that the WING lift-curve slope may be used when the gust loads are being applied to the wing only, with horizontal-tail loads treated separately. Otherwise identical to the proposal.
```

**Validity at 0.5–15 kg.** This is the sharpest ADR 0023 case in the register. mu_g scales linearly with W/S. Scholz (07_WingDesign §7.3) gives transport wing loadings of 1700-3600 N/m^2, against roughly 50-150 N/m^2 for a 0.5-15 kg model - so mu_g for an RC model lands one to two orders of magnitude below the range the Pratt correlation was fitted over. The quantity is still computable and still means what it means, but everything downstream of it (K_g, delta_n) is an extrapolation, not a certified prediction. Report it with that label.

## Implementations (1)

| node | claimed | verified | deviation |
|---|---|---|---|
| [[fe_mu_g]] | EXACT | 🟢 |  |

## Approval

- [ ] **Source** — citation real, or absence stated and adopted on the maintainer's authority
- [ ] **Scale** — holds at 0.5–15 kg, or the limitation is written down (ADR 0023)
- [ ] **Dimensions** — the check balances
- [ ] **Implementations** — all agree, or each deviation is declared and justified
- [ ] **Preconditions** — every binding condition holds, or the violation is ticketed
- [ ] **Inputs approved** — no formula is approvable before its inputs are

> While `status: draft` this entry **cites nothing and decides nothing**.

