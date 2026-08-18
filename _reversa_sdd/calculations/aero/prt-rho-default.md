---
name: prt-rho-default
symbol: ρ
kind: constant
unit: kg/m³
cluster: aero-polars
user_visible: false
source_status: SOURCED
node_class: physical-constant
tags:
  - cluster/aero-polars
  - class/physical-constant
  - source/sourced
  - flag/anomaly
  - flag/divergence
  - flag/physical
---

# Default air density (ISA SL)

**Definition.** Default density for Re labels and band fits.

**Physical constant.** A value of nature. It must be identical everywhere it appears — a second definition is a defect by construction, not a judgement call.
*Identified as: sea-level air density.*

**Value.** `1.225`

**Formula — as the code writes it.**

```
rho: float = 1.225
```

**Inputs.** — *(leaf: a constant or an external input)*

**Produced by.** `app/services/polar_re_table_service.py:70` — `_reynolds_number_from_v (default arg)`

**Consumed by.**

- in this graph: `Aircraft-level Reynolds number (V-band label)`  
  *(these are backlinks — open the Backlinks pane to navigate them)*
- outside it: `lookup_cd0_at_v:96` · `assumption_compute_service.py:420 (rho=1.225)`

**Source.** 🟢 SOURCED

> ICAO Standard Atmosphere / ISO 2533:1975, sea level; also Anderson 6e App. A
>
> — via `aerodynamics-expert`

**The source states it as.**

```
ρ_SL = 1.225 kg/m³
```

**⚠️ Divergence from the source.** Exact match. Three separate producers of the same constant (here, airfoil_low_re_service.RHO, suitability_service._RHO) — ADR 0022.

🟡 *Reported by the extraction pass, not independently verified.*

**⚠️ Anomaly.** Same numeric constant is re-declared in airfoil_low_re_service.RHO:40 and suitability_service._RHO:74 — three producers of ISA-SL density.

🟡 *Reported by the extraction pass, not independently verified. Do not cite as a
defect until confirmed against the code.*

**Cited in the code itself.** `rho: float = 1.225,`

---
*Cluster [[_index-aero-polars|aero-polars]] · generated from the 2026-08-18 extraction.*
