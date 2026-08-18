---
name: cd0_resolved
symbol: CD0
kind: parameter
unit: dimensionless
cluster: perf-matching
user_visible: true
source_status: PARTIAL
code_audit: CONFIRMED
node_class: unclassified-parameter
tags:
  - cluster/perf-matching
  - class/unclassified-parameter
  - source/partial
  - surface/user-visible
  - audit/confirmed
  - flag/anomaly
  - flag/divergence
  - flag/scale
---

# Resolved zero-lift drag

**Definition.** Scalar zero-lift drag coefficient with a hardcoded fallback.

⚪ **Unclassified parameter.** Not yet decided whether this is a user input or an internal tuning value.

**Value.** `0.03 (fallback)`

**Formula — as the code writes it.**

```
cd0: float = float(aircraft.get("cd0", 0.03))
```

**Inputs.** — *(leaf: a constant or an external input)*

**Produced by.** `app/services/matching_chart_service.py:803` — `compute_chart`

🟢 **Verified against the code** — an independent reviewer read this line and confirmed the formula, unit and value (2026-08-18 audit).

**Consumed by.**

- in this graph: `Reynolds-dependent CD0` · `Vertical-climb T/W` · `Resolved cruise speed` · `Minimum-drag speed`  
  *(these are backlinks — open the Backlinks pane to navigate them)*
- outside it: `_v_md:858` · `_climb_tw_at_ws` · `_vertical_climb_constraint:1159` · `hover_text:940`

**Source.** 🟡 PARTIAL

> Sadraey 2013 Table 4.12 §4.3.3.1 gives C_Do by aircraft class (jet transport ~0.015-0.020), with Eq. 4.60 to back-calculate from comparable aircraft. 0.03 is not one of the tabulated class values but is plausible for a draggy light airframe.
>
> — via `aircraft-design-scholz`

**The source states it as.**

```
C_Do from Sadraey Table 4.12 by class, or Eq. 4.60 back-calculated
```

**⚠️ Divergence from the source.** Silent 0.03 fallback with no DesignWarning, duplicated at matching_chart_service.py:793 and matching_chart.py:81 (ADR 0020 + ADR 0022).

🟡 *Reported by the extraction pass, not independently verified.*

**⚠️ Scale (ADR 0023).** Table 4.12 covers manned classes only. RC/UAV airframes at Re ~1e5 with exposed servos, wire and fixed gear typically run C_Do well above 0.03, so the fallback is optimistic for this class and has no RC-scale table behind it.

> This application targets RC/UAV aircraft of **0.5–15 kg**. A constant is not
> justified by being standard in transport-category literature.

**⚠️ Anomaly.** Silent 0.03 fallback, duplicated at line 793 and again at field_lengths-sibling endpoint matching_chart.py:81 — no DesignWarning (ADR 0020).

🟡 *Reported by the extraction pass, not independently verified. Do not cite as a
defect until confirmed against the code.*

---
*Cluster [[_index-perf-matching|perf-matching]] · generated from the 2026-08-18 extraction.*
