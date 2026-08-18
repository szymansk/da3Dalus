---
name: vlm-strip-lift
symbol: lift
kind: quantity
unit: N
cluster: aero-strips
user_visible: false
source_status: SOURCED
---

# Strip lift force

**Definition.** Component of the strip force along the lift direction.

**Formula — as the code writes it.**

```
lift = float(np.dot(f_strip, l_hat))
```

**Inputs.** [[vlm-strip-force-vector|Per-strip force vector]] · [[vlm-lift-direction|Unit lift direction]]

**Produced by.** `app/services/vlm_strip_forces.py:264` — `compute_vlm_strip_forces`

**Consumed by.**

- in this graph: [[vlm-strip-ai|Strip induced angle]] · [[vlm-strip-cl|Local strip lift coefficient]] · [[vlm-total-lift|Accumulated total lift]]

**Source.** 🟢 SOURCED

> Anderson, Fundamentals of Aerodynamics 6e, §1.5; AVL 3.40 source, Avl/src/aero.f:870 (CL_LSTRP = ULIFT . CF)
>
> — via `aerodynamics-expert, avl-advisor`

**The source states it as.**

```
L_strip = F_strip . l_hat
```

**⚠️ Divergence from the source.** AVL projects onto ULIFT, the lift direction in the plane NORMAL TO THE STRIP'S DIHEDRAL (local strip axes, aero.f:868-871). The app projects onto a single global l_hat. On a dihedral/V-tail surface the two differ by cos(dihedral).

🟡 *Reported by the extraction pass, not independently verified.*

**Cited in the code itself.** `app/services/vlm_strip_forces.py:264`

---
*Cluster [[_index-aero-strips|aero-strips]] · generated from the 2026-08-18 extraction.*
