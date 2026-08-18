---
name: mass-dedup-tolerance
kind: constant
unit: kg
cluster: aero-spanwise
user_visible: false
source_status: NO_SOURCE_FOUND
code_audit: CONFIRMED
node_class: numerical-tolerance
tags:
  - cluster/aero-spanwise
  - class/numerical-tolerance
  - source/no-source-found
  - audit/confirmed
---

# Mass de-duplication tolerance

**Definition.** Tolerance for treating a requested mass as identical to an already-collected one.

**Numerical tolerance.** A solver or comparison epsilon, not a domain value. ADR 0023 does not apply.

**Value.** `1e-9`

**Formula — as the code writes it.**

```
tol = 1e-9
```

**Inputs.** — *(leaf: a constant or an external input)*

**Produced by.** `app/services/analysis_service.py:470` — `_compute_speed_polar`

🟢 **Verified against the code** — an independent reviewer read this line and confirmed the formula, unit and value (2026-08-18 audit).

**Consumed by.**

- in this graph: `Speed-polar mass set`  
  *(these are backlinks — open the Backlinks pane to navigate them)*
- outside it: `speed-polar-is-base`

**Source.** 🔴 NO SOURCE FOUND

> Float comparison tolerance; no domain source.
> No citable source was found. **This is recorded, not filled in.** The value is
> in the code without an attributable origin.

---
*Cluster [[_index-aero-spanwise|aero-spanwise]] · generated from the 2026-08-18 extraction.*
