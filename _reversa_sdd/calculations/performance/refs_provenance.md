---
name: refs_provenance
kind: quantity
unit: dimensionless
cluster: perf-oppoints
user_visible: true
source_status: NO_SOURCE_FOUND
node_class: derived
tags:
  - cluster/perf-oppoints
  - class/derived
  - source/no-source-found
  - surface/user-visible
  - flag/divergence
---

# Reference-speed provenance

**Definition.** Marks whether the stall speeds came from a computed polar or from the cold-start estimate.

**Derived quantity.** Computed from the inputs below.

**Formula — as the code writes it.**

```
provenance = "cold_start"  # gh-535: caller must stamp STALE_NO_POLAR / provenance = "polar"
```

**Inputs.**

- [[vs_clean|Clean stall speed reference]]

**Produced by.** `app/services/operating_point_generator_service.py:351` — `_estimate_reference_speeds`

**Consumed by.**

- in this graph: `STALE_NO_POLAR warning`  
  *(these are backlinks — open the Backlinks pane to navigate them)*
- outside it: `app/services/operating_point_generator_service.py:372 (_stamp_stale_no_polar)`

**Source.** 🔴 NO SOURCE FOUND

> No citable source was found. **This is recorded, not filled in.** The value is
> in the code without an attributable origin.

**⚠️ Divergence from the source.** Data-lineage metadata. No engineering source applies; correctly an app concern.

🟡 *Reported by the extraction pass, not independently verified.*

---
*Cluster [[_index-perf-oppoints|perf-oppoints]] · generated from the 2026-08-18 extraction.*
