---
name: alr-min-window-points
symbol: —
kind: constant
unit: count
cluster: aero-polars
user_visible: false
source_status: NO_SOURCE_FOUND
code_audit: CONFIRMED
node_class: unclassified-constant
tags:
  - cluster/aero-polars
  - class/unclassified-constant
  - source/no-source-found
  - audit/confirmed
  - flag/divergence
---

# Minimum points for windowed confidence

**Definition.** Window must contain at least this many finite points or the whole-sweep min is used.

⚪ **Unclassified constant.** Not yet decided whether this is a rule of thumb, a calibration or a physical value. Classifying it is open work — it is deliberately not guessed.

**Value.** `4`

**Formula — as the code writes it.**

```
if len(window_finite) < 4:
    return fallback
```

**Inputs.** — *(leaf: a constant or an external input)*

**Produced by.** `app/services/airfoil_low_re_service.py:563` — `_windowed_min_confidence`

🟢 **Verified against the code** — an independent reviewer read this line and confirmed the formula, unit and value (2026-08-18 audit).

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
