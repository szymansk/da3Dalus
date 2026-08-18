---
canon: clmax-from-polar
entry: formula
kind: procedure
shape: law
status: draft
output: max-lift-coefficient
source_status: PARTIAL
dimensional_check: PROCEDURAL
tags:
  - canon/formula
  - source/partial
  - dim/procedural
  - shape/law
  - kind/procedure
---

# Maximum lift coefficient as the peak of the computed polar

**Canonical form**

```
C_L,max = max over alpha of C_L(alpha)
```

**Produces** [[max-lift-coefficient]]  ·  **from** [[lift-coefficient]] · [[angle-of-attack]]

**Kind: a procedure.** There is no closed form, so an algorithm stands in its place. Source and scale are asked as of any entry — a procedure is not source-free: it either implements a published standard or solves a stated equation. **On top of that** it must say **under which assumptions it holds** and **when it converges**, including what it returns when it does not.

> 🔴 **An assumption of this entry is broken in the code.**
>
> 1) assumption_compute_service.py:1209 - cl_max = np.max(cl_arr) is taken over the flattened velocity x alpha grid built at :1176-1193 (8 velocities up to v_max). C_L,max is Reynolds-dependent, so this returns the peak at the HIGHEST speed in the sweep, while stall physically occurs at the LOWEST. The value is written as the authoritative assumption (:183-190) and consumed by _stall_speed (:1758-1775), so V_stall is biased low (optimistic) by roughly the sqrt of the CL_max ratio between the two Reynolds bands. The same file documents this exact 'mixes Reynolds bands' defect for the sibling (L/D)max at :282-288 and fixed it only there. 2) assumption_compute_service.py:1138 - argmax with no bracketing or plateau check, while _extract_array (:1340-1349) manufactures a constant array filled with default=0.0 whenever the CL key is missing or the shape mismatches; argmax of a constant array returns index 0, so stall_alpha becomes coarse_alpha_min_deg = -5 deg, the fine window collapses to [-10,0] deg, and a low-alpha CL is written as CL_max. No exception, no warning. 3) analysis_service.py:129 and :482 - no interior-extremum check on a user-supplied range; if CL is still rising at alpha_end the boundary sample is reported as CL_max and v_stall (:524) is derived from it.

### The procedure

> A procedure is not invented here. It has **two origins**, and both are citable:
> the **relation** it solves, and the **method** it solves it with. Its assumptions and
> its convergence behaviour are then properties of that method — published, not chosen.

**Relation solved.** Definition of the lift-curve maximum, C_L,max = max_alpha C_L(alpha). No closed form exists here because C_L(alpha) is produced by a black-box solver (AeroBuildup/NeuralFoil, called at analysis_service.py:700-702 and assumption_compute_service.py:1136, 1193). No external standard is cited in the code and none is needed for the definition; NO SOURCE FOUND for the sweep bounds or the step sizes (defaults at app/models/computation_config.py:9-14).

**Method.** Two different methods for the same quantity. (a) Exhaustive search over a 1-D sampled grid: np.argmax(cl) at analysis_service.py:129 and np.max(cl_arr) at :482, over the user-supplied alpha grid (AeroplaneRequest.py:68-70, default -15..20 deg, 36 points = 1.0 deg step) at a single velocity. (b) Two-stage coarse-to-fine grid search in assumption_compute_service.py: _coarse_alpha_sweep (:1115-1138) argmax over alpha in [-5,25] deg at 1.0 deg, then _fine_sweep_cl_max (:1141-1209) max over a flattened velocity x alpha grid, alpha in stall_alpha +/- 5 deg at 0.5 deg, 8 velocities from max(0.5*v_cruise,3) to v_max.

**Assumptions.** (1) The peak lies strictly inside the sampled alpha range (bracketing) - unchecked in both implementations. (2) The spacing resolves the peak: 1.0 deg coarse, 0.5 deg fine; reported alpha at CL_max therefore carries +/-0.25 deg and CL_max is a lower bound on the true peak. (3) C_L(alpha) is single-peaked in the window, else the coarse argmax seeds the fine window around the wrong lobe. (4) For the fine stage only: that C_L,max does not depend on the second sweep axis (velocity, i.e. Reynolds number) - this assumption is false for the RC/UAV Reynolds range the sweep spans. (5) On a plateau or an all-equal array, index 0 is accepted as the maximum.

**Convergence.** None offered. An exhaustive search does not converge; it is exact on the grid and blind between grid points. The coarse->fine pass is a fixed two-step refinement with no residual, no tolerance and no stopping test - it always returns after exactly two sweeps. Final resolution as configured: fine_alpha_step_deg = 0.5 deg (computation_config.py:13). The single-stage path (analysis_service.py:129,482) has one pass at 1.0 deg and no refinement at all.

**On failure.** Never fails visibly. analysis_service.py:482 returns cl_max = 0.0 on an empty array, which turns v_stall into None at :524 with no message; :129 always emits a maximum_lift_coefficient_point even when the maximum sits on a sweep boundary. assumption_compute_service.py:1209 returns -inf on an empty sweep, and :183-190 writes round(cl_max, 4) straight into the authoritative 'cl_max' assumption with source 'aerobuildup' and auto_switch_source=True - no sanity gate on the value. If AeroBuildup raises, :101-105 logs and returns, silently leaving the previous stored cl_max in place. No DesignWarning is emitted anywhere in either file (grep: zero occurrences), so none of this is declared - ADR 0020.

**Dimensional check.** ⚪ procedural — not an algebraic law

**Source.** 🟡 PARTIAL

> Anderson, Fundamentals of Aerodynamics 6e, §4.3 and §4.13: c_l,max is defined as the maximum of the lift curve, occurring just prior to stall; "the maximum lift coefficient occurs just prior to stall". The definition is sourced; taking the discrete max over a sampled alpha array is an implementation of it, not a published method.

**Validity at 0.5–15 kg.** Valid as a definition. The RC problem is upstream: Anderson §4.3 states that the lift slope a_0 is Reynolds-independent but "c_l,max is strongly dependent on Re because stall is governed by viscous flow separation". A VLM/AeroBuildup sweep does not model separation - the peak it produces is entirely inherited from whatever section data sits underneath it. If that section data is not evaluated at the model's actual Re (5e4-3e5), the reported C_L,max is a different aircraft's number. Anderson §4.13 also warns the peak shape differs by stall type (sharp for 10-16% thick leading-edge stall, gentle bend-over above 16%), which changes how well a discrete max locates it.

## Implementations (2)

| node | claimed | verified | deviation |
|---|---|---|---|
| [[cl-max-speed-polar]] | EXACT | 🟢 |  |
| [[max-cl-point]] | EXACT | 🟢 |  |

## Approval

- [ ] **Source** — citation real, or absence stated and adopted on the maintainer's authority
- [ ] **Scale** — holds at 0.5–15 kg, or the limitation is written down (ADR 0023)
- [ ] **Relation and method** — which equation it solves, and by which named method
- [ ] **Assumptions** — the conditions the method requires (bracketing, continuity, range)
- [ ] **Convergence** — the criterion, and what is returned and declared on failure
- [ ] **Dimensions** — the check balances
- [ ] **Implementations** — all agree, or each deviation is declared and justified
- [ ] **Preconditions** — every binding condition holds, or the violation is ticketed
- [ ] **Inputs approved** — no formula is approvable before its inputs are

> While `status: draft` this entry **cites nothing and decides nothing**.

