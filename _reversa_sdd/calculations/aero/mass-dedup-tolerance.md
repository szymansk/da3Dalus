---
name: mass-dedup-tolerance
kind: constant
unit: kg
cluster: aero-spanwise
user_visible: false
source_status: NO_SOURCE_FOUND
---

# Mass de-duplication tolerance

**Definition.** Tolerance for treating a requested mass as identical to an already-collected one.

**Value.** `1e-9`

**Formula — as the code writes it.**

```
tol = 1e-9
```

**Inputs.** — *(leaf: a constant or an external input)*

**Produced by.** `app/services/analysis_service.py:470` — `_compute_speed_polar`

**Consumed by.**

- in this graph: [[mass-set|Speed-polar mass set]]
- outside it: `speed-polar-is-base`

**Source.** 🔴 NO SOURCE FOUND

> Float comparison tolerance; no domain source.
> No citable source was found. **This is recorded, not filled in.** The value is
> in the code without an attributable origin.

---
*Cluster [[_index-aero-spanwise|aero-spanwise]] · generated from the 2026-08-18 extraction.*
