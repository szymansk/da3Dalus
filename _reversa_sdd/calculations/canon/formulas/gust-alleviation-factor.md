---
canon: gust-alleviation-factor
kind: formula
status: draft
output: gust-alleviation-factor
source_status: SOURCED
dimensional_check: BALANCES
tags:
  - canon/formula
  - source/sourced
  - dim/balances
---

# Pratt-Walker gust alleviation factor

**Canonical form**

```
K_g = 0.88 * mu_g / (5.3 + mu_g)
```

**Produces** [[gust-alleviation-factor]]  ·  **from** [[gust-mass-ratio]]

**Dimensional check.** 🟢 balances

**Source.** 🟢 SOURCED

> 14 CFR 23.341(c) verbatim: "Kg = 0.88*mu_g/(5.3 + mu_g) = gust alleviation factor". Identical in 14 CFR 25.341 / CS-25.341(a)(2). Original derivation: W. H. Pratt, NACA Technical Note 2964 (1953), and Pratt & Walker, NACA Report 1206 (1954), "A revised gust-load formula and a re-evaluation of V-G data taken on civil transport airplanes from 1933 to 1950". The factor is based on a one-minus-cosine gust shape and presented as a function of the mass-ratio parameter.

**The source writes it as**

```
Identical to the proposal.
```

**Validity at 0.5–15 kg.** The coefficients 0.88 and 5.3 are a regression fit to V-G records from CIVIL TRANSPORT AIRPLANES flown 1933-1950. This is exactly the ADR 0023 pattern - a constant that is standard in transport-category literature and has never been validated at 0.5-15 kg. Behaviourally it degrades gracefully rather than catastrophically: at the small mu_g typical of a model, K_g -> 0.166*mu_g, staying positive and monotonic, so no clamp is needed. But the number must be presented as an extrapolated transport-category alleviation factor, not as an RC result. Constant provenance must be recorded with the source per ADR 0023.

## Implementations (1)

| node | claimed | verified | deviation |
|---|---|---|---|
| [[fe_k_g]] | EXACT | 🟢 |  |

## Approval

- [ ] **Source** — citation real, or absence stated and adopted on the maintainer's authority
- [ ] **Scale** — holds at 0.5–15 kg, or the limitation is written down (ADR 0023)
- [ ] **Dimensions** — the check balances
- [ ] **Implementations** — all agree, or each deviation is declared and justified
- [ ] **Inputs approved** — no formula is approvable before its inputs are

> While `status: draft` this entry **cites nothing and decides nothing**.

