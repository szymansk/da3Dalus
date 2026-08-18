---
name: mac-m-fallback
symbol: —
kind: constant
unit: m
cluster: stability
user_visible: false
source_status: NO_SOURCE_FOUND
node_class: unclassified-constant
tags:
  - cluster/stability
  - class/unclassified-constant
  - source/no-source-found
  - flag/anomaly
  - flag/divergence
---

# MAC fallback

**Definition.** MAC used when the context value is missing or non-positive.

⚪ **Unclassified constant.** Not yet decided whether this is a rule of thumb, a calibration or a physical value. Classifying it is open work — it is deliberately not guessed.

**Value.** `0.30`

**Formula — as the code writes it.**

```
mac_m: float = float(mac_m_raw) if mac_m_raw and float(mac_m_raw) > 0 else 0.30
```

**Inputs.** — *(leaf: a constant or an external input)*

**Produced by.** `app/services/sm_sizing_service.py:138` — `_dsm_dx_wing`

**Consumed by.**

- in this graph: `Clipped wing shift` · `SM sensitivity to horizontal tail area` · `SM sensitivity to wing longitudinal shift` · `Tail arm fallback` · `Static margin at aft CG` · `Forward-CG SM after wing shift` · `Static margin at forward CG` · `Maximum forward-CG static margin`  
  *(these are backlinks — open the Backlinks pane to navigate them)*
- outside it: `app/services/sm_sizing_service.py:138,154,600,640,678,706`

**Source.** 🔴 NO SOURCE FOUND

>
> — via `aircraft-design-scholz`
> No citable source was found. **This is recorded, not filled in.** The value is
> in the code without an attributable origin.

**⚠️ Divergence from the source.** 0.30 m is a plausible RC-model MAC but is not attributable to any source; it is an arbitrary stand-in repeated six times as an inline literal. The MAC itself is computable from Scholz 07_WingDesign §7.1 (c_MAC = (2/3)c_r(1+λ+λ²)/(1+λ)), so a fallback is avoidable in principle.

🟡 *Reported by the extraction pass, not independently verified.*

**⚠️ Anomaly.** The same magic literal is repeated six times as an inline default rather than a named constant. Docstring claims it is only for unit-test paths, but lines 600, 640, 678 and 706 are production option-builders.

🟡 *Reported by the extraction pass, not independently verified. Do not cite as a
defect until confirmed against the code.*

**Cited in the code itself.** `Callers in suggest_corrections / apply_* are guarded by _is_not_applicable,
so mac_m is always valid there.  The fallback covers unit-test call paths.`

---
*Cluster [[_index-stability|stability]] · generated from the 2026-08-18 extraction.*
