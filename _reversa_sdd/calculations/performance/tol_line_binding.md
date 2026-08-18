---
name: tol_line_binding
symbol: TOL_LINE
kind: constant
unit: fraction
cluster: perf-matching
user_visible: true
source_status: NO_SOURCE_FOUND
---

# Line-constraint binding tolerance

**Definition.** Relative T/W band within which a line constraint counts as binding.

**Value.** `0.03`

**Formula — as the code writes it.**

```
TOL_LINE = 0.03
```

**Inputs.** — *(leaf: a constant or an external input)*

**Produced by.** `app/services/matching_chart_service.py:656` — `_check_feasibility`

**Consumed by.**

- in this graph: [[feasibility_verdict|Feasibility verdict]]
- outside it: `_check_feasibility:673,675`

**Source.** 🔴 NO SOURCE FOUND

> No source. Sadraey §4.3.1 step 3 defines the acceptable region as the strict intersection of the satisfying side of every curve, with no tolerance band.
>
> — via `aircraft-design-scholz`
> No citable source was found. **This is recorded, not filled in.** The value is
> in the code without an attributable origin.

**⚠️ Divergence from the source.** Also used as the infeasibility slack, so a design 2.9% below a hard constraint is reported feasible. The sources treat constraint satisfaction as binary; a tolerance is a UI affordance and should not silently relax the verdict.

🟡 *Reported by the extraction pass, not independently verified.*

**⚠️ Anomaly.** Also used as the infeasibility slack (tw_dp < tw_req * (1 - TOL_LINE)) — a design 2.9% below a hard constraint is reported feasible.

🟡 *Reported by the extraction pass, not independently verified. Do not cite as a
defect until confirmed against the code.*

**Cited in the code itself.** `# 3% T/W tolerance for "binding" line constraints`

---
*Cluster [[_index-perf-matching|perf-matching]] · generated from the 2026-08-18 extraction.*
