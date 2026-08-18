---
name: bwsd-section-area-normalised
symbol: section_area_m2
kind: quantity
unit: m²
cluster: aero-strips
user_visible: false
source_status: PARTIAL
---

# Normalised section area

**Definition.** Section areas rescaled so their sum equals half the reference wing area.

**Formula — as the code writes it.**

```
section_areas *= (s_ref / 2.0) / total_area
```

**Inputs.** [[bwsd-section-area-raw|Raw trapezoidal section area]]

**Produced by.** `app/services/turbulator_optimizer_service.py:423` — `build_wing_section_data`

**Consumed by.**

- in this graph: [[cdftp-delta-cd0|Installed-turbulator 3D drag increment]] · [[tos-cd-clean-avg|Area-weighted mean clean section drag]] · [[tos-cl-avg|Area-weighted mean section CL]] · [[tos-cl-rep|Representative lift coefficient (whole scope)]] · [[tos-delta-cd0|Area-weighted 3D drag increment]] · [[tos-re-rep|Representative Reynolds number (whole scope)]]

**Source.** 🟡 PARTIAL

> AeroSandbox tutorial 06 ('symmetric=True mirrors the wing across the XZ plane; span direction is +y only, -y is implied')
>
> — via `aerosandbox-expert`

**The source states it as.**

```
For a symmetric ASB wing the defined sections cover exactly one semispan, so sum(A_i) = S_ref/2
```

**⚠️ Divergence from the source.** Correct for symmetric=True, which is the cited ASB convention. Wrong when a caller passes wing_symmetric=False: the sections then cover the FULL span, but the code still rescales them to S_ref/2 while tos-symmetry-factor drops the compensating factor of 2 — so delta_cd0 for a non-symmetric surface is half what it should be.

🟡 *Reported by the extraction pass, not independently verified.*

**⚠️ Anomaly.** The s_ref/2 renormalisation assumes the section list always covers exactly one half-span; for a non-symmetric wing (where callers pass wing_symmetric=False) the areas are halved anyway.

🟡 *Reported by the extraction pass, not independently verified. Do not cite as a
defect until confirmed against the code.*

**Cited in the code itself.** `app/services/turbulator_optimizer_service.py:421-423`

---
*Cluster [[_index-aero-strips|aero-strips]] · generated from the 2026-08-18 extraction.*
