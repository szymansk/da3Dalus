---
name: v_release_bungee
symbol: v_release
kind: quantity
unit: m/s
cluster: perf-matching
user_visible: true
source_status: PARTIAL
code_audit: CONFIRMED
node_class: derived
tags:
  - cluster/perf-matching
  - class/derived
  - source/partial
  - surface/user-visible
  - audit/confirmed
  - flag/anomaly
  - flag/divergence
---

# Bungee release speed

**Definition.** Speed at bungee/catapult release from the stored elastic energy.

**Derived quantity.** Computed from the inputs below.

**Formula — as the code writes it.**

```
return math.sqrt(2.0 * e_stored / mass_kg)
```

**Inputs.**

- [[bungee_energy_stored|Bungee stored energy]]

**Produced by.** `app/services/field_length_service.py:177` — `compute_bungee_release_speed`

🟢 **Verified against the code** — an independent reviewer read this line and confirmed the formula, unit and value (2026-08-18 audit).

**Consumed by.**

- in this graph: `Bungee partial ground roll`  
  *(these are backlinks — open the Backlinks pane to navigate them)*
- outside it: `compute_field_lengths:402,410,415`

**Source.** 🟡 PARTIAL

> Energy conservation 0.5*m*v^2 = E. No aircraft-design source for launch-assist release speed in Scholz or Sadraey.
>
> — via `aircraft-design-scholz (confirmed gap)`

**The source states it as.**

```
v = sqrt(2E/m)
```

**⚠️ Divergence from the source.** Assumes 100% energy transfer: no launch losses, no aerodynamic drag over the run-out, no rail/hook friction, no bungee mass. Every one of these reduces v_release, so the model is optimistic and unbounded in its optimism.

🟡 *Reported by the extraction pass, not independently verified.*

**⚠️ Anomaly.** No launch losses, no aircraft drag and no rail friction; also ignores that a 100% energy transfer is assumed.

🟡 *Reported by the extraction pass, not independently verified. Do not cite as a
defect until confirmed against the code.*

**Cited in the code itself.** `"v_release = sqrt(E_stored / (0.5 · m)) = sqrt(F · x / m)"`

---
*Cluster [[_index-perf-matching|perf-matching]] · generated from the 2026-08-18 extraction.*
