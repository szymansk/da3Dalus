---
name: hand_throw_warn
symbol: k_throw_warn
kind: constant
unit: dimensionless
cluster: perf-matching
user_visible: true
source_status: NO_SOURCE_FOUND
node_class: unclassified-constant
tags:
  - cluster/perf-matching
  - class/unclassified-constant
  - source/no-source-found
  - surface/user-visible
  - flag/divergence
---

# Hand-launch climb-out margin threshold

**Definition.** Throw-speed multiple of V_S below which a climb-out-margin warning is emitted.

⚪ **Unclassified constant.** Not yet decided whether this is a rule of thumb, a calibration or a physical value. Classifying it is open work — it is deliberately not guessed.

**Value.** `1.20`

**Formula — as the code writes it.**

```
_HAND_THROW_WARN: float = 1.20
```

**Inputs.** — *(leaf: a constant or an external input)*

**Produced by.** `app/services/field_length_service.py:109` — `_HAND_THROW_WARN`

**Consumed by.**

- in this graph: `Field-length warnings`  
  *(these are backlinks — open the Backlinks pane to navigate them)*
- outside it: `compute_field_lengths:391,393 (warnings list)`

**Source.** 🔴 NO SOURCE FOUND

> No source for a hand-launch climb-out margin in Scholz or Sadraey.
>
> — via `aircraft-design-scholz (confirmed gap)`
> No citable source was found. **This is recorded, not filled in.** The value is
> in the code without an attributable origin.

**⚠️ Divergence from the source.** 1.20 coincides numerically with the FAR 23.51 climb-out speed (>= 1.20*V_S1) that also underlies _V_LOF_FACTOR, but that regulation governs a runway takeoff over a 50-ft obstacle, not a hand throw. The coincidence must not be turned into a citation.

🟡 *Reported by the extraction pass, not independently verified.*

**Cited in the code itself.** `# climb-out margin warning (< 1.20·V_S)`

---
*Cluster [[_index-perf-matching|perf-matching]] · generated from the 2026-08-18 extraction.*
