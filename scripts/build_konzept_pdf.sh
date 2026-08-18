#!/usr/bin/env bash
# Build the canon concept document as a PDF.
#
# The Markdown keeps its emoji so it stays readable on GitHub; this script
# translates them into coloured LaTeX symbols defined in the document's YAML
# header, because no text font carries both the emoji and the mathematics.
set -euo pipefail

SRC="${1:-_reversa_sdd/calculations/canon/KONZEPT.md}"
OUT="${2:-_reversa_sdd/calculations/canon/KONZEPT.pdf}"
TMP="$(mktemp -d)"
trap 'rm -rf "$TMP"' EXIT

python3 - "$SRC" "$TMP/doc.md" <<'PY'
import sys
src, dst = sys.argv[1], sys.argv[2]

# Emoji -> coloured LaTeX symbols (defined in the document's YAML header).
EMOJI = {
    "\ufe0f": "",
    "\U0001F7E2": r"\statusok{}",
    "\U0001F7E1": r"\statusmid{}",
    "\U0001F534": r"\statusbad{}",
    "\u26AA": r"\statusna{}",
    "\u2705": r"\statusyes{}",
    "\u26A0": r"\statuswarn{}",
    "\u2713": r"\statusyes{}",
    "\u2717": r"\statusbad{}",
}
# Glyphs STIX Two Text lacks in its TEXT face — take them from math instead.
# \ensuremath, not $...$: pandoc declines to read math when the closing $ is
# followed by a digit, and would escape the dollars instead.
MATH = {"\u2192": r"\ensuremath{\rightarrow}",
        "\u221A": r"\ensuremath{\surd}",
        "\u221D": r"\ensuremath{\propto}"}
# Inside verbatim blocks neither math nor a macro can be typeset: ASCII only.
EMOJI_VERBATIM = {
    "\ufe0f": "", "\U0001F7E2": "[ok]", "\U0001F7E1": "[~]", "\U0001F534": "[!]",
    "\u26AA": "[-]", "\u2705": "[ok]", "\u26A0": "[!]", "\u2713": "ok", "\u2717": "x",
}
# Inside verbatim blocks no math is possible: fall back to ASCII.
VERBATIM = {"\u2192": "->", "\u2190": "<-", "\u2502": "|", "\u2500": "-",
            "\u221A": "sqrt", "\u221D": "~"}

out, in_code = [], False
for line in open(src, encoding="utf-8"):
    if line.lstrip().startswith("```"):
        in_code = not in_code
        out.append(line)
        continue
    if in_code:
        for a, b in EMOJI_VERBATIM.items():
            line = line.replace(a, b)
    else:
        for a, b in EMOJI.items():
            line = line.replace(a, b)
    if in_code:
        for a, b in VERBATIM.items():
            line = line.replace(a, b)
    else:
        # inline `code` spans are verbatim too — no math inside them
        parts = line.split("`")
        for i, part in enumerate(parts):
            table = VERBATIM if i % 2 else MATH
            for a, b in table.items():
                part = part.replace(a, b)
            parts[i] = part
        line = "`".join(parts)
    out.append(line)
open(dst, "w", encoding="utf-8").write("".join(out))
PY
pandoc "$TMP/doc.md" \
  --from=markdown+yaml_metadata_block+pipe_tables+raw_tex \
  --pdf-engine=xelatex \
  --highlight-style=tango \
  --output="$OUT"

echo "→ $OUT  ($(du -h "$OUT" | cut -f1))"
