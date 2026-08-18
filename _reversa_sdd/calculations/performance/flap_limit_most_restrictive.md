---
name: flap_limit_most_restrictive
kind: quantity
unit: deg
cluster: perf-oppoints
user_visible: false
source_status: PARTIAL
---

# Governing flap deflection limit

**Definition.** Smallest positive/negative TED deflection limit across all flap-role surfaces (gh-536).

**Formula — as the code writes it.**

```
flap_limits = (min(flap_pos_limits), min(flap_neg_limits))
```

**Inputs.** [[flap_roles|Flap control role set]]

**Produced by.** `app/services/operating_point_generator_service.py:93` — `_clip_flap_to_ted_limit`

**Consumed by.**

- in this graph: [[flap_deflection_clipped_value|Clipped flap deflection]]
- outside it: `app/services/operating_point_generator_service.py:98 (clipped_value)`

**Source.** 🟡 PARTIAL

> Sadraey §12.1, Table 12.3 (per-surface maximum deflection is a design output, honoured downstream)
>
> — via `aircraft-design-scholz`

**⚠️ Divergence from the source.** Taking the most restrictive limit across surfaces is sound engineering practice and consistent with Sadraey's δ_max ≤ δ_max,design constraint, but the specific min-over-surfaces rule is not a published method.

🟡 *Reported by the extraction pass, not independently verified.*

**Cited in the code itself.** `# gh-536: most restrictive limit governs across all flap-role TEDs.`

---
*Cluster [[_index-perf-oppoints|perf-oppoints]] · generated from the 2026-08-18 extraction.*
