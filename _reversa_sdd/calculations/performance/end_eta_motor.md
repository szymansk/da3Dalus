---
name: end_eta_motor
symbol: eta_motor
kind: constant
unit: -
cluster: perf-envelope
user_visible: true
source_status: PARTIAL
---

# Default motor efficiency

**Definition.** Assumed brushless-outrunner efficiency when no design assumption is set.

**Value.** `0.85`

**Formula — as the code writes it.**

```
DEFAULT_ETA_MOTOR = 0.85  # Brushless outrunner
```

**Inputs.** — *(leaf: a constant or an external input)*

**Produced by.** `app/services/endurance_service.py:54` — `DEFAULT_ETA_MOTOR`

**Consumed by.**

- in this graph: [[end_eta_total|Total propulsion efficiency]]
- outside it: `powertrain_sizing_service.py`

**Source.** 🟡 PARTIAL

> Roxxy Motoren-Fibel Ch. 2: typical hobby BLDC peak efficiency 75-85%; pp. 21-22 give eta_mot ~ 0.80-0.85; pole/slot design section cites 80-85% across the throttle range.
>
> — via `rc`

**The source states it as.**

```
eta_motor = 0.85
```

**⚠️ Scale (ADR 0023).** 0.85 is the TOP of every band found, and those bands describe PEAK efficiency at the motor's best operating point, not a cruise average. Using peak-as-constant biases P_req low and endurance high. In-code comment 'Brushless outrunner' is a category label, not a source.

> This application targets RC/UAV aircraft of **0.5–15 kg**. A constant is not
> justified by being standard in transport-category literature.

**Cited in the code itself.** `"Brushless outrunner" — NO_SOURCE_FOUND`

---
*Cluster [[_index-perf-envelope|perf-envelope]] · generated from the 2026-08-18 extraction.*
