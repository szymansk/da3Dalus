# gh-1146 — fuselage handed to AeroSandbox at full size through one conversion seam

| | |
|---|---|
| Issue | [#1146](https://github.com/szymansk/da3Dalus/issues/1146) |
| PR | [#PR_NUMBER](https://github.com/szymansk/da3Dalus/pull/PR_NUMBER) |
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
`Q-FD-3` ③ is declared as a `DesignWarning` in the assumptions summary.

## Impacto por artefato da extração

| Unit | Section | Tipo | Delta |
|---|---|---|---|
| `fuselage-design/superellipse-xsecs/requirements.md` | §BR-F1, RF-X1, scenario "The half-axes map to ASB width and height" | `regra-alterada` | Corrected in place by this PR (the issue mandated it): `2a → width`, `2b → height`; the old text recorded the bug as a rule. |
| `fuselage-design/requirements.md` | l.32 and §BR-F1 (l.60-61) | `regra-alterada` | Read "`a → ASB width`" as "`2a → ASB width`" and "`b → ASB height`" as "`2b → ASB height`"; `a`/`b` stay half-axes. |
| `fuselage-design/superellipse-xsecs/` | conversion to ASB | `componente-novo` | One seam `superellipse_to_asb_xsec(xyz, a, b, n, n_lower)` in `app/converters/superellipse_asb.py`, used by `_asb_fuselage_xsecs_from_schema` and `fuselage_model_to_fuselage_config`. |
| `fuselage-design/superellipse-xsecs/` | plausibility | `regra-nova` | `GET /aeroplanes/{id}/assumptions` → `design_warnings` carries `FUSELAGE_ASPECT_RATIO_OUTSIDE_BAND` (`severity: warning`) for a body whose `max(2a)/max(2b)` lies outside `[0.3, 3.0]` (`app/services/fuselage_plausibility_service.py`). Never an exception. |
| `aeroplane-core/` | schema → ASB airplane | `delta-de-contrato-externo` | Every number that depends on the fuselage (AeroBuildup drag, L/D, polar, side force, `C_nβ`) changes for every aircraft with a fuselage; the stored rows do not change. |

## Decisions now implemented

- `Q-FD-3 ①` — one conversion seam for every **app** path. The `cad_designer` slicer keeps
  its own `2.0 * a` (read-only package, routing would modify it); the OpenVSP handler builds
  no ASB section (its `2.0 * a` is the rounded-rectangle exponent input, already correct).
- `Q-FD-3 ③` — aspect-ratio band `2a/2b ∈ [0.3, 3.0]` as `DesignWarning`, judged per body
  on the largest section of each axis.
- **Not implemented:** `Q-FD-3 ②` — the import-time bounding-box check
  `2a ≤ 1.02 · Y_extent(step)` and the audit query over rows with a surviving `step_path`.
  The slicer's metrics carry no source bounding box and the slicer is read-only; it needs
  its own ticket.

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
