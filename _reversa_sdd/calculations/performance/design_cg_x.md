---
name: design_cg_x
symbol: x_cg
kind: quantity
unit: m
cluster: perf-oppoints
user_visible: true
source_status: PARTIAL
code_audit: WRONG_LINE
node_class: derived
tags:
  - cluster/perf-oppoints
  - class/derived
  - source/partial
  - surface/user-visible
  - audit/wrong-line
  - flag/anomaly
  - flag/divergence
---

# Design CG x-position

**Definition.** Longitudinal CG used as the moment reference for every trim solve.

**Derived quantity.** Computed from the inputs below.

**Formula — as the code writes it.**

```
if row.active_source == "CALCULATED" and row.calculated_value is not None: return float(row.calculated_value); return float(row.estimate_value)
```

**Inputs.** — *(leaf: a constant or an external input)*

**Produced by.** `app/services/operating_point_generator_service.py:245` — `_load_design_cg_x`

🟠 **Corrected by the audit** — the extraction claimed `WRONG_LINE`. Original line was `244`. Line 244 is a guard, lines 245/246 return values

**Consumed by.**

- in this graph: `Operating-point moment reference`  
  *(these are backlinks — open the Backlinks pane to navigate them)*
- outside it: `app/services/operating_point_generator_service.py:1116 (asb_airplane.xyz_ref)` · `app/services/operating_point_generator_service.py:1027, 1582 (xyz_ref field)`

**Source.** 🟡 PARTIAL

> Sadraey §11 (CG range) and AeroSandbox Airplane reference — xyz_ref is the moment reference point; aircraft moments are taken about the CG
>
> — via `aircraft-design-scholz, aerosandbox-expert`

**⚠️ Divergence from the source.** Using the CG as the moment reference is the correct and sourced convention. The 0.0 fallback when no cg_x assumption exists is not: it silently places the moment reference at the nose, which changes Cm by (x_cg/c̄)·CL — a first-order error reported as a valid trim. Undeclared fallback (ADR 0020).

🟡 *Reported by the extraction pass, not independently verified.*

**⚠️ Anomaly.** Silent 0.0 fallback when no cg_x assumption row exists (line 243), which places the moment reference at the nose with no DesignWarning (ADR 0020).

🟡 *Reported by the extraction pass, not independently verified. Do not cite as a
defect until confirmed against the code.*

---
*Cluster [[_index-perf-oppoints|perf-oppoints]] · generated from the 2026-08-18 extraction.*
