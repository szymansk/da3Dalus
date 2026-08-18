---
name: sui-min-conf-default
symbol: —
kind: constant
unit: dimensionless
cluster: aero-polars
user_visible: true
source_status: NO_SOURCE_FOUND
node_class: numerical-tolerance
tags:
  - cluster/aero-polars
  - class/numerical-tolerance
  - source/no-source-found
  - surface/user-visible
  - flag/anomaly
  - flag/divergence
---

# min_analysis_confidence default

**Definition.** Confidence assumed when a polar carries no confidence value.

**Numerical tolerance.** A solver or comparison epsilon, not a domain value. ADR 0023 does not apply.

**Value.** `0.0`

**Formula — as the code writes it.**

```
min_conf = polar.get("min_analysis_confidence") if polar else None
if min_conf is None:
    min_conf = 0.0
```

**Inputs.** — *(leaf: a constant or an external input)*

**Produced by.** `app/services/suitability_service.py:536` — `search_suitability`

**Consumed by.**

- outside it: `search_suitability:537,551,567,625`

**Source.** 🔴 NO SOURCE FOUND

> No citable source was found. **This is recorded, not filled in.** The value is
> in the code without an attributable origin.

**⚠️ Divergence from the source.** Coercing a missing confidence to 0.0 conflates 'not measured' with 'certainly untrustworthy'. Sharpe (2024) §7.2.4 defines the scalar only for evaluated points; absence is not a low value. No source supports the substitution, and it silently demotes such airfoils into the low-confidence sort tier.

🟡 *Reported by the extraction pass, not independently verified.*

**⚠️ Anomaly.** Missing data is coerced to the worst possible confidence, silently pushing such airfoils into the low-confidence sort tier.

🟡 *Reported by the extraction pass, not independently verified. Do not cite as a
defect until confirmed against the code.*

**Cited in the code itself.** `if min_conf is None:
    min_conf = 0.0`

---
*Cluster [[_index-aero-polars|aero-polars]] · generated from the 2026-08-18 extraction.*
