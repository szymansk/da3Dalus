/**
 * Parse a text-input value to a number, falling back only when the parse is
 * not a finite number.
 *
 * This replaces the `Number.parseFloat(raw) || fallback` idiom, which wrongly
 * discards a legitimate user-entered `0` (0 is falsy), e.g. an alpha-sweep
 * starting at 0° silently became -5° (gh-787).
 *
 * @param raw      the raw input string (e.g. from a controlled <input>)
 * @param fallback the value to use when `raw` does not parse to a finite number
 */
export function finiteOr(raw: string, fallback: number): number {
  const parsed = Number.parseFloat(raw);
  return Number.isFinite(parsed) ? parsed : fallback;
}
