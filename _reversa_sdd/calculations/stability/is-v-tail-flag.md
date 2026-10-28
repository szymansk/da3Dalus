---
name: is-v-tail-flag
symbol: —
kind: constant
unit: – (bool)
cluster: stability
user_visible: false
source_status: NO_SOURCE_FOUND
code_audit: CONFIRMED
node_class: unclassified-constant
tags:
  - cluster/stability
  - class/unclassified-constant
  - source/no-source-found
  - audit/confirmed
  - flag/anomaly
  - flag/divergence
---

# V-tail configuration flag

**Definition.** Whether the aircraft has a V-tail; gates tail-volume sizing to not_applicable.

⚪ **Unclassified constant.** Not yet decided whether this is a rule of thumb, a calibration or a physical value. Classifying it is open work — it is deliberately not guessed.

**Value.** `True` when some wing has `surface_type == v_tail`, else `False` (gh-1187).

**Formula — as the code writes it.**

```
is_v_tail = bool(wings_of_type(wings, SurfaceType.V_TAIL))  # decomposition stays out of scope (gh-491)
```

**Inputs.** — *(leaf: a constant or an external input)*

**Produced by.** `app/services/tail_sizing_service.py:393` — `build_tail_sizing_context_from_aeroplane`

🟢 **Verified against the code** — an independent reviewer read this line and confirmed the formula, unit and value (2026-08-18 audit).

**Consumed by.**

- outside it: `app/services/tail_sizing_service.py:160,472`

**Source.** 🔴 NO SOURCE FOUND

>
> — via `aircraft-design-scholz`
> No citable source was found. **This is recorded, not filled in.** The value is
> in the code without an attributable origin.

**Updated by gh-1187.** The flag is read from the explicit `surface_type` instead of being a
hard-coded `False`, so the `is_v_tail` guard in `compute_tail_volumes`
(`tail_sizing_service.py`) and the SM-apply guard are reachable: a V-tail is reported
`not_applicable` instead of being sized with the conventional-tail or tailless formula. The
decomposition of a V-tail into a horizontal and a vertical tail (Sadraey §6.7, cos²γ) is
still not implemented (gh-491).

---
*Cluster [[_index-stability|stability]] · generated from the 2026-08-18 extraction.*
