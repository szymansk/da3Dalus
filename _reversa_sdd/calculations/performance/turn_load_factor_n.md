---
name: turn_load_factor_n
symbol: n
kind: quantity
unit: g
cluster: perf-oppoints
user_visible: true
source_status: SOURCED
node_class: derived
tags:
  - cluster/perf-oppoints
  - class/derived
  - source/sourced
  - surface/user-visible
  - flag/divergence
---

# Turn load factor

**Definition.** Load factor of a steady coordinated level turn, read from turn_kinematics.

**Derived quantity.** Computed from the inputs below.

**Formula — as the code writes it.**

```
n = turn_kinematics(bank_deg=float(bank_deg), velocity=float(velocity)).n
```

**Inputs.** — *(leaf: a constant or an external input)*

**Produced by.** `app/services/operating_point_generator_service.py:169` — `_apply_turn_feasibility`

**Consumed by.**

- in this graph: `Stall speed in the turn`  
  *(these are backlinks — open the Backlinks pane to navigate them)*
- outside it: `app/services/operating_point_generator_service.py:170 (v_stall_turn)` · `app/services/operating_point_generator_service.py:173 (warning text)`

**Source.** 🟢 SOURCED

> Lennon, Basics of R/C Model Aircraft Design (1996), Ch. 21 — 'Centrifugal Force and Load Factor in Maneuvers': level turn with CF = 1G and weight = 1G gives wing load sqrt(1²+1²) = 1.414 G at 45° bank
>
> — via `rc-aircraft-designer`

**The source states it as.**

```
n = 1/cos(phi) — Lennon's 45° case is exactly 1/cos(45°) = 1.414
```

**⚠️ Divergence from the source.** Code form matches. Cited from the RC-scale source; the Scholz/Sadraey vault has no turn-performance page at all, so the lead authority is silent here.

🟡 *Reported by the extraction pass, not independently verified.*

**Cited in the code itself.** `A steady level turn at bank angle ``bank_deg`` requires a load factor n = 1/cos(phi).`

---
*Cluster [[_index-perf-oppoints|perf-oppoints]] · generated from the 2026-08-18 extraction.*
