---
canon: aspect-ratio
entry: formula
kind: law
tool: APP
shape: law
status: approved
output: aspect-ratio
source_status: SOURCED
dimensional_check: BALANCES
tags:
  - canon/formula
  - source/sourced
  - dim/balances
  - shape/law
  - kind/law
  - status/approved
inputs: {b_ref: wing-span, s_ref: wing-reference-area}
outputs: {ar: aspect-ratio}
---

# Aspect ratio from span and area

**Canonical form**

```
AR = b_ref^2 / S_ref
```

**Produces** [[aspect-ratio]]  ·  **from** [[wing-span]] · [[wing-reference-area]]

**Kind: a law.** A closed-form relation. Approval asks for its **source** and its **validity in the RC/UAV regime (ADR 0028)**.

**Dimensional check.** 🟢 balances

**Source.** 🟢 SOURCED

> Anderson, Fundamentals of Aerodynamics 6e, §5.3.3: AR = b^2/S, used throughout the finite-wing induced-drag development. Sadraey §5.6 gives the definition AR = b/c_bar; with the mean geometric chord c_bar = S/b this is b^2/S.

**The source writes it as**

```
Sadraey §5.6 writes AR = b/c_bar and notes that b^2/S is "only valid when area equals span x chord". With c_bar the mean geometric chord S/b, b/c_bar = b^2/S holds for every planform; the note only warns against using the mean aerodynamic chord (MAC) as c_bar.
```

**Validity in the RC/UAV regime (ADR 0028).** A geometric definition, independent of Reynolds number, Mach number and equipment, so it holds in the RC/UAV regime. b^2/S holds for every planform, including the flying wings, deltas and elliptical wings common at model scale; AR = b/c_bar is equivalent only with c_bar = S/b, not with the MAC.

## Implementations (2)

| node | claimed | verified | deviation |
|---|---|---|---|
| `aero_kernel/formulas/aspect_ratio.py` | EXACT | 🟢 |  |
| [[fe_aspect_ratio]] | EXACT | 🟢 |  |

## Approval

- [x] **Source** — citation real, or absence stated and adopted on the maintainer's authority
- [x] **Regime** — holds in the RC/UAV regime (Reynolds, Mach, equipment), or the limitation is written down (ADR 0028)
- [x] **Dimensions** — the check balances
- [x] **Implementations** — all agree, or each deviation is declared and justified
- [x] **Preconditions** — every binding condition holds, or the violation is ticketed
- [x] **Inputs approved** — no formula is approvable before its inputs are

> **Approved** (maintainer, 2026-11-10): `AR = b_ref^2 / S_ref`, with span and reference area from the approved
> [[airplane-geometry]]. Two text corrections on approval: Sadraey's caveat is stated as what it is (b/c_bar equals
> b^2/S with c_bar = S/b for every planform; it warns only against the MAC as c_bar), and the sentence on the
> app's 7.0 literal fallback is removed, because the canon replaces that computation. The computation is unchanged.

