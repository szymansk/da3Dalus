---
canon: minimum-drag-speed-from-polar
entry: formula
kind: procedure
shape: route
status: draft
output: minimum-drag-speed
source_status: SOURCED
dimensional_check: PROCEDURAL
tags:
  - canon/formula
  - source/sourced
  - dim/procedural
  - shape/route
  - kind/procedure
---

# Minimum-drag speed as the argmax of the computed glide ratio

**Canonical form**

```
V_md = V( argmax_i (C_L_i / C_D_i) )
```

**Produces** [[minimum-drag-speed]]  ·  **from** [[flight-speed]] · [[lift-to-drag-ratio]]

**Kind: a procedure.** There is no closed form, so an algorithm stands in its place. Source and scale are asked as of any entry — a procedure is not source-free: it either implements a published standard or solves a stated equation. **On top of that** it must say **under which assumptions it holds** and **when it converges**, including what it returns when it does not.

> 🔴 **An assumption of this entry is broken in the code.**
>
> 1) analysis_service.py:685-702 with :514-515 - the CL/CD samples come from ONE AeroBuildup run at a single velocity (sweep_request.velocity, default 10 m/s, AeroplaneRequest.py:71), and :514 then assigns each (CL,CD) pair a different speed V(CL) spanning the whole polar. The drag polar is evaluated far outside the Reynolds number it was computed at, so V_md is read off a fixed-Re polar. The competing implementation fixes exactly this: speed_polar_service.py:130-145 (_cd0_e_at) looks cd0/e up per speed from the Re table, added by gh-924 'so the polar markers match the chips instead of diverging'. 2) ADR 0022 - three producers of this one user-facing speed: the argmax here (:523,545), the closed form plus a fixed 1-pass Picard at speed_polar_service.py:82-182 served by api/v2/endpoints/aeroplane/speed_polar.py:170, and the closed form at assumption_compute_service.py:1917-1943. They do not even share constants: g = 9.81 (analysis_service.py:438) vs 9.80665 (speed_polar_service.py:24); rho from asb.Atmosphere (analysis_service.py:626) vs a hard 1.225. 3) analysis_service.py:546 publishes ld_max from this raw argmax AFTER gh-924 removed exactly that estimator from the assumption path for landing 'on a spurious high-CL sample' (assumption_compute_service.py:282-288, recorded 18.8 @ CL 0.98 vs the correct 23.4 @ CL 0.55). The abandoned argmax (_ld_max_from_sweep, :1369-1387) is nevertheless still the index at which Oswald e is measured (_e_oswald_from_sweep, called at :244-249), and that e feeds the 'corrected' ld_max_pub / cl_at_ld_max_pub at :298-300 - the closed-form fix is anchored on the sample it was introduced to discard.

### The procedure

> A procedure is not invented here. It has **two origins**, and both are citable:
> the **relation** it solves, and the **method** it solves it with. Its assumptions and
> its convergence behaviour are then properties of that method — published, not chosen.

**Relation solved.** V at (L/D)max, i.e. the tangent from the origin to the drag polar; equivalently induced drag = parasite drag, CL_md = sqrt(CD0*pi*AR*e). Stated in-repo at assumption_compute_service.py:1926-1932 and speed_polar_service.py:9-12. The related E_max = 0.5*sqrt(pi*AR*e/CD0) is cited in-code as 'Scholz eq. 5.39' (assumption_compute_service.py:283). Citations passed through as written in the code; not independently verified.

**Method.** Exhaustive search over a sampled discretisation. analysis_service.py:522-523: ld = cl_s / cd_s; i_best = int(np.argmax(ld)); the speed is read out at that index at :545 (v_best_glide) and the ratio at :546 (ld_max). Samples are the alpha-sweep points with CL > 0 (:479-481), co-sorted ascending by V (:517-519).

**Assumptions.** (1) The sampled CL range brackets CL_md = sqrt(CD0*pi*AR*e) - unchecked; an endpoint argmax is returned like any other. (2) The spacing resolves it. This is the weakest point of the method here: L/D is flat near its maximum while V ~ CL^(-1/2), so a grid error that is second-order in L/D is first-order in the reported speed - the quantity actually published. Default resolution is 1.0 deg of alpha (AeroplaneRequest.py:68-70). (3) CD(CL) is valid at the speed each sample is assigned to - see violation. (4) CD > 0 at every sample; unlike the characteristic-point path (:107-108) the speed polar has no guard at :522.

**Convergence.** None. Exhaustive search does not converge: exact on the grid, blind between grid points. Single pass, no tolerance, no refinement, no residual - as configured it evaluates 36 alpha samples once and returns.

**On failure.** argmax always returns an index, so a point is always emitted and a boundary maximum is indistinguishable from an interior one - SpeedPolarCurve (aeroanalysisschema.py:589 ff.) carries no bracketing or quality field. Curves come back empty (V=[], v_best_glide=None) only for s_ref<=0, rho<=0, no positive CL, or m<=0 (:493-512), with no explanation attached. Any exception in the glue is swallowed at :667-669 and the entire speed_polar is returned as null. No DesignWarning anywhere in the file - undeclared, ADR 0020.

**Shape: a route.** This is one of several ways to the same quantity. The canon does not choose between them — it requires that they **agree**.

**Test that follows.** Both routes claim the same quantity by different means; they must agree. Where they do not, the polar is not parabolic — which is a statement about the aircraft, not a defect.

**Dimensional check.** ⚪ procedural — not an algebraic law

**Source.** 🟢 SOURCED

> Anderson, Fundamentals of Aerodynamics 6e, §6.7.2 defines (L/D)_max as the maximum of the C_L/C_D curve over angle of attack. RC-Network Wiki "Gleitzahl": the best glide ratio "occurs at a specific airspeed called the best glide speed", and glide ratio is explicitly a function of airspeed with a single interior optimum.

**The source writes it as**

```
Sources define the condition; the discrete argmax over sweep points is the implementation.
```

**Validity at 0.5–15 kg.** Valid, and at 0.5-15 kg this is the PREFERRED route over the closed form, precisely because the low-Re polar is not parabolic. RC-Network also gives the weight dependence that validates the app's behaviour: heavier aircraft reach best glide ratio at higher speed (the ballast argument). Resolution caveat: the argmax is only as good as the alpha/speed grid - a coarse sweep will quantise V_md.

## Implementations (2)

| node | claimed | verified | deviation |
|---|---|---|---|
| [[i-best-glide]] | EXACT | 🟢 |  |
| [[v-best-glide]] | EXACT | 🟢 |  |

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

