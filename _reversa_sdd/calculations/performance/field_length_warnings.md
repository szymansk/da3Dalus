---
name: field_length_warnings
symbol: warnings
kind: quantity
unit: list[str]
cluster: perf-matching
user_visible: true
source_status: NO_SOURCE_FOUND
code_audit: WRONG_LINE
node_class: derived
tags:
  - cluster/perf-matching
  - class/derived
  - source/no-source-found
  - surface/user-visible
  - audit/wrong-line
  - flag/anomaly
  - flag/divergence
---

# Field-length warnings

**Definition.** User-facing warnings from the field-length computation (currently only the hand-launch climb-out margin).

**Derived quantity.** Computed from the inputs below.

**Formula — as the code writes it.**

```
warnings.append(f"Throw speed ... insufficient climb-out margin. Aim for v_throw ≥ 1.20·V_S.")
```

**Inputs.**

- [[hand_throw_warn|Hand-launch climb-out margin threshold]]  — *⊣ limit*

**Produced by.** `app/services/field_length_service.py:392` — `compute_field_lengths`

🟠 **Corrected by the audit** — the extraction claimed `WRONG_LINE`. Original line was `352`. Claim cites line 352 (initialization: warnings: list[str] = []), but the formula describes the append operation at lines 392-395.

**Consumed by.**

- outside it: `FieldLengthRead.warnings:447` · `app/api/v2/endpoints/aeroplane/field_lengths.py:209`

**Source.** 🔴 NO SOURCE FOUND

> Internal ADR 0020 policy artefact, not a physical quantity.
>
> — via `aircraft-design-scholz`
> No citable source was found. **This is recorded, not filled in.** The value is
> in the code without an attributable origin.

**⚠️ Divergence from the source.** Sole warning in the service is the hand-launch climb-out margin - itself based on the unsourced 1.20 factor. The CL_max = 1.4 fallback, unknown flap type, the 10 m/s default throw speed, and every GA-calibrated constant (2.73, 0.5847, 1.66, mu = 0.4/0.5) produce no warning at all.

🟡 *Reported by the extraction pass, not independently verified.*

**⚠️ Anomaly.** Sole warning in the service; the CL_max=1.4 fallback, unknown flap type and the 10 m/s default throw speed produce none (ADR 0020).

🟡 *Reported by the extraction pass, not independently verified. Do not cite as a
defect until confirmed against the code.*

**Cited in the code itself.** `"Throw speed {v_throw:.1f} m/s < 1.20·V_S ({...} m/s): insufficient climb-out margin. Aim for v_throw ≥ 1.20·V_S."`

---
*Cluster [[_index-perf-matching|perf-matching]] · generated from the 2026-08-18 extraction.*
