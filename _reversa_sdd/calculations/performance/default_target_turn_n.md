---
name: default_target_turn_n
kind: constant
unit: dimensionless
cluster: perf-oppoints
user_visible: false
source_status: PARTIAL
code_audit: WRONG_UNIT
node_class: unclassified-constant
tags:
  - cluster/perf-oppoints
  - class/unclassified-constant
  - source/partial
  - audit/wrong-unit
  - flag/anomaly
  - flag/divergence
---

# Default target turn load factor

**Definition.** Sustained turn load-factor goal in the default profile.

⚪ **Unclassified constant.** Not yet decided whether this is a rule of thumb, a calibration or a physical value. Classifying it is open work — it is deliberately not guessed.

**Value.** `2.0`

**Formula — as the code writes it.**

```
"target_turn_n": 2.0
```

**Inputs.** — *(leaf: a constant or an external input)*

**Produced by.** `app/services/operating_point_generator_service.py:209` — `_default_profile`

🟠 **Corrected by the audit** — the extraction claimed `WRONG_UNIT`. Original unit was `g`. Target load factor is dimensionless, not g

**Consumed by.**

- 🔴 **nothing found.** A computed value nothing reads is a finding (ADR 0021).

**Source.** 🟡 PARTIAL

> Sadraey §12.3.3, Table 12.5 — Class I (small light aircraft), Phase A: 60° bank is the roll-control benchmark; 1/cos(60°) = 2.0
>
> — via `aircraft-design-scholz`

**⚠️ Divergence from the source.** n = 2 is the load factor of the standard 60° steep turn, which is a real benchmark bank angle in the source. But the parameter has no consumer: _build_target_definitions hardcodes banks (20, 40, 60) and never reads target_turn_n.

🟡 *Reported by the extraction pass, not independently verified.*

**⚠️ Anomaly.** No consumer: the schema (app/schemas/flight_profile.py:128) says it "drives turn-performance operating points", but _build_target_definitions hardcodes bank angles (20, 40, 60) and ignores target_turn_n entirely.

🟡 *Reported by the extraction pass, not independently verified. Do not cite as a
defect until confirmed against the code.*

---
*Cluster [[_index-perf-oppoints|perf-oppoints]] · generated from the 2026-08-18 extraction.*
