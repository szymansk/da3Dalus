---
name: profile_constraint_map
symbol: —
kind: constant
unit: n/a
cluster: perf-matching
user_visible: true
source_status: NO_SOURCE_FOUND
---

# Per-profile applicable constraints

**Definition.** Mapping from mission profile to the constraint keys drawn for it.

**Value.** `trainer:[stall,climb,power_loading,wcl]; sport:[stall,climb,mission_min_tw,power_loading,wcl]; wing_racer:[stall,cruise,power_loading]; acro_3d:[stall,mission_min_tw,power_loading,vertical_climb]; stol_bush:[stall,takeoff,landing,climb]; slope_soarer:[stall]; glider:[stall]; sailplane:[stall]; motor_glider:[stall,climb,cruise]; flying_wing:[stall,climb,cruise]`

**Formula — as the code writes it.**

```
_PROFILE_CONSTRAINT_MAP: dict[str, list[str]] = {...}
```

**Inputs.** — *(leaf: a constant or an external input)*

**Produced by.** `app/services/matching_chart_service.py:103` — `_PROFILE_CONSTRAINT_MAP`

**Consumed by.**

- in this graph: [[applicable_for_profile|Profile applicability flag]] · [[effective_keys_custom|Effective constraint keys (custom fallback)]]
- outside it: `compute_chart:977` · `_build_rc_additive_constraints:1075` · `ConstraintLine.applicable_for_profile → frontend`

**Source.** 🔴 NO SOURCE FOUND

> No source. Sadraey §4.3.1 selects constraints from the aircraft's stated REQUIREMENTS (stall, max speed, takeoff, ROC, ceiling, landing), not from a mission-profile taxonomy; the RC profile names have no counterpart in either authority.
>
> — via `aircraft-design-scholz`
> No citable source was found. **This is recorded, not filled in.** The value is
> in the code without an attributable origin.

**⚠️ Divergence from the source.** Two consequences that contradict the sources' method. (1) No profile lists 'hand_launch', so that constraint is always filtered out. (2) Every non-STOL profile drops takeoff AND landing, so field length is silently absent from the chart for trainer/sport/acro - yet Sadraey §4.3.1 and Scholz §5.1-5.2 treat takeoff and landing as the constraints that most often BIND the feasible region. Hiding them by default inverts the method's priorities.

🟡 *Reported by the extraction pass, not independently verified.*

**⚠️ Anomaly.** No profile lists 'hand_launch', so that constraint is always filtered out; and every non-STOL profile drops takeoff+landing, meaning field length is silently absent from the chart for trainer/sport/acro.

🟡 *Reported by the extraction pass, not independently verified. Do not cite as a
defect until confirmed against the code.*

**Cited in the code itself.** `# These match the MissionPreset ids seeded in app/services/mission_preset_seed.py except for "glider" which maps to the "sailplane" preset (gh-613 spec uses "glider"). "custom" → no entry → back-compat: every constraint is applicable.`

---
*Cluster [[_index-perf-matching|perf-matching]] · generated from the 2026-08-18 extraction.*
