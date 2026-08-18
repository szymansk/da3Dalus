---
name: prt-e-oswald-band
symbol: e
kind: quantity
unit: dimensionless
cluster: aero-polars
user_visible: true
source_status: SOURCED
node_class: derived
tags:
  - cluster/aero-polars
  - class/derived
  - source/sourced
  - surface/user-visible
  - flag/divergence
---

# Band Oswald efficiency

**Definition.** Span efficiency inverted from the fitted band slope k using the aspect ratio.

**Derived quantity.** Computed from the inputs below.

**Formula — as the code writes it.**

```
e_oswald = 1.0 / (math.pi * ar * k_fit)
```

**Inputs.**

- [[prt-k-fit|Band induced-drag factor k]]

**Produced by.** `app/services/polar_re_table_service.py:282` — `_fit_band_with_ar`

**Consumed by.**

- in this graph: `e_oswald at query velocity (constant mean)` · `Oswald physical-range guard (0.4, 1.0]`  
  *(these are backlinks — open the Backlinks pane to navigate them)*
- outside it: `PolarReTableRow.e_oswald` · `lookup_e_oswald_at_v:203`

**Source.** 🟢 SOURCED

> Anderson 6e §6.7.2 — Oswald factor defined by C_D = C_D0 + C_L²/(π ẽ AR); inverting the fitted slope gives ẽ = 1/(π AR k)
>
> — via `aerodynamics-expert`

**The source states it as.**

```
ẽ = 1/(π AR k)
```

**⚠️ Divergence from the source.** Algebraically the exact inverse of the source definition. Note Anderson distinguishes Oswald ẽ (0.70–0.85) from span efficiency e (0.9–1.0); the code's name 'e_oswald' is the correct one for this quantity.

🟡 *Reported by the extraction pass, not independently verified.*

**Cited in the code itself.** `e_oswald = 1.0 / (math.pi * ar * k_fit)`

---
*Cluster [[_index-aero-polars|aero-polars]] · generated from the 2026-08-18 extraction.*
