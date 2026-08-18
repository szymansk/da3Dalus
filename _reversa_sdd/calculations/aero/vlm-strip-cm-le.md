---
name: vlm-strip-cm-le
symbol: cm_LE
kind: constant
unit: dimensionless
cluster: aero-strips
user_visible: true
source_status: NO_SOURCE_FOUND
code_audit: CONFIRMED
node_class: numerical-tolerance
tags:
  - cluster/aero-strips
  - class/numerical-tolerance
  - source/no-source-found
  - surface/user-visible
  - audit/confirmed
  - flag/divergence
  - solver-adjacent/vlm
---

# Strip leading-edge moment coefficient

**Definition.** Hardcoded zero on the VLM path.

**Numerical tolerance.** A solver or comparison epsilon, not a domain value. ADR 0023 does not apply.

**Value.** `0.0`

**Formula — as the code writes it.**

```
"cm_LE": 0.0,
```

**Inputs.** — *(leaf: a constant or an external input)*

**Produced by.** `app/services/vlm_strip_forces.py:296` — `compute_vlm_strip_forces`

🟢 **Verified against the code** — an independent reviewer read this line and confirmed the formula, unit and value (2026-08-18 audit).

**Consumed by.**

- outside it: `app/schemas/strip_forces.py:StripForceEntry.cm_le`

**Source.** 🔴 NO SOURCE FOUND

> AVL 3.40 source, Avl/src/aero.f:919-931 (CMLE(J) computed about the strip LE midpoint)
>
> — via `avl-advisor`
> No citable source was found. **This is recorded, not filled in.** The value is
> in the code without an attributable origin.

**⚠️ Divergence from the source.** Same as cm_c/4: computable from the available panel forces and moments, hardcoded to zero instead.

🟡 *Reported by the extraction pass, not independently verified.*

**Cited in the code itself.** `app/services/vlm_strip_forces.py:296`

---
*Cluster [[_index-aero-strips|aero-strips]] · generated from the 2026-08-18 extraction.*
