---
name: default_e_oswald_mc
symbol: e_default
kind: constant
unit: dimensionless
cluster: perf-matching
user_visible: true
source_status: PARTIAL
node_class: unclassified-constant
tags:
  - cluster/perf-matching
  - class/unclassified-constant
  - source/partial
  - surface/user-visible
  - flag/anomaly
  - flag/divergence
  - flag/scale
---

# Default Oswald factor (matching chart)

**Definition.** Oswald efficiency used when no computed value is available.

⚪ **Unclassified constant.** Not yet decided whether this is a rule of thumb, a calibration or a physical value. Classifying it is open work — it is deliberately not guessed.

**Value.** `0.8`

**Formula — as the code writes it.**

```
DEFAULT_E_OSWALD: float = 0.8
```

**Inputs.** — *(leaf: a constant or an external input)*

**Produced by.** `app/services/matching_chart_service.py:77` — `DEFAULT_E_OSWALD`

**Consumed by.**

- in this graph: `Resolved Oswald factor`  
  *(these are backlinks — open the Backlinks pane to navigate them)*
- outside it: `compute_chart:771` · `warnings list:772`

**Source.** 🟡 PARTIAL

> Sadraey 2013 Eq. 4.40/4.41 §4.3.3.1: C_D = C_Do + K*C_L^2, K = 1/(pi*e*AR), with 'Oswald efficiency e in the range 0.7-0.95'; the worked guidance uses e ~ 0.85. 0.8 lies inside the band but is not attributable to a specific tabulated value.
>
> — via `aircraft-design-scholz`

**The source states it as.**

```
e in 0.7-0.95, typical 0.85 (Sadraey Eq. 4.41 inputs)
```

**⚠️ Divergence from the source.** The same 0.8 is independently defined at powertrain_sizing_service.py:45 and inline at assumption_compute_service.py:262 and polar_re_table_service.py:191 - four producers of one constant (ADR 0022).

🟡 *Reported by the extraction pass, not independently verified.*

**⚠️ Scale (ADR 0023).** The 0.7-0.95 band is for full-scale wings at high Reynolds number. At RC Reynolds numbers (Re ~1e5) and low aspect ratios, e is not well characterised by that band; adopting it is an ADR 0023 pattern even though the number happens to be conservative.

> This application targets RC/UAV aircraft of **0.5–15 kg**. A constant is not
> justified by being standard in transport-category literature.

**⚠️ Anomaly.** The same 0.8 default is independently defined at powertrain_sizing_service.py:45 (_DEFAULT_E_OSWALD) and inline at assumption_compute_service.py:262 — three producers of one constant (ADR 0022).

🟡 *Reported by the extraction pass, not independently verified. Do not cite as a
defect until confirmed against the code.*

**Cited in the code itself.** `# gh-956: default Oswald factor used when no computed value is available. Consumers should surface a design warning rather than silently using this.`

---
*Cluster [[_index-perf-matching|perf-matching]] · generated from the 2026-08-18 extraction.*
