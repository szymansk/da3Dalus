---
name: low-re-low-confidence-flag
symbol: —
kind: parameter
unit: dimensionless
cluster: aero-polars
user_visible: true
source_status: NO_SOURCE_FOUND
code_audit: CONFIRMED
node_class: unclassified-parameter
tags:
  - cluster/aero-polars
  - class/unclassified-parameter
  - source/no-source-found
  - surface/user-visible
  - audit/confirmed
  - flag/anomaly
  - flag/divergence
---

# Low-confidence flag threshold

**Definition.** min_analysis_confidence below which an item is caveated and demoted in the sort.

⚪ **Unclassified parameter.** Not yet decided whether this is a user input or an internal tuning value.

**Value.** `0.85`

**Formula — as the code writes it.**

```
low_re_low_confidence_flag: float = 0.85
```

**Inputs.** — *(leaf: a constant or an external input)*

**Produced by.** `app/settings.py:100` — `Settings.low_re_low_confidence_flag`

🟢 **Verified against the code** — an independent reviewer read this line and confirmed the formula, unit and value (2026-08-18 audit).

**Consumed by.**

- in this graph: `Suitability caveat block` · `Confidence sort tier`  
  *(these are backlinks — open the Backlinks pane to navigate them)*
- outside it: `suitability_service:256,537,543,625`

**Source.** 🔴 NO SOURCE FOUND

> No citable source was found. **This is recorded, not filled in.** The value is
> in the code without an attributable origin.

**⚠️ Divergence from the source.** No source for 0.85; it also sits below the acceptance gate of 0.90, so the two thresholds encode inconsistent ideas of 'trustworthy'. Re-hardcoded at frontend/components/workbench/AirfoilSuitabilityCard.tsx:344 — a second producer that will diverge silently (ADR 0022).

🟡 *Reported by the extraction pass, not independently verified.*

**⚠️ Anomaly.** Re-hardcoded in the UI: frontend/components/workbench/AirfoilSuitabilityCard.tsx:344 `const isLowConfidence = item.min_analysis_confidence < 0.85;` — a second producer that will silently diverge if the setting changes.

🟡 *Reported by the extraction pass, not independently verified. Do not cite as a
defect until confirmed against the code.*

**Cited in the code itself.** `# Flag threshold: any item with min_analysis_confidence < flag → caveat.
low_re_low_confidence_flag: float = 0.85`

---
*Cluster [[_index-aero-polars|aero-polars]] · generated from the 2026-08-18 extraction.*
