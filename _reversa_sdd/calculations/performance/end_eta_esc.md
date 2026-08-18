---
name: end_eta_esc
symbol: eta_esc
kind: constant
unit: -
cluster: perf-envelope
user_visible: true
source_status: NO_SOURCE_FOUND
node_class: unclassified-constant
tags:
  - cluster/perf-envelope
  - class/unclassified-constant
  - source/no-source-found
  - surface/user-visible
---

# Default ESC efficiency

**Definition.** Assumed electronic-speed-controller efficiency when no design assumption is set.

⚪ **Unclassified constant.** Not yet decided whether this is a rule of thumb, a calibration or a physical value. Classifying it is open work — it is deliberately not guessed.

**Value.** `0.94`

**Formula — as the code writes it.**

```
DEFAULT_ETA_ESC = 0.94  # Modern ESC
```

**Inputs.** — *(leaf: a constant or an external input)*

**Produced by.** `app/services/endurance_service.py:55` — `DEFAULT_ETA_ESC`

**Consumed by.**

- in this graph: `Total propulsion efficiency`  
  *(these are backlinks — open the Backlinks pane to navigate them)*
- outside it: `powertrain_sizing_service.py`

**Source.** 🔴 NO SOURCE FOUND

> No efficiency figure for RC ESCs in any consulted vault. RC-Network Wiki 'Motorsteller' describes ESC function but states no efficiency. In-code comment 'Modern ESC' is not a citation.
>
> — via `rc`
> No citable source was found. **This is recorded, not filled in.** The value is
> in the code without an attributable origin.

**Cited in the code itself.** `"Modern ESC" — NO_SOURCE_FOUND`

---
*Cluster [[_index-perf-envelope|perf-envelope]] · generated from the 2026-08-18 extraction.*
