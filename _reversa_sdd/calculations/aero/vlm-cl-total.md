---
name: vlm-cl-total
symbol: CL
kind: quantity
unit: dimensionless
cluster: aero-strips
user_visible: false
source_status: SOURCED
code_audit: CONFIRMED
node_class: derived
tags:
  - cluster/aero-strips
  - class/derived
  - source/sourced
  - audit/confirmed
  - flag/anomaly
  - flag/divergence
  - solver-adjacent/vlm
---

# Whole-airplane lift coefficient (VLM run)

**Definition.** Total CL taken directly from the VLM run dict.

**Derived quantity.** Computed from the inputs below.

**Formula — as the code writes it.**

```
"CL": float(run["CL"]),
```

**Inputs.** — *(leaf: a constant or an external input)*

**Produced by.** `app/services/vlm_strip_forces.py:318` — `compute_vlm_strip_forces`

🟢 **Verified against the code** — an independent reviewer read this line and confirmed the formula, unit and value (2026-08-18 audit).

**Consumed by.**

- 🔴 **nothing found.** A computed value nothing reads is a finding (ADR 0021).

**Source.** 🟢 SOURCED

> AeroSandbox docs_aero_3d.md / tutorial 06 (VLM run() returns 'CL', 'CD', 'CY', 'Cl', 'Cm', 'Cn', 'L_over_D')
>
> — via `aerosandbox-expert`

**The source states it as.**

```
CL from the ASB aero dict
```

**⚠️ Divergence from the source.** Quantity is well-defined; it simply has no consumer.

🟡 *Reported by the extraction pass, not independently verified.*

**⚠️ Anomaly.** No consumer: StripForcesResponse has no CL field and neither analysis_service nor spanwise_loads reads result["CL"].

🟡 *Reported by the extraction pass, not independently verified. Do not cite as a
defect until confirmed against the code.*

**Cited in the code itself.** `app/services/vlm_strip_forces.py:318`

---
*Cluster [[_index-aero-strips|aero-strips]] · generated from the 2026-08-18 extraction.*
