---
name: end_cd0_inline_default
symbol: C_D0
kind: constant
unit: -
cluster: perf-envelope
user_visible: false
source_status: NO_SOURCE_FOUND
node_class: unclassified-constant
tags:
  - cluster/perf-envelope
  - class/unclassified-constant
  - source/no-source-found
  - flag/anomaly
  - flag/divergence
---

# Inline C_D0 default

**Definition.** Zero-lift drag coefficient assumed when the assumptions dict has no cd0.

⚪ **Unclassified constant.** Not yet decided whether this is a rule of thumb, a calibration or a physical value. Classifying it is open work — it is deliberately not guessed.

**Value.** `0.03`

**Formula — as the code writes it.**

```
cd0: float = float(da.get("cd0", 0.03))
```

**Inputs.** — *(leaf: a constant or an external input)*

**Produced by.** `app/services/endurance_service.py:270` — `compute_endurance`

**Consumed by.**

- 🔴 **nothing found.** A computed value nothing reads is a finding (ADR 0021).

**Source.** 🔴 NO SOURCE FOUND

> 0.03 is not attributable at RC scale. Nearest reference points: Scholz 05_PreliminarySizing §5.7 worked example uses C_D0 = 0.020 for a jet transport; Lennon Ch. 12 emphasises that sport RC models carry far MORE parasite drag than builders expect; Roxxy Motoren-Fibel Ch. 2 pp. 17-18 avoids C_D0 entirely for models, using a lumped measured model constant MK = c_w*rho*A instead.
>
> — via `rc, scholz`
> No citable source was found. **This is recorded, not filled in.** The value is
> in the code without an attributable origin.

**⚠️ Divergence from the source.** Third copy of the literal (design_assumption.py:76, powertrain_sizing_service.py:45). Silent inline fallback with no warning appended (ADR 0020) — and C_D0 sets (L/D)_max, endurance and range, so a wrong default is not cosmetic.

🟡 *Reported by the extraction pass, not independently verified.*

**⚠️ Anomaly.** Third copy of the same literal: PARAMETER_DEFAULTS['cd0'] = 0.03 (design_assumption.py:76) and _DEFAULT_CD0 = 0.03 (powertrain_sizing_service.py:45). Silent inline fallback, no warning appended (ADR 0020).

🟡 *Reported by the extraction pass, not independently verified. Do not cite as a
defect until confirmed against the code.*

---
*Cluster [[_index-perf-envelope|perf-envelope]] · generated from the 2026-08-18 extraction.*
