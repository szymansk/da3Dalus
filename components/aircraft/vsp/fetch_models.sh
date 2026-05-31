#!/usr/bin/env bash
# Helper for the OpenVSP test models (see README.md in this folder).
#
# The .vsp3 models come from VSP Airshow (https://airshow.openvsp.org/),
# which has no public download API or redistribution licence, so this
# script does NOT auto-download. It reports which expected models are
# present and which are missing, with a link to fetch the rest manually.
set -euo pipefail

DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
AIRSHOW="https://airshow.openvsp.org/"

MODELS=(
  spitfire corsair cessna172 cirrussr22 diamondda42 rv7 dg101g fl50
  generictransport rockwellov10gbronco bugatti romo tdfalconv2 x76
)

present=0
missing=()
echo "OpenVSP models in: $DIR"
for m in "${MODELS[@]}"; do
  if [[ -f "$DIR/$m.vsp3" ]]; then
    printf '  [x] %s.vsp3\n' "$m"
    present=$((present + 1))
  else
    printf '  [ ] %s.vsp3  (missing)\n' "$m"
    missing+=("$m")
  fi
done

echo
echo "$present/${#MODELS[@]} present."
if (( ${#missing[@]} > 0 )); then
  echo "Download the missing models from ${AIRSHOW} into this folder:"
  for m in "${missing[@]}"; do
    printf '  - %s.vsp3\n' "$m"
  done
  exit 1
fi
echo "All expected models present."
