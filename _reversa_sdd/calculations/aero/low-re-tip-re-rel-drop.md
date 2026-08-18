---
name: low-re-tip-re-rel-drop
symbol: —
kind: parameter
unit: dimensionless
cluster: aero-polars
user_visible: false
source_status: NO_SOURCE_FOUND
code_audit: CONFIRMED
node_class: unclassified-parameter
tags:
  - cluster/aero-polars
  - class/unclassified-parameter
  - source/no-source-found
  - audit/confirmed
  - flag/anomaly
  - flag/divergence
---

# Tip-Re relative drop threshold

**Definition.** Absolute Re difference root−tip above which the tip is a different regime.

⚪ **Unclassified parameter.** Not yet decided whether this is a user input or an internal tuning value.

**Value.** `50000.0`

**Formula — as the code writes it.**

```
low_re_tip_re_rel_drop: float = 50_000.0
```

**Inputs.** — *(leaf: a constant or an external input)*

**Produced by.** `app/settings.py:114` — `Settings.low_re_tip_re_rel_drop`

🟢 **Verified against the code** — an independent reviewer read this line and confirmed the formula, unit and value (2026-08-18 audit).

**Consumed by.**

- in this graph: `tip_re_flag`  
  *(these are backlinks — open the Backlinks pane to navigate them)*
- outside it: `suitability_service:275`

**Source.** 🔴 NO SOURCE FOUND

> No citable source was found. **This is recorded, not filled in.** The value is
> in the code without an attributable origin.

**⚠️ Divergence from the source.** No source for 50 000. Name/formula mismatch: called 'rel_drop' but applied as an absolute difference (re_root − re_tip), so it fires on every large model regardless of taper and never fires on a small one however severe the taper — the opposite of the intended relative test.

🟡 *Reported by the extraction pass, not independently verified.*

**⚠️ Anomaly.** Named 'rel_drop' but applied as an ABSOLUTE Re difference (re_root − re_tip), not a ratio — name contradicts the formula.

🟡 *Reported by the extraction pass, not independently verified. Do not cite as a
defect until confirmed against the code.*

**Cited in the code itself.** `low_re_tip_re_rel_drop: float = 50_000.0`

---
*Cluster [[_index-aero-polars|aero-polars]] · generated from the 2026-08-18 extraction.*
