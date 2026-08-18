---
name: trim_method
kind: quantity
unit: dimensionless
cluster: perf-oppoints
user_visible: true
source_status: NO_SOURCE_FOUND
code_audit: CONFIRMED
node_class: derived
tags:
  - cluster/perf-oppoints
  - class/derived
  - source/no-source-found
  - surface/user-visible
  - audit/confirmed
  - flag/divergence
---

# Trim solver path label

**Definition.** Which solver produced the point: "opti" or "grid_fallback".

**Derived quantity.** Computed from the inputs below.

**Formula — as the code writes it.**

```
best_method = "opti" / best_method = "grid_fallback"
```

**Inputs.**

- [[grid_fallback_trigger|Grid-fallback trigger threshold]]  — *⤵ fallback*

**Produced by.** `app/services/operating_point_generator_service.py:956` — `_trim_or_estimate_point`

🟢 **Verified against the code** — an independent reviewer read this line and confirmed the formula, unit and value (2026-08-18 audit).

**Consumed by.**

- outside it: `app/services/trim_enrichment_service.py:536, 562` · `app/services/add_turn_service.py:100`

**Source.** 🔴 NO SOURCE FOUND

> No citable source was found. **This is recorded, not filled in.** The value is
> in the code without an attributable origin.

**⚠️ Divergence from the source.** Solver-provenance metadata ('opti' / 'grid_fallback'). No engineering source applies. It is the only signal that a point's velocity may have been shifted up to ±15 % and its controls zeroed, which makes it load-bearing for interpretation despite being metadata.

🟡 *Reported by the extraction pass, not independently verified.*

**Cited in the code itself.** `gh-627: solver_path lives on trim_method, NOT in trim_residuals. trim_residuals is typed as dict[str, float] (Pydantic-validated in TrimEnrichment) and rejects string values. The earlier `best_residuals["solver_path"] = "opti"` line (gh-528) broke every OP enrichment until removed.`

---
*Cluster [[_index-perf-oppoints|perf-oppoints]] · generated from the 2026-08-18 extraction.*
