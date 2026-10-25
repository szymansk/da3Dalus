---
canon: airplane-components
entry: formula
kind: procedure
tool: KAT
shape: law
status: draft
output: battery-mass, battery-capacity, battery-specific-energy, propulsive-efficiency, motor-voltage-constant, motor-no-load-current, motor-circuit-resistance, battery-voltage, motor-max-power, propeller-diameter
source_status: PARTIAL
dimensional_check: PROCEDURAL
tags:
  - canon/formula
  - source/partial
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

**Kind: a procedure — an evaluation of the model.** Battery data, motor and propeller data and the
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

**Source.** 🟡 PARTIAL. 🟢 for the meaning of `K_v`, `I_0`, `R_m`: Drela, three-parameter DC motor model (`motor1` §1.1, §1.1.1, §1.1.2; measurement protocol §2). The values themselves are catalogue data (manufacturer figures via the committed import snapshot), not derived. 🔴 NO SOURCE FOUND for the constant `propulsive-efficiency` and for the battery quantities: catalogue or maintainer values with no cited calibration.

**Validity in the RC/UAV regime (ADR 0028).** Regime-independent as a read: the entry copies catalogue values and computes nothing. The data are point measurements, valid near the conditions they were measured at. In Drela's three-parameter model `R_m` rises with winding temperature, so a cold catalogue value under-predicts the voltage drop under load; `I_0` depends on shaft speed and is meaningful only when measured near the operating rpm; the model breaks down at very high current (Drela `motor1` §1.1). `propulsive-efficiency` is a single constant, while small propellers run at Re₀.₇₅ ≈ 15–100 k (ADR 0028, after Brandt & Selig 2011 §IV), where efficiency depends strongly on advance ratio and Reynolds number. Battery capacity and voltage depend on discharge rate and temperature [no source].

## Implementations (0)

None in aero_kernel yet; no register node is mapped to this entry.

## Approval

- [ ] **Source** — citation real, or absence stated and adopted on the maintainer's authority
- [ ] **Regime** — holds in the RC/UAV regime (Reynolds, Mach, equipment), or the limitation is written down (ADR 0028)
- [ ] **Relation and method** — which equation it solves, and by which named method
- [ ] **Implementations** — all agree, or each deviation is declared and justified
- [ ] **Inputs approved** — no formula is approvable before its inputs are

> While `status: draft` this entry **cites nothing and decides nothing**.
