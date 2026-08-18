---
name: polar-samples-input
symbol: polar_samples
kind: parameter
unit: mixed
cluster: powertrain
user_visible: false
source_status: SOURCED
code_audit: CONFIRMED
node_class: unclassified-parameter
tags:
  - cluster/powertrain
  - class/unclassified-parameter
  - source/sourced
  - audit/confirmed
  - flag/anomaly
  - flag/divergence
---

# Propeller polar rows

**Definition.** APC PER3 measurement rows (rpm, J, Ct, Cp, Pe, PWR_W, Torque_Nm, Thrust_N) loaded from propeller_polar_samples.

⚪ **Unclassified parameter.** Not yet decided whether this is a user input or an internal tuning value.

**Inputs.** — *(leaf: a constant or an external input)*

**Produced by.** `app/services/powertrain_performance.py:216` — `PowertrainPerformanceRequest.polar_samples`

🟢 **Verified against the code** — an independent reviewer read this line and confirmed the formula, unit and value (2026-08-18 audit).

**Consumed by.**

- in this graph: `Propeller power coefficient` · `Propeller thrust coefficient`  
  *(these are backlinks — open the Backlinks pane to navigate them)*
- outside it: `app/services/powertrain_performance.py:736` · `app/services/powertrain_performance.py:716` · `app/api/v2/endpoints/aeroplane/powertrain_performance.py:151`

**Source.** 🟢 SOURCED

> Brandt, J.B. & Selig, M.S., 'Propeller Performance Data at Low Reynolds Numbers', AIAA 2011-1255, §III eqs. 4-7 and the UIUC propeller database it documents — the measured (RPM, J, C_T, C_P, eta) tables for APC and other small propellers are exactly this dataset's structure. RC-Network Wiki, 'APC-E' documents the APC Electro Flight propeller line the polars cover.
>
> — via `rc-aircraft-designer`

**The source states it as.**

```
Measured rows of J, C_T, C_P, eta at fixed RPM (Brandt & Selig §III)
```

**⚠️ Divergence from the source.** Brandt & Selig report C_T, C_P and eta as the primary measured/derived quantities. The code loads a stored Pe column and stored Torque_Nm/Thrust_N and then discards all three, recomputing from C_T/C_P.

🟡 *Reported by the extraction pass, not independently verified.*

**⚠️ Anomaly.** Three of the eight loaded columns (Pe, Torque_Nm, Thrust_N) are read from the DB by the endpoint (lines 157-160) and never used — two of them explicitly annotated as unused.

🟡 *Reported by the extraction pass, not independently verified. Do not cite as a
defect until confirmed against the code.*

**Cited in the code itself.** `dataclass comments: "Torque_Nm: stored torque — NOT used for physics; see docstring" / "Thrust_N: stored thrust — NOT used for physics; see docstring"`

---
*Cluster [[_index-powertrain|powertrain]] · generated from the 2026-08-18 extraction.*
