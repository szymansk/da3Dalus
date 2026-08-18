---
name: opg_worker_cap
kind: parameter
unit: processes
cluster: perf-oppoints
user_visible: false
source_status: NO_SOURCE_FOUND
code_audit: CONFIRMED
node_class: unclassified-parameter
tags:
  - cluster/perf-oppoints
  - class/unclassified-parameter
  - source/no-source-found
  - audit/confirmed
  - flag/divergence
---

# OP-generation worker cap

**Definition.** Bounded process-pool size for parallel trim solves.

⚪ **Unclassified parameter.** Not yet decided whether this is a user input or an internal tuning value.

**Value.** `4`

**Formula — as the code writes it.**

```
cpu = os.cpu_count() or 1; return max(1, min(4, cpu - 1))
```

**Inputs.** — *(leaf: a constant or an external input)*

**Produced by.** `app/services/operating_point_generator_service.py:1204` — `_opg_worker_count`

🟢 **Verified against the code** — an independent reviewer read this line and confirmed the formula, unit and value (2026-08-18 audit).

**Consumed by.**

- outside it: `app/services/operating_point_generator_service.py:1231-1244` · `app/main.py:194 (shutdown)`

**Source.** 🔴 NO SOURCE FOUND

> No citable source was found. **This is recorded, not filled in.** The value is
> in the code without an attributable origin.

**⚠️ Divergence from the source.** max(1, min(4, cpu-1)) is a process-pool sizing choice. No engineering source applies.

🟡 *Reported by the extraction pass, not independently verified.*

**Cited in the code itself.** `The CasADi/IPOPT trim solve does NOT release the GIL, so a ThreadPool is counter-productive (benchmark: 0.35-0.89x). A ProcessPool with BLAS pinned to one thread per worker gives ~2.9x at 4 workers.`

---
*Cluster [[_index-perf-oppoints|perf-oppoints]] · generated from the 2026-08-18 extraction.*
