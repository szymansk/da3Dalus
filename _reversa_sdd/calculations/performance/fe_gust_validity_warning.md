---
name: fe_gust_validity_warning
symbol: mu_g out of range
kind: quantity
unit: -
cluster: perf-envelope
user_visible: true
source_status: PARTIAL
node_class: derived
tags:
  - cluster/perf-envelope
  - class/derived
  - source/partial
  - surface/user-visible
  - flag/divergence
---

# Pratt validity warning

**Definition.** Structured warning emitted when the gust mass ratio leaves the Pratt-validated band.

**Derived quantity.** Computed from the inputs below.

**Formula — as the code writes it.**

```
if mu_g < _MU_G_MIN: ... elif mu_g > _MU_G_MAX: ...
```

**Inputs.**

- [[fe_mu_g|Gust mass ratio]]
- [[mu_g_min|Pratt-Walker validity lower bound]]  — *⊣ limit*
- [[mu_g_max|Pratt-Walker validity upper bound]]  — *⊣ limit*

**Produced by.** `app/services/flight_envelope_service.py:199` — `_build_gust_lines`

**Consumed by.**

- outside it: `VnDiagram.tsx validityWarnings banner`

**Source.** 🟡 PARTIAL

> The engineering claim in the message — 'RC/UAV with low W/S frequently produce mu_g < 3, making gust loads potentially optimistic (gh-497)' — is sound and confirmed: at RC W/S of 30-120 N/m^2, mu_g lands at 1-4. The numeric band [3, 200] it enforces is NOT attributable to NACA TN 2964 or FAR 25.341.
>
> — via `scholz`

**⚠️ Divergence from the source.** Best-intentioned item in the file and still mis-provenanced: correct instinct, invented bounds, regulator-flavoured citation. Two fixes — (1) relabel the band as an internal engineering judgement; (2) the message says gust loads are 'potentially optimistic' at low mu_g, but the dominant RC error runs the other way (linear CL_alpha extrapolated 4x past stall makes them strongly PESSIMISTIC). Both effects are real and they oppose; the warning names only one.

🟡 *Reported by the extraction pass, not independently verified.*

**Cited in the code itself.** `"RC/UAV with low W/S frequently produce μ_g < 3, making gust loads potentially optimistic (gh-497)."`

---
*Cluster [[_index-perf-envelope|perf-envelope]] · generated from the 2026-08-18 extraction.*
