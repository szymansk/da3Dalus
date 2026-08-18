---
name: required_capabilities_for_target
kind: quantity
unit: dimensionless
cluster: perf-oppoints
user_visible: false
source_status: PARTIAL
code_audit: CONFIRMED
node_class: derived
tags:
  - cluster/perf-oppoints
  - class/derived
  - source/partial
  - audit/confirmed
  - flag/anomaly
  - flag/divergence
---

# Required capabilities per target

**Definition.** Capability flags a named target requires before it may be solved.

**Derived quantity.** Computed from the inputs below.

**Formula — as the code writes it.**

```
if target_name.startswith("turn_"): return {"has_roll_control|has_yaw_control"}; if target_name == "dutch_role_start": return {"has_yaw_control"}; if target_name == "stall_with_flaps": return {"has_flap"}; return set()
```

**Inputs.** — *(leaf: a constant or an external input)*

**Produced by.** `app/services/operating_point_generator_service.py:557` — `_required_capabilities_for_target`

🟢 **Verified against the code** — an independent reviewer read this line and confirmed the formula, unit and value (2026-08-18 audit).

**Consumed by.**

- outside it: `app/services/operating_point_generator_service.py:576 (_validate_target_capability)` · `app/tests/test_turn_default_targets.py:35`

**Source.** 🟡 PARTIAL

> Sadraey §12.1 and §12.4.3 (adverse yaw): 'a coordinated turn combines lateral and directional motions' — the pilot must apply rudder together with aileron; without it the turn is uncoordinated (slip/skid)
>
> — via `aircraft-design-scholz`

**⚠️ Divergence from the source.** The code requires has_roll_control OR has_yaw_control for a turn. Per the source a COORDINATED turn needs both (roll to bank, yaw to suppress sideslip); an aircraft with only one would produce an uncoordinated turn, which is not what the target claims to compute. Also the turn_ branch is unreachable in production (guard returns first) — dead code (ADR 0021).

🟡 *Reported by the extraction pass, not independently verified.*

**⚠️ Anomaly.** The turn_ branch is unreachable from production code — _validate_target_capability returns at line 571-574 before calling this function — so that branch is exercised only by a test (ADR 0021).

🟡 *Reported by the extraction pass, not independently verified. Do not cite as a
defect until confirmed against the code.*

---
*Cluster [[_index-perf-oppoints|perf-oppoints]] · generated from the 2026-08-18 extraction.*
