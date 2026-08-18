---
name: bungee_energy_stored
symbol: E_stored
kind: quantity
unit: J
cluster: perf-matching
user_visible: false
source_status: PARTIAL
node_class: derived
tags:
  - cluster/perf-matching
  - class/derived
  - source/partial
  - flag/divergence
---

# Bungee stored energy

**Definition.** Elastic energy stored in the bungee, using an average-force approximation.

**Derived quantity.** Computed from the inputs below.

**Formula — as the code writes it.**

```
e_stored = 0.5 * bungee_force_N * stretch_m
```

**Inputs.** — *(leaf: a constant or an external input)*

**Produced by.** `app/services/field_length_service.py:176` — `compute_bungee_release_speed`

**Consumed by.**

- in this graph: `Bungee release speed`  
  *(these are backlinks — open the Backlinks pane to navigate them)*
- outside it: `v_release_bungee:177`

**Source.** 🟡 PARTIAL

> Elementary linear-elastic mechanics: for a force rising linearly from 0 to F over extension x, W = integral F dx = 0.5*F*x. No aircraft-design source - Scholz and Sadraey have no bungee/catapult launch model (the vault's only bungee references are homebuilt shock absorbers, sadraey-shock-absorber / sadraey-landing-gear-height).
>
> — via `aircraft-design-scholz (confirmed gap: no launch-assist coverage)`

**The source states it as.**

```
E = 0.5*F*x for a linear spring
```

**⚠️ Divergence from the source.** The code's comment calls this a 'uniform force approximation'; it is actually the exact result for a LINEAR spring and an over-estimate for a constant-force (rubber-plateau) bungee, where E = F*x. Real surgical-tubing bungees are closer to the latter, so this under-estimates stored energy.

🟡 *Reported by the extraction pass, not independently verified.*

**Cited in the code itself.** `"Assumes linear elastic bungee (uniform force approximation): E_stored = 0.5 · F · x  (average force × distance)"`

---
*Cluster [[_index-perf-matching|perf-matching]] · generated from the 2026-08-18 extraction.*
