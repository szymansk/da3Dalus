---
name: prt-re-degeneracy-ratio
symbol: —
kind: parameter
unit: dimensionless
cluster: aero-polars
user_visible: true
source_status: NO_SOURCE_FOUND
---

# Re-table degeneracy threshold

**Definition.** If Re_max/Re_min falls below this, the table collapses to a single fallback row.

**Value.** `2.5`

**Formula — as the code writes it.**

```
_RE_DEGENERACY_RATIO: float = 2.5
```

**Inputs.** — *(leaf: a constant or an external input)*

**Produced by.** `app/services/polar_re_table_service.py:49` — `_RE_DEGENERACY_RATIO`

**Consumed by.**

- in this graph: [[prt-degenerate-flag|polar_re_table_degenerate]]
- outside it: `build_re_table:454` · `build_re_table:460 (log)`

**Source.** 🔴 NO SOURCE FOUND

> No citable source was found. **This is recorded, not filled in.** The value is
> in the code without an attributable origin.

**⚠️ Divergence from the source.** 2.5 is a bare numerical heuristic for 'the V anchors are too close to resolve distinct bands'. No aerodynamic or statistical source; module docstring asserts the rule without support.

🟡 *Reported by the extraction pass, not independently verified.*

**⚠️ Anomaly.** Magic number: module docstring asserts the rule but cites no source for 2.5.

🟡 *Reported by the extraction pass, not independently verified. Do not cite as a
defect until confirmed against the code.*

**Cited in the code itself.** `degenerate = (re_max / re_min) < _RE_DEGENERACY_RATIO if re_min > 0 else True`

---
*Cluster [[_index-aero-polars|aero-polars]] · generated from the 2026-08-18 extraction.*
