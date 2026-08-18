---
name: cdftp-y-span
symbol: y_span
kind: quantity
unit: m
cluster: aero-strips
user_visible: false
source_status: NO_SOURCE_FOUND
---

# Span extent for trip interpolation

**Definition.** Span range over which the turbulator's root-to-tip trip position is interpolated.

**Formula — as the code writes it.**

```
y_span = y_max - y_min if y_max > y_min else 1.0
```

**Inputs.** [[saoa-y|Panel spanwise position]]

**Produced by.** `app/services/turbulator_optimizer_service.py:680` — `compute_delta_cd0_from_turbulator_position`

**Consumed by.**

- in this graph: [[cdftp-frac|Span fraction of a section]]

**Source.** 🔴 NO SOURCE FOUND

> No citable source was found. **This is recorded, not filled in.** The value is
> in the code without an attributable origin.

**⚠️ Divergence from the source.** Substituting 1.0 m for a degenerate span has no basis. It does not merely default a value — it silently rescales frac, so every section's interpolated trip position is wrong rather than absent.

🟡 *Reported by the extraction pass, not independently verified.*

**⚠️ Anomaly.** Undeclared fallback: a degenerate span silently becomes 1.0 m (ADR 0020).

🟡 *Reported by the extraction pass, not independently verified. Do not cite as a
defect until confirmed against the code.*

**Cited in the code itself.** `app/services/turbulator_optimizer_service.py:677-680`

---
*Cluster [[_index-aero-strips|aero-strips]] · generated from the 2026-08-18 extraction.*
