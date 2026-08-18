---
name: alr-gentleness-scale
symbol: —
kind: constant
unit: 1/deg
cluster: aero-polars
user_visible: false
source_status: NO_SOURCE_FOUND
node_class: unclassified-constant
tags:
  - cluster/aero-polars
  - class/unclassified-constant
  - source/no-source-found
  - flag/anomaly
  - flag/divergence
---

# Stall gentleness normalisation scale

**Definition.** dCL/dα magnitude at which the gentleness component reaches 0.

⚪ **Unclassified constant.** Not yet decided whether this is a rule of thumb, a calibration or a physical value. Classifying it is open work — it is deliberately not guessed.

**Value.** `0.15`

**Formula — as the code writes it.**

```
gentleness_score = max(0.0, min(1.0, 1.0 + stall / 0.15))
```

**Inputs.**

- [[alr-stall-gentleness|Stall gentleness]]  — *⊣ limit*

**Produced by.** `app/services/airfoil_low_re_service.py:875` — `score_re_agnostic`

**Consumed by.**

- in this graph: `re_agnostic suitability score`  
  *(these are backlinks — open the Backlinks pane to navigate them)*
- outside it: `score_re_agnostic:876`

**Source.** 🔴 NO SOURCE FOUND

> No citable source was found. **This is recorded, not filled in.** The value is
> in the code without an attributable origin.

**⚠️ Divergence from the source.** No source for 0.15 /deg. A positive post-peak slope (CL still rising because the 18° sweep truncated the peak) is clipped to a full 1.0 instead of being flagged — the truncation artefact scores as ideal stall behaviour.

🟡 *Reported by the extraction pass, not independently verified.*

**⚠️ Anomaly.** Magic scale; a positive stall slope (still-rising CL, sweep truncated at 18°) is clipped to 1.0 rather than flagged.

🟡 *Reported by the extraction pass, not independently verified. Do not cite as a
defect until confirmed against the code.*

**Cited in the code itself.** `# Map: 0 → 1.0, ≤ -0.15 → 0.0 (linear)
gentleness_score = max(0.0, min(1.0, 1.0 + stall / 0.15))`

---
*Cluster [[_index-aero-polars|aero-polars]] · generated from the 2026-08-18 extraction.*
