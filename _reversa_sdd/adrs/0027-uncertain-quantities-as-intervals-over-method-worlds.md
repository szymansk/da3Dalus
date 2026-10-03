# ADR 0027 — Uncertain quantities are intervals over method worlds

- **Status:** Accepted. **Amends [ADR 0026](0026-aero-truth-from-the-solver-not-the-parabola.md)** for
  the neutral point; **clarifies [ADR 0022](0022-one-authority-per-user-facing-quantity.md)** for
  interval-valued quantities.
- **Decided:** 2026-10-03, by the maintainer: "Wir nehmen Unschärfe mit in den Kanon auf". Recorded
  "as practicable as possible to implement in the canon".
- **Basis:**
  - measurements on the reference fleet (BRYAN, e-Hawk)
  - three independent source passes on neutral-point methods
  - a propagation test and an adversarial literature review (`scripts/canon_checks/reference_fleet/`:
    `NP_NIEDRIGE_RE.md`, `UNSCHAERFE_PRUEFUNG.md`, `np_methods.py`, `fuzzy_propagation_test.py`)
- **Confidence:** 🟢 for the measurements and the dependency effect; 🟡 for the bound being a lower bound
  of the true uncertainty (by construction, no validation data yet).
- **Execution:** Soll · Kanon. Canon rule A11 and register K25/K26; code via GH #1154 for the neutral
  point.

## Context

At RC/UAV Reynolds numbers no single method captures the physics. For the neutral point on two reference
aircraft:
- AeroBuildup lies about 10 % MAC aft of AVL, because it has no wing–tail downwash (#1154).
- The textbook formula and Pappas (*Model Aviation* 10/2009) agree with AVL within 1–4 % MAC.
- Flat rules of thumb miss by 5–11 % MAC.
- Feeding NeuralFoil's local low-Re lift slopes into AVL moves the BRYAN neutral point by more than 20 %
  MAC.

A single number would present knowledge that does not exist.

## Decision

1. A quantity whose accepted methods demonstrably disagree is an **interval [min, max] without a core**,
   produced by **one** canon entry whose definition lists the method *worlds*. A core is admitted only
   once a method is calibrated against measurements.
2. The interval is possibilistic, not probabilistic. There are no assumed distributions and no
   root-sum-square.
3. Downstream quantities are computed **per world through the whole chain**, and their interval is the
   min/max over the worlds. Combining intermediate intervals is forbidden: the test turned an exact
   10 % static margin into 6–14 %. Worlds are not mixed.
4. Every chain over an uncertain cause gets a monotonicity check. If it is not monotone, the chain is
   optimised within the bounds.
5. Agreement between methods does not make a quantity crisp. It makes it *not validated*. The method
   spread is reported as a **lower bound**.
6. Which edge of an interval a design uses (for example the first-flight CG from the forward edge of the
   neutral point) is a target of the design or the evaluation, not a canon value (A10).
7. **Neutral point**: worlds textbook (eta 0.9), Pappas, AVL. AeroBuildup is not a world for the
   neutral point. This amends ADR 0026 point "x_np from the solver" for this quantity.

## Consequences

- **ADR 0022 holds.** One entry, one producer; its value is an interval. Worlds are part of the
  definition, not second authorities.
- The canon navigator marks uncertain quantities and everything depending on them, like target-bound
  quantities (A9).
- The app must carry intervals for these quantities: recommended CG, static margin, and the CG window
  edges (#1154).
- Further candidates with measured spread: roll rate, directional stability with fuselage, forward trim
  limit.

## Rejected alternatives

- **Probability (variance addition, Monte Carlo):** needs invented distributions and averages away the
  worst case that robust design needs.
- **Fuzzy triangle with the median as core:** three methods do not justify a "fully plausible" value,
  and the triangle invents a shape (adversarial review).
- **Control instances (one authority plus probes):** keeps a crisp number that the physics does not
  support.
