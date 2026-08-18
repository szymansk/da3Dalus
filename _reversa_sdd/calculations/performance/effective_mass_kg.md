---
name: effective_mass_kg
symbol: m
kind: quantity
unit: kg
cluster: perf-oppoints
user_visible: true
source_status: PARTIAL
node_class: derived
tags:
  - cluster/perf-oppoints
  - class/derived
  - source/partial
  - surface/user-visible
  - flag/divergence
---

# Effective aircraft mass

**Definition.** Mass driving CL_target, from the design assumption with the legacy aircraft field as fallback.

**Derived quantity.** Computed from the inputs below.

**Formula — as the code writes it.**

```
if row.active_source == "CALCULATED" and row.calculated_value is not None: return float(row.calculated_value); return float(row.estimate_value)
```

**Inputs.** — *(leaf: a constant or an external input)*

**Produced by.** `app/services/operating_point_generator_service.py:266` — `_load_effective_mass_kg`

**Consumed by.**

- in this graph: `Target lift coefficient`  
  *(these are backlinks — open the Backlinks pane to navigate them)*
- outside it: `app/services/operating_point_generator_service.py:891 (mass_for_cl)` · `app/services/operating_point_generator_service.py:794-797 (cl_target)` · `app/services/add_turn_service.py:54`

**Source.** 🟡 PARTIAL

> Sadraey §4.3.2, Eq. 4.30: L = W = m·g at the reference condition — mass is the required input to any lift-balance target
>
> — via `aircraft-design-scholz`

**⚠️ Divergence from the source.** That mass drives CL_target is sourced. The precedence rule (CALCULATED over estimate, then legacy aircraft field) is app-internal data governance, not an engineering method.

🟡 *Reported by the extraction pass, not independently verified.*

---
*Cluster [[_index-perf-oppoints|perf-oppoints]] · generated from the 2026-08-18 extraction.*
