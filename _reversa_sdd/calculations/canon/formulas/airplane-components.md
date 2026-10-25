---
canon: airplane-components
entry: formula
kind: procedure
tool: KAT
shape: law
status: draft
output: battery-mass, battery-charge-capacity, battery-capacity, battery-c-rate, battery-current-allowed, motor-voltage-constant, motor-no-load-current, motor-circuit-resistance, battery-voltage, motor-max-power, propeller-diameter
source_status: PARTIAL
dimensional_check: PROCEDURAL
tags:
  - canon/formula
  - source/partial
  - dim/procedural
  - shape/law
  - kind/procedure
  - status/draft
inputs: {components: components, u_cell: cell-voltage-nominal}
outputs:
  m_bat: battery-mass
  q_bat: battery-charge-capacity
  e_bat: battery-capacity
  c_rate: battery-c-rate
  i_bat_max: battery-current-allowed
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
m_bat, Q_bat, C_rate, K_v, I_0, R_m, P_mot,max, D_prop := components of the airplane
U_bat     := cells * U_cell                  (cells from the pack; U_cell = cell-voltage-nominal)
E_bat     := Q_bat / 1000 * U_bat            (Ah times the nominal pack voltage; U_bat = cells * U_cell)
I_bat,max := C_rate * Q_bat / 1000           (continuous current allowed, A)
```

**Produces** [[battery-mass]] · [[battery-charge-capacity]] · [[battery-capacity]] · [[battery-c-rate]] · [[battery-current-allowed]] · [[motor-voltage-constant]] · [[motor-no-load-current]] · [[motor-circuit-resistance]] · [[battery-voltage]] · [[motor-max-power]] · [[propeller-diameter]]  ·  **from** [[components]] · [[cell-voltage-nominal]]

**Kind: a procedure — an evaluation of the model.** Battery data, motor and propeller data
belong to the components the aircraft is built from — motor,
propeller, battery, structure. They are read from the component tree and the parts
catalogue, not chosen per calculation.

**Why this entry exists.** As free inputs they hid that swapping a battery or a motor
changes the mass, the thrust and with them everything downstream. The graph now says it.

**No drive-train efficiency and no specific energy are read** (maintainer, 2026-10-25, #1235). `propulsive-efficiency` is deleted (ADR 0021): flight time and range come from the part-load chain [[motor-propeller-part-load]], not from one assumed constant. `battery-specific-energy` is a design assumption of [[battery-mass-from-capacity]] only. The nameplate static thrust is gone
(2026-10-02): it names neither voltage nor propeller; static thrust is computed instead.

**Battery as the catalogue holds it** (maintainer, 2026-10-25, #1235). The charge is read in mAh ([[battery-charge-capacity]], field `capacity_mah`), the continuous C-rate as [[battery-c-rate]] (field `c_rate`; burst ratings are not modelled). Derived: the pack energy [[battery-capacity]] `= Q_bat/1000 · U_bat` in Wh (nominal cell voltage [[cell-voltage-nominal]], default 3.7 V) and the allowed continuous current [[battery-current-allowed]] `= C_rate · Q_bat/1000` in A, both as values for the evaluation (A10).

**Motor and battery for the torque balance** (added 2026-10-01): `K_v`, `I_0` and `R_m` of the fitted motor, `U_bat` from the cell count and the nominal cell voltage [[cell-voltage-nominal]] (an input with a default, declared when taken). `R_m` and some `I_0` are missing from the catalogue (#1149), so both are **optional** outputs — an absent value is returned as absent, never filled in: `R_m` absent → route A, never estimated (`Q-PT-6`); `I_0` absent → the torque balance runs with `I_0 = 0` (BR-PT15). Both are declared by a `practice` warning (ADR 0020); route B is taken only where the manufacturer publishes `R_m`.

**Motor efficiency** is not produced here: it is the input [[motor-efficiency]]. The caller passes the catalogue's `efficiency_pct` where the manufacturer publishes it, else the sourced default of [[motor-efficiency]] is taken, declared with a `practice` warning. Nothing is measured; only published values are used (#1149).

**Propeller diameter** (moved here from [[airplane-geometry]], maintainer 2026-10-16, D11 on #1174): `D_prop` is a property of the fitted propeller, the same component whose APC table [[propeller-table-lookup]] reads. The geometry format has no propeller, so a missing propeller fails only the drive-train chain, never the wing quantities.

**Source.** 🟡 PARTIAL. 🟢 for the meaning of `K_v`, `I_0`, `R_m`: Drela, three-parameter DC motor model (`motor1` §1.1, §1.1.1, §1.1.2; measurement protocol §2). The values themselves are catalogue data (manufacturer figures via the committed import snapshot), not derived. 🔴 NO SOURCE FOUND for the battery quantities: catalogue values with no cited calibration; the nominal cell voltage is a convention (BR-PM3, default of [[cell-voltage-nominal]]), not a measured pack voltage.

**Validity in the RC/UAV regime (ADR 0028).** Regime-independent as a read: the entry copies catalogue values and computes nothing. The data are point measurements, valid near the conditions they were measured at. In Drela's three-parameter model `R_m` rises with winding temperature, so a cold catalogue value under-predicts the voltage drop under load; `I_0` depends on shaft speed and is meaningful only when measured near the operating rpm; the model breaks down at very high current (Drela `motor1` §1.1). Battery capacity and voltage depend on discharge rate and temperature [no source]: the rated mAh holds at the manufacturer's test rate, the nominal cell voltage is a mid-discharge value, and the pack energy derived from the two inherits both.

**Ist ≠ Soll (#1235).** Ist: the app reads the capacity in Wh and applies one drive-train efficiency of about 0.52 (η_prop 0.65 × η_motor 0.85 × η_ESC 0.94, all assumptions) in `app/services/endurance_service.py`. Soll: the app **must follow** this entry and the part-load chain and drop that constant (#1238).

## Implementations (0)

None in aero_kernel yet; no register node is mapped to this entry.

## Approval

- [ ] **Source** — citation real, or absence stated and adopted on the maintainer's authority
- [ ] **Regime** — holds in the RC/UAV regime (Reynolds, Mach, equipment), or the limitation is written down (ADR 0028)
- [ ] **Relation and method** — which equation it solves, and by which named method
- [ ] **Implementations** — all agree, or each deviation is declared and justified
- [ ] **Inputs approved** — no formula is approvable before its inputs are

> While `status: draft` this entry **cites nothing and decides nothing**.
