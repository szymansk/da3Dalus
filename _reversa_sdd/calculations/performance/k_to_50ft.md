---
name: k_to_50ft
symbol: k_TO_50ft
kind: constant
unit: dimensionless
cluster: perf-matching
user_visible: true
source_status: PARTIAL
node_class: regulatory-constant
tags:
  - cluster/perf-matching
  - class/regulatory-constant
  - source/partial
  - surface/user-visible
  - flag/anomaly
  - flag/divergence
  - flag/scale
---

# Takeoff 50-ft obstacle factor

**Definition.** Multiplier converting takeoff ground roll to distance over a 50-ft obstacle.

**Regulatory constant.** Taken from a standard. It carries the clause *and* the class of aircraft that clause applies to.

**Value.** `1.66`

**Formula — as the code writes it.**

```
_K_TO_50FT: float = 1.66
```

**Inputs.** — *(leaf: a constant or an external input)*

**Produced by.** `app/services/field_length_service.py:75` — `_K_TO_50FT`

**Consumed by.**

- in this graph: `Obstacle-corrected distance` · `Takeoff distance over 50 ft` · `Takeoff constraint T/W`  
  *(these are backlinks — open the Backlinks pane to navigate them)*
- outside it: `compute_field_lengths:419,425` · `matching_chart_service._takeoff_constraint:310` · `matching_chart hover_text:896`

**Source.** 🟡 PARTIAL

> Obstacle height SOURCED: FAR Part 23 §23.53 -> 50 ft (Scholz 05_PreliminarySizing §5.2; CS-25/FAR-25 use 35 ft). The factor 1.66 itself is not in Scholz or Sadraey. Most plausible provenance is the ratio of the two Roskam Part I FAR-23 regressions on the same takeoff parameter (leading coefficients 8.134/4.9 = 1.660) - reconstruction, not a verified citation.
>
> — via `aircraft-design-scholz`

**The source states it as.**

```
s_TO_50ft / s_TO_ground for FAR-23 propeller aircraft
```

**⚠️ Divergence from the source.** Roskam's FAR-23 regressions are built on a POWER-based takeoff parameter TOP_23 = (W/S)(W/P)/(sigma*CL_max_TO); this code's ground roll is THRUST-based. Borrowing the ratio across two different parameterisations is not justified by any source. Roskam is not in the consulted vault, so the '§3.4' section number cannot be confirmed.

🟡 *Reported by the extraction pass, not independently verified.*

**⚠️ Scale (ADR 0023).** 50 ft is an FAR-23 certification obstacle for manned GA aircraft; it has no operational meaning for a 0.5-15 kg hand-thrown or short-field model, and the air-phase/ground-roll split at RC scale differs entirely from the GA case the factor was fitted to (ADR 0023).

> This application targets RC/UAV aircraft of **0.5–15 kg**. A constant is not
> justified by being standard in transport-category literature.

**⚠️ Anomaly.** Single-engine piston AEO GA factor applied to RC/UAV (ADR 0023); 50 ft is also an FAR-23 obstacle height with no meaning for a hand-thrown model.

🟡 *Reported by the extraction pass, not independently verified. Do not cite as a
defect until confirmed against the code.*

**Cited in the code itself.** `# Roskam §3.4, SE-piston AEO, 50-ft obstacle`

---
*Cluster [[_index-perf-matching|perf-matching]] · generated from the 2026-08-18 extraction.*
