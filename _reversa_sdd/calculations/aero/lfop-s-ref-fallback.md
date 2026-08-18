---
name: lfop-s-ref-fallback
symbol: s_ref
kind: constant
unit: m²
cluster: aero-strips
user_visible: false
source_status: NO_SOURCE_FOUND
---

# Reference area fallback

**Definition.** Reference area used when no symmetric wing area could be computed.

**Value.** `0.3`

**Formula — as the code writes it.**

```
s_ref = 0.3  # sensible default [m²]
```

**Inputs.** — *(leaf: a constant or an external input)*

**Produced by.** `app/services/section_aoa_service.py:499` — `_resolve_level_flight_op`

**Consumed by.**

- 🔴 **nothing found.** A computed value nothing reads is a finding (ADR 0021).

**Source.** 🔴 NO SOURCE FOUND

> No citable source was found. **This is recorded, not filled in.** The value is
> in the code without an attributable origin.

**⚠️ Divergence from the source.** 0.3 m^2 has no citable basis. It also silently rescues a geometry with no computable wing area, which is a hard error, not a defaultable input.

🟡 *Reported by the extraction pass, not independently verified.*

**⚠️ Anomaly.** Undeclared fallback magic number (ADR 0020/0023: no source cited for 0.3 m²).

🟡 *Reported by the extraction pass, not independently verified. Do not cite as a
defect until confirmed against the code.*

**Cited in the code itself.** `app/services/section_aoa_service.py:498-499`

---
*Cluster [[_index-aero-strips|aero-strips]] · generated from the 2026-08-18 extraction.*
