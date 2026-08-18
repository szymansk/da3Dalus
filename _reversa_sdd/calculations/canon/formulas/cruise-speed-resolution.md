---
canon: cruise-speed-resolution
entry: formula
kind: procedure
shape: law
status: draft
output: cruise-speed
source_status: NO_SOURCE_FOUND
dimensional_check: PROCEDURAL
tags:
  - canon/formula
  - source/no-source-found
  - dim/procedural
  - shape/law
  - kind/procedure
  - flag/conflict
---

# Resolution of the cruise speed when no mission goal supplies it

**Canonical form**

```
V_cruise := V_md   (substitution, not a physical law)
```

**Produces** [[cruise-speed]]  ·  **from** [[minimum-drag-speed]] · [[max-level-speed]] · [[dive-speed]]

**Kind: a procedure.** There is no closed form, so an algorithm stands in its place. Source and scale are asked as of any entry — a procedure is not source-free: it either implements a published standard or solves a stated equation. **On top of that** it must say **under which assumptions it holds** and **when it converges**, including what it returns when it does not.

### The procedure

> A procedure is not invented here. It has **two origins**, and both are citable:
> the **relation** it solves, and the **method** it solves it with. Its assumptions and
> its convergence behaviour are then properties of that method — published, not chosen.

**Relation solved.** 🔴 not yet stated — which equation or standard does this implement?

**Method.** 🔴 not yet named — bisection, Brent, Newton, Picard, an interior-point solver, a tabulated standard?

**Assumptions.** 🔴 not yet stated — bracketing, continuity, monotonicity, validity range. These follow from the method; they are not a matter of taste.

**Convergence.** 🔴 not yet stated — tolerance, iteration cap, and the guarantee the method actually offers.

**On failure.** 🔴 not yet stated — what is returned when it does not converge, and is it declared? (ADR 0020)

**Dimensional check.** ⚪ procedural — not an algebraic law

**Source.** 🔴 NO SOURCE FOUND

> No source substitutes V_md for a mission cruise speed. The proposal is right to label it "substitution, not a physical law". The sources actively point the other way: Scholz 05_PreliminarySizing §5.7 tabulates best-range cruise at V/V_md = 1.316 (89.6% of E_max), and Sadraey §4.3.3.2 notes cruise is flown at 75-80% power with V_max ~ 1.2-1.3 V_C.

**The source writes it as**

```
Scholz's parametric table is the closest thing to a rule: V/V_md = 1.0 gives 100% of E_max, 1.316 gives 89.6%, 1.5 gives 81.7%, 2.0 gives 63.4% - i.e. real cruise sits above V_md and the efficiency penalty for doing so is initially small.
```

**Validity at 0.5–15 kg.** Scholz's remark that "prop aircraft cruise much closer to (L/D)max speed than jets do" (because power scales with V^3 for props) makes V_md a defensible LOWER BOUND for an electric RC model - closer to truth at RC scale than it would be for a jet. But it is still a floor, not an identity, and substituting it silently biases every downstream number (endurance up, dive speed down, stall-margin ratio down). Under ADR 0020 this substitution must emit a DesignWarning naming which of the three resolution paths was taken.

## ⚠️ Conflict

Three incompatible definitions of V_cruise coexist. (1) A mission goal read from the flight profile -- the only definition the rest of the chain assumes. (2) operating_point_generator_service:277 and matching_chart_service:785 substitute V_md when no goal exists. V_md is by definition the maximum-L/D speed, i.e. the best-endurance / best-rate-of-climb speed and explicitly NOT a cruise speed; the sizing literature puts cruise at V_max/1.2 to V_max/1.3, well above V_md. Because vs_clean can in turn derive V_S1 from V_cruise, this closes a loop in which the stall speed is a function of the minimum-drag speed and the cruise speed is a function of the stall speed. (3) flight_envelope_service:190 back-derives the gust envelope's V_C as V_D/1.4, and since V_D := 1.4*V_max upstream, V_C is identically V_max -- so the gust envelope's 'cruise speed' is the maximum level speed, the one speed at which the aircraft is certainly not cruising. Three different numbers carry the label cruise speed in one application.

> Two or more implementations use **genuinely different laws** for this quantity.
> This is the entry that must be decided, not merely read.

## Implementations (3)

| node | claimed | verified | deviation |
|---|---|---|---|
| [[cruise_speed_resolved]] | DEVIATES | 🟢 | Returns the cached V_md as the cruise speed when the aeroplane has no flight profile, sile |
| [[v_cruise_resolved]] | DEVIATES | 🟢 | Same substitution, plus a worse cold-start branch: it evaluates the V_md closed form at a  |
| [[fe_v_c]] | DEVIATES | 🔴 mismapped | Back-derives V_C = V_D/1.4 from a dive speed that was itself defined as 1.4*V_max, so the  |

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

