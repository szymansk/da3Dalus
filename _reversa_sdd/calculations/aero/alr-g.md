---
name: alr-g
symbol: g
kind: constant
unit: m/s²
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
  - flag/anomaly
  - flag/divergence
  - flag/physical
---

# Standard gravity

**Definition.** Gravitational acceleration used for level-flight CL.

**Physical constant.** A value of nature. It must be identical everywhere it appears — a second definition is a defect by construction, not a judgement call.
*Identified as: gravity.*

**Value.** `9.80665`

**Formula — as the code writes it.**

```
G = 9.80665  # m/s²
```

**Inputs.** — *(leaf: a constant or an external input)*

**Produced by.** `app/services/airfoil_low_re_service.py:39` — `G`

🟢 **Verified against the code** — an independent reviewer read this line and confirmed the formula, unit and value (2026-08-18 audit).

**Consumed by.**

- in this graph: `Level-flight lift coefficient`  
  *(these are backlinks — open the Backlinks pane to navigate them)*
- outside it: `_level_flight_cl:707`

**Source.** 🟢 SOURCED

> Standard gravity g_n = 9.80665 m/s², 3rd CGPM (1901); ISO 80000-3

**The source states it as.**

```
g_n = 9.80665 m/s²
```

**⚠️ Divergence from the source.** Exact match. Duplicated by hand from endurance_service ('keep in sync') rather than imported — ADR 0022.

🟡 *Reported by the extraction pass, not independently verified.*

**⚠️ Anomaly.** Comment says 'reuse values from endurance_service — keep in sync' — a manually-synchronised duplicate rather than one source.

🟡 *Reported by the extraction pass, not independently verified. Do not cite as a
defect until confirmed against the code.*

**Cited in the code itself.** `G = 9.80665  # m/s²`

---
*Cluster [[_index-aero-polars|aero-polars]] · generated from the 2026-08-18 extraction.*
