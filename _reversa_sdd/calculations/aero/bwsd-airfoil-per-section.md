---
name: bwsd-airfoil-per-section
symbol: af_name
kind: quantity
unit: n/a
cluster: aero-strips
user_visible: false
source_status: PARTIAL
---

# Per-section airfoil name

**Definition.** Airfoil assigned to a section by locating the enclosing cross-section index by y.

**Formula — as the code writes it.**

```
xsec_idx = int(np.clip(np.searchsorted(xsec_y, entry.y_m, side="right") - 1, 0, len(xsec_airfoils) - 1))
```

**Inputs.** [[bwsd-main-wing|Main wing selection]] · [[saoa-y|Panel spanwise position]]

**Produced by.** `app/services/turbulator_optimizer_service.py:428` — `build_wing_section_data`

**Consumed by.**

- outside it: `app/services/turbulator_optimizer_service.py:run_turbulator_optimizer`

**Source.** 🟡 PARTIAL

> AeroSandbox tutorial 06, VLM point analysis ('The airfoil is blended linearly between consecutive XSecs'); AVL 3.40 User Primer avl_doc.txt L583-633
>
> — via `aerosandbox-expert, avl-advisor`

**The source states it as.**

```
Section airfoil = linear blend of the two bounding xsec airfoils
```

**⚠️ Divergence from the source.** Real. The searchsorted-minus-one lookup assigns the nearest INBOARD airfoil with no blending, contradicting the documented ASB/AVL loft. On a wing with a different tip section, every panel between the two xsecs is analysed with the root profile — and the vlm_strip_forces module in the same codebase DOES implement the blend (_blend_xsec).

🟡 *Reported by the extraction pass, not independently verified.*

**⚠️ Anomaly.** Nearest-inboard xsec airfoil is used with no blending, so a section between two different airfoils is analysed with the inboard one only.

🟡 *Reported by the extraction pass, not independently verified. Do not cite as a
defect until confirmed against the code.*

**Cited in the code itself.** `app/services/turbulator_optimizer_service.py:428-435`

---
*Cluster [[_index-aero-strips|aero-strips]] · generated from the 2026-08-18 extraction.*
