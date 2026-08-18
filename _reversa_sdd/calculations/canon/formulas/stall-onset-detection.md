---
canon: stall-onset-detection
entry: formula
kind: procedure
shape: law
status: draft
output: stall-onset-index
source_status: PARTIAL
dimensional_check: PROCEDURAL
tags:
  - canon/formula
  - source/partial
  - dim/procedural
  - shape/law
  - kind/procedure
---

# Stall onset from the shape of the computed polar

**Canonical form**

```
i_stall = first i > i(C_L,max) with C_L_i < C_L_(i-1) and C_D_i > C_D_(i-1)
```

**Produces** [[stall-onset-index]]  ·  **from** [[lift-coefficient]] · [[drag-coefficient]] · [[angle-of-attack]]

**Kind: a procedure.** There is no closed form, so an algorithm stands in its place. Source and scale are asked as of any entry — a procedure is not source-free: it either implements a published standard or solves a stated equation. **On top of that** it must say **under which assumptions it holds** and **when it converges**, including what it returns when it does not.

> 🔴 **An assumption of this entry is broken in the code.**
>
> analysis_service.py:170-171 and :176-177 - the two fallbacks above break the method's own bracketing assumption without saying so. Consequence: for any alpha sweep that stops before the break (any user-supplied alpha_end below stall, and the default 20 deg is not guaranteed to clear it for cambered high-lift sections), the response still contains a stall_point and the plot still draws the orange 'Stall' marker (:52, :60, :972) and the 'Stall-Indiz: a=..., CL=...' summary line (:1372-1374). A user reads the last computed alpha as the aircraft's stall angle. Secondary: the criterion at :173 has no source and no noise guard, so a single non-monotone AeroBuildup sample before the real break places the marker early - the same failure mode, in the opposite direction, with the same silent presentation.

### The procedure

> A procedure is not invented here. It has **two origins**, and both are citable:
> the **relation** it solves, and the **method** it solves it with. Its assumptions and
> its convergence behaviour are then properties of that method — published, not chosen.

**Relation solved.** NO SOURCE FOUND. The predicate 'CL fell AND CD rose relative to the previous sample' (analysis_service.py:173) is a local first-difference heuristic with no citation in the code. It is not an airworthiness stall definition (CS-23/CS-25 define the stall through a flight-test manoeuvre and pitch break, not a coefficient difference) and it is not a solver-side criterion from AeroBuildup/NeuralFoil. The only defensible published statement behind it is that stall follows C_L,max - which the scan start at :169 already encodes.

**Method.** First-match linear forward scan over the sampled grid, starting at the argmax index: i_clmax = int(np.argmax(cl)) at :169, then a for-loop from i_clmax+1 to n with an early break on the predicate (:172-175), with a Python for/else fallback (:176-177). analysis_service.py:167-184.

**Assumptions.** (1) The sweep extends past the real stall so that a qualifying sample exists - i.e. the event is bracketed. (2) The 1.0 deg alpha spacing (default 36 points over [-15,20] deg, AeroplaneRequest.py:68-70) resolves the break; post-stall CL and CD move fast, so what is returned is a grid point near the break, not the break. (3) The sampled CL(alpha) and CD(alpha) are smooth enough for a single-sample first difference to be meaningful: there is no smoothing and no noise threshold at :173, so one non-monotone solver sample terminates the scan. (4) CL(alpha) is single-peaked, so the argmax at :169 is the right place to start scanning.

**Convergence.** None. A single forward pass, O(n) worst case, terminating on the first qualifying index or falling through to the else branch. Exact on the grid, blind between grid points, no tolerance and no iteration - the notion of convergence does not apply, and the code offers no accuracy statement in its place.

**On failure.** It always returns a fully populated point, never a null and never an error. Two distinct undeclared substitutions: (a) when no post-peak sample satisfies the predicate, :176-177 declares the sample immediately after the peak to be the stall point; (b) when the peak IS the last sample - the sweep never reached stall, so the criterion is not bracketed at all - the guard at :171 is false and i_stall stays at i_clmax (:170), returning the C_L,max point as the stall point. Both results are byte-identical in shape to a real detection: the point is a bare dict (grep for 'stall_point' in app/schemas returns nothing - there is no schema and no detected/assumed flag), and no DesignWarning is emitted anywhere in the file. Undeclared substitution under ADR 0020.

ℹ️ **Reclassified.** Was recorded as a second producer of another quantity. It produces its own: a design limit, not the actual value.

**Dimensional check.** ⚪ procedural — not an algebraic law

**Source.** 🟡 PARTIAL

> The PHYSICS is sourced: Anderson, Fundamentals of Aerodynamics 6e, §4.3 and §4.13 - past the stalling angle the lift coefficient "decreases precipitously" while there is a "large increase in drag", the two conditions the test encodes. The specific discrete two-condition criterion (first index past C_L,max with C_L falling and C_D rising) is an implementation; no source publishes it as a criterion.

**The source writes it as**

```
Anderson describes the mechanism qualitatively and distinguishes stall types rather than giving a detection rule.
```

**Validity at 0.5–15 kg.** Two RC-scale weaknesses. (1) Anderson §4.13 distinguishes leading-edge stall (thin 10-16% sections: sharp peaked maximum, rapid post-stall drop - the test fires cleanly) from trailing-edge stall (>16% thick: "gentle, gradual bending-over of the lift curve" - the test fires late and is sensitive to alpha step size). Thick sections are common on RC trainers, so the soft case is the normal case here. (2) Lennon records stall AoA falling from 17 deg to 10 deg at low model Rn, so a sweep grid tuned to full-scale stall angles can straddle the peak entirely. Deeper caveat: AeroBuildup/VLM does not model separation, so what this test detects is a feature of the underlying section data, not a computed stall - it must not be presented to the user as a predicted stall angle without stating the Re it came from.

## Implementations (1)

| node | claimed | verified | deviation |
|---|---|---|---|
| [[stall-point]] | EXACT | 🟢 |  |

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

