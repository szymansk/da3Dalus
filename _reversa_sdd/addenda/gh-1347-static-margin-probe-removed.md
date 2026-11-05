# gh-1347 — static-margin probe removed; the fuselage declaration claims no number

| | |
|---|---|
| Issue | [#1347](https://github.com/szymansk/da3Dalus/issues/1347) |
| PR | pending |
| Merged | pending |

## Vigência

Vigente desde 2026-11-05.

## Summary

The issue measured AeroBuildup's static-margin probe (`−C_mα/C_Lα` at `V_md` about the design CG)
on the reference fleet and found it biased beyond its tolerance on every aircraft. The maintainer
chose option D (2026-11-05): delete the probe with recorded reasons. The canon formula, its two
output quantities, its agreement rule, its three warnings, the OPT adapter call and its worker are
gone; with them went the only reader of AeroBuildup's pitching moment, so the polar type loses its
`C_m` column and the AeroBuildup model function its `Cm` output (ADR 0021). Pitch stability stays
covered by the `neutral-point` worlds (ADR 0027, unchanged) and `static-margin`. In the same PR the
`fuselage_not_modelled` declaration of `neutral-point` stops claiming a magnitude.

## Impacto por artefato da extração

| Unit | Section | Tipo | Delta |
|---|---|---|---|
| `calculations/canon/formulas/static-margin-probe.md` | whole entry | `componente-extinto` | Deleted, with `quantities/static-margin-probe.md` and `quantities/pitching-moment-slope.md`; read the canon as having no AeroBuildup moment-slope check. |
| `calculations/canon/rules.yaml` | `static-margin-probe-agreement` | `regra-removida` | Deleted with its parameter `agreement_tolerance` = 0.05; the rule of 2026-11-02 (#1342: tolerance first, a sign disagreement beyond it an `error`) no longer exists. The rule kind `probe` stays defined, with no rule of that kind. |
| `calculations/canon/README.md` | polar type; `checks` example | `regra-alterada` | A `polar` is α, C_L, C_D (no C_m); the `checks` example is now `minimum-drag-speed-probe` checks `minimum-drag-speed`. |
| `calculations/canon/quantities/polar-stall.md`, `formulas/stall-speed.md` | polar content | `delta-de-dados` | The published stall polar carries no C_m. It never reached the public API (a `QuantityResult` holds floats only). |
| `calculations/canon/formulas/neutral-point.md` | "Not validated" paragraph | `regra-alterada` | `fuselage_not_modelled` states no number: the fuselage moves the NP forward by typically a few percent MAC, the static margin is optimistic, choose the CG rather forward for the first flight. The DATCOM estimate stays as a record only. |
| `calculations/canon/ANFORDERUNGEN.md` | §2.3 tables, K22 | `regra-removida` | Probe rows marked struck (05.11.2026, #1347). |
| `aero_kernel` | warning catalogue (`schema.py`) | `delta-de-contrato-externo` | `aerobuildup_no_downwash`, `static_margin_probe_disagrees`, `static_margin_probe_sign_disagrees` no longer exist; the quantities `static-margin-probe` and `pitching-moment-slope` are unknown slugs. No app or frontend code referenced them. |

## Decisions now implemented

- Maintainer decision 2026-11-05 on #1347, option D — recorded in
  `calculations/canon/STAND.md` (entry "Static-margin probe removed").
- Maintainer decision 2026-11-05 on #1347 — `fuselage_not_modelled` claims no number, recorded in
  `calculations/canon/STAND.md` and `formulas/neutral-point.md`.

Reasons, from the measurement of 2026-11-04 (BRYAN, JAGUAR, CHEKKER, BELEMNITOS, WIESEL, RV-7):

- AeroBuildup's NP lies +0.04 … +0.16 MAC aft of AVL's and +0.08 … +0.22 MAC aft of the textbook world,
  because AeroBuildup omits the main-wing downwash on the tail (Sharpe 2024 §5.3/§5.4; AVL's
  1 − dε/dα is 0.50–0.70). The probe read 0.18–0.32 against a target of 0.10: the bias exceeds both the
  0.05 tolerance and the spread of the NP worlds, so the warning fired on every aircraft.
- NeuralFoil's low-Re lift-curve nonlinearity makes the probe vary by up to 0.6 MAC within α_md ± 1.5°.
- Trim (all-moving tail) flips its sign on the RV-7 (0.183 → −0.076).
- Fuselage: the same comparison gave a fuselage effect of 2–11 % MAC with AVL bodies and 0.4–11 % with
  AeroBuildup; the models disagree per aircraft, so no figure is reliable, and for RC the CG is set in
  flight, so no further investigation (maintainer).

## Approved departures

none

## Marker candidates for the next re-extraction

- `calculations/canon/` — the static-longitudinal chain is `neutral-point` → `static-margin` /
  `cg-for-target-margin` only.

## Fontes

- Issue #1347, comments of 2026-11-04 (measurement) and 2026-11-05 (decision)
