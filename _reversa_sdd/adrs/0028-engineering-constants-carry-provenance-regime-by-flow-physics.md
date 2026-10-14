# ADR 0028 — Engineering constants carry provenance; the regime is defined by flow physics

- **Status:** Accepted. **Supersedes [ADR 0023](0023-engineering-constants-carry-provenance.md).**
- **Decided:** 2026-10-14, by the maintainer: "Der ADR0023 ist definitiv nicht korrekt und muss geändert
  werden" — the mass range "was a hint to Claude where RC models and UAVs usually lie … it is not needed
  for our calculations, so it must not be a requirement of the calculation core". Regime by flow physics,
  new ADR superseding 0023 (both maintainer choices, same day).
- **Basis:** research pass 2026-10-14 (aerosandbox-expert, aerodynamics-expert, aircraft-design-scholz
  vaults; Lissaman 1983 read directly; AVL documentation). Reference fleet Reynolds numbers estimated from
  `R = V c / ν`.
- **Confidence:** 🟢 for the physical bounds (Lissaman, Anderson); 🟡 for the warning bands as practice
  (marked 💡 where no source exists).

## Context

ADR 0023 required every engineering constant to carry its source, its calibration regime and a check for
validity "at RC/UAV scale — **0.5–15 kg**, Re ≈ 50 k–500 k". Its core rule was right: a method standard in
transport-aircraft literature is not admissible merely because it is standard (Roskam's braked landing
roll, the 412 N/m² wing loading). Its **definition of the regime** was wrong twice:

- **Mass is not a physical criterion.** No formula's validity depends on the aircraft weighing 0.5 kg.
  The range excluded the project's own reference fleet: BRYAN 0.151 kg, JAGUAR ≈ 0.160 kg, BELEMNITOS
  0.28 kg, CHEKKER 0.439 kg. It was a hint about the size class, read as a requirement.
- **Re ≥ 50 k is too high a floor.** BRYAN and the e-Hawk fly at Re ≈ 35–40 k at stall; indoor and park
  flyers lower still. What changes the physics is the Reynolds number, and the change happens *inside* the
  RC range, not at its edge.

## Decision

**Every engineering constant, default and correlation carries three things** (unchanged from 0023):

1. **its source** — a citable reference, or an explicit statement that it is uncited practice;
2. **the regime it was calibrated for** — aircraft class, **Reynolds range**, Mach range, and any assumed
   equipment (brakes, flaps, retracts);
3. **a statement that it was checked for validity in this product's regime**, and what the check concluded.

**This product's regime is defined by flow physics, not by mass:**

| Quantity | Band | Treatment | Source |
|---|---|---|---|
| Chord Reynolds number `Re_c = V c / ν`, per wing station, at stall and in cruise | **3·10⁴ … 1·10⁶** | core regime | Lissaman 1983 p. 227–228: "low Re" is 10⁴–10⁶; below 3·10⁴ separation can involve the whole trailing edge |
| | 3·10⁴ … 7·10⁴ | inside the core, **warning "bubble-sensitive"** (severity: domain practice) | Lissaman p. 228: critical Re ≈ 70 000, a laminar bubble needs Re ≈ 50 000 of run to reattach; Sharpe 2024 §7.2.4: NeuralFoil's analysis confidence drops near Re 80 k, C_L 1.0 |
| | < 3·10⁴ | compute, **warning "outside the core regime"** — section polars (C_L,max, C_D) not reliable | 💡 from Lissaman p. 228 |
| | > 1·10⁶ | compute, notice only — the tools stay valid (NeuralFoil trained to Re ≈ 2.6·10⁸, Sharpe §7.2.5), the physics becomes more benign | Lissaman p. 228 |
| Mach number | ≤ 0.3 | incompressible | Anderson §8.5: density change < 5 % |
| | 0.3 … 0.6 | compute with Prandtl–Glauert/Laitone correction, **warning** | AVL documentation ("PG expected valid" to M ≈ 0.6); NeuralFoil's Laitone correction |
| | > 0.6 | **warning, severity: defect** | 💡 |
| Equipment | RC/UAV practice: no wheel brakes on most airframes, hand or bungee launch, unpaved fields | stated per constant | ADR 0023's findings, kept |

**Values outside a band are computed and warned, never rejected** (ADR 0020). Rejection is reserved for
physically inadmissible input (mass ≤ 0, chord ≤ 0, non-finite numbers).

**Mass and size are a hint about the class, not a criterion.** RC models and small UAVs typically weigh
from a few grams (indoor) to about 25 kg. A source calibrated on a far heavier class is still suspect, and
that suspicion is checked through the regime above (Re, Mach, equipment), not through the mass.

**Two further regime conditions:**
- **Transition is a precondition below Re ≈ 7·10⁴.** There the result depends on where the boundary layer
  transitions (Anderson §4.12, §20.3.2): a turbulator or a rough printed surface removes the step
  (Lissaman Fig. 2). A constant calibrated on smooth wind-tunnel models states that. 💡
- **Propeller Reynolds numbers are checked separately.** Small propellers run at Re₀.₇₅ ≈ 15–100 k, below
  the wing (Brandt & Selig 2011 §IV; Deters, Ananda & Selig 2014 §V.B).

**Kept from 0023 unchanged:** a method calibrated on certified transport aircraft is not admissible
because it is standard there; a constant's name is part of its documentation; dimensional analysis is part
of provenance; attribution is checked, not inherited; the authority hierarchy (Scholz/Sadraey →
Anderson → AeroSandbox/AVL → RC practice); genuine disagreements are recorded, not smoothed (turbulator
height `Q-WD-10`, `target_static_margin` for `acro_3d` `Q-MS-14`); WCL stays an RC-only constraint, never
applied to UAV profiles.

## Consequences

- **The calculation core validates physical admissibility only.** A Reynolds or Mach number outside a band
  becomes a `DesignWarning`, not an error. All five reference aircraft (SNACK, BRYAN, JAGUAR, CHEKKER,
  BELEMNITOS) are inside the product's regime, most of them in the bubble-sensitive band — which is where
  RC models fly and therefore where the canon must be tested.
- **Canon entries state validity per regime, not per mass:** the field "Validity at 0.5–15 kg" becomes
  "Validity in the RC/UAV regime" and names the Re/Mach band and the conditions.
- **Re is a per-operating-point quantity.** A constant can be valid in cruise and outside its band at stall
  on the same aircraft; the check belongs to the operating point (A3, O10).
- The 0023 findings (Roskam landing roll, 412 N/m², `LANDING_DECEL_COEFF`, WCL) stand; they were found
  through regime and equipment, not through mass.

**Rejected:** keeping a mass range with a lower bound > 0 kg (still not a physical criterion); widening
the Re range without the bubble-sensitive band (it hides the regime change at ≈ 70 k where RC models
actually fly); rejecting out-of-band input (contradicts ADR 0020 and would block the reference fleet).

## Related

- [ADR 0023](0023-engineering-constants-carry-provenance.md) — superseded; its findings and corollaries
  carry over unchanged.
- [ADR 0020](0020-one-designwarning-channel-no-undeclared-fallbacks.md) — the channel out-of-band values
  emit into. [ADR 0027](0027-uncertain-quantities-as-intervals-over-method-worlds.md) — method worlds at
  low Re. [ADR 0003](0003-aerosandbox-default-avl-exception.md) — tool choice.
- Sources: P. B. S. Lissaman, *Low-Reynolds-Number Airfoils*, Ann. Rev. Fluid Mech. 15 (1983) 223–239;
  J. D. Anderson, *Fundamentals of Aerodynamics* 6e, §4.12, §8.5, §20.3.2; P. D. Sharpe, PhD thesis MIT
  2024, §7.2.4–7.2.5 (NeuralFoil); M. Drela & H. Youngren, AVL documentation; Brandt & Selig 2011; Deters,
  Ananda & Selig 2014; UIUC LSAT (Selig) for measured RC airfoil data at 40–500 k.
