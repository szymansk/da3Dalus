---
canon: lift-to-drag-ratio
entry: formula
kind: law
tool: APP
shape: law
status: approved
output: lift-to-drag-ratio
source_status: SOURCED
dimensional_check: BALANCES
tags:
  - canon/formula
  - source/sourced
  - dim/balances
  - shape/law
  - kind/law
  - status/approved
inputs: {l: lift-force, d: drag-force}
outputs: {e: lift-to-drag-ratio}
preconditions:
  - {id: drag_positive, parameter: d, on_violation: error}
---

# Lift-to-drag ratio

**Canonical form**

```
E = L / D
```

**Produces** [[lift-to-drag-ratio]]  ·  **from** [[lift-force]] · [[drag-force]]

**Kind: a law.** A closed-form relation. Approval asks for its **source** and its **validity in the RC/UAV regime (ADR 0028)**.

**Dimensional check.** 🟢 balances

**Source.** 🟢 SOURCED

> Anderson, Fundamentals of Aerodynamics 6e, §6.7.2: L/D = C_L/C_D. Scholz 05_PreliminarySizing §5.7: E = C_L/C_D. RC: RC-Network Wiki "Gleitzahl", E = A/W (Auftrieb/Widerstand).

**The source writes it as**

```
RC-Network adds the operationally useful identity E = horizontal distance / altitude lost in still air, and its reciprocal tan(glide angle) = 1/E. Scholz uses the symbol E throughout, matching the app's choice.
```

**Validity in the RC/UAV regime (ADR 0028).** Exact - it is a ratio of two forces, so no reference quantity enters and there is no scale dependence in the definition itself. RC-Network notes E is not a constant but a function of airspeed, which the app already respects by reporting it per point.

## Preconditions on the bindings

**`drag_positive` — the drag must be greater than zero (on `d`; error).** The relation divides by `D`. A
drag of zero or below is physically impossible: profile drag and induced drag are never negative. Such a
value can only come from a defective solver result, and dividing by it would silently give an infinite or a
negative glide ratio. The violation is therefore an **error** at this formula, never a substituted value
(ADR 0020). The bound is physical, not a tuned threshold.

## Implementations (3)

| node | claimed | verified | deviation |
|---|---|---|---|
| `aero_kernel/formulas/lift_to_drag_ratio.py` | EXACT | 🟢 | the precondition `drag_positive` is the registered check of the same module: a drag of zero or below (or not a number) is `precondition_violated` at this formula, never a value |
| [[speed-polar-ld]] | EXACT | 🟢 |  |
| [[ld-ratio-force]] | EQUIVALENT | 🟢 |  |

## Approval

- [ ] **Source** — citation real, or absence stated and adopted on the maintainer's authority
- [ ] **Regime** — holds in the RC/UAV regime (Reynolds, Mach, equipment), or the limitation is written down (ADR 0028)
- [ ] **Dimensions** — the check balances
- [ ] **Implementations** — all agree, or each deviation is declared and justified
- [ ] **Preconditions** — every binding condition holds, or the violation is ticketed
- [ ] **Inputs approved** — no formula is approvable before its inputs are

> **Approved** (maintainer, 2026-11-01), with the precondition `drag_positive` and the regime text
> corrected to a ratio of two forces (option a). The value holds at the caller's operating point; the best
> glide ratio comes from the best-glide optimisation, the displayed parabola value from
> [[max-lift-to-drag-parabolic]] (ADR 0026).

**2026-11-03 (#1346):** the drag `d` is the kernel's ([[aerobuildup-evaluation]], `D_profile + k_e,D0 · D_induced`).
The relation `E = L / D` and this entry's computation are unchanged, so its approval stands; the re-approval of
[[aerobuildup-evaluation]] that stage 2 waited for was given on 2026-11-07.

**2026-10-02:** from the solver's forces at the operating point, not from the parabola (`C_D,par` is an approximation, measured non-parabolic at Re ≈ 1e5). ADR 0004's closed form governs only `(L/D)max`, see [[max-lift-to-drag-parabolic]].
