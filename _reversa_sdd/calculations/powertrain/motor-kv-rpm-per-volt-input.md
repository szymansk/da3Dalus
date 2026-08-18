---
name: motor-kv-rpm-per-volt-input
symbol: kv_rpm_per_volt
kind: parameter
unit: rpm/V
cluster: powertrain
user_visible: true
source_status: SOURCED
node_class: unclassified-parameter
tags:
  - cluster/powertrain
  - class/unclassified-parameter
  - source/sourced
  - surface/user-visible
---

# Raw motor KV

**Definition.** Motor speed constant before any gearbox, read from the brushless_motor catalog specs.

⚪ **Unclassified parameter.** Not yet decided whether this is a user input or an internal tuning value.

**Inputs.** — *(leaf: a constant or an external input)*

**Produced by.** `app/services/powertrain_performance.py:90` — `MotorSpec.kv_rpm_per_volt`

**Consumed by.**

- in this graph: `Output-shaft KV`  
  *(these are backlinks — open the Backlinks pane to navigate them)*
- outside it: `app/services/powertrain_performance.py:140` · `app/api/v2/endpoints/aeroplane/powertrain_performance.py:94`

**Source.** 🟢 SOURCED

> Roxxy Motoren-Fibel, Ch. 1, pp. 15-16: 'KV (also written as RPM/V) represents the no-load RPM produced per applied volt. It is inversely related to the number of turns in the motor's stator coils ... for a fixed motor size, the product of turn count and KV-rating remains approximately constant.' Also Drela §1.1.3 (Kv definition via back-EMF).
>
> — via `rc-aircraft-designer`

**The source states it as.**

```
KV [RPM/V] = no-load RPM per applied volt
```

**Cited in the code itself.** `class docstring: "The raw kv_rpm_per_volt must never be used directly for RPM/prop matching when gear_ratio > 1 (D-Drive geared motors)."`

---
*Cluster [[_index-powertrain|powertrain]] · generated from the 2026-08-18 extraction.*
