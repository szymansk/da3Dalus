---
name: wing_loading_fl
symbol: W/S
kind: quantity
unit: N/m^2
cluster: perf-matching
user_visible: false
source_status: SOURCED
---

# Wing loading (field length)

**Definition.** Weight per unit wing reference area driving both ground rolls.

**Formula — as the code writes it.**

```
wing_loading = weight_n / s_ref_m2
```

**Inputs.** [[weight_n_fl|Aircraft weight]]

**Produced by.** `app/services/field_length_service.py:200` — `_compute_s_to_ground`

**Consumed by.**

- in this graph: [[s_ldg_ground|Landing ground roll]] · [[s_to_ground|Takeoff ground roll]]
- outside it: `s_to_ground:203` · `s_ldg_ground:264`

**Source.** 🟢 SOURCED

> Sadraey 2013 §4.3.1 (matching plot horizontal axis) and Scholz 05_PreliminarySizing §5.1-5.2: W/S is the primary sizing variable, W in N, S in m^2.
>
> — via `aircraft-design-scholz`

**The source states it as.**

```
W/S [N/m^2]
```

**Cited in the code itself.** `# W/S [N/m²]`

---
*Cluster [[_index-perf-matching|perf-matching]] · generated from the 2026-08-18 extraction.*
