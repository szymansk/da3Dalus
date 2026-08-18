---
name: end_fallback_e
symbol: e_fallback
kind: constant
unit: -
cluster: perf-envelope
user_visible: true
source_status: PARTIAL
node_class: unclassified-constant
tags:
  - cluster/perf-envelope
  - class/unclassified-constant
  - source/partial
  - surface/user-visible
  - flag/anomaly
  - flag/scale
---

# Oswald fallback

**Definition.** Oswald efficiency substituted when the polar fit produced none.

⚪ **Unclassified constant.** Not yet decided whether this is a rule of thumb, a calibration or a physical value. Classifying it is open work — it is deliberately not guessed.

**Value.** `0.8`

**Formula — as the code writes it.**

```
FALLBACK_E_OSWALD = 0.8
```

**Inputs.** — *(leaf: a constant or an external input)*

**Produced by.** `app/services/endurance_service.py:61` — `FALLBACK_E_OSWALD`

**Consumed by.**

- in this graph: `Resolved Oswald efficiency`  
  *(these are backlinks — open the Backlinks pane to navigate them)*

**Source.** 🟡 PARTIAL

> Within published bands: Anderson, Fundamentals of Aerodynamics 6e §6.7.2 (airplane drag polar / Oswald factor); Scholz PreSTo drag estimation gives e ~ 0.80-0.95; Scholz aspect-ratio notes e ~ 0.7-0.85.
>
> — via `aero, scholz`

**The source states it as.**

```
e = 0.8
```

**⚠️ Scale (ADR 0023).** All bands are transport/GA. No RC-scale validation — at RC Reynolds numbers and with typical RC planform/fuselage interference, e is generally lower. ADR 0020: substituted silently. Also duplicated as _DEFAULT_E_OSWALD in powertrain_sizing_service.py:46 (ADR 0022).

> This application targets RC/UAV aircraft of **0.5–15 kg**. A constant is not
> justified by being standard in transport-category literature.

**⚠️ Anomaly.** Same 0.8 also hardcoded as _DEFAULT_E_OSWALD in powertrain_sizing_service.py:46 — two producers of the same fallback.

🟡 *Reported by the extraction pass, not independently verified. Do not cite as a
defect until confirmed against the code.*

---
*Cluster [[_index-perf-envelope|perf-envelope]] · generated from the 2026-08-18 extraction.*
