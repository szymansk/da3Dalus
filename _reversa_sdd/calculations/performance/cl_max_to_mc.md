---
name: cl_max_to_mc
symbol: CL_max_TO
kind: parameter
unit: dimensionless
cluster: perf-matching
user_visible: false
source_status: PARTIAL
---

# Takeoff CL_max (matching chart)

**Definition.** Takeoff CL_max for the takeoff constraint, defaulting to the clean value.

**Formula — as the code writes it.**

```
cl_max_to: float = float(aircraft.get("cl_max_takeoff", cl_max_clean))
```

**Inputs.** [[cl_max_clean_mc|Clean CL_max (matching chart)]]

**Produced by.** `app/services/matching_chart_service.py:808` — `compute_chart`

**Consumed by.**

- in this graph: [[tw_takeoff_constraint|Takeoff constraint T/W]]
- outside it: `_takeoff_constraint:843`

**Source.** 🟡 PARTIAL

> Scholz 05_PreliminarySizing §5.2 Table 5.1: CL_max,TO single-engine propeller 1.3-1.9, twin prop 1.4-2.0, business/jet transport 1.6-2.2. Sadraey Eq. 4.69c: CL_TO = CL_C + dCL_flap,TO with CL_flap_TO ~ 0.3-0.8. Defaulting CL_max,TO to the clean value is not sourced.
>
> — via `aircraft-design-scholz`

**The source states it as.**

```
CL_TO = CL_C + dCL_flap,TO (Sadraey Eq. 4.69c); class ranges Scholz Table 5.1
```

**⚠️ Divergence from the source.** Confirms the ADR 0022 finding: the endpoint (matching_chart.py:99-100) passes cl_max_takeoff = cl_max and cl_max_landing = cl_max*1.3, a hardcoded flap factor that bypasses field_length_service's _FLAP_FACTORS table. Same aircraft, two services, two different landing CL_max. Neither route matches the sources, which use additive increments.

🟡 *Reported by the extraction pass, not independently verified.*

**⚠️ Scale (ADR 0023).** Manned-aircraft class table.

> This application targets RC/UAV aircraft of **0.5–15 kg**. A constant is not
> justified by being standard in transport-category literature.

**⚠️ Anomaly.** The endpoint (matching_chart.py:99-100) passes cl_max_takeoff = cl_max and cl_max_landing = cl_max * 1.3 — a hardcoded flaps factor that bypasses field_length_service's _FLAP_FACTORS table, so the two services disagree on landing CL_max for the same aircraft (ADR 0022).

🟡 *Reported by the extraction pass, not independently verified. Do not cite as a
defect until confirmed against the code.*

---
*Cluster [[_index-perf-matching|perf-matching]] · generated from the 2026-08-18 extraction.*
