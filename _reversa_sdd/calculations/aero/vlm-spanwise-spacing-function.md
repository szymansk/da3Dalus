---
name: vlm-spanwise-spacing-function
symbol: spanwise_spacing_function
kind: parameter
unit: n/a
cluster: aero-strips
user_visible: false
source_status: PARTIAL
code_audit: CONFIRMED
node_class: unclassified-parameter
tags:
  - cluster/aero-strips
  - class/unclassified-parameter
  - source/partial
  - audit/confirmed
  - flag/divergence
  - solver-adjacent/vlm
---

# Spanwise panel spacing function

**Definition.** Uniform (linear) spanwise panel spacing is used instead of cosine clustering.

⚪ **Unclassified parameter.** Not yet decided whether this is a user input or an internal tuning value.

**Value.** `np.linspace`

**Formula — as the code writes it.**

```
spanwise_spacing_function=np.linspace,
```

**Inputs.** — *(leaf: a constant or an external input)*

**Produced by.** `app/services/vlm_strip_forces.py:210` — `compute_vlm_strip_forces`

🟢 **Verified against the code** — an independent reviewer read this line and confirmed the formula, unit and value (2026-08-18 audit).

**Consumed by.**

- outside it: `aerosandbox VortexLatticeMethod (external)`

**Source.** 🟡 PARTIAL

> AVL 3.40 User Primer, avl_doc.txt L1040-1082; AeroSandbox docs_aero_3d.md (spanwise_spacing_function default np.cosspace, 'critical for accuracy')
>
> — via `avl-advisor, aerosandbox-expert`

**The source states it as.**

```
Cosine (Sspace=1.0) chordwise and spanwise is 'the most efficient distribution'; uniform spacing 'always tends to overpredict the span efficiency, and its error decreases only linearly with the number of elements'
```

**⚠️ Divergence from the source.** The code overrides the ASB default cosspace with np.linspace. Uniform spacing is a legitimate AVL option (Sspace=0/3) but both consulted sources recommend against it and quantify the penalty: uniform biases span efficiency HIGH, i.e. this VLM path systematically under-reports induced drag near the tips relative to a cosine mesh at the same count.

🟡 *Reported by the extraction pass, not independently verified.*

**Cited in the code itself.** `app/services/vlm_strip_forces.py:210`

---
*Cluster [[_index-aero-strips|aero-strips]] · generated from the 2026-08-18 extraction.*
