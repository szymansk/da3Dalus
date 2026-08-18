---
name: end_capacity_wh
symbol: E_bat
kind: parameter
unit: Wh
cluster: perf-envelope
user_visible: true
source_status: SOURCED
---

# Battery capacity

**Definition.** Usable pack energy; 0.0 in the DB means 'not configured' and maps to None.

**Value.** `default 0.0 -> None`

**Formula — as the code writes it.**

```
capacity_val = float(_capacity_raw) if (_capacity_raw is not None and _capacity_raw > 0.0) else None
```

**Inputs.** — *(leaf: a constant or an external input)*

**Produced by.** `app/services/endurance_service.py:543` — `compute_endurance_for_aeroplane`

**Consumed by.**

- in this graph: [[end_battery_mass_predicted|Capacity-implied battery mass]] · [[end_t_at_vmd|Flight time at V_md]] · [[end_t_endurance_max|Maximum endurance]]

**Source.** 🟢 SOURCED

> User-supplied pack energy; 0.0 correctly mapped to None ('not configured') rather than treated as a real zero.
>
> — via `rc`

---
*Cluster [[_index-perf-envelope|perf-envelope]] · generated from the 2026-08-18 extraction.*
