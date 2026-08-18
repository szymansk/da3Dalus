---
name: prt-degenerate-flag
symbol: —
kind: quantity
unit: boolean
cluster: aero-polars
user_visible: true
source_status: NO_SOURCE_FOUND
code_audit: CONFIRMED
node_class: derived
tags:
  - cluster/aero-polars
  - class/derived
  - source/no-source-found
  - surface/user-visible
  - audit/confirmed
  - flag/divergence
---

# polar_re_table_degenerate

**Definition.** True when all V anchors sit at nearly the same speed, so only one band is fitted.

**Derived quantity.** Computed from the inputs below.

**Formula — as the code writes it.**

```
degenerate = (re_max / re_min) < _RE_DEGENERACY_RATIO if re_min > 0 else True
```

**Inputs.**

- [[prt-re-aircraft|Aircraft-level Reynolds number (V-band label)]]
- [[prt-re-degeneracy-ratio|Re-table degeneracy threshold]]  — *⤵ fallback*

**Produced by.** `app/services/polar_re_table_service.py:454` — `build_re_table`

🟢 **Verified against the code** — an independent reviewer read this line and confirmed the formula, unit and value (2026-08-18 audit).

**Consumed by.**

- outside it: `assumption_compute_service.py:416,428,455,756 → ctx['polar_re_table_degenerate']`

**Source.** 🔴 NO SOURCE FOUND

> No citable source was found. **This is recorded, not filled in.** The value is
> in the code without an attributable origin.

**⚠️ Divergence from the source.** Derived entirely from prt-re-degeneracy-ratio; inherits its lack of source.

🟡 *Reported by the extraction pass, not independently verified.*

**Cited in the code itself.** `degenerate = (re_max / re_min) < _RE_DEGENERACY_RATIO if re_min > 0 else True`

---
*Cluster [[_index-aero-polars|aero-polars]] · generated from the 2026-08-18 extraction.*
