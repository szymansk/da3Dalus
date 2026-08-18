---
name: fe_rho_default
symbol: rho
kind: constant
unit: kg/m^3
cluster: perf-envelope
user_visible: false
source_status: SOURCED
node_class: physical-constant
tags:
  - cluster/perf-envelope
  - class/physical-constant
  - source/sourced
  - flag/anomaly
  - flag/divergence
  - flag/physical
---

# Default air density (flight envelope)

**Definition.** Sea-level ISA density hardcoded as a bare default in three signatures, never a named constant.

**Physical constant.** A value of nature. It must be identical everywhere it appears — a second definition is a defect by construction, not a judgement call.
*Identified as: sea-level air density.*

**Value.** `1.225`

**Formula — as the code writes it.**

```
rho: float = 1.225
```

**Inputs.** — *(leaf: a constant or an external input)*

**Produced by.** `app/services/flight_envelope_service.py:74` — `_compute_mu_g / _build_gust_lines / compute_vn_curve default arg`

**Consumed by.**

- in this graph: `Gust load-factor increment` · `Gust mass ratio` · `Dynamic pressure` · `Stall speed (1 g)`  
  *(these are backlinks — open the Backlinks pane to navigate them)*

**Source.** 🟢 SOURCED

> ISO 2533:1975 International Standard Atmosphere, sea level; identical in ICAO Doc 7488 Manual of the ICAO Standard Atmosphere.
>
> — via `scholz`

**The source states it as.**

```
rho_0 = 1.225 kg/m^3
```

**⚠️ Divergence from the source.** Value is correct and universal; the defect is purely structural — a bare literal at fe:74/166/288 while endurance_service names the same number RHO_SEA_LEVEL. No altitude parameter exists anywhere, so every result in this cluster is sea-level-only and nothing in the API says so.

🟡 *Reported by the extraction pass, not independently verified.*

**⚠️ Anomaly.** Magic literal repeated at lines 74, 166 and 288; endurance_service names the same value RHO_SEA_LEVEL. No single authority for rho.

🟡 *Reported by the extraction pass, not independently verified. Do not cite as a
defect until confirmed against the code.*

---
*Cluster [[_index-perf-envelope|perf-envelope]] · generated from the 2026-08-18 extraction.*
