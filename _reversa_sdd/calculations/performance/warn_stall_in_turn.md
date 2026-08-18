---
name: warn_stall_in_turn
kind: quantity
unit: dimensionless
cluster: perf-oppoints
user_visible: true
source_status: PARTIAL
---

# STALL_IN_TURN warning + LIMIT_REACHED

**Definition.** Turn point flagged infeasible when the target speed is below the in-turn stall speed.

**Formula — as the code writes it.**

```
if velocity < v_stall_turn: ... point.status = OperatingPointStatus.LIMIT_REACHED
```

**Inputs.** [[v_stall_turn|Stall speed in the turn]]

**Produced by.** `app/services/operating_point_generator_service.py:171` — `_apply_turn_feasibility`

**Consumed by.**

- outside it: `app/models/analysismodels.py:28 (warnings)` · `frontend/components/workbench/OperatingPointsPanel.tsx:483-488` · `app/services/add_turn_service.py:92`

**Source.** 🟡 PARTIAL

> Lennon Ch. 21 — margin against accelerated stall is the stated design reason for the CL_max check in turns
>
> — via `rc-aircraft-designer`

**⚠️ Divergence from the source.** The physical trigger is sourced; the status downgrade to LIMIT_REACHED is app policy. Lennon explicitly asks for a *margin* (E197 CL_max 1.17 vs demanded 0.85), not a bare V < V_s,turn test — the code has no margin, so a turn at exactly V_s,turn passes.

🟡 *Reported by the extraction pass, not independently verified.*

---
*Cluster [[_index-perf-oppoints|perf-oppoints]] · generated from the 2026-08-18 extraction.*
