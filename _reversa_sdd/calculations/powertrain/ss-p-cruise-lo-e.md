---
name: ss-p-cruise-lo-e
symbol: p_cruise_lo_e
kind: quantity
unit: W
cluster: powertrain
user_visible: true
source_status: SOURCED
---

# Electrical cruise power at low prop efficiency

**Definition.** Cruise power at the pessimistic end of the propeller-efficiency band — the higher power number.

**Formula — as the code writes it.**

```
p_cruise_lo_e = _p_elec(p_aero_cruise, assumptions.eta_prop_lo, assumptions.eta_motor, assumptions.eta_esc)
```

**Inputs.** [[ss-p-elec|Electrical power required]] · [[ss-p-aero-cruise|Aerodynamic power at cruise]] · [[ss-eta-prop-lo|Propeller efficiency band lower bound]] · [[ss-eta-motor|Motor efficiency (solution space)]] · [[ss-eta-esc|ESC efficiency (solution space)]]

**Produced by.** `app/services/powertrain_solution_space_service.py:363` — `compute_solution_space`

**Consumed by.**

- in this graph: [[ss-band-energy-lo|Mission energy at low prop efficiency]]
- outside it: `app/services/powertrain_solution_space_service.py:400` · `app/services/powertrain_solution_space_service.py:437`

**Source.** 🟢 SOURCED

> Sadraey (2013), §8.8.1, Eq. 8.15 (P_in = T V / eta_P); the low-efficiency end of the band is taken from Deters, Ananda & Selig (2014) §VI (eta_max plateau 0.60-0.70 for small-scale low-Re propellers).
>
> — via `aircraft-design-scholz / rc-aircraft-designer`

**The source states it as.**

```
P_elec = P_aero / eta_total
```

**⚠️ Anomaly.** Assigned to the field named p_cruise_hi_w (line 437) — deliberate and documented (lo/hi refer to the POWER side, not the efficiency side), but the two naming conventions coexist in the same function and are easy to invert.

🟡 *Reported by the extraction pass, not independently verified. Do not cite as a
defect until confirmed against the code.*

**Cited in the code itself.** `# Electrical power at mid, lo, hi (lo η_prop → hi P_elec)`

---
*Cluster [[_index-powertrain|powertrain]] · generated from the 2026-08-18 extraction.*
