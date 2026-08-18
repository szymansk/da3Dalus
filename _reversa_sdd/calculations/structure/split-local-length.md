---
name: split-local-length
kind: quantity
unit: mm
cluster: structure
user_visible: true
source_status: PARTIAL
code_audit: CONFIRMED
node_class: derived
tags:
  - cluster/structure
  - class/derived
  - source/partial
  - surface/user-visible
  - audit/confirmed
  - flag/divergence
---

# Segment-local split position

**Definition.** A telescoping joint position expressed as a length from the host segment's root, used to split the host segment so each spar diameter gets its own sub-segment.

**Derived quantity.** Computed from the inputs below.

**Formula — as the code writes it.**

```
local = float(_piece_locate_y(piece)) - host_root_y
# Keep strictly inside the host segment so the split helper accepts it.
if _FRACTION_TOL * host_len < local < host_len - _FRACTION_TOL * host_len:
    split_lengths.append(local)
```

**Inputs.**

- [[host-root-y|Host segment root spanwise position]]
- [[fraction-tol|Split-position boundary tolerance]]  — *ε tolerance*
- [[piece-y-start|Spar piece root spanwise position]]

**Produced by.** `app/services/spar_insert_service.py:308` — `_front_split_plan`

🟢 **Verified against the code** — an independent reviewer read this line and confirmed the formula, unit and value (2026-08-18 audit).

**Consumed by.**

- in this graph: `Post-split sub-segment lengths`  
  *(these are backlinks — open the Backlinks pane to navigate them)*
- outside it: `app/services/spar_insert_service.py:399` · `app/services/spar_insert_service.py:481`

**Source.** 🟡 PARTIAL

> RC-Network Wiki, "Steckung (Flugzeugkonstruktion)", https://wiki.rc-network.de/wiki/Steckung — telescoping/plug spar joints are standard in model aircraft, used to "enable transport disassembly" and to transfer bending between spars
>
> — via `rc-aircraft-designer`

**The source states it as.**

```
The source establishes that a spar joint is a real, locatable structural feature; it gives no positioning rule.
```

**⚠️ Divergence from the source.** The joint POSITION here is not chosen by any structural criterion — it falls wherever the solver's OD-driven split landed, which in turn depends on the sampling resolution n_span. The source treats the joint location (especially the wing-fuselage joint) as a deliberate structural decision.

🟡 *Reported by the extraction pass, not independently verified.*

**Cited in the code itself.** `Each subsequent piece's root y is a joint — converted to a segment-local length (joint_y - host_root_y), clamped strictly inside the segment.`

---
*Cluster [[_index-structure|structure]] · generated from the 2026-08-18 extraction.*
