---
canon: neutral-point
entry: formula
kind: procedure
uncertainty: interval
tool: AVL
shape: law
status: approved
output: neutral-point
source_status: SOURCED
dimensional_check: PROCEDURAL
tags:
  - canon/formula
  - source/sourced
  - dim/procedural
  - shape/law
  - kind/procedure
  - status/approved
inputs:
  airplane: airplane
  m: aircraft-mass
  g: gravity
  rho: air-density
  v_md: minimum-drag-speed
  eta_h: tail-efficiency
outputs: {x_np: neutral-point}
worlds: [textbook, pappas, avl]
---

# Neutral point of the airplane — an interval over method worlds (A11)

**Canonical form**

```
world textbook:  x_NP = (S_w*x_ac,w + K*S_h*x_ac,h) / (S_w + K*S_h),  K = eta*(1 - 4/(AR_w+2)) * [AR_h/(AR_h+2)]/[AR_w/(AR_w+2)],  eta = eta_h
world Pappas:    the same barycentre with K = (1 - 3.24/AR_w) * [1/(1+2/AR_h)]/[1/(1+2/AR_w)]
world AVL:       solve for alpha at V_md:  L = m*g;   x_NP := AVL(airplane, alpha).Xnp   (CLAF by ASB's thickness rule)
x_NP := [ min over worlds, max over worlds ]          (an interval, no core — A11)
```

**Produces** [[neutral-point]]  ·  **from** [[airplane]] · [[aircraft-mass]] · [[gravity]] · [[air-density]] · [[minimum-drag-speed]] · [[tail-efficiency]]

**Kind: a procedure with declared uncertainty (A11, maintainer 2026-10-03).** No single method captures
the physics at Re 30k–300k (`scripts/canon_checks/reference_fleet/NP_NIEDRIGE_RE.md`). The neutral point
is therefore the **interval** spanned by three accepted methods, each a self-consistent *world* that is
carried through the whole downstream chain (A11 rule 4). One entry, one producer (ADR 0022, ADR 0027).

- **Textbook world:** the barycentre form is the exact form of `h_n = h_ac + eta*V_H*(a_h/a)*(1 - de/da)`
  with `K = eta*(a_h/a)*(1 - de/da)`, lift slopes `a = 2 pi AR/(AR+2)`, downwash `de/da = 2 a_w/(pi AR_w)`
  (**derived from** Sadraey Eq. 6.67, §6.7.12 — the barycentre is a rearrangement, not the printed form);
  `eta` is the input [[tail-efficiency]] (`eta_h`, default **0.65**, `basis: sourced`; Lennon, *Basics of
  R/C Model Aircraft Design* Ch. 7/8, conventional tail near the wing wake 0.65; Sadraey Eq. 6.28 §6.2.1 gives
  0.85–0.95 conventional and 1 for a T-tail, full-scale; maintainer decision 2026-10-24, #1205). It is **not
  checked at RC Reynolds number (ADR 0028)**: the wing wake is thicker at low Re, unquantified. Pappas and AVL
  are unchanged: they imply `eta = 1`, so part of the textbook–Pappas gap is the choice of `eta_h`.
  Aerodynamic centres at 25 % of each surface's MAC.
- **Geometry of the textbook and Pappas worlds (maintainer 2026-10-25, #1253).** Area, aspect ratio and MAC of
  the main wing and of the horizontal tail are AeroSandbox's: `Wing.area(type="planform", include_centerline_distance=True)`,
  `AR = b²/S` with `b = Wing.span(type="yz", include_centerline_distance=True)`, and `Wing.mean_aerodynamic_chord()`
  (#1262: the flags are set in code, for both surfaces: each is a mirrored surface carried through the fuselage
  to the centreline, as the reference wing is, and for a root on y = 0 the flag changes nothing); the leading edge of the MAC is
  `x_le,MAC = x_AC − 0.25·c_MAC` with `x_AC` from `Wing.aerodynamic_center()` (the same MAC definition), so the
  surface's aerodynamic centre is ASB's. The same route as [[airplane-geometry]] (one producer, ADR 0022); the
  kernel's earlier own integration of the sections is gone. Quote: "Um ASB-konform zu sein, rechnen wir aus dem
  ASB-Wert entsprechend zurück."
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
fleet. **No fuselage in any world** (maintainer, 2026-10-23, #1203; decided 2026-10-24, #1205): the kernel
models none, deliberately (KISS), and every result carries the declared warning `fuselage_not_modelled`
(`practice`, a declared simplification, ADR 0020). A fuselage moves the neutral point forward, so the
interval is biased slightly aft. Sourced magnitude: USAF DATCOM 1978 §4.2.2.1 Method 1 (Multhopp,
Eq. 4.2.2.1-a; Hoak et al., AFWAL-TR-83-3048, DTIC ADB072483, printed pp. 4.2.2.1-1 to -4) gives about
1.5–2.1 % MAC forward for BRYAN and 0.7–1.0 % for JAGUAR, inside Sadraey's "about ±5 % c̄" (§6.2.1
footnote). That is smaller than the spread of the three worlds and outweighed by the η default 0.65
(3–5 % MAC forward against 0.9). It is larger for a fat fuselage or a long nose, hence the warning.
DATCOM Method 1 is a possible later extension, not scheduled.
Reference fleet (np_methods.py): BRYAN [32.9, 36.9] % MAC, e-Hawk [48.8, 52.9] % MAC.

**Source.** 🟢 derived from Sadraey Eq. 6.67, §6.7.12 (textbook); η from Lennon Ch. 7/8 and Sadraey Eq. 6.28, §6.2.1; Pappas, *Model Aviation* 10/2009; Drela, AVL. Review of the
uncertainty procedure: `reference_fleet/UNSCHAERFE_PRUEFUNG.md`.

**Validity in the RC/UAV regime (ADR 0028).** All three worlds are evaluated incompressible (Mach ≤ 0.3). The textbook world's tail efficiency is the input [[tail-efficiency]] (default 0.65 from Lennon, *Basics of R/C Model Aircraft Design*, Ch. 7/8, for a conventional tail near the wing wake); Sadraey's 0.85–0.95 conventional and 1 for a T-tail (Eq. 6.28, §6.2.1, p. 276) are full-scale practice and state no Reynolds number. Lower efficiency moves the neutral point forward. At low Re the wing's laminar separation and transition (Anderson §20.3.2) can thicken its wake and change the downwash at the tail [no source for the magnitude]. The lift slopes `2πAR/(AR+2)` assume a 2π section slope, which falls at low Re (Anderson §20.3.2, qualitative); the smaller-chord tail, at lower Re, is affected more [no source]. The fuselage is not modelled by decision (above, #1205), declared as `fuselage_not_modelled`.

## Implementations (1)

| node | claimed | verified | deviation |
|---|---|---|---|
| `aero_kernel/formulas/neutral_point.py` | EXACT | 🟢 | textbook (with the input `eta_h`) and Pappas barycentres as written, with the surfaces measured by the GEO adapter (AeroSandbox, `aero_kernel/solvers/geometry.py`); the AVL world calls the AVL adapter at C_L = m·g/(q·S_ref); every world declares `fuselage_not_modelled`; the interval over the worlds is formed by the engine (A11) |

## Approval

- [ ] **Source** — citation real, or absence stated and adopted on the maintainer's authority
- [ ] **Regime** — holds in the RC/UAV regime (Reynolds, Mach, equipment), or the limitation is written down (ADR 0028)
- [ ] **Relation and method** — which equation it solves, and by which named method
- [ ] **Assumptions** — the conditions the method requires (bracketing, continuity, range)
- [ ] **Convergence** — the criterion, and what is returned and declared on failure
- [ ] **Dimensions** — the check balances
- [ ] **Implementations** — all agree, or each deviation is declared and justified
- [ ] **Preconditions** — every binding condition holds, or the violation is ticketed
- [ ] **Inputs approved** — no formula is approvable before its inputs are

> While `status: draft` this entry **cites nothing and decides nothing**.
