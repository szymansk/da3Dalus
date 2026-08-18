---
name: vlm-strip-te
symbol: te_pt
kind: quantity
unit: m
cluster: aero-strips
user_visible: false
source_status: PARTIAL
---

# Strip trailing-edge point

**Definition.** Midpoint of the back-left/back-right vertices of the strip's last panel.

**Formula — as the code writes it.**

```
te_pt = 0.5 * (bl[hi - 1] + br[hi - 1])
```

**Inputs.** — *(leaf: a constant or an external input)*

**Produced by.** `app/services/vlm_strip_forces.py:261` — `compute_vlm_strip_forces`

**Consumed by.**

- in this graph: [[vlm-strip-chord|Local strip chord]]

**Source.** 🟡 PARTIAL

> AVL 3.40 source, Avl/src/aoutput.f:300-320 (AVL reports no trailing-edge column; chord is carried directly as CHORD(J))
>
> — via `avl-advisor`

**⚠️ Divergence from the source.** Internal intermediate with no counterpart in the cited strip-force convention; it exists only to reconstruct a chord that AVL simply knows.

🟡 *Reported by the extraction pass, not independently verified.*

**Cited in the code itself.** `app/services/vlm_strip_forces.py:261`

---
*Cluster [[_index-aero-strips|aero-strips]] · generated from the 2026-08-18 extraction.*
