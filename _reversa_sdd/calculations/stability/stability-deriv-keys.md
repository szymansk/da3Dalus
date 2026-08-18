---
name: stability-deriv-keys
symbol: —
kind: constant
unit: – (set of strings)
cluster: stability
user_visible: true
source_status: SOURCED
node_class: unclassified-constant
tags:
  - cluster/stability
  - class/unclassified-constant
  - source/sourced
  - surface/user-visible
  - flag/anomaly
  - flag/divergence
  - solver-adjacent/aerobuildup
---

# Reported stability derivative whitelist

**Definition.** Keys extracted from the AeroBuildup result and reported as stability derivatives; also the input set for enrichment's stability classification.

⚪ **Unclassified constant.** Not yet decided whether this is a rule of thumb, a calibration or a physical value. Classifying it is open work — it is deliberately not guessed.

**Value.** `{"CL_a", "CL_b", "CY_a", "CY_b", "Cm_a", "Cn_b", "Cl_b", "Clb", "Cnr", "Clr", "Cnb"}`

**Inputs.** — *(leaf: a constant or an external input)*

**Produced by.** `app/services/aerobuildup_trim_service.py:23` — `_STABILITY_DERIV_KEYS`

**Consumed by.**

- outside it: `app/services/aerobuildup_trim_service.py:274,316,336` · `app/services/trim_enrichment_service.py:131-138 (classify_stability reads Cm_a, Cn_b/Cnb, Cl_b/Clb, CL_a)`

**Source.** 🟢 SOURCED

> Sadraey (Wiley 2013) §12.5.2 (control-derivatives fundamentals) lists the static stability derivatives C_mα, C_nβ, C_yβ, C_lβ as the bare-airframe set; §6.2.2 and §12.6.2 give their stability signs; §11.6.2 Eq. 11.19 introduces the damping derivative C_mq and §12.3.3 the lateral-directional rate derivatives (C_nr, C_lr) used in the Dutch-roll and spiral criteria (spiral instability if \|C_lβ·C_nr\| < \|C_lr·C_nβ\|). Key naming: AeroSandbox docs (stability-derivatives-from-asb-solvers) use the underscore form CL_a = dCL/dα; AVL uses the legacy compact form.
>
> — via `aircraft-design-scholz + aerosandbox-expert`

**The source states it as.**

```
Static: C_Lα, C_mα, C_nβ, C_lβ, C_Yβ ; rate: C_nr, C_lr ; damping: C_mq
```

**⚠️ Divergence from the source.** The set omits C_mq entirely, which Sadraey §11.6.2 Eq. 11.19 calls "the dominant factor" in conventional dynamic longitudinal stability, and it carries both notations for the same derivatives (Cl_b and Clb, Cn_b and Cnb). If a result contained both, classify_stability's get("Cl_b", get("Clb", 0.0)) picks the underscore one silently while the response reports both under different names.

🟡 *Reported by the extraction pass, not independently verified.*

**⚠️ Anomaly.** Carries both notations for the same derivatives (Cl_b and Clb, Cn_b and Cnb). If a result ever contained both, classify_stability's `get("Cl_b", get("Clb", 0.0))` picks the underscore one silently, and the response reports both under different names.

🟡 *Reported by the extraction pass, not independently verified. Do not cite as a
defect until confirmed against the code.*

**Cited in the code itself.** `# Aerosandbox uses underscore notation (CL_a = dCL/dalpha);
# legacy AVL-style keys (Clb, Cnr) may also appear in output.`

---
*Cluster [[_index-stability|stability]] · generated from the 2026-08-18 extraction.*
