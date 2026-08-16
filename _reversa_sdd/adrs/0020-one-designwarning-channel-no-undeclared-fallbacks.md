# ADR 0020 — One `DesignWarning` channel: no *undeclared* fallbacks

- **Status:** Accepted — refines [ADR 0012](0012-design-warnings-instead-of-silent-fallbacks.md)
- **Decided:** 2026-08-13, during the specification validation interview (`P-WARN-0`)
- **Deciders:** Marc Szymanski (maintainer)
- **Confidence:** 🟢 CONFIRMED (interview answer with a worked classification table; 34 catalogued instances across 13 modules)

## Context

ADR 0012 states the principle and defines **no mechanism**. That omission is why
the principle is violated at roughly 30 sites: there was nothing to emit *into*.
Exactly two subsystems honour it today, and **each invented its own shape** — the
polar fit's categorised `PolarRejection` gates and the turbulator optimiser's
warning list. Everywhere else the substitution is silent: the computation context's
per-consumer RC defaults (`cd0 0.03`, `e 0.8`, `AR 8.0`, `S 0.5 m²`,
`mass 1.0 kg`), `DEFAULT_E_OSWALD = 0.8` in the matching chart, the OpenVSP
sewing-tolerance retry, `inject_cdcl`'s truncating loop, swallowed
`ImportError`/`FileNotFoundError`, `except Exception: pass` in the copilot's
retarget path. It surfaced as **34 separate questions across 13 modules** before the
interview named it as one policy — *"the highest-leverage decision in the
catalogue"*.

One further input shaped the answer: several substitutions **are** legitimate
engineering practice. Relaxing a sewing tolerance from 1 mm to 5 mm is what a CAD
engineer does; assuming `e = 0.8` where a fit cannot converge at low Reynolds
number is a defensible domain value. What is unacceptable is doing either
*invisibly*.

## Decision

**One shared, mandatory structured warning channel. Every response whose numbers
were degraded carries `warnings: [DesignWarning]`.**

```
DesignWarning:
  code      stable machine token — OSWALD_FIT_NOT_CONVERGED |
            SEWING_TOLERANCE_RELAXED | ASSUMPTION_KEY_MISSING | …
  category  substituted_assumption | fit_not_converged | geometry_healed |
            input_missing | result_truncated | capability_unavailable
  severity  notice   → legitimate, declared substitution (domain practice)
            warning  → number usable, confidence reduced
            error    → number not physically meaningful; do not build on it
  message   human-readable, including the justification
  context   the concrete numbers (value used, Re regime, residual, missing key)
```

**The rule is not "no fallbacks". It is "no _undeclared_ fallbacks."** A
substitution stays permissible and becomes part of the answer instead of a hidden
premise of it.

**Worked classification, agreed in the interview:**

| Case | Classification | Rationale |
|---|---|---|
| Sewing tolerance 1 mm → 5 mm | `notice` · `geometry_healed` | Standard CAD healing; the user should still know healing occurred |
| `e = 0.8` because the fit does not converge at **low Re** | `notice` · `fit_not_converged` | Model limitation, not a design fault; 0.8 is a defensible domain value — but `e` was *assumed*, not *determined* |
| `e` fallback masking **`k ≤ 0` / unphysical `e`** | `warning` / `error` · `fit_not_converged` | A design or data problem, and must not be hidden behind 0.8 |
| `mass = 1.0 kg` because the context key was missing | `error` · `input_missing` | A placeholder unrelated to the aircraft — a defect, not engineering |

**The last three rows are indistinguishable today** — the same silent substitution
of the same constant by the same code. Severity is what separates them.

**Why severity is load-bearing, not decoration.** Without it the channel becomes
noise: if a routine tolerance heal is as loud as a missing mass, warnings stop being
read within weeks — and a channel nobody reads is *worse* than the status quo,
because it converts an acknowledged blind spot into a discharged obligation.
ADR 0012 already records the symptom. Rendering follows the grade: `notice` may be a
subtle "assumed" marker beside the number; `error` must be prominent.

## Consequences

- The ~30 violating sites acquire a destination — each becomes a one-line emit rather
  than a design question, which is why one policy answer resolves or constrains
  **34 catalogued questions**. The two bespoke shapes converge on one contract, and
  `severity` gives the copilot a machine-readable confidence signal on every degraded
  number.
- Legitimate engineering substitutions survive the policy instead of being driven
  underground — the failure mode of a "no fallbacks" rule is that the fallback moves
  somewhere less visible.
- **Cost:** every degradable response schema gains a `warnings` field and every
  frontend surface that renders one gains a renderer — wide and shallow, touching
  most routers. **Grading is a judgement per site**; the four-row table is
  calibration, not an algorithm. Removing the RC-typical defaults means some
  responses that used to render a plausible chart now render nothing plus an `error`.
- This **refines** ADR 0012; it does not supersede it. Existing provenance labels
  (`e_oswald_provenance`, `trim_method`, KPI confidence tiers) are not replaced: they
  answer "which method produced this", `DesignWarning` answers "what was substituted
  and how bad is that".

**Rejected:** forbidding fallbacks outright (bans legitimate domain practice, and a
rule wrong in defensible cases is routed around); one flat list with no severity (the
fatigue argument above); a sentinel value per failure mode (a magic number is another
undeclared encoding — the warning carries the information, the number stays a
number).

## Related

- [ADR 0012](0012-design-warnings-instead-of-silent-fallbacks.md) — the principle
  this ADR supplies the mechanism for.
- [ADR 0004](0004-one-aero-truth-per-aircraft.md) — the context whose per-consumer
  fallbacks are the largest single group of violations.
- [ADR 0010](0010-design-assumptions-carry-estimate-and-calculated.md), amended
  2026-08-15 to remove the RC-typical defaults in favour of an `error`-severity
  `DesignWarning`.
- [ADR 0022](0022-one-authority-per-user-facing-quantity.md) — the companion rule:
  a warning is not a substitute for designating one producer.
- `P-WARN-0` in [`../questions.md`](../questions.md), and the **34** questions it
  resolves or constrains: `Q-CC-10` · `Q-AC-7` · `Q-AC-8` · `Q-WD-6` · `Q-WD-8` ·
  `Q-WD-10` · `Q-FD-4` · `Q-FD-6` · `Q-AF-8` · `Q-AF-9` · `Q-CP-3` · `Q-CP-9` ·
  `Q-VI-3` · `Q-VI-5` · `Q-VI-7` · `Q-AA-1` · `Q-AA-3` · `Q-AV-5` · `Q-AV-7` ·
  `Q-MS-4` · `Q-MS-5` · `Q-MS-8` · `Q-MS-9` · `Q-MS-10` · `Q-MS-12` · `Q-PT-1` ·
  `Q-PT-2` · `Q-PT-8` · `Q-PT-12` · `Q-CO-2` · `Q-CO-3` · `Q-MC-4` · `Q-MC-5` ·
  `Q-PC-1`.
