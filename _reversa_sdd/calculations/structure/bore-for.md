---
name: bore-for
kind: quantity
unit: mm
cluster: structure
user_visible: false
source_status: PARTIAL
---

# Strength bore from tube sizing

**Definition.** Bore for a tube of a given OD, obtained by feeding the governing station's reconstructed erf_W into the tube path of the #1008 solver; falls back to a fixed wall fraction when no feasible bore exists.

**Formula — as the code writes it.**

```
erf_w = required_section_modulus_from_od(governing_od)
sol = solve_dimension(shape="tube", erf_w=erf_w, outer_mm=od)
if sol["feasible"] and sol["inner_mm"] is not None:
    return float(sol["inner_mm"])
return max(0.0, od * spec.wall_factor)
```

**Inputs.** [[required-section-modulus-from-od|Section modulus provided by a solid rod]] · [[solved-tube-inner-diameter|Solved tube inner diameter]] · [[wall-factor|Tube wall fraction fallback]]

**Produced by.** `cad_designer/airplane/geometry/spar_solver.py:511` — `_bore_for`

**Consumed by.**

- in this graph: [[strength-bore|Strength-driven bore]]
- outside it: `cad_designer/airplane/geometry/spar_solver.py:420` · `cad_designer/airplane/geometry/spar_solver.py:424`

**Source.** 🟡 PARTIAL

> Kirch, "Hauptholm", https://www.flugmodellbau-kirch.de/Hauptholm.htm, procedure steps 3-4
>
> — via `direct verification of the kirch source`

**The source states it as.**

```
Available section modulus from geometry; verify W_available > W_required.
```

**⚠️ Divergence from the source.** The strength-solve branch follows the source's logic. The FALLBACK does not and inverts it: when the tube path finds no feasible bore — i.e. when strength demands a solid section — the code returns a hollow bore of 0.6·OD and emits the piece as buildable, with no warning (ADR 0020). That is the source's step-4 verification silently failing open, in the most heavily loaded case.

🟡 *Reported by the extraction pass, not independently verified.*

**⚠️ Anomaly.** Undeclared fallback (ADR 0020): when strength wants a solid section the code silently returns a hollow bore of 0.6·OD with no warning — the piece is emitted as buildable at 60 % bore in exactly the case where the solver just concluded a tube cannot do the job.

🟡 *Reported by the extraction pass, not independently verified. Do not cite as a
defect until confirmed against the code.*

**Cited in the code itself.** `required_od was sized as a *rod-equivalent*; for a tube of larger OD we can hollow it. Use solve_dimension's tube path with the governing W.`

---
*Cluster [[_index-structure|structure]] · generated from the 2026-08-18 extraction.*
