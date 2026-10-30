---
canon: stall-wing-loading-limit
entry: formula
kind: law
tool: APP
shape: law
status: approved
output: wing-loading-limit-stall
source_status: SOURCED
dimensional_check: BALANCES
tags:
  - canon/formula
  - direction/design
  - source/sourced
  - dim/balances
  - shape/law
  - kind/law
  - status/approved
inputs: {rho: air-density, v_s_target: stall-speed-target, cl_max: max-lift-coefficient}
outputs: {ws_max_stall: wing-loading-limit-stall}
applications:
  - id: at_stall_speed_target
    given: [stall-speed-target]
---

# Maximum wing loading permitted by a stall-speed requirement

**Canonical form**

```
(W/S)_max,stall = 0.5 * rho * V_S,target^2 * C_L,max,clean
```

**Produces** [[wing-loading-limit-stall]]  ·  **from** [[air-density]] · [[stall-speed-target]] · [[max-lift-coefficient]]

**Kind: a law.** A closed-form relation. Approval asks for its **source** and its **validity in the RC/UAV regime (ADR 0028)**.

ℹ️ **Reclassified.** Was recorded as a second producer of another quantity. It produces its own: a design limit, not the actual value.

**Density at the set altitude (maintainer, 2026-10-25).** `rho` is the air density of
[[air-density-isa]] at the designer's altitude — one atmosphere for every calculation. With the
starting value of the altitude (0 m, the ISA reference) it is exactly Sadraey's sea-level value; at a
field altitude of 500 m the permitted wing loading falls by about 5 %, as it must, because the aircraft
stalls faster there at the same wing loading. This departs from Sadraey's usage rule (a) below (sea
level always) on purpose, and supersedes the convention of 2026-10-02 (stall-speed target stated at sea
level, quantity `sea-level-air-density`, now deleted): "Wir haben uns auf ISA geeinigt, also rechnen wir
auch mit ISA, und wenn jemand die Höhe angeben möchte, dann darf er es machen und bekommt entsprechende
Werte! Wir werden nicht eine Ausnahme von der Regel machen, um einer alten Regel Genüge zu tun!"
(maintainer, 2026-10-25).

**Dimensional check.** 🟢 balances

**Source.** 🟢 SOURCED

> Sadraey, Aircraft Design: A Systems Engineering Approach, §4.3.2, Eq. 4.31 verbatim: (W/S)_Vs = 0.5*rho*V_s^2*C_L,max. Boxed in the source as the stall-speed sizing constraint.

**The source writes it as**

```
Identical. Sadraey adds two usage rules: (a) rho is the SEA-LEVEL value (1.225 kg/m^3). Corrected 2026-10-02: the earlier gloss called this the conservative choice because lowest density gives highest V_s — that is backwards, sea level is the densest air and gives the LOWEST V_s. It is a convention (stall speeds stated as equivalent airspeed), and the maintainer adopts it for simplicity: RC models are flown by feel, almost never with an airspeed sensor, so V_S,target is meant at sea level. (b) the acceptable region is to the LEFT of the resulting vertical line (lower W/S is always acceptable). Sadraey also notes FAR 23 caps V_s at 61 kt and CS-VLA at 45 kt - FAR 25 has no V_s cap and uses landing field length instead.
```

**Validity in the RC/UAV regime (ADR 0028).** Valid at RC scale, and it is the right constraint to use for RC (Scholz's Loftin landing-field-length alternative, s_LFL with k_L = 0.107 kg/m^3, is a statistical fit to 1980s jet transports and must NOT be used at 0.5-15 kg). Caveat under ADR 0023: Sadraey's C_L,max source tables 4.10/4.11 have no RC row. The nearest bands are Home-built 1.2-1.8 and Microlight 1.8-2.4. The app's 1.4 default sits inside the home-built band, which is a defensible provenance, but it is a manned-aircraft band, not an RC measurement.

## Implementations (2)

| node | claimed | verified | deviation |
|---|---|---|---|
| `aero_kernel/formulas/stall_wing_loading_limit.py` | EXACT | 🟢 |  |
| [[ws_stall_constraint]] | EQUIVALENT | 🟢 |  |

## Approval

- [x] **Source** — citation real, or absence stated and adopted on the maintainer's authority
- [x] **Regime** — holds in the RC/UAV regime (Reynolds, Mach, equipment), or the limitation is written down (ADR 0028)
- [x] **Dimensions** — the check balances
- [x] **Implementations** — all agree, or each deviation is declared and justified
- [x] **Preconditions** — every binding condition holds, or the violation is ticketed
- [x] **Inputs approved** — no formula is approvable before its inputs are


## Design direction — what this entry is for (maintainer, 2026-10-02)

It turns a **mission target** into a **requirement on the construction** before the airplane
exists: the highest wing loading that still meets `V_S,target`. That is the purpose of the
design direction, not a defect — the system is meant to help the designer (a person or an AI
agent) judge the aircraft's properties and steer the construction. Once an airplane exists,
the analysis computes `V_S` and the comparison with `V_S,target` closes the loop in the Ablauf.

**O12 decided (2026-10-02):** the design direction is an **Urmodell** generated from the guided
questions and computed by the canon like any airplane. This entry stays only as an aid when a
stall-speed target is given; its `C_L,max` then comes from the **chosen airfoil** (NeuralFoil at
the mission Reynolds number, scaled to the wing with AeroSandbox's `CL_over_Cl`), not from a table.

> **Approved — stage 1** (maintainer, 2026-10-25): Sadraey Eq. 4.31 as the stall-speed sizing limit,
> with the density of air-density-isa at the set altitude instead of the fixed sea-level value (decision
> (a)). Stage 2 is open on `stall-speed-target` until the app carries it as a designer input variable
> (maintainer: close the gap as an input variable; #1264).
