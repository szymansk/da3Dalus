---
canon: airplane-components
entry: formula
kind: procedure
tool: KAT
shape: law
status: draft
output: battery-mass, battery-capacity, battery-specific-energy, propulsive-efficiency, motor-voltage-constant, motor-no-load-current, motor-circuit-resistance, battery-voltage, motor-max-power, propeller-diameter
source_status: SOURCED
dimensional_check: PROCEDURAL
tags:
  - canon/formula
  - source/sourced
  - dim/procedural
  - shape/law
  - kind/procedure
  - status/draft
inputs: {components: components}
outputs:
  m_bat: battery-mass
  e_bat: battery-capacity
  e_star: battery-specific-energy
  eta_total: propulsive-efficiency
  k_v: motor-voltage-constant
  i_0: motor-no-load-current
  r_m: motor-circuit-resistance
  u_bat: battery-voltage
  p_mot_max: motor-max-power
  d_prop: propeller-diameter
---

# Component properties of the airplane

**Canonical form**

```
m_bat, E_bat, E_star, eta_total, K_v, I_0, R_m, U_bat, P_mot,max, D_prop := components of the airplane
```

**Produces** [[battery-mass]] · [[battery-capacity]] · [[battery-specific-energy]] · [[propulsive-efficiency]] · [[motor-voltage-constant]] · [[motor-no-load-current]] · [[motor-circuit-resistance]] · [[battery-voltage]] · [[motor-max-power]] · [[propeller-diameter]]  ·  **from** [[components]]

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

**Propeller diameter** (moved here from [[airplane-geometry]], maintainer 2026-10-16, D11 on #1174): `D_prop` is a property of the fitted propeller, the same component whose APC table [[propeller-table-lookup]] reads. The geometry format has no propeller, so a missing propeller fails only the drive-train chain, never the wing quantities.
