/**
 * Provenance helpers for version nodes (gh-961).
 *
 * `created_by` is free-form text from the backend. Agent-authored nodes use
 * "ai" OR "copilot" (the in-app copilot writes "copilot"); humans use "human";
 * legacy rows have null/empty. Detecting only "ai" misclassifies copilot work as
 * human — surfaced in UAT against real data (root 8 "Olek"). Same lesson as the
 * is_main-vs-name divergence: match on the real values, not an assumed one.
 */

const AGENT_AUTHORS = new Set(["ai", "copilot"]);

/** True when the node was authored by the AI copilot (any agent alias). */
export function isAgentAuthor(createdBy: string | null | undefined): boolean {
  return createdBy != null && AGENT_AUTHORS.has(createdBy.trim().toLowerCase());
}

/**
 * Display label for an author. Unknown/legacy (null/empty) renders as an em
 * dash rather than the trust-eroding word "unknown".
 */
export function authorLabel(createdBy: string | null | undefined): string {
  if (createdBy == null || createdBy.trim() === "") return "—";
  return createdBy;
}
