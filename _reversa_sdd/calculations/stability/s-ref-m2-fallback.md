---
name: s-ref-m2-fallback
symbol: —
kind: constant
unit: m²
cluster: stability
user_visible: false
source_status: NO_SOURCE_FOUND
code_audit: CONFIRMED
node_class: unclassified-constant
tags:
  - cluster/stability
  - class/unclassified-constant
  - source/no-source-found
  - audit/confirmed
  - flag/anomaly
  - flag/divergence
---

# Reference area fallback

**Definition.** Wing reference area used when the context value is missing or non-positive.

⚪ **Unclassified constant.** Not yet decided whether this is a rule of thumb, a calibration or a physical value. Classifying it is open work — it is deliberately not guessed.

**Value.** `0.60`

**Formula — as the code writes it.**

```
s_ref_m2: float = float(s_ref_raw) if s_ref_raw and float(s_ref_raw) > 0 else 0.60
```

**Inputs.** — *(leaf: a constant or an external input)*

**Produced by.** `app/services/sm_sizing_service.py:156` — `_dsm_dsh`

🟢 **Verified against the code** — an independent reviewer read this line and confirmed the formula, unit and value (2026-08-18 audit).

**Consumed by.**

- in this graph: `Tail efficiency factor` · `SM sensitivity to horizontal tail area`  
  *(these are backlinks — open the Backlinks pane to navigate them)*
- outside it: `app/services/sm_sizing_service.py:156,162`

**Source.** 🔴 NO SOURCE FOUND

>
> — via `rc-aircraft-designer`
> No citable source was found. **This is recorded, not filled in.** The value is
> in the code without an attributable origin.

**⚠️ Divergence from the source.** 0.60 m² is unattributed. Combined with mac-m-fallback = 0.30 m it implies an aspect ratio 6 / 2 m span rectangular wing — which happens to coincide with Lennon's reference case (Ch. 7: "if the wing has AR 6 …") but nothing in the code states that intent, and Lennon prescribes no absolute area.

🟡 *Reported by the extraction pass, not independently verified.*

**⚠️ Anomaly.** Magic number with no source; combined with mac fallback 0.30 it implies a 2 m span rectangular wing, which is never stated.

🟡 *Reported by the extraction pass, not independently verified. Do not cite as a
defect until confirmed against the code.*

---
*Cluster [[_index-stability|stability]] · generated from the 2026-08-18 extraction.*
