#!/usr/bin/env bash
# Build a canon document as a PDF, rendering any ```mermaid block on the way.
#
# The Markdown keeps its mermaid fence so GitHub renders the diagram natively; this
# script extracts each fence, renders it with mermaid-cli, and substitutes an
# \includegraphics for the PDF. One source, both outputs.
set -euo pipefail

SRC="${1:?usage: build_canon_pdf.sh <doc.md> [out.pdf]}"
OUT="${2:-${SRC%.md}.pdf}"
# A dot-free directory: \includegraphics guesses the extension from the last dot in
# the path, and mktemp's "tmp.XXXX" would make it guess wrong.
TMP="${TMPDIR:-/tmp}/canonbuild-$$"
mkdir -p "$TMP"
trap 'rm -rf "$TMP"' EXIT

python3 - "$SRC" "$TMP" <<'PY'
import re, sys, pathlib
src, tmp = pathlib.Path(sys.argv[1]), pathlib.Path(sys.argv[2])

EMOJI = {"️": "", "\U0001F7E2": r"\statusok{}", "\U0001F7E1": r"\statusmid{}",
         "\U0001F534": r"\statusbad{}", "⚪": r"\statusna{}", "✅": r"\statusyes{}",
         "⚠": r"\statuswarn{}", "✓": r"\statusyes{}", "✗": r"\statusbad{}"}
EMOJI_V = {"️": "", "\U0001F7E2": "[ok]", "\U0001F7E1": "[~]", "\U0001F534": "[!]",
           "⚪": "[-]", "✅": "[ok]", "⚠": "[!]", "✓": "ok", "✗": "x"}
MATH = {"→": r"\ensuremath{\rightarrow}", "√": r"\ensuremath{\surd}",
        "∝": r"\ensuremath{\propto}", "≤": r"\ensuremath{\leq}",
        "≥": r"\ensuremath{\geq}",
        "≠": r"\ensuremath{\neq}"}
VERB = {"→": "->", "←": "<-", "│": "|", "─": "-",
        "√": "sqrt", "∝": "~", "≤": "<=", "≥": ">=", "≠": "!="}

lines = src.read_text(encoding="utf-8").splitlines(keepends=True)
out, in_code, in_mermaid, buf, n = [], False, False, [], 0

for line in lines:
    stripped = line.strip()
    if stripped.startswith("```mermaid"):
        in_mermaid, buf = True, []
        continue
    if in_mermaid and stripped == "```":
        n += 1
        (tmp / f"diagram{n}.mmd").write_text("".join(buf), encoding="utf-8")
        # A placeholder, not the \includegraphics: how the diagram is placed depends on
        # how wide it turns out, and that is only known once mermaid has rendered it.
        out.append(f"\n%%DIAGRAM{n}%%\n\n")
        in_mermaid = False
        continue
    if in_mermaid:
        buf.append(line)
        continue
    if stripped.startswith("```"):
        in_code = not in_code
        out.append(line)
        continue
    if in_code:
        for a, b in EMOJI_V.items():
            line = line.replace(a, b)
        for a, b in VERB.items():
            line = line.replace(a, b)
    else:
        for a, b in EMOJI.items():
            line = line.replace(a, b)
        parts = line.split("`")
        for i, part in enumerate(parts):
            for a, b in (VERB if i % 2 else MATH).items():
                part = part.replace(a, b)
            parts[i] = part
        line = "`".join(parts)
    out.append(line)

(tmp / "doc.md").write_text("".join(out), encoding="utf-8")
print(n)
PY

COUNT=$(ls -1 "$TMP"/*.mmd 2>/dev/null | wc -l | tr -d ' ')
echo "  Diagramme gefunden: $COUNT"
if [ "$COUNT" -gt 0 ]; then
  printf '{"theme":"neutral","themeVariables":{"fontFamily":"Helvetica","fontSize":"15px"}}' \
    > "$TMP/mermaid.json"
  for f in "$TMP"/*.mmd; do
    npx --yes @mermaid-js/mermaid-cli@11 -i "$f" -o "${f%.mmd}.pdf" \
      -c "$TMP/mermaid.json" --pdfFit 2>&1 | sed 's/^/    mermaid: /'
  done

  # Place each diagram according to its aspect ratio. A graph wider than it is tall
  # loses all its detail when squeezed into a text column, so it goes onto a page of
  # its own, turned 90 degrees — the usual treatment for a wide figure in a thesis.
  python3 - "$TMP" <<'PY'
import re, sys, pathlib
tmp = pathlib.Path(sys.argv[1])
doc = tmp / "doc.md"
text = doc.read_text(encoding="utf-8")

# A4 minus the 2.3 cm margins this document class uses, in points.
TEXTWIDTH, TEXTHEIGHT = 465.0, 712.0
#: What counts as legible depends on what the labels contain. KaTeX sets a subscript at
#: ~0.7 of the base, so in a diagram full of formulas 0.9 of an 11 pt label already puts
#: the subscripts near 7 pt. A diagram labelled in words survives far more shrinking.
LEGIBLE_MATH, LEGIBLE_WORDS = 0.90, 0.70
#: A page of its own costs the reader a break in the flow. Only take one when it buys
#: enough to be worth it — otherwise a diagram that is merely wide and short gets a page
#: for nothing.
WORTH_A_PAGE = 1.20

for pdf in sorted(tmp.glob("diagram*.pdf")):
    n = re.search(r"diagram(\d+)", pdf.name).group(1)
    box = re.search(rb"/MediaBox\s*\[\s*([\d.+-]+)\s+([\d.+-]+)\s+([\d.+-]+)\s+([\d.+-]+)",
                    pdf.read_bytes())
    w = h = 0.0
    if box:
        x0, y0, x1, y1 = (float(v) for v in box.groups())
        w, h = abs(x1 - x0), abs(y1 - y0)

    # How far each of the three placements would shrink the diagram. Aspect ratio alone
    # is the wrong test: a three-box flow is very wide and still perfectly legible in the
    # column, while a tall one gains nothing from being turned.
    inline  = min(TEXTWIDTH / w, 0.62 * TEXTHEIGHT / h) if w and h else 1.0
    upright = min(TEXTWIDTH / w, 0.95 * TEXTHEIGHT / h) if w and h else 0.0
    turned  = min(TEXTHEIGHT / w, 0.95 * TEXTWIDTH / h) if w and h else 0.0

    src_mmd = pdf.with_suffix(".mmd")
    has_math = "$$" in src_mmd.read_text(encoding="utf-8") if src_mmd.exists() else False
    legible = LEGIBLE_MATH if has_math else LEGIBLE_WORDS

    img = pdf.as_posix()   # absolute: pandoc passes raw LaTeX through, so
                           # --resource-path does not apply to it
    own_page = max(upright, turned)
    if inline >= legible or own_page < inline * WORTH_A_PAGE:
        block = ("\n\\begin{center}\\includegraphics[width=\\textwidth,"
                 f"height=0.62\\textheight,keepaspectratio]{{{img}}}\\end{{center}}\n")
        how = f"in der Spalte ({inline:.2f}x, Schwelle {legible:.2f})"
    else:
        angle = "angle=90," if turned > upright else ""
        block = (f"\n\\clearpage\n\\begin{{center}}\\includegraphics[{angle}"
                 "height=0.95\\textheight,width=\\textwidth,keepaspectratio]"
                 f"{{{img}}}\\end{{center}}\n\\clearpage\n")
        lage = "gedreht" if angle else "aufrecht"
        how = (f"eigene Seite, {lage} — in der Spalte {inline:.2f}x, "
               f"auf eigener Seite {own_page:.2f}x")
    text = text.replace(f"%%DIAGRAM{n}%%", block)
    print(f"    Diagramm {n}: {how}")

doc.write_text(text, encoding="utf-8")
PY
fi

pandoc "$TMP/doc.md" \
  --from=markdown+yaml_metadata_block+pipe_tables+raw_tex \
  --pdf-engine=xelatex --resource-path="$TMP" \
  --syntax-highlighting=tango \
  --output="$OUT"

echo "→ $OUT  ($(du -h "$OUT" | cut -f1), $COUNT Diagramm(e))"
