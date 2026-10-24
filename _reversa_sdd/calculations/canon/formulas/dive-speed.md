---
canon: dive-speed
entry: formula
kind: procedure
tool: OPT
shape: law
status: draft
output: dive-speed
source_status: PARTIAL
dimensional_check: PROCEDURAL
tags:
  - canon/formula
  - source/partial
  - dim/procedural
  - shape/law
  - kind/procedure
  - status/draft
inputs:
  airplane: airplane
  components: components
  m: aircraft-mass
  g: gravity
  rho: air-density
  k_v: motor-voltage-constant
  i_0: motor-no-load-current
  r_m: motor-circuit-resistance
  u_bat: battery-voltage
  p_mot_max: motor-max-power
  d_prop: propeller-diameter
  eta_mot: motor-efficiency
outputs: {v_d: dive-speed}
embeds: [motor-propeller-equilibrium, advance-ratio-from-speed, propeller-table-lookup, thrust-at-airspeed-from-coefficient]
variables: [flight-speed]
optional: [r_m]
---

# Dive speed — terminal speed in a vertical dive

**Canonical form**

```
solve for V, alpha, n_prop:   L(V, alpha) = 0
                             D(V, alpha) = m * g + T(V, n_prop)
                             motor-propeller torque balance at (V, n_prop)
```

**Produces** [[dive-speed]]  ·  **from** [[airplane]] · [[components]] · [[aircraft-mass]] · [[gravity]] · [[air-density]] · [[motor-voltage-constant]] · [[motor-no-load-current]] · [[motor-circuit-resistance]] · [[battery-voltage]] · [[motor-max-power]] · [[propeller-diameter]] · [[motor-efficiency]]

**Kind: a procedure — a closure by a prescribed value**, not an extremum: the speed at which a vertical dive stops accelerating. Lift is zero, so drag balances weight plus thrust. It is a property of the aircraft and an **upper bound**, and a model reaches it from ordinary flying height.

**Replaces** `V_D = 1.4 · V_max` (2026-10-01, maintainer). The factor came from FAR 23.335, where 1.40 / 1.50 / 1.55 multiply the design **cruise** speed of a certified aircraft, not `V_max`; neither Scholz/Sadraey nor the RC sources give any factor for models (ADR 0023). With the thrust table the full-throttle and the power-off dive give the same number: beyond the zero-thrust advance ratio the thrust coefficient is clamped at 0.

**On the safe side, declared.** The drag of a windmilling or stopped propeller is not modelled (`Q-PT-10`), so the real dive speed is lower. The result says so (ADR 0020).

**Source.** 🟡 PARTIAL — physics of the vertical dive; the reading of `V_D` as terminal dive speed is the domain experts' own proposal for unregulated models, adopted by the maintainer on 2026-10-01. Not a textbook definition: Scholz knows `V_D` only from CS-25.

**Validity in the RC/UAV regime (ADR 0028).** The balance itself (zero lift, drag = weight + thrust) is regime-independent physics; the regime enters through the drag. At zero lift the drag is almost all profile drag, which depends on laminar–turbulent transition and so on the chord Reynolds number (Anderson §4.12). AeroBuildup's total drag agrees closely with lifting line on an RC sailplane at `Re_c = 1.55·10⁵` — a cross-method check, not a wind-tunnel one (Sharpe 2024 §5.4). The incompressible solver is exact only while the dive stays below M ≈ 0.3 (Anderson §1.10.3); BRYAN's 31.6 m/s is M ≈ 0.09. Small propellers lose efficiency below a blade Reynolds number of about 10⁵ (Brandt & Selig 2011 §IV), so the thrust table holds only at the Re it belongs to. `V_D` is an aerodynamic speed, not a structural one: the limit high-speed models actually meet is flutter of control surfaces and wings (RC-Network wiki, *Flattern*, *Vollgasfest*), which this entry does not model. No textbook gives a dive-speed definition for models [no source].

**What it is for.** The right-hand edge of the envelope, and the speed of the pull-out case: fully pulled at `V_D` the wing could produce `(V_D / V_S)²` g. BRYAN, power off, no propeller drag: **31.6 m/s** at α = −5.9° — a full pull there could demand about 35 g. Whether the aircraft survives the pull-out is decided by the pilot below [[maneuvering-speed]], not above it.

**Termination.** A failed solve returns no value (ADR 0020).

## Implementations (3)

| node | claimed | verified | deviation |
|---|---|---|---|
| [[fe_dive_factor]] | DEVIATES | 🟢 | Ist: `V_D = 1.4 · V_max` — the factor this entry replaced on 2026-10-01 |
| [[fe_v_dive]] | DEVIATES | 🟢 | Ist: `1.4 · V_max`, with `V_max` a 28 m/s default |
| [[kpi_dive_speed]] | DEVIATES | 🟢 | Ist: `1.4 · V_max` |

## Approval

- [ ] **Source** — citation real, or absence stated and adopted on the maintainer's authority
- [ ] **Regime** — holds in the RC/UAV regime (Reynolds, Mach, equipment), or the limitation is written down (ADR 0028)
- [ ] **Dimensions** — the check balances
- [ ] **Implementations** — all agree, or each deviation is declared and justified
- [ ] **Preconditions** — every binding condition holds, or the violation is ticketed
- [ ] **Inputs approved** — no formula is approvable before its inputs are

> While `status: draft` this entry **cites nothing and decides nothing**.
