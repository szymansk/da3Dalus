---
name: is-tailless-flag
symbol: —
kind: quantity
unit: – (bool)
cluster: stability
user_visible: false
source_status: SOURCED
code_audit: CONFIRMED
node_class: derived
tags:
  - cluster/stability
  - class/derived
  - source/sourced
  - audit/confirmed
  - flag/anomaly
  - flag/divergence
---

# Tailless configuration flag

**Definition.** True when the aircraft has no horizontal tail and is not a canard; gates both tail-volume sizing and SM apply operations.

**Derived quantity.** Computed from the inputs below.

**Formula — as the code writes it.**

```
is_tailless = htail is None and not is_v_tail and not is_canard
# htail / is_v_tail / is_canard are read from the wings' surface_type (gh-1187)
```

**Inputs.** — *(leaf: a constant or an external input)*

**Produced by.** `app/services/tail_sizing_service.py:395` — `build_tail_sizing_context_from_aeroplane`

🟢 **Verified against the code** — an independent reviewer read this line and confirmed the formula, unit and value (2026-08-18 audit).

**Consumed by.**

- outside it: `app/services/tail_sizing_service.py:160,472` · `app/services/sm_sizing_service.py:204,329 (reads ctx['is_tailless'])`

**Source.** 🟢 SOURCED

> Lennon, "Basics of R/C Model Aircraft Design" (1996) Ch. 23: a tailless aircraft is one where "the wing's aerodynamic center (AC) and the neutral point (NP) coincide — there is no horizontal tail to push the NP aft of the AC." Sadraey §6.7.1 treats the presence/absence of a horizontal surface as the configuration discriminator for tail sizing.
>
> — via `rc-aircraft-designer + aircraft-design-scholz`

**The source states it as.**

```
Tailless ⇔ no horizontal surface aft of the wing contributing to the neutral point (Lennon Ch. 23)
```

**Updated by gh-1187.** The flag no longer matches wing NAMES. `htail` is the wing with
`surface_type == horizontal_tail`, `is_v_tail` is any `v_tail` wing and `is_canard` any
`canard` wing, so a correctly modelled tail named 'Stabilizer' is a tail, and a V-tail or a
canard is not misread as tailless. The earlier name-substring detection (and its stale
wing-count comment) is deleted (ADR 0021).

---
*Cluster [[_index-stability|stability]] · generated from the 2026-08-18 extraction.*
