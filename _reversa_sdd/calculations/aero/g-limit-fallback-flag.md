---
name: g-limit-fallback-flag
kind: quantity
unit: -
cluster: aero-spanwise
user_visible: true
source_status: NO_SOURCE_FOUND
node_class: derived
tags:
  - cluster/aero-spanwise
  - class/derived
  - source/no-source-found
  - surface/user-visible
---

# g_limit fallback flag

**Definition.** Boolean telling the spar service that the default load factor was substituted.

**Derived quantity.** Computed from the inputs below.

**Formula — as the code writes it.**

```
g_limit_fallback = True / g_limit_fallback = False
```

**Inputs.**

- [[g-limit-effective|Effective manoeuvre load factor]]  — *⤵ fallback*

**Produced by.** `app/services/analysis_service.py:2161` — `_compute_spar_sizing_for_surfaces`

**Consumed by.**

- outside it: `compute_spar_sizing`

**Source.** 🔴 NO SOURCE FOUND

> Plumbing boolean; no domain source. It is, however, the one ADR-0020-compliant fallback signal in this cluster — the flag reaches compute_spar_sizing.
> No citable source was found. **This is recorded, not filled in.** The value is
> in the code without an attributable origin.

---
*Cluster [[_index-aero-spanwise|aero-spanwise]] · generated from the 2026-08-18 extraction.*
