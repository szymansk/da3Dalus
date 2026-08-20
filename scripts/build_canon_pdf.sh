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

raw = src.read_text(encoding="utf-8")

# Pull the mermaid blocks out first, together with the caption line that may follow one.
# A caption is written as *Abbildung -- ...* so GitHub shows it as italic text under the
# diagram while the PDF turns it into a real, numbered figure caption.
n = 0

def _take(m):
    global n
    n += 1
    (tmp / f"diagram{n}.mmd").write_text(m.group(1), encoding="utf-8")
    if m.group(2):
        (tmp / f"diagram{n}.cap").write_text(m.group(2).strip(), encoding="utf-8")
    # A placeholder, not the \includegraphics: how the diagram is placed depends on how
    # big it turns out, and that is only known once mermaid has rendered it.
    return f"\n%%DIAGRAM{n}%%\n\n"

raw = re.sub(
    r"```mermaid\n(.*?)\n```[ \t]*\n(?:[ \t]*\n)?"
    r"(?:\*Abbildung[ \t]*[\u2014-][ \t]*(.+?)\*[ \t]*\n)?",
    _take, raw, flags=re.S)

lines = raw.splitlines(keepends=True)
out, in_code = [], False

for line in lines:
    stripped = line.strip()
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
#: A page of its own costs the reader a break in the flow, so a diagram that is already
#: legible in the column stays there (the test above). Once it is not, any real gain is
#: worth the page — this guard only rejects a move that changes nothing.
WORTH_A_PAGE = 1.05

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
    cap_file = pdf.with_suffix(".cap")
    caption = cap_file.read_text(encoding="utf-8").strip() if cap_file.exists() else ""
    cap_tex = f"\\caption{{{caption}}}" if caption else ""

    own_page = max(upright, turned)
    if inline >= legible or own_page < inline * WORTH_A_PAGE:
        block = ("\n\\begin{figure}[H]\\centering\\includegraphics[width=\\textwidth,"
                 f"height=0.62\\textheight,keepaspectratio]{{{img}}}"
                 f"{cap_tex}\\end{{figure}}\n")
        how = f"in der Spalte ({inline:.2f}x, Schwelle {legible:.2f})"
    else:
        if turned > upright:
            # sidewaysfigure turns the caption with the figure, which \rotatebox on the
            # graphic alone would not.
            block = (f"\n\\begin{{sidewaysfigure}}\\centering\\includegraphics["
                     "width=\\textheight,height=0.86\\textwidth,keepaspectratio]"
                     f"{{{img}}}{cap_tex}\\end{{sidewaysfigure}}\n")
            lage = "gedreht"
        else:
            block = (f"\n\\begin{{figure}}[p]\\centering\\includegraphics["
                     "height=0.92\\textheight,width=\\textwidth,keepaspectratio]"
                     f"{{{img}}}{cap_tex}\\end{{figure}}\n")
            lage = "aufrecht"
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
