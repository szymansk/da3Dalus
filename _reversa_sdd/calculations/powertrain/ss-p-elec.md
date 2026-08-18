---
name: ss-p-elec
symbol: P_elec
kind: quantity
unit: W
cluster: powertrain
user_visible: true
source_status: SOURCED
---

# Electrical power required

**Definition.** Battery-side electrical power: aerodynamic power divided by the full propulsive chain efficiency.

**Formula — as the code writes it.**

```
eta = eta_prop * eta_motor * eta_esc ; if eta <= 0: return float("inf") ; return p_aero_w / eta
```

**Inputs.** [[ss-p-aero|Aerodynamic power]] · [[ss-eta-prop-lo|Propeller efficiency band lower bound]] · [[ss-eta-prop-hi|Propeller efficiency band upper bound]] · [[ss-eta-motor|Motor efficiency (solution space)]] · [[ss-eta-esc|ESC efficiency (solution space)]]

**Produced by.** `app/services/powertrain_solution_space_service.py:113` — `_p_elec`

**Consumed by.**

- in this graph: [[ss-i-peak|Peak battery current]] · [[ss-p-cruise-hi-e|Electrical cruise power at high prop efficiency]] · [[ss-p-cruise-lo-e|Electrical cruise power at low prop efficiency]] · [[ss-p-cruise-mid|Electrical cruise power (mid band)]] · [[ss-p-top-hi-e|Electrical peak power at high prop efficiency]] · [[ss-p-top-lo-e|Electrical peak power at low prop efficiency]] · [[ss-p-top-mid|Electrical peak power (mid band)]]
- outside it: `app/services/powertrain_solution_space_service.py:360` · `app/services/powertrain_solution_space_service.py:361` · `app/services/powertrain_solution_space_service.py:363` · `app/services/powertrain_solution_space_service.py:367` · `app/services/powertrain_solution_space_service.py:369` · `app/services/powertrain_solution_space_service.py:372`

**Source.** 🟢 SOURCED

> Sadraey (2013), §8.8.1, Eq. 8.15: eta_P = T V / P_in, 'valid for all prop-driven engines - piston, turboprop, solar-powered, electric, and even human-powered'; rearranged P_in = T V / eta. The three-stage chain follows from Deters/Ananda/Selig 2014 §II.D eq 7 (propeller) and Drela §1.2 (motor).
>
> — via `aircraft-design-scholz / rc-aircraft-designer`

**The source states it as.**

```
P_in = T V / eta_P  (Sadraey Eq. 8.15);  chain eta = eta_prop x eta_motor x eta_esc
```

**Cited in the code itself.** `docstring: "Electrical power [W] = P_aero / (η_prop · η_motor · η_esc)."`

---
*Cluster [[_index-powertrain|powertrain]] · generated from the 2026-08-18 extraction.*
