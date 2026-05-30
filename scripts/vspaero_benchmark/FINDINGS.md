# Benchmark Findings

The point of this cross-validation wasn't just "do the numbers match" —
it was to surface where our import + analysis path diverges from an
independent reference (VSPAERO) and from reality. It found several
genuine app-level issues. Each is a candidate GH bug ticket.

## F1 (#788) — Converter: reference area taken from the *first* wing geom, not the main wing
**Severity: high.** `aeroplane_schema_to_asb_airplane` sets
`airplane.s_ref` (and b_ref/c_ref) from `wings[0]`. When the OpenVSP
import order places the tailplane before the main wing, the reference
area becomes the **tail** area and **every aerodynamic coefficient is
wrong by the wing/tail area ratio**.

- **Evidence:** Spitfire import order is `HTP, VTP, Wing`. The main
  wing area is 22.08 m² but `airplane.s_ref` came out as 2.69 m² (the
  HTP area) → C_L inflated ~8.2×, C_Lα ≈ 0.60/deg (physically
  impossible, > 2π/rad). DG-101G and Cessna were unaffected only
  because their main `Wing` geom imports first.
- **Impact:** any analysis (the app's default AeroBuildup included) on
  such an aircraft reports coefficients ~8× wrong, silently.
- **Fix direction:** pick the reference wing by largest planform area
  (or an explicit "main wing" flag), not by import order.
- **Benchmark workaround:** `pipeline_asb.correct_reference_to_main_wing`.

## F2 (#789) — Importer: airfoil .dat files contain duplicate adjacent points
**Severity: medium.** Imported airfoils carry duplicate adjacent
coordinates, which makes `aerosandbox.Airfoil.repanel()` (used during
VLM section subdivision) raise *"duplicate point"*.

- **Evidence:** DG-101G import → 3 duplicate points removed before ASB
  VLM would run; without removal `VortexLatticeMethod.run()` crashes.
- **Fix direction:** de-duplicate consecutive points when writing
  `vsp_imported_*.dat`.
- **Benchmark workaround:** `pipeline_asb._sanitize_airfoils`.

## F3 (#790) — AeroBuildup fails (divide-by-zero) on the Stratos boxwing fuselage
**Severity: medium.** For the Ligeti Stratos, AeroBuildup returns
all-NaN. The traceback is a divide-by-zero in
`aerosandbox/geometry/fuselage.py` and `aero_buildup.py` (`log10`),
triggered by the imported fuselage geometry (degenerate dimension).

- **Evidence:** Stratos AeroBuildup sweep → 15/15 NaN. VLM on the same
  airplane succeeds. So it's the fuselage representation feeding
  AeroBuildup, not the boxwing lifting surfaces.
- **Fix direction:** guard the fuselage fineness-ratio / length calc
  against zero, or sanitise degenerate fuselage dimensions on import.

## F4 (#791) — Importer airfoil camber fidelity (C_L0 offset)
**Severity: low/medium (accuracy).** Same-method (VLM) comparison shows
matched lift *slope* but a consistent C_L0 offset between VSPAERO
(reads the native .vsp3 section) and ASB (reads the importer's
extracted `.dat`).

- **Evidence (DG-101G):** C_Lα agree to ~1.7 % (0.102 vs 0.104 /deg),
  but C_L0 differs by ~0.43 (VSPAERO 0.87 vs ASB-VLM 0.44). Reference
  areas are byte-identical and all twists are 0°, so the offset
  localises to the **airfoil camber / zero-lift angle** the importer
  reproduces.
- **Fix direction:** verify the camber line of `vsp_imported_*.dat`
  against the source section; the extraction appears to lose part of
  the camber's zero-lift contribution.

## F5 (#792) — Importer xsec augmentation makes ASB VLM intractable at default resolution
**Severity: low (perf, VLM only).** The wing xsec augmentation
(gh-754/760) produces many sections (Cessna → 31 wing xsecs). ASB's
default `spanwise_resolution=10` subdivides *each* section → a single
VLM solve took **215 s** (≈ 54 min for a 15-α sweep).

- **Note:** the app's default method is AeroBuildup (0.4 s for the same
  sweep), so end users are unaffected unless they explicitly pick VLM.
- **Benchmark mitigation:** scale `spanwise_resolution` to the section
  count (`pipeline_asb._vlm_spanwise_resolution`).

---

## What validated well

- **AeroBuildup vs reality (DG-101G):** max L/D ≈ 39 vs Akaflieg's
  measured 38.3 (+2 %). The app's default method matches a real glider
  polar closely.
- **VLM lift-slope (ASB vs VSPAERO):** agree within ~2–3 % on the
  conventional aircraft — the two independent VLM implementations are
  consistent once references match.
