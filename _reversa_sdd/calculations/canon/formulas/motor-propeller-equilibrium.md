---
canon: motor-propeller-equilibrium
entry: formula
kind: procedure
tool: APP
shape: route
status: draft
output: propeller-speed, motor-torque
source_status: SOURCED
dimensional_check: PROCEDURAL
tags:
  - canon/formula
  - source/sourced
  - dim/procedural
  - shape/route
  - kind/procedure
  - status/draft
inputs:
  components: components
  v: flight-speed
  rho: air-density
  k_v: motor-voltage-constant
  i_0: motor-no-load-current
  r_m: motor-circuit-resistance
  u_bat: battery-voltage
  p_mot_max: motor-max-power
  d_prop: propeller-diameter
  eta_mot: motor-efficiency
outputs: {n_prop: propeller-speed, q_m: motor-torque}
optional: [r_m, i_0]
---

# Propeller speed from the motor–propeller torque balance

**Canonical form**

```
route B (R_m known):  (I(n_prop) - I_0) / K_v' = C_P(J) * rho * n_prop^2 * D_prop^5 / (2*pi)
                      I(n_prop) = (U_bat - 2*pi*n_prop / K_v') / R_m,   J = V / (n_prop * D_prop)
route A (R_m absent): n_prop = min( K_v * U_bat / 60 ,  n_prop  with  C_P(J) * rho * n_prop^3 * D_prop^5 = eta_mot * P_mot,max )
both routes:          Q_m = C_P(J) * rho * n_prop^2 * D_prop^5 / (2*pi)          (torque absorbed; equal to the motor torque at the balance on route B; route A below the power limit: upper estimate)
```

**Produces** [[propeller-speed]] · [[motor-torque]]  ·  **from** [[components]] · [[flight-speed]] · [[air-density]] · [[motor-voltage-constant]] · [[motor-no-load-current]] · [[motor-circuit-resistance]] · [[battery-voltage]] · [[motor-max-power]] · [[propeller-diameter]] · [[motor-efficiency]]

**Second output: the motor torque** (maintainer, 2026-10-19, #1174). The balance already equates
motor and propeller torque; `Q_m = C_P(J)·ρ·n_prop²·D_prop⁵/(2π) = P_shaft/(2π·n_prop)` is that torque
at the solved `n_prop` (on route A at the power limit `Q_m = eta_mot·P_mot,max /
(2π·n_prop)`). Route B: exact at the balance point. **Route A below the power limit is an upper
estimate, declared (ADR 0020):** it runs at the free-run rpm `K_v·U_bat`, which ignores the rpm drop
under load — by this entry's own measurement (D-Power AL 28-13, APC 6x4E: 10 064 vs 8 973 rpm) the
torque `∝ n_prop²` is about 26 % too high. It is covered by the existing `practice` warning that names
route A (`Q-PT-6`). At the power limit it uses `eta_mot`, the sourced default 0.75 (Roxxy
Motoren-Fibel, `defaults.yaml`). Both routes take the nominal battery voltage. The construction side sizes the motor
mount from it; the speed it is read at (static, `V = 0`, is the usual maximum) and any factor are the
construction's and the evaluation's (A10). Source: the torque balance itself (Drela `motor1` §1.1);
Sadraey §6.8.2 treats propeller reaction torque only as a roll-trim effect — no source for its
structural use.

**Kind: a procedure with two routes, selected by data.** `K_v'` is the speed constant in rad/s per volt.

**Route B — the torque balance.** At every airspeed the propeller turns where the motor torque meets the propeller torque; the rpm drops as the propeller is loaded. This is Drela's first-order DC motor model (`motor1` §1.1) against the measured `C_P(J)` table of the fitted propeller. It is the more accurate route and the only one without a singularity at `V = 0`. Implemented today as Model B, solved by bisection (gh-1006, BR-PT15). Inside an optimisation problem the rpm becomes a variable and this balance a constraint (verified with `asb.Opti` and `motor_electric_performance`, 01.10.2026).

**Route A — free-run rpm, limited by the motor's power.** Without `R_m` the rpm is the free-run value `K_v · U_bat` — **unless the propeller would absorb more than the motor delivers there; then the rpm drops until it absorbs exactly `eta_mot · P_mot,max`.** Decided by the maintainer 2026-10-01 (O11). It needs only published values and is the normal case: almost no hobby manufacturer publishes `R_m`.

*Why the limit.* Route A as built (gh-615, BR-PT14) computes thrust at free-run rpm and clips only the **reported** shaft power. On BRYAN (Pulsar Micro 1510, 45 W, APC 6x4E, 2S) the propeller then asks 75–82 W of a 45 W motor; limited, static thrust falls from 489 g to 307 g. The code also cannot read `max_power_w` — it knows only currents. Ticketed as #1150.

*What it still ignores.* The rpm drop under load below the power ceiling — measured on a D-Power AL 28-13 with APC 6x4E: loaded 8 973 vs free-run 10 064 rpm, about 25 % too much thrust. And `eta_mot` is the input [[motor-efficiency]] (maintainer, 2026-10-15, E1): default 0.75 from the Roxxy Motoren-Fibel, Ch. 3 (band 75–85 %), the lower bound because route A applies it at `P_mot,max`, above the peak-efficiency point; taking the default is visible (INFO, `provenance.defaults_used`) and, since 2026-10-25 (#1235), declared with a `practice` warning (ADR 0020). [[airplane-components]] produces no efficiency; the caller passes the catalogue's `efficiency_pct` where the manufacturer publishes it as the [[motor-efficiency]] input, else the default is taken. Ist: BR-PM3 uses 0.85. Whether the catalogue's power rating is electrical or shaft power is open — the source does not say; [[motor-max-power]] reads it as electrical, 🟡 INFERRED (STAND §10, E1).

**Already decided — `Q-PT-6`** (maintainer, 2026-08-14). The route is chosen by data availability, and the result **declares which route ran** (ADR 0020). `R_m` is sourced only where a manufacturer publishes it and **never synthesised** from `K_v` and `I_0`. Today no catalogue motor carries it, so every number comes from route A until #1149 fills the data. `r_m` is therefore `optional`: route A without `R_m` is a **declared method limitation**, and a `practice` warning names the route (`Q-PT-6`). `i_0` is `optional` as well (2026-10-25, #1235): absent, the balance runs with `I_0 = 0` (BR-PT15), declared with a `practice` warning.

**Full throttle only.** This entry answers for the full-throttle point (`T_full(V)`, the static thrust, top speed, climb). The part-load point of level flight — thrust equal to drag, battery current and power — is [[motor-propeller-part-load]], which embeds this entry for `T_full(V)`.

**Why not constant power.** Sadraey's propeller relation `T = eta_P · P / V` with constant `P` (Eq. 8.2, 4.84; `eta_P` 0.5–0.6 in climb, §4.3.5.2) is stated there as "sufficient for preliminary sizing". A voltage-fed motor on a fixed-pitch propeller does not deliver constant power, the relation diverges at `V = 0`, and it still needs the rpm to read `eta_P(J)`. It stays out of the canon.

**Sensitivity.** Varying `R_m` by ×0.5 / ×2 moves thrust by 28 % static and 40 % at 10 m/s (`scripts/canon_checks/thrust_motor_resistance_sensitivity.py`). The resistance is the dominant uncertainty of thrust at airspeed.

**Source.** 🟢 Drela `motor1` §1.1: the three-parameter DC motor model, `v = i·R + Ω/K_v` and `Q_m = (i − i_0)/K_Q`, with `K_Q = K_v` in the ideal case; §2 gives the bench measurement of `R`, `i_0` and `K_v` (Eq. 9–12). Propeller power from `C_P = P/(ρ·n³·D⁵)` (Brandt & Selig 2011 §II.F). The default band of `eta_mot`, 75–85 % peak efficiency for hobby brushless motors, is from Roxxy Motoren-Fibel Ch. 3 pp. 28–29. 🔴 NO SOURCE FOUND for the structural use of the torque output.

**Validity in the RC/UAV regime (ADR 0028).** The torque balance itself is exact; what it is worth depends on the motor model and on `C_P(J)`. Drela's three-parameter model is valid across typical RC speeds and currents and breaks down only at very low speed or very high current (Drela `motor1` §1.1). `R_m` rises with winding temperature, so a cold catalogue value predicts too high an rpm under load (§1.1.1, §2.1). Small propellers run at Re₀.₇₅ ≈ 15–100 k (ADR 0028; Brandt & Selig 2011 §IV), where `C_T` and `C_P` change with Reynolds number (Deters, Ananda & Selig 2014 §V.A–B); the table block is chosen by nearest rpm, so the solved rpm also fixes the propeller Re the coefficients belong to. Blade tips of RC propellers typically run near Ma ≈ 0.5 (Roxxy Motoren-Fibel Ch. 1 pp. 9–10), above the airframe's M ≤ 0.3; tip compressibility is whatever the table contains. Route A runs at free-run rpm, which loaded brushless motors do not reach — about 85 % of no-load rpm in flight (Roxxy Ch. 1 pp. 9–10). Battery voltage sag under load is not modelled [no source].

## Implementations (0)

None in aero_kernel yet; no register node is mapped to this entry.

## Approval

- [ ] **Source** — citation real, or absence stated and adopted on the maintainer's authority
- [ ] **Regime** — holds in the RC/UAV regime (Reynolds, Mach, equipment), or the limitation is written down (ADR 0028)
- [ ] **Relation and method** — which equation it solves, and by which named method
- [ ] **Assumptions** — the conditions the method requires (bracketing, continuity, range)
- [ ] **Convergence** — the criterion, and what is returned and declared on failure
- [ ] **Dimensions** — the check balances
- [ ] **Implementations** — all agree, or each deviation is declared and justified
- [ ] **Preconditions** — every binding condition holds, or the violation is ticketed
- [ ] **Inputs approved** — no formula is approvable before its inputs are

> While `status: draft` this entry **cites nothing and decides nothing**.
