---
name: end_battery_component_mass
symbol: m_bat
kind: parameter
unit: kg
cluster: perf-envelope
user_visible: true
source_status: SOURCED
code_audit: CONFIRMED
node_class: unclassified-parameter
tags:
  - cluster/perf-envelope
  - class/unclassified-parameter
  - source/sourced
  - surface/user-visible
  - audit/confirmed
  - flag/anomaly
  - flag/divergence
---

# Battery component mass

**Definition.** Mass of the first weight item with category 'battery'.

⚪ **Unclassified parameter.** Not yet decided whether this is a user input or an internal tuning value.

**Formula — as the code writes it.**

```
battery_mass_kg = battery_item.mass_kg if battery_item else None
```

**Inputs.** — *(leaf: a constant or an external input)*

**Produced by.** `app/services/endurance_service.py:507` — `compute_endurance_for_aeroplane`

🟢 **Verified against the code** — an independent reviewer read this line and confirmed the formula, unit and value (2026-08-18 audit).

**Consumed by.**

- in this graph: `Battery-mass deviation`  
  *(these are backlinks — open the Backlinks pane to navigate them)*

**Source.** 🟢 SOURCED

> User-supplied component mass — provenance is the user's.
>
> — via `rc`

**⚠️ Divergence from the source.** Only the FIRST weight item with category 'battery' is read, so a multi-pack aircraft cross-checks against one pack and will reliably trip the 30% deviation warning. Docstring claims 'm_TO always uses the user-component mass', but m_TO is the independent `mass` design assumption (end:510) — battery component mass never enters the total.

🟡 *Reported by the extraction pass, not independently verified.*

**⚠️ Anomaly.** Only the *first* battery weight item is read; a multi-pack aircraft silently cross-checks against one pack. Docstring claims 'm_TO always uses the user-component mass' but m_TO is actually the independent `mass` design assumption (line 510) — battery component mass never enters the total.

🟡 *Reported by the extraction pass, not independently verified. Do not cite as a
defect until confirmed against the code.*

---
*Cluster [[_index-perf-envelope|perf-envelope]] · generated from the 2026-08-18 extraction.*
