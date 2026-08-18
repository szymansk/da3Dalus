---
name: combo-eta-total
symbol: eta_total
kind: quantity
unit: dimensionless (0..1)
cluster: powertrain
user_visible: true
source_status: SOURCED
code_audit: CONFIRMED
node_class: derived
tags:
  - cluster/powertrain
  - class/derived
  - source/sourced
  - surface/user-visible
  - audit/confirmed
  - flag/anomaly
  - flag/divergence
---

# Combo total propulsive efficiency

**Definition.** Chain efficiency from battery to thrust: propeller x motor x ESC, each taken from the request or the endurance-service default.

**Derived quantity.** Computed from the inputs below.

**Formula — as the code writes it.**

```
eta_total = eta_prop * eta_motor * eta_esc
```

**Inputs.**

- [[default-eta-prop-endurance|Default propeller efficiency]]  — *⤵ fallback*
- [[default-eta-motor-endurance|Default motor efficiency (sizing path)]]  — *⤵ fallback*
- [[default-eta-esc-endurance|Default ESC efficiency]]  — *⤵ fallback*

**Produced by.** `app/services/powertrain_sizing_service.py:238` — `_evaluate_motor_battery_combo`

🟢 **Verified against the code** — an independent reviewer read this line and confirmed the formula, unit and value (2026-08-18 audit).

**Consumed by.**

- in this graph: `Estimated cruise power` · `Power required for a motor+battery combo`  
  *(these are backlinks — open the Backlinks pane to navigate them)*
- outside it: `app/services/powertrain_sizing_service.py:249`

**Source.** 🟢 SOURCED

> Sadraey (2013), §8.8.1, Eq. 8.15: eta_P = T V / P_in, 'valid for all prop-driven engines - piston, turboprop, solar-powered, electric, and even human-powered'. The chain decomposition into prop x motor x ESC follows from Drela, 'DC Motor / Propeller Matching' §1.2 (eta_m = P_shaft/(V I)) applied in series with the propeller efficiency of Deters/Ananda/Selig 2014 §II.D Eq. 7.
>
> — via `aircraft-design-scholz / rc-aircraft-designer`

**The source states it as.**

```
eta_P = T V / P_in  (Sadraey Eq. 8.15);  eta_m = P_shaft/(V I)  (Drela §1.2);  eta = J C_T/C_P  (Deters §II.D eq 7)
```

**⚠️ Divergence from the source.** The multiplicative chain is a correct composition of the cited definitions. What no source supports is holding eta_motor constant across every catalog motor: Drela §1.2 makes eta_m an explicit function of (i, Omega, R, i0, Kv), and the code has R, i0 and Kv available in the same catalog it is sweeping.

🟡 *Reported by the extraction pass, not independently verified.*

**⚠️ Anomaly.** eta_motor here is a flat request/default value; the catalog motor's own efficiency_pct (which powertrain_performance.py:145 does read) is ignored, so the sweep rates every motor with the same efficiency.

🟡 *Reported by the extraction pass, not independently verified. Do not cite as a
defect until confirmed against the code.*

---
*Cluster [[_index-powertrain|powertrain]] · generated from the 2026-08-18 extraction.*
