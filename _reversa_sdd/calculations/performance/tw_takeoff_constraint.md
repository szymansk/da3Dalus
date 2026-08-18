---
name: tw_takeoff_constraint
symbol: (T/W)_TO
kind: quantity
unit: dimensionless
cluster: perf-matching
user_visible: true
source_status: PARTIAL
code_audit: CONFIRMED
node_class: derived
tags:
  - cluster/perf-matching
  - class/derived
  - source/partial
  - surface/user-visible
  - audit/confirmed
  - flag/anomaly
  - flag/divergence
  - flag/scale
---

# Takeoff constraint T/W

**Definition.** Minimum T/W to reach the takeoff field-length target at a given W/S.

**Derived quantity.** Computed from the inputs below.

**Formula — as the code writes it.**

```
return (_C_TO * _K_TO_50FT * ws) / (rho * g * cl_max_to * s_runway)
```

**Inputs.**

- [[ws_range_mc|W/S sweep vector]]
- [[mode_default_s_runway|Mode default field length]]  — *⤵ fallback*
- [[cl_max_to_mc|Takeoff CL_max (matching chart)]]  — *⤵ fallback*
- [[rho_sl|Sea-level ISA density]]  — *⤵ fallback*
- [[g_gravity|Standard gravity]]
- [[c_to_roskam|Roskam takeoff ground-roll coefficient]]
- [[k_to_50ft|Takeoff 50-ft obstacle factor]]

**Produced by.** `app/services/matching_chart_service.py:310` — `_takeoff_constraint`

🟢 **Verified against the code** — an independent reviewer read this line and confirmed the formula, unit and value (2026-08-18 audit).

**Consumed by.**

- outside it: `to_tw:843` · `constraints_raw 'Takeoff':885` · `MatchingChartResponse.constraints` · `frontend MatchingChartTab.tsx`

**Source.** 🟡 PARTIAL

> Form SOURCED: Scholz 05_PreliminarySizing §5.2 / Loftin (1980) - T_TO/(m*g) = k_TO/(s_TOF*sigma*CL_max,TO) * (m/S_W), i.e. T/W linear in W/S and inverse in s, sigma and CL_max, with k_TO = 2.34 m^3/kg. Sadraey's exact equivalents are Eq. 4.71 (jet) / 4.76 (prop). The code's composite coefficient C_TO*k_50ft = 1.21*1.66 = 2.009 is not from either source.
>
> — via `aircraft-design-scholz`

**The source states it as.**

```
T/(m*g) = k_TO/(s_TOF*sigma*CL_max,TO) * (m/S_W), k_TO = 2.34 m^3/kg
```

**⚠️ Divergence from the source.** Structurally identical to Loftin but numerically ~30% less demanding: converting k_TO = 2.34 into the code's rho-form gives 2.87 against the code's 2.009. Also the docstring attributes the line to 'Scholz §5.2.3' while the coefficient is actually a Roskam-lineage product - the attribution should not name Scholz for a constant Scholz does not give. Implementation notes: returns exactly 0.0 when s_runway <= 0 (undeclared constraint-disabled path, ADR 0020), and hover_text hardcodes the string 'C_TO=1.21' instead of interpolating _C_TO.

🟡 *Reported by the extraction pass, not independently verified.*

**⚠️ Scale (ADR 0023).** k_TO = 2.34 is a JET-TRANSPORT statistical correlation (Loftin 1980) and must not be adopted at 0.5-15 kg. The code does not use it, which is correct - but the alternative it does use is a GA regression ratio, so neither path is RC-validated (ADR 0023).

> This application targets RC/UAV aircraft of **0.5–15 kg**. A constant is not
> justified by being standard in transport-category literature.

**⚠️ Anomaly.** Returns exactly 0.0 when s_runway <= 0 — an undeclared 'constraint disabled' path with no DesignWarning (ADR 0020); the hover_text at line 896 hardcodes the string "C_TO=1.21" instead of interpolating _C_TO, defeating the module's stated zero-drift goal.

🟡 *Reported by the extraction pass, not independently verified. Do not cite as a
defect until confirmed against the code.*

**Cited in the code itself.** `"Minimum T/W required to meet takeoff field length target (Scholz §5.2.3). Derived from Roskam §3.4 simplified ground-roll"`

---
*Cluster [[_index-perf-matching|perf-matching]] · generated from the 2026-08-18 extraction.*
