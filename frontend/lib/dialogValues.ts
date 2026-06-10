/**
 * Shared value coercion helpers for edit-dialog forms (gh-936).
 *
 * Extracted so dialog components (e.g. TurbulatorEditDialog) reuse one
 * implementation instead of copying it — keeps the dialogs free of
 * duplicated boilerplate.
 */

/** Safely convert a value to string, avoiding [object Object]. */
export function safeStr(v: unknown, fallback = ""): string {
  if (v == null) return fallback;
  if (typeof v === "string") return v;
  if (typeof v === "number" || typeof v === "boolean") return String(v);
  return JSON.stringify(v);
}

/** Parse a form string to a finite number, or undefined when empty/invalid. */
export function optFloat(v: string): number | undefined {
  const trimmed = v.trim();
  if (!trimmed) return undefined;
  const n = Number.parseFloat(trimmed);
  return Number.isFinite(n) ? n : undefined;
}
