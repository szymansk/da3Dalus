---
name: avl-strip-forces-timeout
kind: parameter
unit: s
cluster: aero-spanwise
user_visible: false
source_status: NO_SOURCE_FOUND
node_class: unclassified-parameter
tags:
  - cluster/aero-spanwise
  - class/unclassified-parameter
  - source/no-source-found
  - flag/anomaly
  - solver-adjacent/avl
---

# AVL strip-forces timeout

**Definition.** Subprocess timeout for the AVL strip-forces run.

⚪ **Unclassified parameter.** Not yet decided whether this is a user input or an internal tuning value.

**Value.** `60 / 30`

**Formula — as the code writes it.**

```
timeout=60   (airplane / spanwise paths)   /   timeout=30   (single-wing path)
```

**Inputs.** — *(leaf: a constant or an external input)*

**Produced by.** `app/services/analysis_service.py:1881` — `analyze_airplane_strip_forces`

**Consumed by.**

- outside it: `AVLRunner`

**Source.** 🔴 NO SOURCE FOUND

> Subprocess timeout; infrastructure, not a design quantity. Two literals (60 at lines 1881/2044, 30 at 1962) for the same operation.
> No citable source was found. **This is recorded, not filled in.** The value is
> in the code without an attributable origin.

**⚠️ Anomaly.** Two different literals for the same operation (60 at lines 1881 and 2044, 30 at line 1962) with no shared constant.

🟡 *Reported by the extraction pass, not independently verified. Do not cite as a
defect until confirmed against the code.*

---
*Cluster [[_index-aero-spanwise|aero-spanwise]] · generated from the 2026-08-18 extraction.*
