---
name: cruise_speed_resolved
symbol: V_cruise
kind: quantity
unit: m/s
cluster: perf-oppoints
user_visible: true
source_status: PARTIAL
code_audit: CONFIRMED
node_class: derived
tags:
  - cluster/perf-oppoints
  - class/derived
  - source/partial
  - surface/user-visible
  - audit/confirmed
  - flag/divergence
---

# Resolved cruise speed

**Definition.** Cruise speed, replaced by the cached minimum-drag speed V_md when the aircraft has no flight profile.

**Derived quantity.** Computed from the inputs below.

**Formula — as the code writes it.**

```
cruise_from_goals = float(goals.get("cruise_speed_mps", 18.0)); if source_profile_id is not None: return cruise_from_goals; v_md = ctx.get("v_md_mps"); if isinstance(v_md, (int, float)) and v_md > 0: return float(v_md); return cruise_from_goals
```

**Inputs.**

- [[default_cruise_speed_mps|Default cruise speed]]  — *⤵ fallback*

**Produced by.** `app/services/operating_point_generator_service.py:277` — `_resolve_cruise_speed_with_md_fallback`

🟢 **Verified against the code** — an independent reviewer read this line and confirmed the formula, unit and value (2026-08-18 audit).

**Consumed by.**

- in this graph: `Vx target speed` · `Vy target speed` · `loiter_endurance target speed` · `Maximum level speed target` · `max_range target speed` · `Turn target speed` · `Clean stall speed reference`  
  *(these are backlinks — open the Backlinks pane to navigate them)*
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
