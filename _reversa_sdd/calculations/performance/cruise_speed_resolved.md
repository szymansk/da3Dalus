---
name: cruise_speed_resolved
symbol: V_cruise
kind: quantity
unit: m/s
cluster: perf-oppoints
user_visible: true
source_status: PARTIAL
---

# Resolved cruise speed

**Definition.** Cruise speed, replaced by the cached minimum-drag speed V_md when the aircraft has no flight profile.

**Formula — as the code writes it.**

```
cruise_from_goals = float(goals.get("cruise_speed_mps", 18.0)); if source_profile_id is not None: return cruise_from_goals; v_md = ctx.get("v_md_mps"); if isinstance(v_md, (int, float)) and v_md > 0: return float(v_md); return cruise_from_goals
```

**Inputs.** [[default_cruise_speed_mps|Default cruise speed]]

**Produced by.** `app/services/operating_point_generator_service.py:277` — `_resolve_cruise_speed_with_md_fallback`

**Consumed by.**

- in this graph: [[v_best_angle_climb_vx|Vx target speed]] · [[v_best_rate_climb_vy|Vy target speed]] · [[v_loiter_endurance|loiter_endurance target speed]] · [[v_max_level|Maximum level speed target]] · [[v_max_range|max_range target speed]] · [[v_turn|Turn target speed]] · [[vs_clean|Clean stall speed reference]]
- outside it: `app/services/operating_point_generator_service.py:1101 (profile goals)` · `app/services/operating_point_generator_service.py:398 and all target velocities` · `app/services/add_turn_service.py:47`

**Source.** 🟡 PARTIAL

> Sadraey §4.2.5.2: for a prop-driven aircraft 'optimum range is achieved when the aircraft flies at the minimum-drag speed, which is the L/D-maximum condition'
>
> — via `aircraft-design-scholz`

**⚠️ Divergence from the source.** Falling back to the cached V_md when no flight profile exists is defensible and matches the source's definition of the best cruise speed for a propeller aircraft. The substitution rule itself (profile present ⇒ ignore V_md) is app policy. Note the inconsistency: V_md is trusted here but ignored by v_max_range, which is the point that should use it.

🟡 *Reported by the extraction pass, not independently verified.*

**Cited in the code itself.** `When the aircraft has no flight profile, use V_md from the cached computation context as the cruise speed. Mirrors the chip behaviour in the Info Chip Row.`

---
*Cluster [[_index-perf-oppoints|perf-oppoints]] · generated from the 2026-08-18 extraction.*
