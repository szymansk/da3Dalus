---
name: mkpi_glide
symbol: (L/D)_max
kind: quantity
unit: -
cluster: perf-envelope
user_visible: true
source_status: SOURCED
code_audit: CONFIRMED
node_class: derived
tags:
  - cluster/perf-envelope
  - class/derived
  - source/sourced
  - surface/user-visible
  - audit/confirmed
  - flag/anomaly
  - flag/divergence
---

# KPI: maximum glide ratio

**Definition.** Best lift-to-drag ratio, empirical from the sweep when available, else parabolic-polar closed form.

**Derived quantity.** Computed from the inputs below.

**Formula — as the code writes it.**

```
value = float(ld_emp) if ld_emp is not None else 0.5 * math.sqrt(math.pi * e * ar / cd0)
```

**Inputs.**

- [[mkpi_resolve_polar|Clean-polar provenance chain]]  — *⤵ fallback*

**Produced by.** `app/services/mission_kpi_service.py:182` — `_kpi_glide`

🟢 **Verified against the code** — an independent reviewer read this line and confirmed the formula, unit and value (2026-08-18 audit).

**Consumed by.**

- outside it: `MissionRadarChart.tsx` · `AxisDrawer.tsx`

**Source.** 🟢 SOURCED

> Confirmed independently by two authorities: Anderson, Fundamentals of Aerodynamics 6e §6.7.2-6.7.3 (differentiate C_L/C_D, C_D0 = C_L^2/(pi*e*AR) at the optimum); and Scholz, Flugzeugentwurf 05_PreliminarySizing §5.7 Eq. 5.39.
>
> — via `aero, scholz`

**The source states it as.**

```
(L/D)_max = 0.5*sqrt(pi*e*AR/C_D0)
```

**⚠️ Divergence from the source.** Best-sourced formula in the cluster, undermined by its own UI string: the `formula` shipped to AxisDrawer is UNCONDITIONALLY the parabolic closed form, while the value is usually the empirical ld_max from the sweep. Provenance is reported as 'computed' in both cases, so the user is shown a formula that did not produce the number and has no way to tell which branch ran.

🟡 *Reported by the extraction pass, not independently verified.*

**⚠️ Anomaly.** The `formula` string shipped to the AxisDrawer is unconditionally the parabolic closed form, but the value is usually the empirical ld_max from the sweep. The user is shown a formula that did not produce the number, with provenance 'computed' in both cases.

🟡 *Reported by the extraction pass, not independently verified. Do not cite as a
defect until confirmed against the code.*

**Cited in the code itself.** `formula string exposed to the UI: "(L/D)_max = 0.5 · √(π · e · AR / C_D0)"`

---
*Cluster [[_index-perf-envelope|perf-envelope]] · generated from the 2026-08-18 extraction.*
