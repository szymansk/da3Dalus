---
canon: parasite-drag-split
entry: formula
kind: procedure
shape: law
status: draft
output: zero-lift-drag-coefficient, oswald-efficiency
source_status: SOURCED
dimensional_check: PROCEDURAL
tags:
  - canon/formula
  - source/sourced
  - dim/procedural
  - shape/law
  - kind/procedure
  - status/draft
tex: C_{D0} = C_D - \frac{C_L^2}{\pi\,AR\,e_{osw}} \quad\text{am Reiseflugpunkt}
---

# Parasite drag coefficient and span efficiency at the cruise point (ADR 0004)

**Canonical form**

```
solve for alpha at the cruise point:   L(V_cruise, alpha) = m * g          (AeroBuildup)
e_osw  := AeroBuildup's Oswald factor (empirical, Nita & Scholz 2012), read back as C_L^2 / (pi * AR * C_Di)
C_D0   := C_D - C_L^2 / (pi * AR * e_osw)                                   (parasite, not total C_D)
```

**Produces** [[zero-lift-drag-coefficient]] · [[oswald-efficiency]]  ·  **from** [[airplane]] · [[cruise-speed]] · [[aircraft-mass]] · [[gravity]] · [[air-density]] · [[aspect-ratio]]

**Kind: a procedure — one evaluation of the solver at one named point.** This is the
canon's statement of **ADR 0004** (gh-924, binding): *one aircraft has exactly one
aerodynamic truth, produced once at the cruise design point and read by everyone.*
`C_D0` is the total `C_D` minus the induced part (Anderson §6.7.2).

**⚠ Under review (maintainer, 2026-10-02) — not adopted as given.** A critical reading of
ADR 0004 found: (1) `e` is **not** a Trefftz-plane result. AeroBuildup has no Trefftz plane;
it computes `e` from the empirical correlation of Nita & Scholz (2012) from aspect ratio,
taper and sweep (`aerosandbox/library/aerodynamics/inviscid.py:25`), and the app reads it
back as `C_L²/(π·AR·C_Di)` and merely *labels* it "aerobuildup_trefftz"
(`assumption_compute_service.py:244-254`). Its validity at model scale is unchecked
(ADR 0023). (2) With an empirical induced part, `C_D0` is "everything but the estimated
induced drag at the cruise point" — the lift-dependent profile drag is in it, so it is not
parasite drag in the textbook sense. (3) It hangs on `V_cruise`, which is still open.
The definitions of `C_D0`, `e` and `(L/D)max` go to a domain-expert review and then to a
new ADR (O13); the **principle** of one value per aircraft (ADR 0004, ADR 0022) stays.

**Replaces** (2026-10-02) the two producers the canon had, both departing from ADR 0004:
`zero-lift-drag-from-sweep` (`C_D` at the `C_L = 0` crossing — for a cambered RC section
that reads the rising left branch of the polar, not the parasite drag) and
`reynolds-scheduled-polar` (an interpolation over Reynolds number that listed its own
output as an input). With them goes the false cycle `C_D → C_D0 → C_D` that the navigator
had to cut by hand.

**Design direction.** Before an airplane exists, `C_D0` and `e` are **estimates**
(ADR 0010: a design assumption carries an estimate and a calculated value). This entry is
the producer of the calculated value; the source of the estimate is O12.

**Bound to the cruise speed.** Its value is only as settled as `V_cruise`, which is still
`cruise-speed-resolution` (open).

**Source.** 🟡 ADR 0004 (definitions under review, see above); Anderson, *Fundamentals of Aerodynamics* §6.7.2; Scholz eq. 5.39 for
the companion `(L/D)max` (see [[max-lift-to-drag-parabolic]]).
