---
name: trim-fallback-index
kind: quantity
unit: index
cluster: aero-spanwise
user_visible: true
source_status: NO_SOURCE_FOUND
---

# Trim nearest-point fallback

**Definition.** When Cm never crosses zero the point of minimum \|Cm\| is reported as the trim point.

**Formula — as the code writes it.**

```
i = int(np.argmin(np.abs(cm)))
```

**Inputs.** [[cm-values|Pitching-moment coefficient array]]

**Produced by.** `app/services/analysis_service.py:209` — `_compute_trim_point`

**Consumed by.**

- 🔴 **nothing found.** A computed value nothing reads is a finding (ADR 0021).

**Source.** 🔴 NO SOURCE FOUND

> argmin\|Cm\| substitution has no source. An aircraft with no Cm=0 crossing is untrimmable in the swept range; presenting a 'Trim (Cm=0)' marker with Cm≠0 contradicts Sadraey §11.6.2 and emits no DesignWarning (ADR 0020).
> No citable source was found. **This is recorded, not filled in.** The value is
> in the code without an attributable origin.

**⚠️ Anomaly.** An untrimmable aircraft still gets a 'Trim (Cm=0)' marker with Cm != 0 and no warning (ADR 0020).

🟡 *Reported by the extraction pass, not independently verified. Do not cite as a
defect until confirmed against the code.*

---
*Cluster [[_index-aero-spanwise|aero-spanwise]] · generated from the 2026-08-18 extraction.*
