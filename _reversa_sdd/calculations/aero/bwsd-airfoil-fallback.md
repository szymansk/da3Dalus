---
name: bwsd-airfoil-fallback
symbol: af_name
kind: constant
unit: n/a
cluster: aero-strips
user_visible: false
source_status: NO_SOURCE_FOUND
---

# Airfoil name fallback

**Definition.** NACA 0012 is substituted when a cross-section has no airfoil name.

**Value.** `"naca0012"`

**Formula — as the code writes it.**

```
af_name = getattr(xs.airfoil, "name", None) or "naca0012"
```

**Inputs.** — *(leaf: a constant or an external input)*

**Produced by.** `app/services/turbulator_optimizer_service.py:405` — `build_wing_section_data`

**Consumed by.**

- 🔴 **nothing found.** A computed value nothing reads is a finding (ADR 0021).

**Source.** 🔴 NO SOURCE FOUND

> Anderson, Fundamentals of Aerodynamics 6e, §20.3.2 (low-Re airfoil flow: laminar separation and bubble behaviour are strongly section-dependent; a Wortmann section at Re_c = 1e5 separates on both surfaces laminarly and reattaches fully when tripped)
>
> — via `aerodynamics-expert`
> No citable source was found. **This is recorded, not filled in.** The value is
> in the code without an attributable origin.

**⚠️ Divergence from the source.** No source supports NACA 0012 as a default. It is symmetric (alpha_L0 = 0, cambered-section behaviour absent) and its pressure recovery differs sharply from a cambered low-Re section, so its cd(x_tr) response — the exact thing being optimised — is not representative.

🟡 *Reported by the extraction pass, not independently verified.*

**⚠️ Scale (ADR 0023).** Section identity dominates results precisely in the Re 5e4-3e5 band this app targets, per the cited Anderson case. A substituted section is a much larger error here than it would be at transport Reynolds numbers.

> This application targets RC/UAV aircraft of **0.5–15 kg**. A constant is not
> justified by being standard in transport-category literature.

**⚠️ Anomaly.** Undeclared fallback: a symmetric NACA 0012 replaces an unknown section airfoil, and its cd/xtr behaviour differs sharply from a cambered low-Re section (ADR 0020).

🟡 *Reported by the extraction pass, not independently verified. Do not cite as a
defect until confirmed against the code.*

**Cited in the code itself.** `app/services/turbulator_optimizer_service.py:405,407,435`

---
*Cluster [[_index-aero-strips|aero-strips]] · generated from the 2026-08-18 extraction.*
