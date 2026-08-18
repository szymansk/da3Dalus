---
name: mkpi_climb_energy
symbol: (C_L^1.5/C_D)_max
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
  - flag/divergence
---

# KPI: climb-energy figure

**Definition.** Maximum power-factor of the parabolic polar, proxy for rate of climb and thermalling.

**Derived quantity.** Computed from the inputs below.

**Formula — as the code writes it.**

```
value = (3.0 * math.pi * e * ar) ** 0.75 / (4.0 * cd0**0.25)
```

**Inputs.**

- [[mkpi_resolve_polar|Clean-polar provenance chain]]  — *⤵ fallback*

**Produced by.** `app/services/mission_kpi_service.py:213` — `_kpi_climb_energy`

🟢 **Verified against the code** — an independent reviewer read this line and confirmed the formula, unit and value (2026-08-18 audit).

**Consumed by.**

- outside it: `MissionRadarChart.tsx` · `AxisDrawer.tsx`

**Source.** 🟢 SOURCED

> Derivation verified algebraically and matches the published optimum: at minimum power C_L* = sqrt(3*C_D0/k) and C_D* = 4*C_D0 — Sadraey §4.2.5.4 (Eq. 4.22, (L/D)_Emax = 0.866*(L/D)_max) and §4.3 (ROC prop-driven, C_L = sqrt(3*C_Do/K), V_Pmin = 0.76*V_Dmin).
>
> — via `scholz`

**The source states it as.**

```
(C_L^1.5/C_D)_max = (3*pi*e*AR)^0.75 / (4*C_D0^0.25)
```

**⚠️ Divergence from the source.** The in-code derivation is correct and self-consistent; it is described as self-derived but is in fact standard and CAN be cited to Sadraey §4.2.5.4 / §4.3. Worth attaching the citation — it upgrades an apparently ad-hoc formula to a sourced one at zero cost.

🟡 *Reported by the extraction pass, not independently verified.*

**Cited in the code itself.** `derivation given inline: "CD = CD0 + CL^2/(π·e·AR). Setting d(CL^1.5/CD)/dCL = 0 gives 1.5·CD = 2·k·CL^2 with k = 1/(π·e·AR), so CL*^2 = 3·π·e·AR·CD0 and CD* = 4·CD0." — self-derived, no external reference`

---
*Cluster [[_index-perf-envelope|perf-envelope]] · generated from the 2026-08-18 extraction.*
