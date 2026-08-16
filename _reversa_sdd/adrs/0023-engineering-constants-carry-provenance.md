# ADR 0023 — Engineering constants carry provenance and are validated at RC/UAV scale

- **Status:** Accepted — new decision
- **Decided:** 2026-08-14, ratified against the domain-expert consensus round
- **Deciders:** Marc Szymanski (maintainer); rulings from `expert-consensus-{sizing,aero,powertrain,turbulator}.md`
- **Confidence:** 🟢 CONFIRMED (constants traced to their source in code docstrings; divergences computed with worked examples)

## Context

The expert round asked one question of every constant, default and correlation in
the sizing and aero layers: **what was this calibrated on, and is that regime this
product's regime?** The answers were not random errors — they were all the same
error: a method standard in the literature was adopted without checking whether the
literature's aircraft resembles this product's aircraft. The product's regime is
*"hobby RC and small UAV aircraft: roughly **0.5–15 kg** … **no wheel brakes on the
vast majority of airframes**"*, at **Re ≈ 50 000 – 500 000**. Four representative
findings:

- **Roskam §3.4 landing distance is calibrated on a braked Cessna 172N** (whose POH
  the docstring itself names): `K_LDG = 0.5847` derives from a *braking* `μ = 0.4`
  where Sadraey Table 4.15 gives **rolling** friction of 0.03–0.3, so an unbraked
  model decelerates at roughly a quarter of the assumed rate. **35.5 m from Roskam
  against 52.5 m from the energy balance for the same 1.5 kg trainer.**
- **`wing_loading`'s default `412 N/m²` is a full-scale value that leaked in** —
  420 g/dm², roughly **4× above the RC "danger zone"**, where the correct trainer
  value is **≈ 55 N/m²**. It survived on a numerical coincidence
  (1 g/dm² = 0.981 N/m²), and it clips the trainer's Soll score to 1.0 against a
  declared target vertex of 0.3.
- **`LANDING_SURFACE_MU` is not what its name says** — in
  `s = V_TD²/(2·g·μ_eff)`, `μ_eff` is `a/g`, not a tyre friction coefficient. Read
  as friction it invites a reader to "correct" `grass_short = 0.15` to 0.09 and
  silently make every landing 60 % longer. Hence the rename to
  `LANDING_DECEL_COEFF`.
- **The WCL conversion was wrong three ways and misattributed** — `W/S^1.5` in oz
  and ft² is **oz/ft³**, not `lb/ft^4.5`; `47.88` is a *pressure* conversion; the
  derivation invents an AR dependence while dropping aircraft weight, the entire
  point of a cube loading. WCL is Francis Reynolds' metric, not Lennon's.

## Decision

**Every engineering constant, default and correlation carries three things:**

1. **its source** — a citable reference, or an explicit statement that it is uncited
   practice;
2. **the regime it was calibrated for** — aircraft class, mass range, Reynolds
   range, and any assumed equipment (brakes, flaps, retracts);
3. **an explicit statement that it was checked for validity at RC/UAV scale —
   0.5–15 kg, Re ≈ 50 k–500 k** — and what that check concluded.

**A method calibrated on certified transport aircraft is not admissible merely
because it is standard in that literature.** Roskam's landing chain is correct
engineering for the aircraft Roskam wrote it for; that is exactly why it produces a
confidently wrong 35.5 m here. Standard-in-the-field is evidence about pedigree, not
about applicability.

Three corollaries: **a constant's name is part of its documentation** (a wrong name
is an active hazard — it tells the next reader to make the code worse);
**dimensional analysis is part of provenance** (the WCL defects were found with no
new data); **attribution is checked, not inherited** (a citation nobody verified is
worse than none, because it stops the next reader from looking).

**Authority hierarchy** (from `CLAUDE.md`, unchanged): **1.
`aircraft-design-scholz`** (Scholz + Sadraey — lead, first choice for any sizing or
performance question) · **2. `aerodynamics-expert`** (Anderson — physics ground
truth) · **3. `aerosandbox-expert`, `avl-advisor`** (implementation tooling) ·
**4. `rc-aircraft-designer`** (RC practice, **lower authority**; legitimate where a
concrete RC number is needed and academic sources are silent at this scale —
**defers to Scholz on conflict, not for UAV**).

**Genuine disagreement is recorded, not smoothed** — the ruling states what was
overruled and why, so a later reader can reopen it:

- **Turbulator height** (`Q-WD-10`): theory says a 0.3 mm zigzag should not force
  transition, RC practice says it does. Resolved by **reclassifying the criterion** —
  `Re_k ≥ Re_k,crit` is **sufficient, not necessary** — so the policy is a *graded
  warning, never a hard block*: below `k_min` a `warning` (computed polars are
  optimistic); far above (`k/δ ≳ 0.8`, `Δcd_trip ∝ k³`) a `notice`; above
  Re ≈ 250 000 a `notice` that the measured benefit has vanished (40 % at Re 60 k →
  **0 % at 400 k**). The default rises to **0.5 mm** and must be sized at
  ≈1.1–1.3 × V_stall, not at cruise, because `Re_k ∝ V^1.5`. The `Re_k,crit` values
  (600 for 3D roughness, ≈300 for 2D) come from **Braslow & Knox, NACA TN 4363** —
  an external source, in no project vault.
- **`target_static_margin` for `acro_3d`** (`Q-MS-14`): rcplanedesigner's acrobatic
  average of 1.5 % sits inside Sadraey's 2–3 % MAC dynamic-instability band.
  Resolved for Scholz/Sadraey — **0.03, not 0.015** — because a **default** in a tool
  that also serves UAVs and first-time builders cannot assume the skilled pilot who
  can hand-fly a marginally unstable 1 m model. 0.015 stays a documented expert
  override, never the default.

Where an RC-only method has no academic counterpart, that is a **scope boundary, not
a conflict**: WCL is legitimate as an RC-specific additive constraint for trainer and
sport profiles, as `_PROFILE_CONSTRAINT_MAP` already scopes it, and **must never be
applied to a UAV profile**.

## Consequences

- Wrong numbers become findable, and several fixes are **verifiable without new
  data**: the corrected `W/S_max = (WCL[oz/ft³] · 9.818)^(2/3) · W^(1/3)` reproduces
  the independent RC trainer band, which the old code could not, because it returned
  70.8 N/m² **for every aircraft regardless of mass**.
- **Every constant now needs a home with room for prose** — a bare module-level float
  cannot carry three fields of provenance — and **the check is only as good as the
  reviewer**: a routine PR will not reproduce four dedicated expert passes.
- **Confidence is not uniform and must be stated**: `Q-MS-3` is high confidence for
  the WCL fix and **medium** for the friction table, because *"no measured RC rollout
  exists to pin `Δ_aero = 0.06`"*. Recording provenance does not make a constant
  right.
- Some corrections are **counter-intuitive and need UI explanation**: raising
  `hard_paved` to 0.10 makes paved the *longest* rollout of any surface — physically
  correct once brakes are absent, hence the new `hard_paved_braked = 0.40` as the
  lever a user expects.
- The rule governs constants and correlations, not model choice (that is
  [ADR 0003](0003-aerosandbox-default-avl-exception.md)). Fixed constants replaced by
  scaling laws — `_LANDING_FLARE_M = 15.0` becoming
  `s_air = h_obstacle · (L/D)_approach` — follow from applying it.

**Rejected:** trusting the literature (the status quo, which produced the 48 %
landing-distance split and the 412 N/m² default); re-deriving from first principles
(the academic *methods* transfer — `Q-MS-2` keeps Roskam's `_C_TO = 1.21` precisely
because it is a ground-roll energy constant, not a braking one); deferring to RC
practice throughout; recording provenance but skipping the regime statement
(`LANDING_SURFACE_MU` *had* a provenance note — the regime and the physical meaning
were what was missing).

## Related

- [ADR 0003](0003-aerosandbox-default-avl-exception.md) ·
  [ADR 0004](0004-one-aero-truth-per-aircraft.md) ·
  [ADR 0022](0022-one-authority-per-user-facing-quantity.md) (calibration regime as
  the designation argument) ·
  [ADR 0020](0020-one-designwarning-channel-no-undeclared-fallbacks.md) (the channel
  the graded turbulator policy emits into).
- [ADR 0011](0011-cg-is-a-top-down-design-target.md) — `Q-MS-14` supplies the
  citation its static-margin ladder was missing: Sadraey §11.4's 2–3 % MAC
  dynamic-instability band, now anchoring `error` below SM 0.02 and `warning` below
  0.03.
- [`../questions.md`](../questions.md) §Q-MS-1 · Q-MS-2 · Q-MS-3 · Q-MS-11 ·
  Q-MS-14 · Q-WD-10; full reasoning in
  [`../expert-consensus-sizing.md`](../expert-consensus-sizing.md),
  [`../expert-consensus-aero.md`](../expert-consensus-aero.md),
  [`../expert-consensus-turbulator.md`](../expert-consensus-turbulator.md).
