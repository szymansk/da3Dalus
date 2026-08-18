---
name: host-root-y
kind: quantity
unit: mm
cluster: structure
user_visible: false
source_status: NO_SOURCE_FOUND
node_class: derived
tags:
  - cluster/structure
  - class/derived
  - source/no-source-found
  - flag/anomaly
---

# Host segment root spanwise position

**Definition.** Spanwise start of the segment hosting a telescoping front spar — the sum of preceding segment lengths. Used to convert absolute joint positions into segment-local split lengths.

**Derived quantity.** Computed from the inputs below.

**Formula — as the code writes it.**

```
host_root_y = float(sum(segment_lengths_mm[:host_index]))
```

**Inputs.**

- [[segment-lengths|Per-segment spanwise lengths]]
- [[segment-for-y|Spanwise position to segment index]]  — *⊣ limit*

**Produced by.** `app/services/spar_insert_service.py:303` — `_front_split_plan`

**Consumed by.**

- in this graph: `Segment-local split position`  
  *(these are backlinks — open the Backlinks pane to navigate them)*
- outside it: `app/services/spar_insert_service.py:308`

**Source.** 🔴 NO SOURCE FOUND

>
> — via `aircraft-design-scholz + rc-aircraft-designer (accumulated segment-length bookkeeping; not a design calculation)`
> No citable source was found. **This is recorded, not filled in.** The value is
> in the code without an attributable origin.

**⚠️ Anomaly.** Second producer of the same expression at app/services/spar_insert_service.py:437 (_subsegment_root_y), which computes the identical accumulated root y from a WingConfiguration instead of a length list.

🟡 *Reported by the extraction pass, not independently verified. Do not cite as a
defect until confirmed against the code.*

**Cited in the code itself.** `All front pieces of one telescoping spar run continuously root→tip inside a single host segment; the host is resolved from the first front piece's root y.`

---
*Cluster [[_index-structure|structure]] · generated from the 2026-08-18 extraction.*
