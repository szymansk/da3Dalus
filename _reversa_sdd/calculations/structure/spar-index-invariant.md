---
name: spar-index-invariant
symbol: spar_index
kind: constant
unit: index
cluster: structure
user_visible: true
source_status: PARTIAL
---

# Spar index assignment (hard invariant)

**Definition.** Per-segment sort_index each structural role receives: front (main) spar 0, rear 1, reinforcement 2. spare_list[0] is the main spar — the only one that receives the vase-mode print slot.

**Value.** `_FRONT_INDEX = 0; _REAR_INDEX = 1; _REINFORCEMENT_INDEX = 2`

**Formula — as the code writes it.**

```
if is_reinforcement:
    return _REINFORCEMENT_INDEX
if piece.role == SparRole.REAR:
    return _REAR_INDEX
return _FRONT_INDEX
```

**Inputs.** — *(leaf: a constant or an external input)*

**Produced by.** `app/services/spar_insert_service.py:119` — `_spar_index_for`

**Consumed by.**

- outside it: `app/services/spar_insert_service.py:213` · `app/services/spar_insert_service.py:247` · `app/schemas/spar_insert.py`

**Source.** 🟡 PARTIAL

> RC-Network Wiki, "Holm (Flugzeugkonstruktion)", https://wiki.rc-network.de/wiki/Holm — the main spar is "the principal structural element"; Scholz, Flugzeugentwurf, 07_WingDesign §7.4 / [[wing-box-spars]] — the front spar carries the primary bending moment, the rear spar carries secondary bending and torsional constraint
>
> — via `aircraft-design-scholz + rc-aircraft-designer`

**The source states it as.**

```
The front/main spar is the primary structural member and the rear spar is secondary. Both sources agree, which is what makes front=0, rear=1 the right ordering.
```

**⚠️ Divergence from the source.** The literature justifies the RANKING (main spar first). The specific integer contract and its coupling to VaseModeWingCreator's vase-mode print slot is an internal construction invariant with no external source, and correctly documented as such in the code.

🟡 *Reported by the extraction pass, not independently verified.*

**Cited in the code itself.** `HARD INVARIANT (cad_designer construction relies on it — verified against :class:`cad_designer.airplane.creator.wing.VaseModeWingCreator.VaseModeWingCreator`): ``spare_list[0]`` is the **main spar**; it is the only spar that receives the vase-mode print slot and is built first.`

---
*Cluster [[_index-structure|structure]] · generated from the 2026-08-18 extraction.*
