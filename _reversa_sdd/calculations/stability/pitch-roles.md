---
name: pitch-roles
symbol: —
kind: constant
unit: – (set of strings)
cluster: stability
user_visible: false
source_status: PARTIAL
---

# Pitch-control roles

**Definition.** Set of trailing-edge-device roles that count as pitch control for elevator authority.

**Value.** `{"elevator", "ruddervator", "elevon", "flaperon"}`

**Inputs.** — *(leaf: a constant or an external input)*

**Produced by.** `app/services/elevator_authority_service.py:99` — `_PITCH_ROLES`

**Consumed by.**

- in this graph: [[forward-cg-confidence|Forward CG confidence tier]]
- outside it: `app/services/elevator_authority_service.py:178,527,535,540`

**Source.** 🟡 PARTIAL

> The individual surface types are all recognised in the literature: elevator and all-moving stabilator (Sadraey §12.5.5 step 12, "If C_E/C_h > 0.5 → switch to all-moving tail (C_E/C_h = 1)"); ruddervator/V-tail (Sadraey §6.7 other tail geometries); elevon (Lennon Ch. 23, tailless elevon mixing). No source enumerates a canonical set of 'pitch-control roles'.
>
> — via `aircraft-design-scholz + rc-aircraft-designer`

**The source states it as.**

```
—
```

**⚠️ Divergence from the source.** The set omits 'stabilator', which Sadraey §12.5.5 step 12 treats as the standard escalation from an elevator (C_E/C_h = 1, all-moving tail) — so an all-moving-tail RC model is classified as having no pitch control at all. It includes 'flaperon', whose primary axis is roll in the app's own ROLE_COEFFICIENT_MAP. Three mutually inconsistent pitch-role sets exist in this codebase (here, retrim_service.py:31, trim_enrichment_service.py:347).

🟡 *Reported by the extraction pass, not independently verified.*

**⚠️ Anomaly.** Three different pitch-role sets exist in the codebase and none agree: this one, retrim_service.py:31 {elevator, stabilator, elevon, ruddervator}, and trim_enrichment_service.py:347 ("elevator", "stabilator", "elevon", "ruddervator"). 'stabilator' is pitch control but is absent here; 'flaperon' is present here but absent there.

🟡 *Reported by the extraction pass, not independently verified. Do not cite as a
defect until confirmed against the code.*

**Cited in the code itself.** `#: elevator → conventional H-tail
#: ruddervator → V-tail (ASB 3D, no extra cos² needed)
#: elevon → tailless / flying wing
#: flaperon → wing-only pitch+roll combined surface`

---
*Cluster [[_index-stability|stability]] · generated from the 2026-08-18 extraction.*
