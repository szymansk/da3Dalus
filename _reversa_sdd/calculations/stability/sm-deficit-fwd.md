---
name: sm-deficit-fwd
symbol: —
kind: quantity
unit: – (fraction of MAC)
cluster: stability
user_visible: false
source_status: NO_SOURCE_FOUND
---

# Forward-CG SM excess

**Definition.** Amount by which the forward-CG static margin exceeds the elevator-authority limit.

**Formula — as the code writes it.**

```
sm_deficit = sm_fwd - sm_max_fwd  # positive excess above limit
```

**Inputs.** [[sm-fwd|Static margin at forward CG]] · [[sm-max-fwd|Maximum forward-CG static margin]]

**Produced by.** `app/services/sm_sizing_service.py:556` — `_suggest_corrections_fwd`

**Consumed by.**

- outside it: `app/services/sm_sizing_service.py:565`

**Source.** 🔴 NO SOURCE FOUND

>
> — via `aircraft-design-scholz`
> No citable source was found. **This is recorded, not filled in.** The value is
> in the code without an attributable origin.

**⚠️ Divergence from the source.** A difference of two static margins; no source needed for the subtraction, and none exists for treating it as a sizing driver. The name contradicts the code and comment, which both describe an excess above the limit. The comment block at sm_sizing_service.py:557-564 contains an abandoned derivation ("…no.") left in the source.

🟡 *Reported by the extraction pass, not independently verified.*

**⚠️ Anomaly.** Named 'deficit' but the comment and the code both describe an EXCESS — the name contradicts the definition. The surrounding comment block (lines 557-564) contains an abandoned derivation including the line 'Increasing S_H increases x_NP by dsm_dsh * ΔS_H * MAC... no.' left in the source.

🟡 *Reported by the extraction pass, not independently verified. Do not cite as a
defect until confirmed against the code.*

**Cited in the code itself.** `# Conservative estimate: same magnitude of ΔS_H as for the aft case (covers the gap).`

---
*Cluster [[_index-stability|stability]] · generated from the 2026-08-18 extraction.*
