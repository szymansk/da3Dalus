---
name: vlm-strip-drag
symbol: drag
kind: quantity
unit: N
cluster: aero-strips
user_visible: false
source_status: SOURCED
---

# Strip drag force

**Definition.** Component of the strip force along the freestream direction (induced drag only, VLM is inviscid).

**Formula — as the code writes it.**

```
drag = float(np.dot(f_strip, d_hat))
```

**Inputs.** [[vlm-strip-force-vector|Per-strip force vector]] · [[vlm-drag-direction|Unit freestream (drag) direction]]

**Produced by.** `app/services/vlm_strip_forces.py:265` — `compute_vlm_strip_forces`

**Consumed by.**

- in this graph: [[vlm-strip-ai|Strip induced angle]] · [[vlm-strip-cd|Local strip drag coefficient]] · [[vlm-total-drag|Accumulated total drag]]

**Source.** 🟢 SOURCED

> Anderson, Fundamentals of Aerodynamics 6e, §1.5 and §5.5 (lifting-surface/VLM is potential flow, so the only drag is induced); AeroSandbox docs_aero_3d.md ('VLM-only CD is induced drag only')
>
> — via `aerodynamics-expert, aerosandbox-expert`

**The source states it as.**

```
D_strip = F_strip . d_hat, induced only
```

**⚠️ Divergence from the source.** Same local-vs-global axis issue as strip lift (AVL uses UDRAG in local strip axes, aero.f:871).

🟡 *Reported by the extraction pass, not independently verified.*

**Cited in the code itself.** `app/services/vlm_strip_forces.py:265`

---
*Cluster [[_index-aero-strips|aero-strips]] · generated from the 2026-08-18 extraction.*
