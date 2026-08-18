---
name: sui-rho
symbol: ρ
kind: constant
unit: kg/m³
cluster: aero-polars
user_visible: false
source_status: SOURCED
code_audit: CONFIRMED
node_class: physical-constant
tags:
  - cluster/aero-polars
  - class/physical-constant
  - source/sourced
  - audit/confirmed
  - flag/divergence
  - flag/physical
---

# ISA sea-level density (suitability)

**Definition.** Density used for the root/tip Reynolds computation.

**Physical constant.** A value of nature. It must be identical everywhere it appears — a second definition is a defect by construction, not a judgement call.
*Identified as: sea-level air density.*

**Value.** `1.225`

**Formula — as the code writes it.**

```
_RHO = 1.225  # kg/m³
```

**Inputs.** — *(leaf: a constant or an external input)*

**Produced by.** `app/services/suitability_service.py:74` — `_RHO`

🟢 **Verified against the code** — an independent reviewer read this line and confirmed the formula, unit and value (2026-08-18 audit).

**Consumed by.**

- in this graph: `Root-chord Reynolds number`  
  *(these are backlinks — open the Backlinks pane to navigate them)*
- outside it: `_compute_re:121`

**Source.** 🟢 SOURCED

> ICAO Standard Atmosphere / ISO 2533:1975, sea level

**The source states it as.**

```
ρ_SL = 1.225 kg/m³
```

**⚠️ Divergence from the source.** Exact; third of three declarations of this constant (ADR 0022).

🟡 *Reported by the extraction pass, not independently verified.*

**Cited in the code itself.** `_RHO = 1.225  # kg/m³`

---
*Cluster [[_index-aero-polars|aero-polars]] · generated from the 2026-08-18 extraction.*
