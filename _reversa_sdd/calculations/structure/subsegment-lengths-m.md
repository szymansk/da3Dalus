---
name: subsegment-lengths-m
kind: quantity
unit: m
cluster: structure
user_visible: true
source_status: NO_SOURCE_FOUND
code_audit: CONFIRMED
node_class: derived
tags:
  - cluster/structure
  - class/derived
  - source/no-source-found
  - surface/user-visible
  - audit/confirmed
  - flag/anomaly
---

# Post-split sub-segment lengths

**Definition.** Spanwise length of each sub-segment produced by splitting the host segment at the telescoping joints, in metres for the API response.

**Derived quantity.** Computed from the inputs below.

**Formula — as the code writes it.**

```
host_len = float(segment_lengths_mm[host_index])
boundaries = [0.0, *split_lengths, host_len]
return [(boundaries[i + 1] - boundaries[i]) * _MM_TO_M for i in range(len(boundaries) - 1)]
```

**Inputs.**

- [[split-local-length|Segment-local split position]]
- [[segment-lengths|Per-segment spanwise lengths]]
- [[mm-to-m-factor|Millimetre-to-metre conversion factor]]  — *× unit*

**Produced by.** `app/services/spar_insert_service.py:531` — `_preview_subsegment_lengths_m`

🟢 **Verified against the code** — an independent reviewer read this line and confirmed the formula, unit and value (2026-08-18 audit).

**Consumed by.**

- outside it: `app/services/spar_insert_service.py:481` · `app/services/spar_insert_service.py:519` · `frontend/hooks/useSparPlan.ts:105`

**Source.** 🔴 NO SOURCE FOUND

>
> — via `aircraft-design-scholz + rc-aircraft-designer (post-split geometric bookkeeping; not a design calculation. Independent of provenance: two producers exist — the preview computes it arithmetically at app/services/spar_insert_service.py:531 while the commit path reads it back from the post-split WingConfiguration at :403-407 — so a preview and its own commit can report different numbers)`
> No citable source was found. **This is recorded, not filled in.** The value is
> in the code without an attributable origin.

**⚠️ Anomaly.** Two producers of the same list: the preview computes it arithmetically here (line 531), while the commit path reads it back from the post-split WingConfiguration (app/services/spar_insert_service.py:403-407). A preview and its own commit can therefore report different numbers.

🟡 *Reported by the extraction pass, not independently verified. Do not cite as a
defect until confirmed against the code.*

**Cited in the code itself.** `gh-1063: when the main (front) spar telescopes the host segment is SPLIT at each joint; these are the resulting per-sub-segment spanwise lengths (m), root→tip.`

---
*Cluster [[_index-structure|structure]] · generated from the 2026-08-18 extraction.*
