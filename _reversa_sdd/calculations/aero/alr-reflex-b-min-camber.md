---
name: alr-reflex-b-min-camber
symbol: —
kind: parameter
unit: % chord
cluster: aero-polars
user_visible: false
source_status: NO_SOURCE_FOUND
---

# Reflex Signal B camber guard

**Definition.** Signal B only fires above this max camber, preventing symmetric false positives.

**Value.** `2.0`

**Formula — as the code writes it.**

```
_REFLEX_B_MIN_CAMBER_PCT = 2.0
```

**Inputs.** — *(leaf: a constant or an external input)*

**Produced by.** `app/services/airfoil_low_re_service.py:88` — `_REFLEX_B_MIN_CAMBER_PCT`

**Consumed by.**

- outside it: `classify_family:265`

**Source.** 🔴 NO SOURCE FOUND

> No citable source was found. **This is recorded, not filled in.** The value is
> in the code without an attributable origin.

**⚠️ Divergence from the source.** 2.0 %-chord guard exists to suppress false positives on symmetric sections; purely internal, no source.

🟡 *Reported by the extraction pass, not independently verified.*

**Cited in the code itself.** `aft_concavity > _REFLEX_AFT_CONCAVITY_MIN and max_camber_pct > _REFLEX_B_MIN_CAMBER_PCT`

---
*Cluster [[_index-aero-polars|aero-polars]] · generated from the 2026-08-18 extraction.*
