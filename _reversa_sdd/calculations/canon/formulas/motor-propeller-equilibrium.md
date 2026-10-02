---
canon: motor-propeller-equilibrium
entry: formula
kind: procedure
shape: route
status: draft
output: propeller-speed
source_status: SOURCED
dimensional_check: PROCEDURAL
tags:
  - canon/formula
  - source/sourced
  - dim/procedural
  - shape/route
  - kind/procedure
  - status/draft
---

# Propeller speed from the motor–propeller torque balance

**Canonical form**

```
route B (R_m known):  (I(n_prop) - I_0) / K_v' = C_P(J) * rho * n_prop^2 * D_prop^5 / (2*pi)
                      I(n_prop) = (U_bat - 2*pi*n_prop / K_v') / R_m,   J = V / (n_prop * D_prop)
route A (R_m absent): n_prop = min( K_v * U_bat / 60 ,  n_prop  with  C_P(J) * rho * n_prop^3 * D_prop^5 = eta_mot * P_mot,max )
```

**Produces** [[propeller-speed]]  ·  **from** [[airplane]] · [[flight-speed]] · [[air-density]] · [[motor-voltage-constant]] · [[motor-no-load-current]] · [[motor-circuit-resistance]] · [[battery-voltage]] · [[motor-max-power]] · [[propeller-diameter]]

**Kind: a procedure with two routes, selected by data.** `K_v'` is the speed constant in rad/s per volt.

**Route B — the torque balance.** At every airspeed the propeller turns where the motor torque meets the propeller torque; the rpm drops as the propeller is loaded. This is Drela's first-order DC motor model (`motor1` §1.1) against the measured `C_P(J)` table of the fitted propeller. It is the more accurate route and the only one without a singularity at `V = 0`. Implemented today as Model B, solved by bisection (gh-1006, BR-PT15). Inside an optimisation problem the rpm becomes a variable and this balance a constraint (verified with `asb.Opti` and `motor_electric_performance`, 01.10.2026).

**Route A — free-run rpm, limited by the motor's power.** Without `R_m` the rpm is the free-run value `K_v · U_bat` — **unless the propeller would absorb more than the motor delivers there; then the rpm drops until it absorbs exactly `eta_mot · P_mot,max`.** Decided by the maintainer 2026-10-01 (O11). It needs only published values and is the normal case: almost no hobby manufacturer publishes `R_m`.

*Why the limit.* Route A as built (gh-615, BR-PT14) computes thrust at free-run rpm and clips only the **reported** shaft power. On BRYAN (Pulsar Micro 1510, 45 W, APC 6x4E, 2S) the propeller then asks 75–82 W of a 45 W motor; limited, static thrust falls from 489 g to 307 g. The code also cannot read `max_power_w` — it knows only currents. Ticketed as #1150.

*What it still ignores.* The rpm drop under load below the power ceiling — measured on a D-Power AL 28-13 with APC 6x4E: loaded 8 973 vs free-run 10 064 rpm, about 25 % too much thrust. And `eta_mot` is the default 0.85 (BR-PM3) unless the catalogue carries an efficiency — a constant without a model-scale source (ADR 0023), declared.

**Already decided — `Q-PT-6`** (maintainer, 2026-08-14). The route is chosen by data availability, and the result **declares which route ran** (ADR 0020). `R_m` is sourced only where a manufacturer publishes it and **never synthesised** from `K_v` and `I_0`. Today no catalogue motor carries it, so every number comes from route A until #1149 fills the data.

**Why not constant power.** Sadraey's propeller relation `T = eta_P · P / V` with constant `P` (Eq. 8.2, 4.84; `eta_P` 0.5–0.6 in climb, §4.3.5.2) is stated there as "sufficient for preliminary sizing". A voltage-fed motor on a fixed-pitch propeller does not deliver constant power, the relation diverges at `V = 0`, and it still needs the rpm to read `eta_P(J)`. It stays out of the canon.

**Sensitivity.** Varying `R_m` by ×0.5 / ×2 moves thrust by 28 % static and 40 % at 10 m/s (`scripts/canon_checks/thrust_motor_resistance_sensitivity.py`). The resistance is the dominant uncertainty of thrust at airspeed.
