---
name: control_capabilities
kind: quantity
unit: dimensionless
cluster: perf-oppoints
user_visible: true
source_status: PARTIAL
---

# Control capability flags

**Definition.** Booleans stating which control axes the geometry provides, plus the sorted control-surface name list.

**Formula — as the code writes it.**

```
{"has_pitch_control": bool(roles_found & PITCH_ROLES), "has_roll_control": bool(roles_found & ROLL_ROLES), "has_yaw_control": bool(roles_found & YAW_ROLES), "has_flap": bool(roles_found & FLAP_ROLES), "available_controls": sorted(set(control_names))}
```

**Inputs.** [[pitch_roles|Pitch control role set]] · [[roll_roles|Roll control role set]] · [[yaw_roles|Yaw control role set]] · [[flap_roles|Flap control role set]]

**Produced by.** `app/services/operating_point_generator_service.py:548` — `_detect_control_capabilities`

**Consumed by.**

- outside it: `app/services/operating_point_generator_service.py:567-582 (_validate_target_capability)` · `app/services/operating_point_generator_service.py:613-615` · `app/services/add_turn_service.py:75` · `app/api/v2/endpoints/operating_points.py (ValidationError details)`

**Source.** 🟡 PARTIAL

> Sadraey §12.2, Table 12.4 — the enumeration of control-surface configurations and which axes each provides
>
> — via `aircraft-design-scholz`

**⚠️ Divergence from the source.** The taxonomy is sourced (see pitch/roll/yaw_roles). The boolean derivation is app logic. Finding: has_pitch_control is computed and never read — pitch is the one axis never validated before a trim solve, although Sadraey §12.5 makes elevator/pitch authority the primary trim constraint.

🟡 *Reported by the extraction pass, not independently verified.*

**⚠️ Anomaly.** has_pitch_control is computed but never read by any consumer — the pitch axis is the one axis never validated before a trim solve.

🟡 *Reported by the extraction pass, not independently verified. Do not cite as a
defect until confirmed against the code.*

---
*Cluster [[_index-perf-oppoints|perf-oppoints]] · generated from the 2026-08-18 extraction.*
