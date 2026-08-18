---
name: prt-top-anchor-clamp
symbol: —
kind: quantity
unit: m/s
cluster: aero-polars
user_visible: false
source_status: NO_SOURCE_FOUND
code_audit: CONFIRMED
node_class: derived
tags:
  - cluster/aero-polars
  - class/derived
  - source/no-source-found
  - audit/confirmed
  - flag/anomaly
  - flag/divergence
---

# Top anchor clamp to sweep max

**Definition.** Highest V anchor is clamped down to the actual sweep upper bound before binning.

**Derived quantity.** Computed from the inputs below.

**Formula — as the code writes it.**

```
clamped_top = min(top_anchor, v_sweep_max)
```

**Inputs.** — *(leaf: a constant or an external input)*

**Produced by.** `app/services/polar_re_table_service.py:441` — `build_re_table`

🟢 **Verified against the code** — an independent reviewer read this line and confirmed the formula, unit and value (2026-08-18 audit).

**Consumed by.**

- outside it: `build_re_table:449 (v_anchors[-1])`

**Source.** 🔴 NO SOURCE FOUND

> No citable source was found. **This is recorded, not filled in.** The value is
> in the code without an attributable origin.

**⚠️ Divergence from the source.** Implementation clamp with no domain content. Emits only logger.warning, no DesignWarning (ADR 0020).

🟡 *Reported by the extraction pass, not independently verified.*

**⚠️ Anomaly.** Clamp emits only logger.warning, no DesignWarning (ADR 0020).

🟡 *Reported by the extraction pass, not independently verified. Do not cite as a
defect until confirmed against the code.*

**Cited in the code itself.** `clamped_top = min(top_anchor, v_sweep_max)`

---
*Cluster [[_index-aero-polars|aero-polars]] · generated from the 2026-08-18 extraction.*
