---
name: safe_coeff_default
kind: constant
unit: dimensionless
cluster: perf-oppoints
user_visible: false
source_status: NO_SOURCE_FOUND
code_audit: CONFIRMED
node_class: numerical-tolerance
tags:
  - cluster/perf-oppoints
  - class/numerical-tolerance
  - source/no-source-found
  - audit/confirmed
  - flag/anomaly
  - flag/divergence
  - solver-adjacent/aerobuildup
---

# Coefficient extraction default

**Definition.** Value substituted when an AeroBuildup coefficient is missing or an empty array.

**Numerical tolerance.** A solver or comparison epsilon, not a domain value. ADR 0023 does not apply.

**Value.** `0.0`

**Formula — as the code writes it.**

```
def _safe_coeff(result, key, default: float = 0.0)
```

**Inputs.** — *(leaf: a constant or an external input)*

**Produced by.** `app/services/operating_point_generator_service.py:181` — `_safe_coeff`

🟢 **Verified against the code** — an independent reviewer read this line and confirmed the formula, unit and value (2026-08-18 audit).

**Consumed by.**

- outside it: `app/services/operating_point_generator_service.py:737-739` · `app/services/operating_point_generator_service.py:775`

**Source.** 🔴 NO SOURCE FOUND

> No citable source was found. **This is recorded, not filled in.** The value is
> in the code without an attributable origin.

**⚠️ Divergence from the source.** Substituting 0.0 for a missing coefficient has no engineering basis. For Cm specifically, Cm = 0 is the definition of trim (Sadraey §12, ΣM = 0), so a missing value is silently reported as a perfectly trimmed aircraft. Undeclared fallback (ADR 0020).

🟡 *Reported by the extraction pass, not independently verified.*

**⚠️ Anomaly.** Undeclared fallback: a missing Cm silently becomes 0.0, which reads as perfectly trimmed and emits no DesignWarning (ADR 0020).

🟡 *Reported by the extraction pass, not independently verified. Do not cite as a
defect until confirmed against the code.*

---
*Cluster [[_index-perf-oppoints|perf-oppoints]] · generated from the 2026-08-18 extraction.*
