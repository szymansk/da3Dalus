---
name: v_approach
kind: quantity
unit: m/s
cluster: perf-oppoints
user_visible: true
source_status: SOURCED
---

# approach_landing target speed

**Definition.** Speed of the landing-approach operating point.

**Formula — as the code writes it.**

```
approach = float(goals.get("approach_speed_margin_vs_ldg", 1.30)) * refs["vs_ldg"]
```

**Inputs.** [[default_approach_speed_margin_vs_ldg|Default approach margin]] · [[vs_ldg|Landing-config stall speed reference]]

**Produced by.** `app/services/operating_point_generator_service.py:403` — `_build_target_definitions`

**Consumed by.**

- outside it: `app/services/operating_point_generator_service.py:475`

**Source.** 🟢 SOURCED

> Scholz 05_PreliminarySizing §5.1 citing CS 25.125 — stabilised approach at not less than 1.3 V_s
>
> — via `aircraft-design-scholz, rc-aircraft-designer`

**The source states it as.**

```
V_APP = 1.30 · V_S0
```

**⚠️ Divergence from the source.** Form matches exactly.

🟡 *Reported by the extraction pass, not independently verified.*

**⚠️ Scale (ADR 0023).** Transport-category (CS-25/FAR-25) rule applied to a 0.5–15 kg RC/UAV. The RC-scale authority (Lennon Ch. 4) uses 1.2·V_s for landing. ADR 0023 finding.

> This application targets RC/UAV aircraft of **0.5–15 kg**. A constant is not
> justified by being standard in transport-category literature.

---
*Cluster [[_index-perf-oppoints|perf-oppoints]] · generated from the 2026-08-18 extraction.*
