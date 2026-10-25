# ADR 0030 — The Expert View may show kernel values beside the app's: a development exception to ADR 0022

- **Status:** Accepted — a scoped exception to [ADR 0022](0022-one-authority-per-user-facing-quantity.md); ADR 0022 stays in force everywhere else.
- **Decided:** 2026-10-25, during the canon approval session (#1282)
- **Deciders:** Marc Szymanski (maintainer)
- **Confidence:** 🟢 CONFIRMED (maintainer decision, quoted below)

## Context

ADR 0022 allows one authority per user-facing quantity, and the aero_kernel plan (E8) states that the
kernel is not a second producer of visible values until the app is switched over. The app still computes
many quantities in its own services (stall speed, neutral point, endurance, …). The Expert View (#1282)
lets an expert load an aircraft, compute the canon step by step with the kernel, see errors and
warnings at the formula that raises them, the kernel logs, and Drela's verdicts. Its values would stand
next to the app's own numbers for the same quantities.

Maintainer, 2026-10-25: "Die App ist eh eine riesige Baustelle. Da es der Entwicklung dient, gibt es
hierfür eine Ausnahme. Dafür ist der Kernel dann auch erreichbarer Code."

## Decision

1. The Expert View may display kernel results for quantities the app also produces.
2. It is labelled in the UI as a **canon/kernel view for development, experts only**, and is not the
   default view; its values are never written back into the app's stored values.
3. The exception covers this view only. Every other app surface keeps ADR 0022: one producer per
   user-facing number. Switching an app surface to the kernel removes the app's own producer for that
   quantity (ADR 0021), it does not add a second one.
4. Divergences between the app and the kernel that the view reveals are findings for the migration, not
   two truths.

## Consequences

- The kernel becomes reachable code from the app (ADR 0021 no longer argues against its API surface).
- The Expert View is the place where the app-to-kernel migration is checked quantity by quantity.
- Reviews treat any kernel value shown outside the Expert View, while the app still has its own
  producer, as an ADR 0022 violation.
