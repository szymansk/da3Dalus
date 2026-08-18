---
name: e_resolved
symbol: e
kind: quantity
unit: dimensionless
cluster: perf-matching
user_visible: true
source_status: PARTIAL
---

# Resolved Oswald factor

**Definition.** Oswald efficiency taken from the aircraft dict or defaulted with a warning.

**Formula — as the code writes it.**

```
_e_provided = aircraft.get("e_oswald", aircraft.get("e")); if _e_provided is None or float(_e_provided) <= 0: e = DEFAULT_E_OSWALD; warnings.append(...) else: e = float(_e_provided)
```

**Inputs.** [[default_e_oswald_mc|Default Oswald factor (matching chart)]]

**Produced by.** `app/services/matching_chart_service.py:768` — `compute_chart`

**Consumed by.**

- in this graph: [[chart_warnings|Matching-chart design warnings]] · [[e_at_v|Reynolds-dependent Oswald factor]] · [[induced_drag_factor_k|Induced-drag factor]] · [[tw_vertical_climb|Vertical-climb T/W]] · [[v_cruise_resolved|Resolved cruise speed]] · [[v_md|Minimum-drag speed]]
- outside it: `_v_md:796,858` · `_climb_constraint` · `_vertical_climb_constraint:1159` · `warnings:772` · `hover_text:940`

**Source.** 🟡 PARTIAL

> Sadraey 2013 Eq. 4.41 §4.3.3.1: K = 1/(pi*e*AR) with 'Oswald efficiency e in the range 0.7-0.95'; typical worked value e ~ 0.85. The fallback 0.8 lies in the band but is not a tabulated value.
>
> — via `aircraft-design-scholz`

**The source states it as.**

```
e in 0.7-0.95 (Sadraey Eq. 4.41 inputs)
```

**⚠️ Divergence from the source.** This is the one fallback in the service that behaves correctly per ADR 0020 - it treats a missing OR non-physical (<= 0) value as 'not computed' and emits a design warning. It should be the template for the other seven silent fallbacks.

🟡 *Reported by the extraction pass, not independently verified.*

**⚠️ Scale (ADR 0023).** The 0.7-0.95 band is for full-scale wings. At RC Reynolds numbers and the low aspect ratios common in this class, e is not characterised by that band, so adopting the transport-derived range is an ADR 0023 pattern.

> This application targets RC/UAV aircraft of **0.5–15 kg**. A constant is not
> justified by being standard in transport-category literature.

**Cited in the code itself.** `# gh-956: Treat a missing OR non-physical (<= 0) value as "not computed": fall back to the default AND surface a design warning instead of silently defaulting (gh-924 single-source-of-truth policy).`

---
*Cluster [[_index-perf-matching|perf-matching]] · generated from the 2026-08-18 extraction.*
