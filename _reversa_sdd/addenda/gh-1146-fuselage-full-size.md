# gh-1146 — fuselage handed to AeroSandbox at full size through one conversion seam

| | |
|---|---|
| Issue | [#1146](https://github.com/szymansk/da3Dalus/issues/1146) |
| PR | [#1351](https://github.com/szymansk/da3Dalus/pull/1351) |
| Merged | pending |

## Vigência

Vigente desde 2026-11-03.

## Summary

The app converters passed the super-ellipse half-axes `a` / `b` as AeroSandbox's full
`FuselageXSec.width` / `.height`, so every analysed fuselage was half its size (BRYAN:
best L/D 9.20 instead of 7.78). Every app path now goes through one seam,
`app/converters/superellipse_asb.py::superellipse_to_asb_xsec`, which gives
`width = 2a`, `height = 2b` (also for split sections with `n_lower`, gh-1157). The
previous inline conversion `_asb_fuselage_xsec` is deleted. The aspect-ratio band of
`Q-FD-3` ③ is not built: the maintainer rejected it (see *Decisions*).

## Impacto por artefato da extração

| Unit | Section | Tipo | Delta |
|---|---|---|---|
| `fuselage-design/superellipse-xsecs/requirements.md` | §BR-F1, RF-X1, scenario "The half-axes map to ASB width and height" | `regra-alterada` | Corrected in place by this PR (the issue mandated it): `2a → width`, `2b → height`; the old text recorded the bug as a rule. |
| `fuselage-design/requirements.md` | l.32 and §BR-F1 (l.60-61) | `regra-alterada` | Corrected in place: `2a → ASB width`, `2b → ASB height`; `a`/`b` stay half-axes. |
| `fuselage-design/superellipse-xsecs/design.md` | §F7 axis convention, l.152 | `regra-alterada` | Corrected in place: the seam applies the factor two once (`width = 2a`, `height = 2b`). |
| `fuselage-design/superellipse-xsecs/tasks.md` | T-04, its definition of done (l.65), TT-12 (l.188) | `regra-alterada` | Corrected in place: tests assert `width == 2a`, `height == 2b`. |
| `fuselage-design/tasks.md` | T-04, its definition of done (l.64), TT-21 (l.347) | `regra-alterada` | Corrected in place: tests assert `width == 2a`, `height == 2b`. |
| `fuselage-design/step-slicing/tasks.md` | definition of done, l.162 | `regra-alterada` | Clarified in place: stored `a`/`b` round-trip unchanged; the factor two belongs only to the ASB seam. |
| `fuselage-design/contracts.md` | l.48 and the field table (l.106-107) | `regra-alterada` | Corrected in place: `2a`/`2b` map to ASB `width`/`height`. |
| `fuselage-design/design.md` | axis-convention block, l.194 | `regra-alterada` | Corrected in place. |
| `data-dictionary.md` | `fuselage_xsecs.a` / `.b`, l.281-282 | `regra-alterada` | Corrected in place. |
| `erd-complete.md` | `fuselage_xsecs` entity, l.230-231 | `regra-alterada` | Corrected in place. |
| `code-analysis.md` | fuselage axis convention, l.597 | `regra-alterada` | Corrected in place. |
| `flowcharts/fuselage-design.md` | shape-law nodes M2/M3, l.101-102 | `regra-alterada` | Corrected in place. |
| `fuselage-design/superellipse-xsecs/` | conversion to ASB | `componente-novo` | One seam `superellipse_to_asb_xsec(xyz, a, b, n, n_lower)` in `app/converters/superellipse_asb.py`, used by `_asb_fuselage_xsecs_from_schema` and `fuselage_model_to_fuselage_config`. |
| `aeroplane-core/` | schema → ASB airplane | `delta-de-contrato-externo` | Every number that depends on the fuselage (AeroBuildup drag, L/D, polar, side force, `C_nβ`) changes for every aircraft with a fuselage; the stored rows do not change. |

The corrections above edit the extraction in place, which this README normally reserves
for re-extraction; issue #1146 mandated it because the old text recorded the bug as a rule.

**One seam per package:** `aero_kernel` keeps its own, already correct factor two
(`aero_kernel/solvers/asb_airplane.py:273-278`, gh-1307) because the kernel must not import
`app`; inside `app` the only conversion is `superellipse_to_asb_xsec`.

## Decisions now implemented

- `Q-FD-3 ①` — one conversion seam for every **app** path. The `cad_designer` slicer keeps
  its own `2.0 * a` (read-only package, routing would modify it); the OpenVSP handler builds
  no ASB section (its `2.0 * a` is the rounded-rectangle exponent input, already correct).
- **Rejected:** `Q-FD-3 ③` — Q-FD-3 ③ rejected, maintainer 2026-11-04: no source for the [0.3, 3.0] band; plausibility only against real reference geometry (#1353 STEP bounding box, #1349 contour). Recorded under the `Q-FD-3` answer in
  `questions.md`.
- **Not implemented:** `Q-FD-3 ②` — the import-time bounding-box check
  `2a ≤ 1.02 · Y_extent(step)` and the audit query over rows with a surviving `step_path`.
  The slicer's metrics carry no source bounding box and the slicer is read-only; tracked
  as #1353.

## Approved departures

none

## Marker candidates for the next re-extraction

- `fuselage-design/superellipse-xsecs/` — BR-F1 🟢 now matches the code at
  `app/converters/superellipse_asb.py`.
- `fuselage-design/superellipse-xsecs/` — two equivalent-section rules for `n_lower`
  coexist: the app's `area_equivalent_exponent` (ASB's closed-form area law,
  `app/converters/split_superellipse.py`) and the kernel's `equivalent_exponent`
  (exact Gamma-function area, `aero_kernel/superellipse.py`, gh-1307); they differ by
  under 0.6 %. Not changed here.

## Fontes

- Issue #1146 (Spec-Anker, `Q-FD-3`)
- `_reversa_sdd/questions.md` `Q-FD-3`
