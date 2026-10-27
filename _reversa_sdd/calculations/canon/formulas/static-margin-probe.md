---
canon: static-margin-probe
entry: formula
kind: procedure
tool: AB
shape: law
status: approved
output: pitching-moment-slope, static-margin-probe
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
  mu: dynamic-viscosity
  a: speed-of-sound
  v_md: minimum-drag-speed
  x_cg: centre-of-gravity-design
  sm_target: static-margin-target
outputs: {c_m_alpha: pitching-moment-slope, sm_probe: static-margin-probe}
---

# Static margin from the moment slope — the Probe

**Canonical form**

```
solve for alpha at V_md:   L = m * g
C_m_alpha, C_L_alpha := AeroBuildup(airplane, x_ref = x_cg_design, V_md, alpha).run_with_stability_derivatives()
SM_probe = - C_m_alpha / C_L_alpha
```

**Produces** [[pitching-moment-slope]] · [[static-margin-probe]]  ·  **from** [[airplane]] · [[aircraft-mass]] · [[gravity]] · [[air-density]] · [[dynamic-viscosity]] · [[speed-of-sound]] · [[minimum-drag-speed]] · [[centre-of-gravity-design]] · [[static-margin-target]]

**Kind: a procedure — the Probe of [[static-margin-target]].** With the moment reference at the
design CG, `x_cg,design = x_NP − SM_target·c_MAC`, `−C_mα/C_Lα` must reproduce `SM_target`: the design
CG and the probe are two paths to one margin. Two paths to one quantity are a **test**, not a second
truth (A7): a deviation beyond tolerance is reported, never averaged. The tolerance allows the declared
method offset: AeroBuildup has no wing-tail downwash, which biases the probe toward a larger margin.
Checking a measured CG is the path of [[static-margin-measured]], not of the probe.

**Inputs added at implementation (#1277).** AeroBuildup needs the viscosity and the speed of sound next to the density (the Reynolds and Mach number of its sections), exactly as [[roll-rate]] binds them from [[air-density]]'s ISA state; and the probe cannot compare with the target without being given it, so [[static-margin-target]] is an input. The comparison is the only use of the target: the probe's value does not depend on it.

**How the agreement is reported.** The value `SM_probe` is always returned. If it differs from `SM_target` by more than `agreement_tolerance`, the result carries the warning `static_margin_probe_disagrees` (`defect`, the rule's `on_violation: warning`) with the deviation, the tolerance and the target in its detail — reported, never averaged. Every value also carries `aerobuildup_no_downwash` (`practice`), the declared bias of the method.

**Agreement tolerance (adopted, maintainer 2026-10-25, #1260).** The probe agrees with the target if the two margins differ by at most 0.05, 5 % of the mean aerodynamic chord: the parameter `agreement_tolerance` of the rule `static-margin-probe-agreement` in `rules.yaml` (basis `convention`). It rests on the spread of the neutral-point worlds (3-6 % MAC, textbook against AVL on BRYAN and JAGUAR) plus the declared bias of the probe. The caller may override it; the override is declared in the provenance.

Unlike `x_NP`, `C_mα` **does** depend on the reference: its sign flips exactly at
`x_ref = x_NP` (§2.3). That is why the Probe — and only the Probe — needs the CG, and it is [[centre-of-gravity-design]] (`x_cg,design`, produced by cg-for-target-margin), never an app input (maintainer 2026-10-25).

**Source.** 🟢 `SM = −C_mα/C_Lα`: Sadraey Eq. 11.17 (`C_mα = C_Lα·(X_cg − X_np)`) with Eq. 11.18, §11.6.2. (Anderson §4.9, cited here before, is the airfoil aerodynamic-centre relation, the 2D analogue, not the airplane static margin.)

**Validity in the RC/UAV regime (ADR 0028).** The relation `SM = −C_mα/C_Lα` with the moment reference at the CG holds in any regime (Sadraey Eq. 11.17, §11.6.2); its value carries AeroBuildup's limits. AeroBuildup omits main-wing downwash on the tail, over-counts tail effectiveness and returns too negative a `C_mα` (Sharpe 2024 §5.3, §5.4), so the Probe is biased toward a larger margin, consistent with the ≈ 10 % MAC aft shift recorded in GH #1154. At `V_md` small models fly at fairly high C_L, near NeuralFoil's low-confidence region (Re ≈ 8·10⁴, C_L ≈ 1.0; §7.2.4). Mach ≤ 0.3: incompressible.

## Implementations (1)

| node | claimed | verified | deviation |
|---|---|---|---|
| `aero_kernel/formulas/static_margin_probe.py` | EXACT | 🟢 | `L = m g` is solved by interpolating the AeroBuildup alpha sweep (-15..25 deg, 0.25 deg steps, first C_L peak as the branch end) at V_md, then one AeroBuildup run with `run_with_stability_derivatives(alpha=True, beta=False, p=False, q=False, r=False)` and the moment reference `xyz_ref = (x_cg,design, y_ref, z_ref)` passed explicitly (`aero_kernel/solvers/opti.py`, `moment_slope_worker`); inputs `mu`, `a` and `sm_target` added (see above); per neutral-point world |

## Approval

- [x] **Source** — citation real, or absence stated and adopted on the maintainer's authority
- [x] **Regime** — holds in the RC/UAV regime (Reynolds, Mach, equipment), or the limitation is written down (ADR 0028)
- [x] **Relation and method** — which equation it solves, and by which named method
- [x] **Assumptions** — the conditions the method requires (bracketing, continuity, range)
- [x] **Convergence** — the criterion, and what is returned and declared on failure
- [x] **Dimensions** — the check balances
- [x] **Implementations** — all agree, or each deviation is declared and justified
- [x] **Preconditions** — every binding condition holds, or the violation is ticketed
- [x] **Inputs approved** — no formula is approvable before its inputs are

> **Approved** (maintainer, 2026-10-25): −C_mα/C_Lα from AeroBuildup at V_md with the moment reference at the
> design CG must reproduce SM_target — a test, not a second truth (A7); per world, since the design CG is an
> interval. Declared: no wing–tail downwash, biased toward a larger margin. Agreement tolerance 0.05 (5 % MAC),
> adopted the same day (`rules.yaml` `static-margin-probe-agreement`, #1260). No aero_kernel implementation yet
> (#1277).
