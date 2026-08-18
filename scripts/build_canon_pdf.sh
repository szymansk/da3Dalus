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
        "∝": r"\ensuremath{\propto}"}
VERB = {"→": "->", "←": "<-", "│": "|", "─": "-",
        "√": "sqrt", "∝": "~"}

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
        # absolute path: pandoc passes raw LaTeX through untouched, so --resource-path
        # does not apply and xelatex runs in a directory of its own.
        img = (tmp / f"diagram{n}.pdf").as_posix()
        out.append(f"\n\\begin{{center}}\\includegraphics[width=\\textwidth,"
                   f"height=0.62\\textheight,keepaspectratio]{{{img}}}\\end{{center}}\n\n")
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
fi

pandoc "$TMP/doc.md" \
  --from=markdown+yaml_metadata_block+pipe_tables+raw_tex \
  --pdf-engine=xelatex --resource-path="$TMP" \
  --syntax-highlighting=tango \
  --output="$OUT"

echo "→ $OUT  ($(du -h "$OUT" | cut -f1), $COUNT Diagramm(e))"
