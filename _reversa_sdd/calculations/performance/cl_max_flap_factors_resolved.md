---
name: cl_max_flap_factors_resolved
symbol: (f_TO, f_LDG)
kind: quantity
unit: dimensionless
cluster: perf-matching
user_visible: false
source_status: NO_SOURCE_FOUND
node_class: derived
tags:
  - cluster/perf-matching
  - class/derived
  - source/no-source-found
  - flag/anomaly
  - flag/divergence
---

# Resolved flap factors

**Definition.** Flap multipliers looked up for the aircraft's flap type, defaulting to (1.0, 1.0).

**Derived quantity.** Computed from the inputs below.

**Formula — as the code writes it.**

```
key = flap_type.lower() if isinstance(flap_type, str) else None; return _FLAP_FACTORS.get(key, (1.0, 1.0))
```

**Inputs.**

- [[flap_factors|Flap CL_max multiplier table]]  — *⊣ limit*

**Produced by.** `app/services/field_length_service.py:158` — `detect_cl_max_flap_factors`

**Consumed by.**

- in this graph: `Landing CL_max (field length)` · `Takeoff CL_max (field length)`  
  *(these are backlinks — open the Backlinks pane to navigate them)*
- outside it: `compute_field_lengths:358`

**Source.** 🔴 NO SOURCE FOUND

> Inherits flap_factors: no source for a multiplicative flap table (see that entry).
>
> — via `aircraft-design-scholz`
> No citable source was found. **This is recorded, not filled in.** The value is
> in the code without an attributable origin.

**⚠️ Divergence from the source.** Unknown flap strings silently degrade to (1.0, 1.0) with no warning (ADR 0020), so a typo in flap_type silently removes all high-lift benefit.

🟡 *Reported by the extraction pass, not independently verified.*

**⚠️ Anomaly.** Unknown flap strings silently degrade to (1.0, 1.0) with no warning (ADR 0020).

🟡 *Reported by the extraction pass, not independently verified. Do not cite as a
defect until confirmed against the code.*

**Cited in the code itself.** `# Source: gh-489 spec, Amendment 2 (accepted Spec-Gate findings).`

---
*Cluster [[_index-perf-matching|perf-matching]] · generated from the 2026-08-18 extraction.*
