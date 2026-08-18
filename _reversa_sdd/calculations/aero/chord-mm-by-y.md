---
name: chord-mm-by-y
kind: quantity
unit: mm
cluster: aero-spanwise
user_visible: false
source_status: NO_SOURCE_FOUND
---

# Station chord in millimetres

**Definition.** Per-station chord converted from metres to millimetres for the t/c division.

**Formula — as the code writes it.**

```
chord_mm_by_y = {float(st["y_m"]): float(st["chord_m"]) * 1000.0 for st in stations}
```

**Inputs.** [[spanwise-chord-m|Local strip chord]]

**Produced by.** `app/services/analysis_service.py:2253` — `_get_tc_by_y_for_surface`

**Consumed by.**

- in this graph: [[tc-by-y|Local thickness-to-chord ratio]]

**Source.** 🔴 NO SOURCE FOUND

> Unit conversion m→mm (×1000.0); plumbing, no domain source.
> No citable source was found. **This is recorded, not filled in.** The value is
> in the code without an attributable origin.

---
*Cluster [[_index-aero-spanwise|aero-spanwise]] · generated from the 2026-08-18 extraction.*
