---
name: default_max_level_speed_mps
kind: constant
unit: m/s
cluster: perf-oppoints
user_visible: true
source_status: NO_SOURCE_FOUND
---

# Default maximum level speed

**Definition.** Top level-flight speed target in the default profile.

**Value.** `28.0`

**Formula — as the code writes it.**

```
"max_level_speed_mps": 28.0
```

**Inputs.** — *(leaf: a constant or an external input)*

**Produced by.** `app/services/operating_point_generator_service.py:205` — `_default_profile`

**Consumed by.**

- in this graph: [[v_max_level|Maximum level speed target]]
- outside it: `app/services/operating_point_generator_service.py:399 (v_max_level)` · `app/services/assumption_compute_service.py:1038`

**Source.** 🔴 NO SOURCE FOUND

> Nearest authority: Sadraey §4.3.3.2 — 'V_max ≈ 1.2–1.3 V_C if only cruise speed is specified (cruise is at 75–80 % power)'
>
> — via `aircraft-design-scholz`
> No citable source was found. **This is recorded, not filled in.** The value is
> in the code without an attributable origin.

**⚠️ Divergence from the source.** 28.0 against the 18.0 cruise default is V_max = 1.56 V_C, well outside Sadraey's 1.2–1.3 band. The pair of defaults is internally inconsistent with the only published rule linking them.

🟡 *Reported by the extraction pass, not independently verified.*

---
*Cluster [[_index-perf-oppoints|perf-oppoints]] · generated from the 2026-08-18 extraction.*
