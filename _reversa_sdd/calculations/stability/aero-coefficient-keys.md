---
name: aero-coefficient-keys
symbol: —
kind: constant
unit: – (set of strings)
cluster: stability
user_visible: true
source_status: SOURCED
node_class: unclassified-constant
tags:
  - cluster/stability
  - class/unclassified-constant
  - source/sourced
  - surface/user-visible
---

# Reported aero coefficient whitelist

**Definition.** Keys extracted from the AeroBuildup result and reported as aero coefficients.

⚪ **Unclassified constant.** Not yet decided whether this is a rule of thumb, a calibration or a physical value. Classifying it is open work — it is deliberately not guessed.

**Value.** `{"CL", "CD", "CY", "Cm", "Cl", "Cn"}`

**Inputs.** — *(leaf: a constant or an external input)*

**Produced by.** `app/services/aerobuildup_trim_service.py:22` — `_AERO_COEFF_KEYS`

**Consumed by.**

- outside it: `app/services/aerobuildup_trim_service.py:269,335`

**Source.** 🟢 SOURCED

> Standard body-axis force and moment coefficient set: Sadraey (Wiley 2013) §12.5.2 / §12.6.2 use C_L, C_D, C_y, C_m, C_l, C_n as the six aerodynamic coefficients; Anderson, "Fundamentals of Aerodynamics" 6e §1.5 (aerodynamic force coefficients) defines the non-dimensionalisation. Naming convention for the AeroSandbox output keys: AeroSandbox documentation, aero_3d solver return conventions.
>
> — via `aircraft-design-scholz + aerodynamics-expert + aerosandbox-expert`

**The source states it as.**

```
C_L, C_D, C_Y (forces) and C_l, C_m, C_n (roll, pitch, yaw moments) — the standard six
```

**Cited in the code itself.** `# Aerosandbox uses underscore notation (CL_a = dCL/dalpha);
# legacy AVL-style keys (Clb, Cnr) may also appear in output.`

---
*Cluster [[_index-stability|stability]] · generated from the 2026-08-18 extraction.*
