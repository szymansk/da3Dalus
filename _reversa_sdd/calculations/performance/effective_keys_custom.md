---
name: effective_keys_custom
symbol: effective_keys
kind: quantity
unit: n/a
cluster: perf-matching
user_visible: true
source_status: NO_SOURCE_FOUND
node_class: derived
tags:
  - cluster/perf-matching
  - class/derived
  - source/no-source-found
  - surface/user-visible
  - flag/anomaly
  - flag/divergence
---

# Effective constraint keys (custom fallback)

**Definition.** Constraint keys treated as active when no known profile is set.

**Derived quantity.** Computed from the inputs below.

**Formula — as the code writes it.**

```
effective_keys: list[str] = (list(_PROFILE_CONSTRAINT_MAP.get(profile_key, [])) if profile_key else list(_MISSION_MIN_TW_BY_PROFILE.keys()))
```

**Inputs.**

- [[profile_constraint_map|Per-profile applicable constraints]]
- [[mission_min_tw_table|Mission-min T/W table]]  — *⊣ limit*

**Produced by.** `app/services/matching_chart_service.py:1074` — `_build_rc_additive_constraints`

**Consumed by.**

- outside it: `_build_rc_additive_constraints:1155 (vertical-climb gate)`

**Source.** 🔴 NO SOURCE FOUND

> No source; implementation-level defect.
>
> — via `aircraft-design-scholz`
> No citable source was found. **This is recorded, not filled in.** The value is
> in the code without an attributable origin.

**⚠️ Divergence from the source.** Confirmed logic defect. The fallback branch yields PROFILE names ['acro_3d','wing_racer','sport'] but line 1155 tests `'vertical_climb' in effective_keys`, a CONSTRAINT key. The test can never be true, so the Vertical-Climb curve is never emitted for custom/unknown profiles despite the docstring promising it.

🟡 *Reported by the extraction pass, not independently verified.*

**⚠️ Anomaly.** The fallback branch yields PROFILE names ['acro_3d','wing_racer','sport'] but line 1155 tests `"vertical_climb" in effective_keys` — a constraint key. The test can never be true, so the Vertical-Climb curve is never emitted for custom/unknown profiles despite the docstring promising it.

🟡 *Reported by the extraction pass, not independently verified. Do not cite as a
defect until confirmed against the code.*

**Cited in the code itself.** `# For "custom" / unknown we still emit the additives — they're tagged rc_specific and the caller marks applicable_for_profile=True.`

---
*Cluster [[_index-perf-matching|perf-matching]] · generated from the 2026-08-18 extraction.*
