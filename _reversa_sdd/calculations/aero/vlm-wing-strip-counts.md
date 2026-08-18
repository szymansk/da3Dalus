---
name: vlm-wing-strip-counts
symbol: wing_counts
kind: quantity
unit: strips
cluster: aero-strips
user_visible: false
source_status: PARTIAL
code_audit: CONFIRMED
node_class: derived
tags:
  - cluster/aero-strips
  - class/derived
  - source/partial
  - audit/confirmed
  - flag/anomaly
  - flag/divergence
  - solver-adjacent/vlm
---

# Expected strips per wing

**Definition.** Expected spanwise strip count per wing = segments × spanwise_resolution × (2 if symmetric).

**Derived quantity.** Computed from the inputs below.

**Formula — as the code writes it.**

```
n = segments * spanwise_resolution * (2 if wing.symmetric else 1)
```

**Inputs.**

- [[vlm-spanwise-resolution-fixed|VLM spanwise_resolution literal]]

**Produced by.** `app/services/vlm_strip_forces.py:53` — `_wing_strip_counts`

🟢 **Verified against the code** — an independent reviewer read this line and confirmed the formula, unit and value (2026-08-18 audit).

**Consumed by.**

- in this graph: `Spanwise strip count per surface`  
  *(these are backlinks — open the Backlinks pane to navigate them)*
- outside it: `app/services/vlm_strip_forces.py:compute_vlm_strip_forces (surface attribution)`

**Source.** 🟡 PARTIAL

> AVL 3.40 source, Avl/src/aoutput.f:211 ('# Chordwise', '# Spanwise', 'First strip' per surface)
>
> — via `avl-advisor`

**⚠️ Divergence from the source.** Counting strips per surface is AVL's own reporting model. The collapse-to-one-surface fallback on mismatch has no source.

🟡 *Reported by the extraction pass, not independently verified.*

**⚠️ Anomaly.** Undeclared fallback: on a count mismatch all strips collapse into one aggregate surface (lines 239-241) with no warning emitted (ADR 0020).

🟡 *Reported by the extraction pass, not independently verified. Do not cite as a
defect until confirmed against the code.*

**Cited in the code itself.** `app/services/vlm_strip_forces.py:52-53`

---
*Cluster [[_index-aero-strips|aero-strips]] · generated from the 2026-08-18 extraction.*
