# ADR 0026 — The aero truth comes from the solver, not from the parabola

- **Status:** Accepted — **amends [ADR 0004](0004-one-aero-truth-per-aircraft.md)** in its
  definitions; ADR 0004's principle stays in force
- **Amended by:** [ADR 0027](0027-uncertain-quantities-as-intervals-over-method-worlds.md) for the neutral point (an interval over method worlds, AeroBuildup excluded)
- **Decided:** 2026-10-02, by the maintainer
- **Basis:** a critical re-reading of ADR 0004 requested by the maintainer ("decisions made
  on an incomplete view must not be taken as given"), two independent domain reviews
  (Anderson, Scholz/Sadraey) and a measurement on the BRYAN reference aircraft
- **Confidence:** 🟢 for the findings below (read from code, measured); the decision is the
  maintainer's
- **Execution:** Soll. The calculation canon (`_reversa_sdd/calculations/canon/`) states it;
  code tickets follow once the ticket rule is settled (canon §5 / review item D)

## Context — what ADR 0004 got right, and what it rested on

ADR 0004 ended a real defect: one aircraft showed three `cd0`, two neutral points and two
`L/D`. Its **principle** — one value per aircraft, produced once, read by everyone — is
correct and is generalised by [ADR 0022](0022-one-authority-per-user-facing-quantity.md).

Its **definitions** do not survive a critical reading:

1. **`e` is not a Trefftz value.** AeroBuildup has no Trefftz plane. Its span efficiency is
   the empirical correlation of Nita & Scholz (2012) from aspect ratio, taper and sweep
   (`aerosandbox/library/aerodynamics/inviscid.py:25`), times a viscous factor
   `k_e,D0 = 0.836` — the mean of jet transport, business jet, turboprop and general
   aviation (`:33-38`). The app reads it back as `C_L²/(π·AR·C_Di)` and *labels* it
   `aerobuildup_trefftz` (`assumption_compute_service.py:244-254`).
2. **`cd0 = CD − CL²/(π·AR·e)` at cruise is not parasite drag** in Anderson's sense
   (§6.7.2): with that `e` it is "all drag except the estimated induced drag at the cruise
   C_L", lift-dependent profile drag included. It also hangs on the cruise speed, which the
   canon has not yet settled (`cruise-speed-resolution`).
3. **`(L/D)max = ½·√(π·AR·e/CD0)` was chosen against a defective alternative.** "Not
   argmax" was right because that argmax ran over a sweep mixing the Reynolds numbers of
   different speeds (18.8 vs 23.4). The canon's optimisations enforce `L = W` at the correct
   Reynolds number per speed — the defect does not exist there. The closed form, by
   contrast, assumes a parabolic polar, which RC wings at Re ≈ 1e5 are not (1.5 kg trainer:
   `V_mp/V_md = 0.70` against the parabolic 0.76). The citation is also off: Scholz eq.
   5.39 is `C_L,md`; the formula follows from the same polar but is not that equation.

## Decision

1. **Principle kept.** One authority per quantity (ADR 0004, ADR 0022).
2. **The analysis computes with the solver drag.** Every performance quantity — `V_md`,
   `V_mp`, climb, turn, `V_max`, `(L/D)max`, power required, endurance, range — comes from
   the solver drag with `L = W` at the correct Reynolds number. `(L/D)max = W / D(V_md)` at
   the minimum-drag optimum: no new producer. The parabolic closed form is the **Probe**;
   a deviation beyond tolerance is reported as a `DesignWarning` ("polar not parabolic",
   ADR 0020), never substituted.
3. **`C_D0` and `e` are the parabola fitted by least squares over the operating `C_L`
   window** of the solver polar along level flight (each point at its own speed). `C_D0` is
   then the fitted zero-lift parasite drag and `e` the Oswald factor, comparable with
   literature values. They serve **display** and the **calculated value** of the `cd0`
   design assumption (ADR 0010, estimate vs calculated) — **never an input** to the
   performance computation. The fit residual says how non-parabolic the polar is.
4. **Design direction** (before geometry exists): Scholz's chain — `E_max` from the wetted
   aspect ratio, `C_D0 = c_f · form factor · S_wet/S_ref` — with `c_f` evaluated at the
   **mission Reynolds number** (≈ 0.006–0.008 at Re 1e5). The textbook constants
   (`c_f = 0.003`, `k_E = 14.9`, Sadraey Table 4.12, `k_e,D0`) are **not** carried over
   (ADR 0023). These values are estimates and give way to the solver once an airplane exists.
5. **Declared caveat.** AeroBuildup's `e` carries the full-scale `k_e,D0` on top of the
   section profile drag it already takes from NeuralFoil — lift-dependent profile drag is
   partly counted twice. Measured on BRYAN: AeroBuildup `e = 0.805`, AVL (inviscid)
   `e = 0.875` → about 9 % more induced drag than AVL. Not correctable without changing
   AeroSandbox; declared under ADR 0023.

## Consequences

- **Superseded rules** in `aero-analysis/requirements.md`: BR-AA7 and RF-15 (`(L/D)max`
  from the closed form), BR-AA11 (Picard refinement), BR-AA13 (Re-table backfill), and the
  `cd0`/`e` definitions of BR-14. BR-14's principle stands.
- **User-visible numbers change**: `L/D`, endurance and range move from the parabola to the
  solver; `cd0` and `e` change meaning (fitted, labelled honestly).
- **The canon** carries it: `parabolic-polar-fit` (C_D0, e), `minimum-drag-speed-from-polar`
  also producing `(L/D)max`, `max-lift-to-drag-parabolic` as Probe, `power-required` from
  the solver drag.

## Related

[ADR 0004](0004-one-aero-truth-per-aircraft.md) (amended) ·
[ADR 0010](0010-design-assumptions-carry-estimate-and-calculated.md) ·
[ADR 0020](0020-one-designwarning-channel-no-undeclared-fallbacks.md) ·
[ADR 0022](0022-one-authority-per-user-facing-quantity.md) ·
[ADR 0023](0023-engineering-constants-carry-provenance.md)
