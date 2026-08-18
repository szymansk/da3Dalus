---
name: mkpi_context_hash
symbol: context_hash
kind: quantity
unit: -
cluster: perf-envelope
user_visible: false
source_status: SOURCED
---

# Context hash

**Definition.** SHA-256 of the computation context for client-side cache validation.

**Formula — as the code writes it.**

```
blob = json.dumps(ctx, sort_keys=True, default=str).encode("utf-8"); return hashlib.sha256(blob).hexdigest()
```

**Inputs.** — *(leaf: a constant or an external input)*

**Produced by.** `app/services/mission_kpi_service.py:395` — `_hash_context`

**Consumed by.**

- outside it: `frontend/hooks/useMissionKpis.ts (type declaration only)`

**Source.** 🟢 SOURCED

> Standard content hash; no engineering source applies.
>
> — via `scholz`

**The source states it as.**

```
SHA-256 over the sorted-key JSON of ctx
```

**⚠️ Divergence from the source.** ADR 0021: declared in the response schema (min_length=64) and typed in the frontend MissionKpiSet, but no frontend code reads it. The stated purpose — client-side cache validation — is not implemented on any consumer. Complete but unreachable.

🟡 *Reported by the extraction pass, not independently verified.*

**⚠️ Anomaly.** Declared in the response schema (min_length=64) and in the frontend MissionKpiSet type, but no frontend code reads it — the stated purpose (cache validation) is not implemented on any consumer.

🟡 *Reported by the extraction pass, not independently verified. Do not cite as a
defect until confirmed against the code.*

---
*Cluster [[_index-perf-envelope|perf-envelope]] · generated from the 2026-08-18 extraction.*
