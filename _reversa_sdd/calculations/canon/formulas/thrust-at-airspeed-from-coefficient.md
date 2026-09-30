---
canon: thrust-at-airspeed-from-coefficient
entry: formula
kind: law
shape: law
status: draft
output: thrust-at-airspeed
source_status: SOURCED
dimensional_check: BALANCES
tags:
  - canon/formula
  - source/sourced
  - dim/balances
  - shape/law
  - kind/law
  - status/draft
---

# Thrust at airspeed from the thrust coefficient

**Canonical form**

```
T = C_T * rho * n_prop^2 * D_prop^4
```

**Produces** [[thrust-at-airspeed]]  ·  **from** [[thrust-coefficient]] · [[air-density]] · [[propeller-speed]] · [[propeller-diameter]]

**Kind: a law.** A closed-form relation. Approval asks for its **source** and its **validity at 0.5–15 kg**.

**Dimensional check.** 🟢 balances — (kg/m^3) * (1/s^2) * m^4 = kg*m/s^2 = N.

**The lookup, stated separately.** `C_T = C_T(J)` with `J = V / (n_prop · D_prop)` — read from the
measured table. The law above is evaluable and the table is not, so they are written apart:
folding the lookup into the canonical form made the whole entry unevaluable for the
dimensional checker, which is a worse trade than one extra line.

**Source.** 🟢 SOURCED

> Definitional: C_T is *defined* as T/(rho*n^2*D^4), so the relation is the definition read backwards, and the content sits entirely in C_T(J). The advance ratio J = V/(nD) is standard propeller notation. The C_T(J) table is **measured**, not modelled: 454 APC propellers, 300 187 sample points over 45 RPM blocks each, J from 0 to about 1.17, no null coefficients.

**Why this entry exists.** The canon reached thrust at speed only through
[[mean-thrust-derate]], a blanket factor on static thrust whose factor has no entry, no
unit and no source — the one symbol the dimensional check reports as unregistered. This
relation replaces the guess with a measurement.

**Validity at 0.5–15 kg.** This is the *right* scale for it: the tables are APC model
propellers. Two limits are real. The coefficient is clamped at zero past the zero-thrust
point, so nothing windmilling is modelled. And a table lookup outside its `J` range is an
extrapolation, which the implementation already flags.

## ⚠️ Conflict — two authorities for thrust

🔴 The application computes this **twice, incompatibly.**

`powertrain_performance.py` implements exactly this relation from the measured tables and
publishes `T(V)` and `P_shaft(V)`. Three services that need thrust —
`field_length_service`, `matching_chart_service`, `mission_kpi_service` — use
`t_static_N` instead, a hand-entered **bench** number that holds only at `V = 0`, and none
of them calls the powertrain service.

So the field length, the sizing chart and the mission KPI axes are computed with a thrust
the aircraft only has while standing still, while the correct curve sits one module away.
ADR 0022: one authority per user-facing quantity.

## Approval

- [ ] **Source** — citation real, or absence stated and adopted on the maintainer's authority
- [ ] **Scale** — holds at 0.5–15 kg, or the limitation is written down (ADR 0023)
- [ ] **Dimensions** — the check balances
- [ ] **Implementations** — all agree, or each deviation is declared and justified
- [ ] **Preconditions** — every binding condition holds, or the violation is ticketed
- [ ] **Inputs approved** — no formula is approvable before its inputs are
