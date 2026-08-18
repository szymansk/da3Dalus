---
name: volts-per-lipo-cell
symbol: _VOLTS_PER_LIPO_CELL
kind: constant
unit: V/cell
cluster: powertrain
user_visible: true
source_status: SOURCED
---

# Loaded LiPo cell voltage

**Definition.** Nominal loaded voltage of one LiPo cell, deliberately 3.7 V rather than the 4.2 V fully-charged peak.

**Value.** `3.7`

**Inputs.** — *(leaf: a constant or an external input)*

**Produced by.** `app/services/powertrain_performance.py:50` — `_VOLTS_PER_LIPO_CELL`

**Consumed by.**

- in this graph: [[battery-nominal-voltage|Nominal pack voltage]] · [[motor-continuous-electrical-power|Motor continuous electrical input power (estimated)]] · [[motor-max-electrical-power|Motor maximum electrical input power (estimated)]]
- outside it: `app/services/powertrain_performance.py:159` · `app/services/powertrain_performance.py:171` · `app/services/powertrain_performance.py:184`

**Source.** 🟢 SOURCED

> RC-Network Wiki, 'Nennspannung' (wiki.rc-network.de/wiki/Nennspannung), rated-voltage table: LiIo/LiPo = 3.7 V per cell; example '3-cell LiPo = 3 x 3.7 = 11.1 V'. The wiki defines rated voltage explicitly as 'the nominal voltage measured during discharge under typical operating current' — i.e. a loaded value, not the 4.2 V charged peak.
>
> — via `rc-aircraft-designer`

**The source states it as.**

```
V_pack = n_cells x 3.7 V
```

**Cited in the code itself.** `# loaded nominal (NOT 4.2 V peak)  /  module docstring: "Uses 3.7 V/cell (loaded, not 4.2 V peak) to avoid 13% inflation." (UAT note, gh-615 comment #3)`

---
*Cluster [[_index-powertrain|powertrain]] · generated from the 2026-08-18 extraction.*
