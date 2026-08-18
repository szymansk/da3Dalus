---
name: solver-default
kind: parameter
unit: -
cluster: aero-spanwise
user_visible: true
source_status: PARTIAL
code_audit: CONFIRMED
node_class: unclassified-parameter
tags:
  - cluster/aero-spanwise
  - class/unclassified-parameter
  - source/partial
  - surface/user-visible
  - audit/confirmed
  - flag/divergence
  - solver-adjacent/vlm
---

# Strip-force solver default

**Definition.** Default solver for strip forces and spanwise loads is the in-process AeroSandbox VLM.

⚪ **Unclassified parameter.** Not yet decided whether this is a user input or an internal tuning value.

**Value.** `"vlm"`

**Formula — as the code writes it.**

```
solver: str = "vlm"
```

**Inputs.** — *(leaf: a constant or an external input)*

**Produced by.** `app/services/analysis_service.py:1838` — `analyze_airplane_strip_forces`

🟢 **Verified against the code** — an independent reviewer read this line and confirmed the formula, unit and value (2026-08-18 audit).

**Consumed by.**

- outside it: `compute_vlm_strip_forces` · `_run_avl_strip_forces`

**Source.** 🟡 PARTIAL

> AeroSandbox tutorial 06 'Vortex Lattice Method' / docs_aero_3d.md (VortexLatticeMethod returns the same key set as AeroBuildup and AVL)
>
> — via `aerosandbox-expert`

**The source states it as.**

```
VLM: inviscid vortex-lattice solution of the lifting surfaces; strip forces available per panel row
```

**⚠️ Divergence from the source.** The tool is sourced; preferring in-process VLM over AVL is a project decision (consistent with the recorded 'ASB over AVL' preference), not a literature one.

🟡 *Reported by the extraction pass, not independently verified.*

---
*Cluster [[_index-aero-spanwise|aero-spanwise]] · generated from the 2026-08-18 extraction.*
