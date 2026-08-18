---
name: tos-cd-clean-nan-fallback
symbol: cd_clean
kind: quantity
unit: dimensionless
cluster: aero-strips
user_visible: true
source_status: NO_SOURCE_FOUND
---

# cd_clean → cd_tripped fallback

**Definition.** When the clean baseline is non-finite, cd_clean is silently replaced by cd_tripped so delta_cd becomes zero.

**Formula — as the code writes it.**

```
if not math.isfinite(cd_clean): cd_clean = cd_tripped  # fallback — can't compute delta
```

**Inputs.** [[tos-cd-clean|Natural-transition section drag]] · [[tos-cd-tripped|Tripped section drag]]

**Produced by.** `app/services/turbulator_optimizer_service.py:271` — `optimize_section_xtr`

**Consumed by.**

- 🔴 **nothing found.** A computed value nothing reads is a finding (ADR 0021).

**Source.** 🔴 NO SOURCE FOUND

> No citable source was found. **This is recorded, not filled in.** The value is
> in the code without an attributable origin.

**⚠️ Divergence from the source.** No source supports equating a failed baseline to the tripped value. It manufactures delta_cd = 0.0 exactly — the value that means 'the turbulator does nothing' — from a computation that failed, in a module whose docstring promises this is 'NOT a silent fallback'.

🟡 *Reported by the extraction pass, not independently verified.*

**⚠️ Anomaly.** Undeclared fallback in a module whose docstring promises 'NOT a silent fallback': no warning is appended, so a failed baseline reports delta_cd = 0.0 as if the turbulator had no effect (ADR 0020).

🟡 *Reported by the extraction pass, not independently verified. Do not cite as a
defect until confirmed against the code.*

**Cited in the code itself.** `app/services/turbulator_optimizer_service.py:270-271`

---
*Cluster [[_index-aero-strips|aero-strips]] · generated from the 2026-08-18 extraction.*
