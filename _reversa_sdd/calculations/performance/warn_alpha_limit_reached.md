---
name: warn_alpha_limit_reached
kind: quantity
unit: dimensionless
cluster: perf-oppoints
user_visible: true
source_status: PARTIAL
---

# ALPHA_LIMIT_REACHED warning

**Definition.** Status downgrade when the solved alpha exceeds the profile's alpha limit.

**Formula — as the code writes it.**

```
if max_alpha is not None and abs(best_alpha) > float(max_alpha): trim_status = OperatingPointStatus.LIMIT_REACHED; warnings.append("ALPHA_LIMIT_REACHED")
```

**Inputs.** [[alpha_trimmed|Trimmed angle of attack]] · [[default_max_alpha_deg|Default maximum angle of attack]]

**Produced by.** `app/services/operating_point_generator_service.py:860` — `_apply_limit_warnings`

**Consumed by.**

- outside it: `app/models/analysismodels.py:28` · `frontend/components/workbench/OperatingPointsPanel.tsx:483-488`

**Source.** 🟡 PARTIAL

> Sadraey §5.4.3 / Scholz 08_HighLift §8.2 (α_s 12–16°); Anderson 6e §4.13 — the physical alpha limit is the stall angle
>
> — via `aircraft-design-scholz, aerodynamics-expert`

**⚠️ Divergence from the source.** That an alpha limit should exist is sourced; this implementation does not test it. It uses abs(best_alpha), so a strongly NEGATIVE alpha trips a limit the constraint never described (negative stall is a different, usually smaller-magnitude angle). And since the Opti upper bound already equals max_alpha, the check can only ever fire on the grid path.

🟡 *Reported by the extraction pass, not independently verified.*

**⚠️ Anomaly.** Uses abs(best_alpha), so a strongly negative alpha trips an "alpha limit" the constraint never described; and the Opti upper bound already equals max_alpha, so the check can only fire on the grid path.

🟡 *Reported by the extraction pass, not independently verified. Do not cite as a
defect until confirmed against the code.*

---
*Cluster [[_index-perf-oppoints|perf-oppoints]] · generated from the 2026-08-18 extraction.*
