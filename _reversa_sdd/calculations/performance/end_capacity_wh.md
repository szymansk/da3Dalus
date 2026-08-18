---
name: end_capacity_wh
symbol: E_bat
kind: parameter
unit: Wh
cluster: perf-envelope
user_visible: true
source_status: SOURCED
code_audit: CONFIRMED
node_class: unclassified-parameter
tags:
  - cluster/perf-envelope
  - class/unclassified-parameter
  - source/sourced
  - surface/user-visible
  - audit/confirmed
---

# Battery capacity

**Definition.** Usable pack energy; 0.0 in the DB means 'not configured' and maps to None.

⚪ **Unclassified parameter.** Not yet decided whether this is a user input or an internal tuning value.

**Value.** `default 0.0 -> None`

**Formula — as the code writes it.**

```
capacity_val = float(_capacity_raw) if (_capacity_raw is not None and _capacity_raw > 0.0) else None
```

**Inputs.** — *(leaf: a constant or an external input)*

**Produced by.** `app/services/endurance_service.py:543` — `compute_endurance_for_aeroplane`

🟢 **Verified against the code** — an independent reviewer read this line and confirmed the formula, unit and value (2026-08-18 audit).

**Consumed by.**

- in this graph: `Capacity-implied battery mass` · `Flight time at V_md` · `Maximum endurance`  
  *(these are backlinks — open the Backlinks pane to navigate them)*

**Source.** 🟢 SOURCED

> User-supplied pack energy; 0.0 correctly mapped to None ('not configured') rather than treated as a real zero.
>
> — via `rc`

---
*Cluster [[_index-perf-envelope|perf-envelope]] · generated from the 2026-08-18 extraction.*
