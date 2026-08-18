---
name: strength-bore
kind: quantity
unit: mm
cluster: structure
user_visible: false
source_status: PARTIAL
---

# Strength-driven bore

**Definition.** Largest bore a tube of the given OD may have and still meet its strength requirement.

**Formula — as the code writes it.**

```
strength_bore = _bore_for(runs[i], spec, ods[i])
```

**Inputs.** [[bore-for|Strength bore from tube sizing]]

**Produced by.** `cad_designer/airplane/geometry/spar_solver.py:424` — `plan_spar`

**Consumed by.**

- in this graph: [[piece-bore|Spar piece inner diameter]]
- outside it: `cad_designer/airplane/geometry/spar_solver.py:425`

**Source.** 🟡 PARTIAL

> Kirch, "Hauptholm", https://www.flugmodellbau-kirch.de/Hauptholm.htm, procedure step 3-4 (available section modulus from geometry; verify W_available > W_required)
>
> — via `direct verification of the kirch source`

**The source states it as.**

```
The source's principle — hollow out the section as far as strength permits — is implicit in step 4. No tube bore relation is given.
```

---
*Cluster [[_index-structure|structure]] · generated from the 2026-08-18 extraction.*
