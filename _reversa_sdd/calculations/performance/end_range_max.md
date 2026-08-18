---
name: end_range_max
symbol: R_max
kind: quantity
unit: m
cluster: perf-envelope
user_visible: true
source_status: PARTIAL
code_audit: CONFIRMED
node_class: derived
tags:
  - cluster/perf-envelope
  - class/derived
  - source/partial
  - surface/user-visible
  - audit/confirmed
  - flag/divergence
---

# Maximum range

**Definition.** Still-air distance on a full pack flown at minimum-drag speed.

**Derived quantity.** Computed from the inputs below.

**Formula — as the code writes it.**

```
range_max_m = t_at_vmd_s * float(v_md)
```

**Inputs.**

- [[end_t_at_vmd|Flight time at V_md]]

**Produced by.** `app/services/endurance_service.py:412` — `compute_endurance`

🟢 **Verified against the code** — an independent reviewer read this line and confirmed the formula, unit and value (2026-08-18 audit).

**Consumed by.**

- outside it: `EnduranceCard.tsx` · `metricsAdapters.toPowertrainItems` · `GET /aeroplanes/{id}/endurance`

**Source.** 🟡 PARTIAL

> Traub, Journal of Aircraft 48(2), 2011, pp. 703-707. Flying at V_md for maximum range at constant mass is correct for an electric aircraft (mass does not fall with discharge — module assumption 2, correctly stated).
>
> — via `scholz`

**The source states it as.**

```
R = t(V_md) * V_md
```

**⚠️ Divergence from the source.** Inherits the nameplate-capacity optimism. Still-air only, sea-level only; neither is stated in the API description.

🟡 *Reported by the extraction pass, not independently verified.*

**Cited in the code itself.** `"range(V_md) = t_endurance(V_md) × V_md"; Traub 2011 in module header`

---
*Cluster [[_index-perf-envelope|perf-envelope]] · generated from the 2026-08-18 extraction.*
