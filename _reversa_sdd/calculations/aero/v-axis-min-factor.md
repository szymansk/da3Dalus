---
name: v-axis-min-factor
kind: constant
unit: -
cluster: aero-spanwise
user_visible: false
source_status: NO_SOURCE_FOUND
---

# Lower axis-bound factor

**Definition.** Fraction of the lowest V_stall used as the chart's left edge.

**Value.** `0.7`

**Formula — as the code writes it.**

```
0.7 * min(v_stall_values)
```

**Inputs.** — *(leaf: a constant or an external input)*

**Produced by.** `app/services/analysis_service.py:556` — `_compute_speed_polar`

**Consumed by.**

- in this graph: [[v-axis-min|Speed-polar X-axis lower bound]]

**Source.** 🔴 NO SOURCE FOUND

> 0.7 is a plotting margin. Documented in aeroanalysisschema.py:620 but with no literature attribution.
> No citable source was found. **This is recorded, not filled in.** The value is
> in the code without an attributable origin.

**⚠️ Anomaly.** Magic display factor; documented in the schema description (aeroanalysisschema.py:620) but NO_SOURCE_FOUND.

🟡 *Reported by the extraction pass, not independently verified. Do not cite as a
defect until confirmed against the code.*

---
*Cluster [[_index-aero-spanwise|aero-spanwise]] · generated from the 2026-08-18 extraction.*
