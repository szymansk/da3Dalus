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
route B (R_m known):  (I(n) - I_0) / K_v' = C_P(J) * rho * n^2 * D^5 / (2*pi)
                      I(n) = (U_bat - 2*pi*n / K_v') / R_m,   J = V / (n * D)
route A (R_m absent): n = K_v * U_bat / 60
```

**Produces** [[propeller-speed]]  ·  **from** [[airplane]] · [[flight-speed]] · [[air-density]] · [[motor-voltage-constant]] · [[motor-no-load-current]] · [[motor-circuit-resistance]] · [[battery-voltage]] · [[propeller-diameter]]

**Kind: a procedure with two routes, selected by data.** `K_v'` is the speed constant in rad/s per volt.

**Route B — the torque balance.** At every airspeed the propeller turns where the motor torque meets the propeller torque; the rpm drops as the propeller is loaded. This is Drela's first-order DC motor model (`motor1` §1.1) against the measured `C_P(J)` table of the fitted propeller. It is the more accurate route and the only one without a singularity at `V = 0`. Implemented today as Model B, solved by bisection (gh-1006, BR-PT15). Inside an optimisation problem the rpm becomes a variable and this balance a constraint (verified with `asb.Opti` and `motor_electric_performance`, 01.10.2026).

**Route A — fixed rpm.** Without `R_m` the rpm is the free-run value. Model A today (gh-615, BR-PT14), which also caps shaft power by the motor and battery limits. It ignores the rpm drop under load and is therefore **optimistic**: on a catalogue motor (AL 28-13, APC 6x4E, 2S) loaded 8 973 vs free-run 10 064 rpm — about 25 % too much thrust, since `T ~ n²`.

**Already decided — `Q-PT-6`** (maintainer, 2026-08-14). The route is chosen by data availability, and the result **declares which route ran** (ADR 0020). `R_m` is sourced only where a manufacturer publishes it and **never synthesised** from `K_v` and `I_0`. Today no catalogue motor carries it, so every number comes from route A until #1149 fills the data.

**Why not constant power.** Sadraey's propeller relation `T = eta_P · P / V` with constant `P` (Eq. 8.2, 4.84; `eta_P` 0.5–0.6 in climb, §4.3.5.2) is stated there as "sufficient for preliminary sizing". A voltage-fed motor on a fixed-pitch propeller does not deliver constant power, the relation diverges at `V = 0`, and it still needs the rpm to read `eta_P(J)`. It stays out of the canon.

**Sensitivity.** Varying `R_m` by ×0.5 / ×2 moves thrust by 28 % static and 40 % at 10 m/s (`scripts/canon_checks/thrust_motor_resistance_sensitivity.py`). The resistance is the dominant uncertainty of thrust at airspeed.
