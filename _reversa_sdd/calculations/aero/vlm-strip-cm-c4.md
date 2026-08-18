---
name: vlm-strip-cm-c4
symbol: cm_c/4
kind: constant
unit: dimensionless
cluster: aero-strips
user_visible: true
source_status: NO_SOURCE_FOUND
node_class: numerical-tolerance
tags:
  - cluster/aero-strips
  - class/numerical-tolerance
  - source/no-source-found
  - surface/user-visible
  - flag/divergence
---

# Strip quarter-chord moment coefficient

**Definition.** Hardcoded zero because chordwise pressure is not resolved on the VLM path.

**Numerical tolerance.** A solver or comparison epsilon, not a domain value. ADR 0023 does not apply.

**Value.** `0.0`

**Formula — as the code writes it.**

```
"cm_c/4": 0.0,
```

**Inputs.** — *(leaf: a constant or an external input)*

**Produced by.** `app/services/vlm_strip_forces.py:295` — `compute_vlm_strip_forces`

**Consumed by.**

- outside it: `app/schemas/strip_forces.py:StripForceEntry.cm_c4`

**Source.** 🔴 NO SOURCE FOUND

> AVL 3.40 source, Avl/src/aero.f:874 (CMC4(J) = ENSZ*CMY - ENSY*CMZ, computed from the same panel forces)
>
> — via `avl-advisor`
> No citable source was found. **This is recorded, not filled in.** The value is
> in the code without an attributable origin.

**⚠️ Divergence from the source.** Not a physical result. A vortex-lattice method that resolves camber DOES produce a non-zero strip cm_c/4 — AVL computes it from exactly the panel forces this code already has in hand. The 0.0 is a placeholder presented as a computed field.

🟡 *Reported by the extraction pass, not independently verified.*

**Cited in the code itself.** `app/services/vlm_strip_forces.py:295`

---
*Cluster [[_index-aero-strips|aero-strips]] · generated from the 2026-08-18 extraction.*
