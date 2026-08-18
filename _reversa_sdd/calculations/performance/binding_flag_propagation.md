---
name: binding_flag_propagation
symbol: binding
kind: quantity
unit: bool
cluster: perf-matching
user_visible: true
source_status: NO_SOURCE_FOUND
---

# Binding-flag back-propagation

**Definition.** Per-constraint flag saying the design point sits on that constraint.

**Formula — as the code writes it.**

```
match = next((cc for cc in _checked_subset if cc["name"] == c["name"] and cc.get("category") == c.get("category")), None); c2 = {**c, "binding": match["binding"] if match else c.get("binding", False)}
```

**Inputs.** [[feasibility_verdict|Feasibility verdict]]

**Produced by.** `app/services/matching_chart_service.py:1015` — `compute_chart`

**Consumed by.**

- outside it: `ConstraintLine.binding (schema)` · `frontend/hooks/useMatchingChart.ts ConstraintLine.binding`

**Source.** 🔴 NO SOURCE FOUND

> Implementation detail with no methodological content; not a quantity the literature addresses.
>
> — via `aircraft-design-scholz`
> No citable source was found. **This is recorded, not filled in.** The value is
> in the code without an attributable origin.

**⚠️ Divergence from the source.** binding_by_id is built and then explicitly discarded (`_ = binding_by_id`), and the matcher keys on name+category while the constraints carry a stable 'key' field it ignores (ADR 0021).

🟡 *Reported by the extraction pass, not independently verified.*

**⚠️ Anomaly.** binding_by_id is built at line 1001 and then explicitly discarded at line 1017 (`_ = binding_by_id  # retained for clarity, not used`) — dead code that ADR 0021 forbids; the constraints carry a stable "key" field that the matcher ignores in favour of name+category.

🟡 *Reported by the extraction pass, not independently verified. Do not cite as a
defect until confirmed against the code.*

**Cited in the code itself.** `# _check_feasibility creates new dicts so we look up by original key identity via name+category — works because the names are unique within a single chart.`

---
*Cluster [[_index-perf-matching|perf-matching]] · generated from the 2026-08-18 extraction.*
