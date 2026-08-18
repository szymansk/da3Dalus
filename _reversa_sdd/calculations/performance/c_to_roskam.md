---
name: c_to_roskam
symbol: C_TO
kind: constant
unit: dimensionless
cluster: perf-matching
user_visible: true
source_status: PARTIAL
---

# Roskam takeoff ground-roll coefficient

**Definition.** Simplified-ground-roll regression coefficient in the Roskam takeoff formula.

**Value.** `1.21`

**Formula — as the code writes it.**

```
_C_TO: float = 1.21
```

**Inputs.** — *(leaf: a constant or an external input)*

**Produced by.** `app/services/field_length_service.py:72` — `_C_TO`

**Consumed by.**

- in this graph: [[s_to_ground|Takeoff ground roll]] · [[tw_takeoff_constraint|Takeoff constraint T/W]]
- outside it: `_compute_s_to_ground:203` · `matching_chart_service._takeoff_constraint:310`

**Source.** 🟡 PARTIAL

> Form: Scholz 05_PreliminarySizing §5.2 simplified ground roll s_TOG = (1/(rho*C_L,LOF)) * (g*m^2/S)/(T/(m*g)); exact counterpart Sadraey 2013 Eq. 4.66/4.71 §4.3.4. The value 1.21 is NOT in either source; it is exactly (1.1)^2, i.e. V_LOF = 1.1*V_S substituted into s = V_LOF^2/(2*g*(T/W)).
>
> — via `aircraft-design-scholz`

**The source states it as.**

```
s_G = (V_LOF/V_S)^2 * (W/S)/(g*rho*CL_max*(T/W))
```

**⚠️ Divergence from the source.** Two problems. (1) The docstring claim that 1.21 'bakes in the T_mean/T_static ratio for a piston GA aircraft' is unsupported: 1.21 is a purely kinematic factor (V_LOF/V_S)^2, nothing to do with thrust lapse. That invalidates the stated justification for _T_STATIC_MEAN_FACTOR = 1.0. (2) 1.21 implies V_LOF = 1.1*V_S, but the module's own _V_LOF_FACTOR is 1.2; Scholz §5.2 also assumes 1.2, which would give 1.44. The takeoff roll and the reported V_LOF are internally inconsistent. Roskam is not in the consulted vault, so '§3.4' is unverifiable.

🟡 *Reported by the extraction pass, not independently verified.*

**⚠️ Scale (ADR 0023).** The (1.1)^2 derivation is scale-free and legitimate at 0.5-15 kg, but only if acceleration really is a ~ g*(T/W). For an electric model the static-thrust curve decays strongly with airspeed, so constant-thrust is a worse assumption here than for the GA piston aircraft the constant is associated with.

> This application targets RC/UAV aircraft of **0.5–15 kg**. A constant is not
> justified by being standard in transport-category literature.

**⚠️ Anomaly.** Module docstring claims this constant already bakes in the T_mean/T_static ratio for a piston GA aircraft; adopted unchanged for 0.5–15 kg electric models (ADR 0023).

🟡 *Reported by the extraction pass, not independently verified. Do not cite as a
defect until confirmed against the code.*

**Cited in the code itself.** `# Roskam §3.4 simplified ground-roll coefficient`

---
*Cluster [[_index-perf-matching|perf-matching]] · generated from the 2026-08-18 extraction.*
