---
canon: static-margin-probe
entry: formula
kind: procedure
tool: AB
shape: law
status: draft
output: pitching-moment-slope, static-margin-probe
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
  x_cg: centre-of-gravity
outputs: {c_m_alpha: pitching-moment-slope, sm_probe: static-margin-probe}
---

# Static margin from the moment slope — the Probe

**Canonical form**

```
solve for alpha at V_md:   L = m * g
C_m_alpha, C_L_alpha := AeroBuildup(airplane, x_ref = x_CG, V_md, alpha).run_with_stability_derivatives()
SM_probe = - C_m_alpha / C_L_alpha
```

**Produces** [[pitching-moment-slope]] · [[static-margin-probe]]  ·  **from** [[airplane]] · [[aircraft-mass]] · [[gravity]] · [[air-density]] · [[minimum-drag-speed]] · [[centre-of-gravity]]

**Kind: a procedure — the Probe of [[static-margin]].** With the moment reference at the
CG, `−C_mα/C_Lα` is the static margin by a second path. Two paths to one quantity are a
**test**, not a second truth (A7): a deviation beyond tolerance is reported, never averaged.

Unlike `x_NP`, `C_mα` **does** depend on the reference: its sign flips exactly at
`x_ref = x_NP` (§2.3). That is why the Probe — and only the Probe — needs the CG.

**Source.** 🟢 `SM = −C_mα/C_Lα`: Sadraey Eq. 11.17 (`C_mα = C_Lα·(X_cg − X_np)`) with Eq. 11.18, §11.6.2. (Anderson §4.9, cited here before, is the airfoil aerodynamic-centre relation, the 2D analogue, not the airplane static margin.)

**Validity in the RC/UAV regime (ADR 0028).** The relation `SM = −C_mα/C_Lα` with the moment reference at the CG holds in any regime (Sadraey Eq. 11.17, §11.6.2); its value carries AeroBuildup's limits. AeroBuildup omits main-wing downwash on the tail, over-counts tail effectiveness and returns too negative a `C_mα` (Sharpe 2024 §5.3, §5.4), so the Probe is biased toward a larger margin, consistent with the ≈ 10 % MAC aft shift recorded in GH #1154. At `V_md` small models fly at fairly high C_L, near NeuralFoil's low-confidence region (Re ≈ 8·10⁴, C_L ≈ 1.0; §7.2.4). Mach ≤ 0.3: incompressible.

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
