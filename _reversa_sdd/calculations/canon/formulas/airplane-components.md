---
canon: airplane-components
entry: formula
kind: procedure
tool: KAT
shape: law
status: draft
output: battery-mass, battery-capacity, battery-specific-energy, propulsive-efficiency, motor-voltage-constant, motor-no-load-current, motor-circuit-resistance, battery-voltage, motor-max-power
source_status: SOURCED
dimensional_check: PROCEDURAL
tags:
  - canon/formula
  - source/sourced
  - dim/procedural
  - shape/law
  - kind/procedure
  - status/draft
---

# Component properties of the airplane

**Canonical form**

```
m_bat, E_bat, E_star, eta_total, K_v, I_0, R_m, U_bat, P_mot,max := components of the airplane
```

**Produces** [[battery-mass]] · [[battery-capacity]] · [[battery-specific-energy]] · [[propulsive-efficiency]] · [[motor-voltage-constant]] · [[motor-no-load-current]] · [[motor-circuit-resistance]] · [[battery-voltage]] · [[motor-max-power]]  ·  **from** [[airplane]]

**Kind: a procedure — an evaluation of the model.** Battery data, static thrust and the
drive-train efficiency belong to the components the aircraft is built from — motor,
propeller, battery, structure. They are read from the component tree and the parts
catalogue, not chosen per calculation.

**Why this entry exists.** As free inputs they hid that swapping a battery or a motor
changes the mass, the thrust and with them everything downstream. The graph now says it.

`propulsive-efficiency` is the weaker route — a single constant where the tables give the
propeller's efficiency as a function of advance ratio. The nameplate static thrust is gone
(2026-10-02): it names neither voltage nor propeller; static thrust is computed instead.

**Motor and battery for the torque balance** (added 2026-10-01): `K_v`, `I_0` and `R_m` of the fitted motor, `U_bat` from the cell count. `R_m` and some `I_0` are missing from the catalogue (#1149) — `R_m` absent → route A, never estimated (`Q-PT-6`); `I_0` absent → the torque balance runs with `I_0 = 0` (BR-PT15), declared.
