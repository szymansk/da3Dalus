---
name: rod-fit-tolerance
kind: constant
unit: mm
cluster: structure
user_visible: false
source_status: NO_SOURCE_FOUND
code_audit: CONFIRMED
node_class: numerical-tolerance
tags:
  - cluster/structure
  - class/numerical-tolerance
  - source/no-source-found
  - audit/confirmed
---

# Rod fit tolerance

**Definition.** Absolute slack added to the profile thickness before declaring a solved rod diameter too large to fit.

**Numerical tolerance.** A solver or comparison epsilon, not a domain value. ADR 0023 does not apply.

**Value.** `1e-9`

**Formula — as the code writes it.**

```
if d > outer_mm + 1e-9:
```

**Inputs.** — *(leaf: a constant or an external input)*

**Produced by.** `app/services/spar_sizing.py:160` — `_solve_rod`

🟢 **Verified against the code** — an independent reviewer read this line and confirmed the formula, unit and value (2026-08-18 audit).

**Consumed by.**

- outside it: `app/services/spar_sizing.py:160`

**Source.** 🔴 NO SOURCE FOUND

>
> — via `aircraft-design-scholz + rc-aircraft-designer (floating-point epsilon, not an engineering quantity)`
> No citable source was found. **This is recorded, not filled in.** The value is
> in the code without an attributable origin.

---
*Cluster [[_index-structure|structure]] · generated from the 2026-08-18 extraction.*
