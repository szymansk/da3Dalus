---
canon: flight-speed
kind: quantity
symbol: V
unit: m/s
role: input
status: draft
tags:
  - canon/quantity
  - role/input
---

# Flight speed · `V`

The airspeed of the operating point being evaluated — the **free variable** of the
performance machinery. Dynamic pressure, required lift coefficient, drag, power required
and the polar lookups are all evaluated *at* a given `V`. No formula produces it. Solving
the lift balance for a speed happens only inside a **named** closure of an operating point
(`V_S`, `V_md`, `V_mp`, `V_app` …), never into this generic quantity.

AeroSandbox treats it the same way: `velocity` is always an input of
`asb.OperatingPoint`, and none of its 3D solvers solves for it.

**Two caveats on every evaluation.** A point whose required `C_L` exceeds `C_L,max` — that
is, `V < V_S` — is not flyable and must be reported as such, not computed through. And
`L = n·W` assumes a small flight-path angle.

**Unit.** `m/s`

**Used by.** [[advance-ratio-from-speed]] · [[aerobuildup-evaluation]] · [[dynamic-pressure]] · [[motor-propeller-equilibrium]] · [[power-required-electrical]] · [[reynolds-scheduled-polar]] · [[sink-rate]]
