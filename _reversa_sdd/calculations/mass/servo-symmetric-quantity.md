---
name: servo-symmetric-quantity
symbol: n_servo
kind: constant
unit: count
cluster: mass
user_visible: true
source_status: PARTIAL
code_audit: CONFIRMED
node_class: unclassified-constant
tags:
  - cluster/mass
  - class/unclassified-constant
  - source/partial
  - surface/user-visible
  - audit/confirmed
  - flag/divergence
---

# Symmetric servo quantity

**Definition.** Quantity assigned to an auto-synced servo node: 2 when the wing section is mirrored to both half-spans, else 1.

⚪ **Unclassified constant.** Not yet decided whether this is a rule of thumb, a calibration or a physical value. Classifying it is open work — it is deliberately not guessed.

**Value.** `2 (symmetric) / 1 (asymmetric); also at line 626 for the create branch`

**Formula — as the code writes it.**

```
quantity=2 if symmetric else 1
```

**Inputs.** — *(leaf: a constant or an external input)*

**Produced by.** `app/services/component_tree_service.py:616` — `upsert_synced_servo`

🟢 **Verified against the code** — an independent reviewer read this line and confirmed the formula, unit and value (2026-08-18 audit).

**Consumed by.**

- outside it: `app/services/component_tree_service.py:438 (_weight_from_cots)`

**Source.** 🟡 PARTIAL

> Lennon, A., "Basics of R/C Model Aircraft Design", Air Age 1996, Ch. 6 ("CG Location") — the balancing-act weight breakdown treats 'control components' as one of the fixed-weight classes to be enumerated and positioned before build (Swift example: >50% of gross weight is fixed, incl. control components).
>
> — via `rc-aircraft-designer`

**⚠️ Divergence from the source.** The rule 'mirrored section ⇒ quantity 2' is not stated by any consulted source. It is a bookkeeping consequence of wing mirroring, not an aircraft-design constant. Lennon enumerates control components in the weight statement but gives no doubling rule.

🟡 *Reported by the extraction pass, not independently verified.*

---
*Cluster [[_index-mass|mass]] · generated from the 2026-08-18 extraction.*
