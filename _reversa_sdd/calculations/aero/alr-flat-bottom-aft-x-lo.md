---
name: alr-flat-bottom-aft-x-lo
symbol: —
kind: parameter
unit: chord fraction
cluster: aero-polars
user_visible: false
source_status: NO_SOURCE_FOUND
node_class: unclassified-parameter
tags:
  - cluster/aero-polars
  - class/unclassified-parameter
  - source/no-source-found
  - flag/divergence
---

# Flat-bottom aft window start

**Definition.** Chordwise start of the window over which lower-surface linearity is tested.

⚪ **Unclassified parameter.** Not yet decided whether this is a user input or an internal tuning value.

**Value.** `0.30`

**Formula — as the code writes it.**

```
_FLAT_BOTTOM_AFT_X_LO = 0.30
```

**Inputs.** — *(leaf: a constant or an external input)*

**Produced by.** `app/services/airfoil_low_re_service.py:109` — `_FLAT_BOTTOM_AFT_X_LO`

**Consumed by.**

- in this graph: `Aft lower-surface quadratic coefficient`  
  *(these are backlinks — open the Backlinks pane to navigate them)*
- outside it: `classify_family:242`

**Source.** 🔴 NO SOURCE FOUND

> No citable source was found. **This is recorded, not filled in.** The value is
> in the code without an attributable origin.

**⚠️ Divergence from the source.** 0.30 chord is an arbitrary window start for the linearity test; no source.

🟡 *Reported by the extraction pass, not independently verified.*

**Cited in the code itself.** `aft_mask = x_eval >= _FLAT_BOTTOM_AFT_X_LO`

---
*Cluster [[_index-aero-polars|aero-polars]] · generated from the 2026-08-18 extraction.*
