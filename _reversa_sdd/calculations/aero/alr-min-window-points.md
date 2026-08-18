---
name: alr-min-window-points
symbol: —
kind: constant
unit: count
cluster: aero-polars
user_visible: false
source_status: NO_SOURCE_FOUND
---

# Minimum points for windowed confidence

**Definition.** Window must contain at least this many finite points or the whole-sweep min is used.

**Value.** `4`

**Formula — as the code writes it.**

```
if len(window_finite) < 4:
    return fallback
```

**Inputs.** — *(leaf: a constant or an external input)*

**Produced by.** `app/services/airfoil_low_re_service.py:563` — `_windowed_min_confidence`

**Consumed by.**

- 🔴 **nothing found.** A computed value nothing reads is a finding (ADR 0021).

**Source.** 🔴 NO SOURCE FOUND

> No citable source was found. **This is recorded, not filled in.** The value is
> in the code without an attributable origin.

**⚠️ Divergence from the source.** 4 is an unsourced sufficiency count for taking a minimum.

🟡 *Reported by the extraction pass, not independently verified.*

**Cited in the code itself.** `if len(window_finite) < 4:
    return fallback`

---
*Cluster [[_index-aero-polars|aero-polars]] · generated from the 2026-08-18 extraction.*
