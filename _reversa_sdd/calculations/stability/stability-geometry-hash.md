---
name: stability-geometry-hash
symbol: —
kind: quantity
unit: – (hex string)
cluster: stability
user_visible: false
source_status: NO_SOURCE_FOUND
code_audit: CONFIRMED
node_class: derived
tags:
  - cluster/stability
  - class/derived
  - source/no-source-found
  - audit/confirmed
  - flag/anomaly
  - flag/divergence
---

# Stability geometry hash

**Definition.** Deterministic 16-hex-char digest over the wing/fuselage geometry that affects stability, used to invalidate cached stability results.

**Derived quantity.** Computed from the inputs below.

**Formula — as the code writes it.**

```
raw = json.dumps(data, sort_keys=True, default=str)
return hashlib.sha256(raw.encode()).hexdigest()[:16]
```

**Inputs.** — *(leaf: a constant or an external input)*

**Produced by.** `app/services/stability_service.py:141` — `compute_geometry_hash`

🟢 **Verified against the code** — an independent reviewer read this line and confirmed the formula, unit and value (2026-08-18 audit).

**Consumed by.**

- outside it: `app/services/stability_service.py:356,357` · `app/services/stability_service.py:180 (geometry_hash column)`

**Source.** 🔴 NO SOURCE FOUND

>
> — via `none — not a design quantity`
> No citable source was found. **This is recorded, not filled in.** The value is
> in the code without an attributable origin.

**⚠️ Divergence from the source.** Cache-invalidation implementation detail (SHA-256 truncated to 16 hex chars), not an engineering quantity. Out of aircraft-design scope; no aerodynamic source applies.

🟡 *Reported by the extraction pass, not independently verified.*

**⚠️ Anomaly.** Three functions named compute_geometry_hash exist with different inputs and truncations: here [:16], avl_artefact_service.py:33, tessellation_cache_service.py:22. The [:16] truncation has no stated rationale.

🟡 *Reported by the extraction pass, not independently verified. Do not cite as a
defect until confirmed against the code.*

---
*Cluster [[_index-stability|stability]] · generated from the 2026-08-18 extraction.*
