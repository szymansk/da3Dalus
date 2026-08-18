---
name: i-min-sink
kind: quantity
unit: index
cluster: aero-spanwise
user_visible: false
source_status: PARTIAL
code_audit: CONFIRMED
node_class: derived
tags:
  - cluster/aero-spanwise
  - class/derived
  - source/partial
  - audit/confirmed
  - flag/divergence
---

# Minimum-sink index

**Definition.** Index of the lowest sink rate on the sorted curve.

**Derived quantity.** Computed from the inputs below.

**Formula — as the code writes it.**

```
i_min_sink = int(np.argmin(w))
```

**Inputs.**

- [[speed-polar-w|Sink rate]]

**Produced by.** `app/services/analysis_service.py:521` — `_compute_speed_polar`

🟢 **Verified against the code** — an independent reviewer read this line and confirmed the formula, unit and value (2026-08-18 audit).

**Consumed by.**

- in this graph: `Alpha at minimum sink` · `Minimum-sink speed` · `Minimum sink rate`  
  *(these are backlinks — open the Backlinks pane to navigate them)*

**Source.** 🟡 PARTIAL

> RC-Network Wiki 'Gleitzahl' establishes the speed-dependent polar with distinct optima; no page read gives the minimum-sink point explicitly.
>
> — via `rc-aircraft-designer`

**The source states it as.**

```
polar optimum: E = E(V), maximum at one specific speed
```

**⚠️ Divergence from the source.** Minimum-sink (min w) and best-glide (max V/w) are distinct polar points; the code correctly computes them separately, but no consulted source was found stating the min-sink definition.

🟡 *Reported by the extraction pass, not independently verified.*

---
*Cluster [[_index-aero-spanwise|aero-spanwise]] · generated from the 2026-08-18 extraction.*
