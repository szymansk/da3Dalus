---
name: vlm-panels-per-segment-degenerate
symbol: —
kind: constant
unit: panels
cluster: aero-strips
user_visible: false
source_status: NO_SOURCE_FOUND
node_class: unclassified-constant
tags:
  - cluster/aero-strips
  - class/unclassified-constant
  - source/no-source-found
  - flag/anomaly
  - flag/divergence
---

# Degenerate-span panel fallback

**Definition.** When total span is non-positive every segment gets max(min_per_segment, 1) panels.

⚪ **Unclassified constant.** Not yet decided whether this is a rule of thumb, a calibration or a physical value. Classifying it is open work — it is deliberately not guessed.

**Value.** `1`

**Formula — as the code writes it.**

```
return [max(min_per_segment, 1) for _ in spans]
```

**Inputs.**

- [[vlm-min-panels-per-segment|Minimum panels per wing segment]]  — *⊣ limit*

**Produced by.** `app/services/vlm_strip_forces.py:73` — `_panels_per_segment`

**Consumed by.**

- outside it: `app/services/vlm_strip_forces.py:remesh_uniform_density`

**Source.** 🔴 NO SOURCE FOUND

> No citable source was found. **This is recorded, not filled in.** The value is
> in the code without an attributable origin.

**⚠️ Divergence from the source.** Pure error-path fallback. No aerodynamic source; a zero/negative span is a geometry defect, and no consulted source treats it as meshable.

🟡 *Reported by the extraction pass, not independently verified.*

**⚠️ Anomaly.** Undeclared fallback: zero/negative total span silently yields a mesh instead of an error or DesignWarning (ADR 0020).

🟡 *Reported by the extraction pass, not independently verified. Do not cite as a
defect until confirmed against the code.*

**Cited in the code itself.** `app/services/vlm_strip_forces.py:73`

---
*Cluster [[_index-aero-strips|aero-strips]] · generated from the 2026-08-18 extraction.*
