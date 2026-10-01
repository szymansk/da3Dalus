---
canon: airplane-components
entry: formula
kind: procedure
shape: law
status: draft
output: component-mass, battery-mass, battery-capacity, battery-specific-energy, static-thrust, propulsive-efficiency
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
m_i, m_bat, E_bat, E_star, T_static, eta_total := components of the airplane
```

**Produces** [[component-mass]] · [[battery-mass]] · [[battery-capacity]] · [[battery-specific-energy]] · [[static-thrust]] · [[propulsive-efficiency]]  ·  **from** [[airplane]]

**Kind: a procedure — an evaluation of the model.** Masses, battery data, static thrust and the
drive-train efficiency belong to the components the aircraft is built from — motor,
propeller, battery, structure. They are read from the component tree and the parts
catalogue, not chosen per calculation.

**Why this entry exists.** As free inputs they hid that swapping a battery or a motor
changes the mass, the thrust and with them everything downstream. The graph now says it.

`static-thrust` and `propulsive-efficiency` stay listed for completeness; both are the
weaker route — thrust at airspeed comes from the measured propeller tables
(`thrust-at-airspeed-from-coefficient`), and the efficiency is a single constant where the
tables give it as a function of advance ratio.
