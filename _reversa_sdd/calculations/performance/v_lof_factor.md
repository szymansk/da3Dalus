---
name: v_lof_factor
symbol: k_LOF
kind: constant
unit: dimensionless
cluster: perf-matching
user_visible: true
source_status: SOURCED
code_audit: CONFIRMED
node_class: unclassified-constant
tags:
  - cluster/perf-matching
  - class/unclassified-constant
  - source/sourced
  - surface/user-visible
  - audit/confirmed
  - flag/scale
---

# Lift-off speed factor

**Definition.** Ratio of lift-off speed to stall speed.

⚪ **Unclassified constant.** Not yet decided whether this is a rule of thumb, a calibration or a physical value. Classifying it is open work — it is deliberately not guessed.

**Value.** `1.2`

**Formula — as the code writes it.**

```
_V_LOF_FACTOR: float = 1.2
```

**Inputs.** — *(leaf: a constant or an external input)*

**Produced by.** `app/services/field_length_service.py:104` — `_V_LOF_FACTOR`

🟢 **Verified against the code** — an independent reviewer read this line and confirmed the formula, unit and value (2026-08-18 audit).

**Consumed by.**

- in this graph: `Lift-off speed`  
  *(these are backlinks — open the Backlinks pane to navigate them)*
- outside it: `_v_lof:132`

**Source.** 🟢 SOURCED

> FAR 23.51 (via Scholz 05_PreliminarySizing §5.2): single-engine, speed at 50 ft >= 1.20*V_S1; multi-engine, higher of 1.10*V_MC or 1.20*V_S1. Sadraey 2013 Eq. 4.72 §4.3.4: V_TO = 1.1*V_s to 1.3*V_s. Scholz's simplified ground roll assumes V_LOF = 1.2*V_S,TO.
>
> — via `aircraft-design-scholz`

**The source states it as.**

```
V_LOF = 1.2 * V_S,TO
```

**⚠️ Scale (ADR 0023).** A certification speed for manned GA aircraft. Conservative rather than dangerous at model scale, but not derived from any 0.5-15 kg evidence.

> This application targets RC/UAV aircraft of **0.5–15 kg**. A constant is not
> justified by being standard in transport-category literature.

**Cited in the code itself.** `# V_LOF = 1.2 · V_S  ("V factors (Roskam standard)")`

---
*Cluster [[_index-perf-matching|perf-matching]] · generated from the 2026-08-18 extraction.*
