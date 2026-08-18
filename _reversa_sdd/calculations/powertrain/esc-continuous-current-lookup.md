---
name: esc-continuous-current-lookup
symbol: cont_a
kind: quantity
unit: A
cluster: powertrain
user_visible: true
source_status: SOURCED
---

# ESC continuous current rating

**Definition.** Continuous current rating read from an ESC catalog entry, with a legacy key fallback and a zero default.

**Formula — as the code writes it.**

```
cont_a = esc_specs.get("continuous_current_a", esc_specs.get("max_continuous_a", 0)) or 0
```

**Inputs.** — *(leaf: a constant or an external input)*

**Produced by.** `app/services/powertrain_sizing_service.py:110` — `_find_matching_esc`

**Consumed by.**

- outside it: `app/services/powertrain_sizing_service.py:111`

**Source.** 🟢 SOURCED

> RC-Network Wiki, 'Motorsteller' (motor controller / ESC): 'Current Rating (Amperage) - The most important specification: maximum continuous current capacity determines controller size and weight. Reputable manufacturers rate continuous capacity at standard battery capacity ... Cheap imports sometimes advertise peak (pulse) capacity, which is substantially higher than continuous rating.'
>
> — via `rc-aircraft-designer`

**The source states it as.**

```
ESC sizing governed by maximum CONTINUOUS current capacity
```

**⚠️ Divergence from the source.** The code's preference for continuous_current_a matches the source. Its zero-default for entries with no current data does not: the source treats the continuous rating as the defining specification, so an ESC without one is unusable data rather than a 0 A device.

🟡 *Reported by the extraction pass, not independently verified.*

**⚠️ Anomaly.** An ESC with no current data silently becomes 0 A and is simply skipped, with no warning that catalog entries were unusable. Also the matcher returns the FIRST ESC in unordered query order that clears the bar (line 112), so the recommended ESC is nondeterministic across DB orderings.

🟡 *Reported by the extraction pass, not independently verified. Do not cite as a
defect until confirmed against the code.*

**Cited in the code itself.** `# gh-986 catalog stores continuous current under continuous_current_a; fall back to legacy max_continuous_a for older entries (gh-992).`

---
*Cluster [[_index-powertrain|powertrain]] · generated from the 2026-08-18 extraction.*
