---
name: tos-symmetry-factor
symbol: symmetry_factor
kind: constant
unit: dimensionless
cluster: aero-strips
user_visible: false
source_status: SOURCED
---

# Symmetric-wing doubling factor

**Definition.** Factor of 2 applied to the half-span area-weighted sum for symmetric wings.

**Value.** `2.0`

**Formula — as the code writes it.**

```
symmetry_factor = 2.0 if wing_symmetric else 1.0
```

**Inputs.** — *(leaf: a constant or an external input)*

**Produced by.** `app/services/turbulator_optimizer_service.py:330` — `compute_turbulator_delta_cd0`

**Consumed by.**

- in this graph: [[cdftp-delta-cd0|Installed-turbulator 3D drag increment]] · [[tos-delta-cd0|Area-weighted 3D drag increment]]

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
