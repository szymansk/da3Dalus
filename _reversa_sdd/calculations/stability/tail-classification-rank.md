---
name: tail-classification-rank
symbol: —
kind: constant
unit: – (rank)
cluster: stability
user_visible: true
source_status: NO_SOURCE_FOUND
code_audit: CONFIRMED
node_class: unclassified-constant
tags:
  - cluster/stability
  - class/unclassified-constant
  - source/no-source-found
  - surface/user-visible
  - audit/confirmed
  - flag/anomaly
  - flag/divergence
---

# Classification severity ranking

**Definition.** Severity order used to reduce the per-surface classifications to a single top-level one.

⚪ **Unclassified constant.** Not yet decided whether this is a rule of thumb, a calibration or a physical value. Classifying it is open work — it is deliberately not guessed.

**Value.** `{"in_range": 0, "below_range": 1, "above_range": 1, "out_of_physical_range": 2, "not_applicable": 3}`

**Inputs.** — *(leaf: a constant or an external input)*

**Produced by.** `app/services/tail_sizing_service.py:333` — `_CLASSIFICATION_RANK`

🟢 **Verified against the code** — an independent reviewer read this line and confirmed the formula, unit and value (2026-08-18 audit).

**Consumed by.**

- outside it: `app/services/tail_sizing_service.py:344 (_worst_classification)`

**Source.** 🔴 NO SOURCE FOUND

>
> — via `none — not a design quantity`
> No citable source was found. **This is recorded, not filled in.** The value is
> in the code without an attributable origin.

**⚠️ Divergence from the source.** Presentation-layer severity ordering; no engineering source applies. Note 'not_applicable' ranks as most severe (3), above out_of_physical_range — so a missing vertical tail would dominate a genuinely out-of-range horizontal tail, except that line 300 substitutes 'in_range' when v_v is None, masking it.

🟡 *Reported by the extraction pass, not independently verified.*

**⚠️ Anomaly.** 'not_applicable' ranks as the MOST severe (3), above out_of_physical_range — so a missing vertical tail would dominate a genuinely out-of-range horizontal tail. In practice line 300 substitutes 'in_range' when v_v is None, masking it.

🟡 *Reported by the extraction pass, not independently verified. Do not cite as a
defect until confirmed against the code.*

---
*Cluster [[_index-stability|stability]] · generated from the 2026-08-18 extraction.*
