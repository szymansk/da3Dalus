---
name: end_p_aero
symbol: P_aero
kind: quantity
unit: W
cluster: perf-envelope
user_visible: false
source_status: SOURCED
---

# Aerodynamic power

**Definition.** Power to overcome drag at the evaluation speed.

**Formula — as the code writes it.**

```
p_aero = drag * v
```

**Inputs.** [[end_drag|Drag force]]

**Produced by.** `app/services/endurance_service.py:124` — `_power_required`

**Consumed by.**

- in this graph: [[end_p_req|Battery power required]]

**Source.** 🟢 SOURCED

> Power required in steady level flight; Anderson, INTRODUCTION TO FLIGHT, Ch. 6 (Elements of Airplane Performance).
>
> — via `aero`

**The source states it as.**

```
P_req = D*V
```

**⚠️ Divergence from the source.** Module header cites 'Anderson 6e §6.4-6.5: P_req(V), V_md, V_min_sink'. Verified wrong book: in Fundamentals of Aerodynamics 6e, Ch. 6 is 'Three-Dimensional Incompressible Flow' (§6.4 three-dimensional doublet, §6.7.2 airplane drag polar) — it contains no performance material. The content described lives in Introduction to Flight Ch. 6. This is the SAME book-confusion defect as fe_cl_alpha_helmbold; two independent occurrences suggest a systematic habit of citing 'Anderson 6e' without fixing which Anderson.

🟡 *Reported by the extraction pass, not independently verified.*

---
*Cluster [[_index-perf-envelope|perf-envelope]] · generated from the 2026-08-18 extraction.*
