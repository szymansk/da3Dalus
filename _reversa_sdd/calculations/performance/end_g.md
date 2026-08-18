---
name: end_g
symbol: g
kind: constant
unit: m/s^2
cluster: perf-envelope
user_visible: false
source_status: SOURCED
code_audit: CONFIRMED
node_class: physical-constant
tags:
  - cluster/perf-envelope
  - class/physical-constant
  - source/sourced
  - audit/confirmed
  - flag/anomaly
  - flag/divergence
  - flag/physical
---

# Gravitational acceleration (endurance)

**Definition.** Standard gravity used for the level-flight lift coefficient.

**Physical constant.** A value of nature. It must be identical everywhere it appears — a second definition is a defect by construction, not a judgement call.
*Identified as: gravity.*

**Value.** `9.80665`

**Formula — as the code writes it.**

```
G = 9.80665  # m/s²
```

**Inputs.** — *(leaf: a constant or an external input)*

**Produced by.** `app/services/endurance_service.py:49` — `G`

🟢 **Verified against the code** — an independent reviewer read this line and confirmed the formula, unit and value (2026-08-18 audit).

**Consumed by.**

- in this graph: `Level-flight lift coefficient`  
  *(these are backlinks — open the Backlinks pane to navigate them)*
- outside it: `airfoil_low_re_service.py` · `powertrain_sizing_service.py`

**Source.** 🟢 SOURCED

> Standard gravity, 3rd CGPM (1901); ISO 80000-3. This is the correct value of the three in the cluster.
>
> — via `scholz`

**The source states it as.**

```
g_n = 9.80665 m/s^2
```

**⚠️ Divergence from the source.** airfoil_low_re_service duplicates the literal with a 'keep in sync' comment rather than importing it — a comment where an import belongs.

🟡 *Reported by the extraction pass, not independently verified.*

**⚠️ Anomaly.** Differs from flight_envelope_service.GRAVITY (9.81) and the inline 9.81 in mission_kpi_service. airfoil_low_re_service duplicates the literal with the comment 'keep in sync' rather than importing it.

🟡 *Reported by the extraction pass, not independently verified. Do not cite as a
defect until confirmed against the code.*

---
*Cluster [[_index-perf-envelope|perf-envelope]] · generated from the 2026-08-18 extraction.*
