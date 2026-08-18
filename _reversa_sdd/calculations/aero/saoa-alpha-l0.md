---
name: saoa-alpha-l0
symbol: alpha_L0
kind: quantity
unit: deg
cluster: aero-strips
user_visible: false
source_status: SOURCED
node_class: derived
tags:
  - cluster/aero-strips
  - class/derived
  - source/sourced
  - flag/divergence
---

# Section zero-lift angle

**Definition.** Angle of attack where the section's 2D NeuralFoil CL crosses zero.

**Derived quantity.** Computed from the inputs below.

**Formula — as the code writes it.**

```
alpha_l0 = float(np.interp(0.0, cl_2d, alphas))
```

**Inputs.**

- [[saoa-re-local|Local chord Reynolds number (alpha_L0 lookup)]]  — *⊣ limit*
- [[saoa-alpha-l0-sweep|Alpha sweep for zero-lift angle]]
- [[saoa-neuralfoil-model-size|NeuralFoil model size (alpha_L0)]]

**Produced by.** `app/services/section_aoa_service.py:188` — `_compute_alpha_l0_per_section`

**Consumed by.**

- in this graph: `Interpolated zero-lift angle at panel y`  
  *(these are backlinks — open the Backlinks pane to navigate them)*

**Source.** 🟢 SOURCED

> Anderson, Fundamentals of Aerodynamics 6e, §4.7-4.8 (alpha_L=0 is the angle of attack at which c_l = 0)
>
> — via `aerodynamics-expert`

**The source states it as.**

```
c_l(alpha_L=0) = 0
```

**⚠️ Divergence from the source.** Method (interpolate the zero crossing of the NeuralFoil polar) is the direct numerical form of the definition. The window limitation is captured under saoa-alpha-l0-sweep.

🟡 *Reported by the extraction pass, not independently verified.*

**Cited in the code itself.** `app/services/section_aoa_service.py:188`

---
*Cluster [[_index-aero-strips|aero-strips]] · generated from the 2026-08-18 extraction.*
