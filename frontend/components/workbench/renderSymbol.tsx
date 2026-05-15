import React from "react";

/**
 * Render an engineering symbol where `_` is treated as LaTeX-style subscript.
 *
 *   V_x         → V<sub>x</sub>
 *   V_min_sink  → V<sub>min,sink</sub>   (inner _ → ',' per aerospace convention)
 *   V_cruise*   → V<sub>cruise</sub>*    (trailing non-word chars stay outside)
 *   MAC         → MAC                    (no underscore: passthrough)
 *
 * Differs from strict LaTeX (`V_min_sink` would otherwise be V_{m}in_sink):
 * everything between the first `_` and the trailing non-word run is the
 * subscript group. This matches how aerospace texts typeset V_{min,sink}.
 */
export function renderSymbol(label: string): React.ReactNode {
  const idx = label.indexOf("_");
  if (idx === -1) return label;

  const base = label.slice(0, idx);
  const tail = label.slice(idx + 1);

  const match = /^\w+/.exec(tail);
  if (!match) return label;

  const subRaw = match[0];
  const trailing = tail.slice(subRaw.length);
  const sub = subRaw.replace(/_/g, ",");

  return (
    <>
      {base}
      <sub className="text-[9px]">{sub}</sub>
      {trailing}
    </>
  );
}
