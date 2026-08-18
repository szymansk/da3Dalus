---
canon: minimum-sink-speed-from-polar
entry: formula
kind: procedure
shape: route
status: draft
output: minimum-sink-speed
source_status: SOURCED
dimensional_check: PROCEDURAL
tags:
  - canon/formula
  - source/sourced
  - dim/procedural
  - shape/route
  - kind/procedure
---

# Minimum-sink speed as the argmin of the computed sink rate

**Canonical form**

```
V_mp = V( argmin_i w_i ),  w_min = min_i w_i
```

**Produces** [[minimum-sink-speed]]  ·  **from** [[flight-speed]] · [[sink-rate]]

**Kind: a procedure.** There is no closed form, so an algorithm stands in its place. Source and scale are asked as of any entry — a procedure is not source-free: it either implements a published standard or solves a stated equation. **On top of that** it must say **under which assumptions it holds** and **when it converges**, including what it returns when it does not.

> 🔴 **An assumption of this entry is broken in the code.**
>
> 1) analysis_service.py:514-515 with :685-702 - same defect as V_md and worse here: the polar is computed once at a single velocity (default 10 m/s) and then re-used across the whole speed range, and the min-sink point sits at the lowest speed of the characteristic points (V_ms ~= 0.76*V_md), i.e. where the relative Reynolds error against the 10 m/s polar is largest. The sink rate being minimised is built from CD values that do not belong to the speed they are multiplied by. 2) ADR 0022 - three producers again: the argmin here (:521,543-544), speed_polar_service.py:156-158 plus 178-182 (closed form + Picard, served at api/v2/endpoints/aeroplane/speed_polar.py:170), and assumption_compute_service.py:1946-1969. 3) speed_polar_service.py:163-171 clamps CL_ms to cl_max and V_min_sink to V_stall when the closed-form optimum exceeds CL_max (high-AR / low-CD0 gliders - the RC/UAV thermal-glider case this app targets) and emits no DesignWarning; the sampled path cannot clamp because CL_max bounds its samples by construction. For that whole aircraft class the two authorities differ systematically and neither declares it.

### The procedure

> A procedure is not invented here. It has **two origins**, and both are citable:
> the **relation** it solves, and the **method** it solves it with. Its assumptions and
> its convergence behaviour are then properties of that method — published, not chosen.

**Relation solved.** Minimum of the steady-glide sink rate w = V*CD/CL; at minimum power the induced drag is three times the parasite drag, giving CL_mp = sqrt(3*pi*e*AR*CD0). Cited in-code as 'Anderson section 6.7.2' at assumption_compute_service.py:1957-1959 and restated at speed_polar_service.py:11-12. Citation passed through as written in the code; not independently verified.

**Method.** Exhaustive search over a sampled discretisation: i_min_sink = int(np.argmin(w)) at analysis_service.py:521, over w = v*(cd_pos/cl_pos) computed at :515 for the positive-CL alpha-sweep samples, co-sorted by V at :517-519. v_min_sink and w_min are read out at that index (:543-544).

**Assumptions.** (1) The sampled CL range brackets CL_ms = sqrt(3)*CL_md - unchecked. CL_ms sits close to CL_max, so this is a demand on the high-CL (low-speed) end of the alpha sweep specifically. (2) The polar is still physically valid there: with the default alpha_end = 20 deg the samples run past CL_max, so the argmin is taken over a set that includes post-stall points, where AeroBuildup/NeuralFoil is least reliable and where no steady glide exists. (3) The spacing resolves a minimum that is flatter than the L/D maximum in CL, while V ~ CL^(-1/2) - so, as for V_md, grid error is first-order in the published speed. (4) CD(CL) valid at the speed it is assigned to - see violation.

**Convergence.** None. Exhaustive search: exact on the 36-sample grid, blind between grid points, single pass, no tolerance, no refinement. Note the contrast with the sibling implementation, which does have an iterative scheme - one Picard pass, _PICARD_PASSES = 1 at speed_polar_service.py:34, itself a fixed pass count with no convergence test.

**On failure.** argmin always returns an index; an endpoint minimum (the sweep stopped before the sink minimum) is reported as v_min_sink/w_min with nothing in the response to distinguish it. Empty curve with v_min_sink = None only for the degenerate-geometry branch at :493-512. Whole polar returned as null on any exception (:667-669). No DesignWarning in the file - undeclared, ADR 0020.

**Shape: a route.** This is one of several ways to the same quantity. The canon does not choose between them — it requires that they **agree**.

**Test that follows.** Both routes claim the same quantity by different means; they must agree. Where they do not, the polar is not parabolic — which is a statement about the aircraft, not a defect.

**Dimensional check.** ⚪ procedural — not an algebraic law

**Source.** 🟢 SOURCED

> Sadraey, Aircraft Design: A Systems Engineering Approach, §4.3.5.2, Eq. 4.85: V for minimum power = sqrt( 2W / (rho*S*sqrt(3*C_Do/K)) ), identified as the speed for maximum rate of climb of a PROP-DRIVEN aircraft, explicitly distinguished from the jet's minimum-drag speed. Sadraey's supporting text gives C_L at minimum power = sqrt(3*C_Do/K) and the resulting 1.155 = sqrt(4/3) factor in Eq. 4.89.

**The source writes it as**

```
Sadraey gives the closed form; the proposal's argmin over computed sink rate is the numerical equivalent of the same condition. Sadraey also fixes the exact ratio: V_mp = V_md/3^0.25 = V_md/1.316, and (L/D) at minimum power = 0.866*(L/D)_max.
```

**Validity at 0.5–15 kg.** Valid and directly RC-relevant: Sadraey's statement that the minimum-power speed is the best-climb speed for a PROPELLER aircraft applies to essentially every 0.5-15 kg electric model. The V_mp = V_md/1.316 identity is a free consistency assertion the app should enforce between its two speeds - if the computed argmin and argmax disagree with it by much, the polar fit is bad, not the physics.

## Implementations (3)

| node | claimed | verified | deviation |
|---|---|---|---|
| [[i-min-sink]] | EXACT | 🟢 |  |
| [[v-min-sink]] | EXACT | 🟢 |  |
| [[w-min]] | EXACT | 🟢 |  |

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

