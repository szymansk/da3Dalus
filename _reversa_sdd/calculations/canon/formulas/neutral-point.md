---
canon: neutral-point
entry: formula
kind: procedure
uncertainty: interval
tool: AVL
shape: law
status: draft
output: neutral-point
source_status: SOURCED
dimensional_check: PROCEDURAL
tags:
  - canon/formula
  - source/sourced
  - dim/procedural
  - shape/law
  - kind/procedure
  - status/draft
inputs:
  airplane: airplane
  m: aircraft-mass
  g: gravity
  rho: air-density
  v_md: minimum-drag-speed
outputs: {x_np: neutral-point}
worlds: [textbook, pappas, avl]
---

# Neutral point of the airplane — an interval over method worlds (A11)

**Canonical form**

```
world textbook:  x_NP = (S_w*x_ac,w + K*S_h*x_ac,h) / (S_w + K*S_h),  K = eta*(1 - 4/(AR_w+2)) * [AR_h/(AR_h+2)]/[AR_w/(AR_w+2)],  eta = 0.9
world Pappas:    the same barycentre with K = (1 - 3.24/AR_w) * [1/(1+2/AR_h)]/[1/(1+2/AR_w)]
world AVL:       solve for alpha at V_md:  L = m*g;   x_NP := AVL(airplane, alpha).Xnp   (CLAF by ASB's thickness rule)
x_NP := [ min over worlds, max over worlds ]          (an interval, no core — A11)
```

**Produces** [[neutral-point]]  ·  **from** [[airplane]] · [[aircraft-mass]] · [[gravity]] · [[air-density]] · [[minimum-drag-speed]]

**Kind: a procedure with declared uncertainty (A11, maintainer 2026-10-03).** No single method captures
the physics at Re 30k–300k (`scripts/canon_checks/reference_fleet/NP_NIEDRIGE_RE.md`). The neutral point
is therefore the **interval** spanned by three accepted methods, each a self-consistent *world* that is
carried through the whole downstream chain (A11 rule 4). One entry, one producer (ADR 0022, ADR 0027).

- **Textbook world:** the barycentre form is the exact form of `h_n = h_ac + eta*V_H*(a_h/a)*(1 - de/da)`
  with `K = eta*(a_h/a)*(1 - de/da)`, lift slopes `a = 2 pi AR/(AR+2)`, downwash `de/da = 2 a_w/(pi AR_w)`
  (**derived from** Sadraey Eq. 6.67, §6.7.4 — the barycentre is a rearrangement, not the printed form);
  `eta = 0.9` (Sadraey §6, 0.85–0.95 conventional), **not checked for the RC regime (ADR 0028)**
  (maintainer, 2026-10-23). Pappas implies `η = 1`; part of the textbook–Pappas gap is this choice.
  Aerodynamic centres at 25 % of each surface's MAC.
- **Pappas world:** Dean Pappas, "If It Flies", *Model Aviation* 10/2009 (after von Mises/Prager/Kuerti),
  verbatim barycentre with downwash factor `1 - 3.24/AR_w` and aspect-ratio correction `1/(1 + 2/AR)`.
- **AVL world:** vortex lattice with the wing's downwash at the tail; Drela's CLAF thickness rule as
  written by AeroSandbox.

**Mach 0.** All three worlds are evaluated incompressible, Mach 0: the RC/UAV regime has M ≤ 0.3
(ADR 0028), and the regime warnings inherited from [[minimum-drag-speed]] cover the Mach band.

**Refused configurations.** The three worlds cover **one main wing with one horizontal tail** (any fins
and winglets). Tailless, canard, tandem and V-tail layouts are `unsupported_configuration`, decided from
`surface_type` (#1187), never from the planform. Each is open in its own ticket: #1206 (tailless),
#1207 (canard, tandem), #1208 (V-tail). The textbook world's former V-tail rule — horizontal projection
`A cos^2(nu)` (Drela) — is not a canon statement any more; it is an open point of #1208 (what is
projected, and per segment).

**Not used:** AeroBuildup (no wing–tail downwash, about 10 % MAC aft — GH #1154); the flat rules with a
fixed tail weight (rcplanedesigner K = 0.5 and −5 % MAC, Harding, Krauss), because they ignore aspect
ratio and miss by 5–11 % MAC on the reference fleet; Lennon's fixed 35 %.

**Not validated (A11 rule 5).** The interval is a **lower bound** of the true uncertainty: all three
worlds share blind spots, above all the fuselage (only rcplanedesigner's flat −5 % and Lennon's "up to
15 %" are sourced; Raymer's formula is unchecked). A validation margin needs flown CGs of the reference
fleet. **No fuselage in any world** (maintainer, 2026-10-23, #1203): the kernel models none, and every
result carries the declared warning `fuselage_not_modelled` (`defect`, ADR 0020) — a fuselage moves the
neutral point forward, so the interval is biased aft. The sourced fuselage term is open in #1205.
Reference fleet (np_methods.py): BRYAN [32.9, 36.9] % MAC, e-Hawk [48.8, 52.9] % MAC.

**Source.** 🟢 derived from Sadraey Eq. 6.67 (textbook); Pappas, *Model Aviation* 10/2009; Drela, AVL. Review of the
uncertainty procedure: `reference_fleet/UNSCHAERFE_PRUEFUNG.md`.
