---
name: vs_ldg
symbol: V_s0
kind: quantity
unit: m/s
cluster: perf-oppoints
user_visible: true
source_status: PARTIAL
code_audit: CONFIRMED
node_class: derived
tags:
  - cluster/perf-oppoints
  - class/derived
  - source/partial
  - surface/user-visible
  - audit/confirmed
  - flag/divergence
---

# Landing-config stall speed reference

**Definition.** Landing-configuration stall speed, falling back to the clean value.

**Derived quantity.** Computed from the inputs below.

**Formula — as the code writes it.**

```
vs_ldg = _pick("v_s0_mps") or vs_clean ... "vs_ldg": max(2.0, vs_ldg)
```

**Inputs.**

- [[vs_clean|Clean stall speed reference]]

**Produced by.** `app/services/operating_point_generator_service.py:356` — `_estimate_reference_speeds`

🟢 **Verified against the code** — an independent reviewer read this line and confirmed the formula, unit and value (2026-08-18 audit).

**Consumed by.**

- in this graph: `approach_landing target speed` · `stall_with_flaps target speed`  
  *(these are backlinks — open the Backlinks pane to navigate them)*
- outside it: `app/services/operating_point_generator_service.py:403 (approach)` · `app/services/operating_point_generator_service.py:483 (stall_with_flaps)`

**Source.** 🟡 PARTIAL

> Scholz 05_PreliminarySizing §5.1 (CS 25.125, landing configuration, CL_max,L) — V_S0 is the stall speed in the landing configuration
>
> — via `aircraft-design-scholz`

**⚠️ Divergence from the source.** Standard quantity. Same silent clean-value fallback as vs_to.

🟡 *Reported by the extraction pass, not independently verified.*

---
*Cluster [[_index-perf-oppoints|perf-oppoints]] · generated from the 2026-08-18 extraction.*
