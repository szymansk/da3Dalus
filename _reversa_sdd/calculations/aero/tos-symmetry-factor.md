---
name: tos-symmetry-factor
symbol: symmetry_factor
kind: constant
unit: dimensionless
cluster: aero-strips
user_visible: false
source_status: SOURCED
code_audit: CONFIRMED
node_class: unclassified-constant
tags:
  - cluster/aero-strips
  - class/unclassified-constant
  - source/sourced
  - audit/confirmed
  - flag/divergence
---

# Symmetric-wing doubling factor

**Definition.** Factor of 2 applied to the half-span area-weighted sum for symmetric wings.

⚪ **Unclassified constant.** Not yet decided whether this is a rule of thumb, a calibration or a physical value. Classifying it is open work — it is deliberately not guessed.

**Value.** `2.0`

**Formula — as the code writes it.**

```
symmetry_factor = 2.0 if wing_symmetric else 1.0
```

**Inputs.** — *(leaf: a constant or an external input)*

**Produced by.** `app/services/turbulator_optimizer_service.py:330` — `compute_turbulator_delta_cd0`

🟢 **Verified against the code** — an independent reviewer read this line and confirmed the formula, unit and value (2026-08-18 audit).

**Consumed by.**

- in this graph: `Installed-turbulator 3D drag increment` · `Area-weighted 3D drag increment`  
  *(these are backlinks — open the Backlinks pane to navigate them)*

**Source.** 🟢 SOURCED

> AVL 3.40 User Primer, avl_doc.txt L422-450 (YDUPLICATE / iYsym: mirror image about the XZ plane); AeroSandbox tutorial 06 ('symmetric=True mirrors the wing across the XZ plane; span direction is +y only, -y is implied')
>
> — via `avl-advisor, aerosandbox-expert`

**The source states it as.**

```
A symmetric wing's total contribution = 2 x the half-wing contribution
```

**⚠️ Divergence from the source.** Geometric identity, correctly applied. It is only valid together with bwsd-section-area-normalised's assumption that the section list covers exactly one semispan — see that entry.

🟡 *Reported by the extraction pass, not independently verified.*

**Cited in the code itself.** `app/services/turbulator_optimizer_service.py:330`

---
*Cluster [[_index-aero-strips|aero-strips]] · generated from the 2026-08-18 extraction.*
