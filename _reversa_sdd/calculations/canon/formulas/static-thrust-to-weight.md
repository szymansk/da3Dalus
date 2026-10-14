---
canon: static-thrust-to-weight
entry: formula
kind: law
tool: APP
shape: law
status: draft
output: static-thrust-to-weight
source_status: SOURCED
dimensional_check: BALANCES
tags:
  - canon/formula
  - source/sourced
  - dim/balances
  - shape/law
  - kind/law
  - status/draft
tex: \frac{T_0}{W} = \frac{T(V = 0)}{W}
inputs:
  w: weight
  airplane: airplane
  rho: air-density
  k_v: motor-voltage-constant
  i_0: motor-no-load-current
  r_m: motor-circuit-resistance
  u_bat: battery-voltage
  p_mot_max: motor-max-power
  d_prop: propeller-diameter
outputs: {t0_w: static-thrust-to-weight}
embeds: [motor-propeller-equilibrium, advance-ratio-from-speed, propeller-table-lookup, thrust-at-airspeed-from-coefficient]
variables: [flight-speed]
optional: [r_m]
---

# Static thrust-to-weight ratio

**Canonical form**

```
T_0/W = T / W
```

**Produces** [[static-thrust-to-weight]]  ·  **from** [[weight]] · [[airplane]] · [[air-density]] · [[motor-voltage-constant]] · [[motor-no-load-current]] · [[motor-circuit-resistance]] · [[battery-voltage]] · [[motor-max-power]] · [[propeller-diameter]]

**Kind: a law.** `T` is the static thrust, evaluated inside this entry at `V = 0`: it embeds the
motor-propeller balance and the measured propeller table (`embeds:`) and reads no thrust value — the
computed static thrust over the weight. A common RC figure: above 1 the model can climb
vertically and hang on the propeller (BRYAN, route A power-limited: 2.0).

**Replaces** (2026-10-02, maintainer) `thrust-to-weight` with `T_mean = f_T · T_static`:
a blanket factor without source on a nameplate thrust that names neither voltage nor
propeller (`mean-thrust-derate`, `mean-thrust`, `static-thrust` deleted). §3.9 had already
stated *"we need no factor for this"*.

**Not the matching-chart ordinate.** For propeller aircraft Sadraey (§4.3.3.2, §4.3.5.2) and RC
practice size on power loading `W/P`, not `T/W` — that belongs to the design direction (O12).

**Source.** 🟢 Definitional (Scholz §5.2 `T_TO/(m·g)`; Sadraey Eq. 4.47).
