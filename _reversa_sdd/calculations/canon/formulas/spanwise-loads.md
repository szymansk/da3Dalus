---
canon: spanwise-loads
entry: formula
kind: procedure
tool: AVL
shape: law
status: draft
output: spanwise-lift-distribution, spanwise-shear-force, spanwise-bending-moment
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
  n_load: load-factor
  rho: air-density
  v: flight-speed
outputs:
  l_y: spanwise-lift-distribution
  v_y: spanwise-shear-force
  m_y: spanwise-bending-moment
---

# Spanwise lift, shear force and bending moment of the main wing

**Canonical form**

```
solve for alpha at V:   L = n * m * g                 (AVL: A C CL,  CL = 2 n m g / (rho V^2 S_ref))
                        pitch NOT trimmed, controls undeflected
strips j of the main wing (surface_type main_wing):     q = 0.5 * rho * V^2
  l(y_j)  = q * c_cl_j                                   (FS: normal force per unit span)
  V(y)    = q * S_ref * Vz(y)                            (VM: integral of l from the tip to y)
  M(y)    = q * S_ref * B_ref * Mx(y)                    (VM: local moment at y)
  referred to the centreline:  M_cl(y) = M(y) + V(y_root) * y_root   for the root row
  abscissa:  y in m from the centreline, positive outward; one half (the right one, Y > 0) — the load is
             symmetric, controls undeflected
```

**Produces** [[spanwise-lift-distribution]] · [[spanwise-shear-force]] · [[spanwise-bending-moment]]  ·  **from** [[airplane]] · [[aircraft-mass]] · [[gravity]] · [[load-factor]] · [[air-density]] · [[flight-speed]]

**Kind: a procedure — one AVL solution, integrated along the span.** Maintainer decision 2026-10-19
(#1174): it **replaces the elliptic assumption** the construction side used. The operating point —
speed and load factor — is the caller's: the load case, any design load factor and any safety factor
belong to the evaluation (A10). `n` is bound to the generic input `load-factor` (default 1), so one
call is one load case.

**Main wing only, normal force only — decided (maintainer, 2026-10-19).** The distributions are those
of the main wing (`surface_type main_wing`, #1187); tails and fin are not covered for now. Shear and
bending are integrated from the **normal force** per unit span (`c_cl`), which is what AVL's `VM`
integrates; on a wing with dihedral it differs from the lift by the dihedral cosine. Pitch is **not
trimmed** (declared, ADR 0020): α comes from `L = n·m·g` for the whole aircraft with undeflected
controls, so the main wing's share of the lift is the untrimmed one, not that of a trimmed flight state.

**The curves.** `l(y)`, `V(y)` and `M(y)` are curves over `y`, in m from the centreline, positive
outward, for one half of the main wing (the right one); the load is symmetric because no control is
deflected. Their symbols name the swept variable, as the README's `curve` type asks.

**What AVL returns (avl-advisor, Avl/src).** `FS` per strip: `c_cl = c·c_n`, the normal force per unit
span divided by `q`, normal to the strip in the Y-Z plane, inviscid, including the on-surface
trailing legs (`aero.f:358, 566`; strip forces printed by `OUTSTRP`, `aoutput.f:267` ff.) — this is
what `VM` integrates. `VM` per surface: `2Y/B_ref`, `Vz/(q·S_ref)`, `Mx/(q·S_ref·B_ref)`, a trapezoidal
integral from the last strip toward the first, i.e. from the tip toward the root (`getvm.f:64-80`). Two traps the form states instead of leaving to the reader: the root row is the
moment about the **surface root**, not about `y = 0` (`getvm.f:88-94`), so the centreline moment is
`M_root + V_root·y_root`; and the moment is sign-flipped for surfaces at `Y < 0` (`getvm.f:96-97`).
The kernel therefore writes the main wing with its sections **root → tip** and the left half by
`YDUPLICATE` (`avl_doc:424-436`); otherwise `VM` integrates from the wrong end (`getvm.f:64-80`).
AVL's abscissa is `Y` even with dihedral. A converged `X` run is required. The moment reference `Xref`
is the AVL file's reference point, a procedure detail: α comes from the `C_L` constraint and there are
no rates, so it changes no strip force — the CG is no input (ADR 0021).

**Aerodynamic load only — declared (ADR 0020).** No inertial relief (wing, servo, battery or motor
mass × `n·g`), no fuselage carry-over detail, no in-plane drag loads, no gust or dynamic loads, no
torsion. Leaving out relief is conservative for positive-g bending, **not** for negative g or for heavy
masses near the tip. The net load (aerodynamic minus inertia) is the construction's, which owns the
mass distribution (Scholz/Sadraey: relief only qualitatively, Sadraey §8; Anderson: no source).

**Validity in the RC/UAV regime (ADR 0028).** Better than the elliptic assumption: AVL resolves
planform, taper, twist, sweep, dihedral and deflections; elliptic is exact only for an untwisted
elliptic planform (Anderson §5.3.1–5.3.2; Sadraey §5.8, §5.14 prefers vortex lattice over lifting
line for swept wings). Attached flow with every section below `c_l,max`: no tip or local stall is
detected (§5.4, §4.13). AVL's implicit section slope ≈ 2π over-predicts section lift at a given α at
low Re (§20.3.2); solving for the required `C_L` cancels most of the magnitude error and leaves a shape
error. Reliable as an estimate at chord Re ≳ 2·10⁵ [no source], degraded 7·10⁴–2·10⁵, section loads
unvalidated below 7·10⁴ (the regime edges 3·10⁴, 7·10⁴ and 1·10⁶ come from ADR 0028; the 2·10⁵ edge
has no source; Anderson qualitative). Mach ≤ 0.3: no correction
(§1.10.3). For comparison, the elliptic reference is `c·c_l,ell(y) = 4·C_L·S_ref/(π·b)·√(1 − (2y/b)²)`
— AVL has no elliptic output of its own.

**Source.** 🟢 Anderson §5.3 (`L′ = ρ·V·Γ`, lifting line), §5.5 (vortex lattice); Sadraey §5.8, §5.14;
Scholz Wing Design §7.3 (load distribution `L′ = c·C_l` for structural sizing); AVL user guide and
source (`aoutput.f:267` ff., `getvm.f:21-118`).

## Implementations (0)

None in aero_kernel yet; no register node is mapped to this entry.

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
