---
name: ss-v-cruise
symbol: V_cruise
kind: quantity
unit: m/s
cluster: powertrain
user_visible: true
source_status: NO_SOURCE_FOUND
---

# Cruise speed (solution space)

**Definition.** Cruise speed from the computation context, preferring v_cruise_mps and falling back to v_md_mps (minimum-drag speed), then to a hardcoded 15 m/s with a warning.

**Formula — as the code writes it.**

```
v_cruise_ctx: float | None = ctx.get("v_cruise_mps") or ctx.get("v_md_mps") ; if v_cruise_ctx is None or v_cruise_ctx <= 0: warnings.append(...) ; v_cruise_ctx = 15.0
```

**Inputs.** — *(leaf: a constant or an external input)*

**Produced by.** `app/services/powertrain_solution_space_service.py:299` — `compute_solution_space`

**Consumed by.**

- in this graph: [[ss-p-aero-cruise|Aerodynamic power at cruise]] · [[ss-v-top|Top speed used for peak sizing]]
- outside it: `app/services/powertrain_solution_space_service.py:325` · `app/services/powertrain_solution_space_service.py:336` · `app/services/powertrain_solution_space_service.py:349` · `frontend/components/workbench/PowertrainTab.tsx:1144`

**Source.** 🔴 NO SOURCE FOUND

>
> — via `aircraft-design-scholz`
> No citable source was found. **This is recorded, not filled in.** The value is
> in the code without an attributable origin.

**The source states it as.**

```
Sadraey (2013) §4.6 treats V_C (cruise) and V_max as distinct design requirements; V_md (minimum drag / best glide) is a third, separate speed at which (L/D)_max occurs.
```

**⚠️ Divergence from the source.** The 15.0 m/s fallback is unattributed. More significant is the silent substitution of v_md_mps for v_cruise_mps when the latter is absent: in Sadraey's framework V_md and V_C are different design points (V_md maximises L/D, V_C is the mission requirement), and sizing the powertrain at V_md rather than the intended cruise shifts both the energy budget and, through V_top = 1.4 V_cruise, the peak-power point.

🟡 *Reported by the extraction pass, not independently verified.*

**⚠️ Anomaly.** Silently substitutes V_md (best-glide / minimum-drag speed) for cruise speed when v_cruise_mps is absent. These are different design points — sizing the powertrain at V_md rather than the intended cruise changes both the energy budget and the peak-power point, and the response says only that the context was read, not that a different speed definition was used.

🟡 *Reported by the extraction pass, not independently verified. Do not cite as a
defect until confirmed against the code.*

**Cited in the code itself.** `NO_SOURCE_FOUND for 15.0 (matches design_assumption.py:107 design_speed_mps default of 15.0)`

---
*Cluster [[_index-powertrain|powertrain]] · generated from the 2026-08-18 extraction.*
