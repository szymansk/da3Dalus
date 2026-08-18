---
name: applicable_for_profile
symbol: applicable_for_profile
kind: quantity
unit: bool
cluster: perf-matching
user_visible: true
source_status: NO_SOURCE_FOUND
node_class: derived
tags:
  - cluster/perf-matching
  - class/derived
  - source/no-source-found
  - surface/user-visible
  - flag/divergence
---

# Profile applicability flag

**Definition.** Whether the constraint is drawn for the active mission profile.

**Derived quantity.** Computed from the inputs below.

**Formula — as the code writes it.**

```
if applicable_keys is None: c["applicable_for_profile"] = True else: c["applicable_for_profile"] = c.get("key") in applicable_keys
```

**Inputs.**

- [[profile_constraint_map|Per-profile applicable constraints]]

**Produced by.** `app/services/matching_chart_service.py:980` — `compute_chart`

**Consumed by.**

- outside it: `constraints_for_feasibility:989` · `ConstraintLine.applicable_for_profile` · `frontend/hooks/useMatchingChart.ts`

**Source.** 🔴 NO SOURCE FOUND

> Implementation flag deriving from profile_constraint_map, which is itself unsourced.
>
> — via `aircraft-design-scholz`
> No citable source was found. **This is recorded, not filled in.** The value is
> in the code without an attributable origin.

**⚠️ Divergence from the source.** Inherits the profile_constraint_map defect: hand_launch is never applicable, and takeoff/landing are suppressed for all non-STOL profiles.

🟡 *Reported by the extraction pass, not independently verified.*

**Cited in the code itself.** `# gh-613 Phase B: profile-aware applicability tagging`

---
*Cluster [[_index-perf-matching|perf-matching]] · generated from the 2026-08-18 extraction.*
