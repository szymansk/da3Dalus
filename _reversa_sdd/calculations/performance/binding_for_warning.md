---
name: binding_for_warning
symbol: binding_for_warning
kind: quantity
unit: bool
cluster: perf-matching
user_visible: true
source_status: NO_SOURCE_FOUND
---

# Warning-relevance flag

**Definition.** Whether a constraint may drive the infeasibility verdict.

**Formula — as the code writes it.**

```
"binding_for_warning": True  (False only for Wing-Cube-Loading at line 1122)
```

**Inputs.** — *(leaf: a constant or an external input)*

**Produced by.** `app/services/matching_chart_service.py:892` — `compute_chart`

**Consumed by.**

- outside it: `constraints_for_feasibility:989` · `ConstraintLine.binding_for_warning` · `frontend/hooks/useMatchingChart.ts`

**Source.** 🔴 NO SOURCE FOUND

> Implementation flag; no methodological counterpart. Sadraey §4.3.1 step 3 treats every stated requirement as equally binding on the feasible region.
>
> — via `aircraft-design-scholz`
> No citable source was found. **This is recorded, not filled in.** The value is
> in the code without an attributable origin.

**Cited in the code itself.** `# "binding_for_warning" — False excludes from insufficient-T/W warning`

---
*Cluster [[_index-perf-matching|perf-matching]] · generated from the 2026-08-18 extraction.*
