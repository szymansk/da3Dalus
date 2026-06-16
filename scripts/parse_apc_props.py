#!/usr/bin/env python3
"""Parse APC PER3 propeller performance .dat files → data/cots/apc_props.json.gz

Usage:
    poetry run python scripts/parse_apc_props.py [--raw-dir <path>] [--output <path>]

Raw APC PER3 .dat files must be in:
    data/apc_raw/   (default; gitignored)

The script writes (or overwrites) data/cots/apc_props.json.gz with a list of
propeller records in the snapshot format — the durable reimport source.
The snapshot is gzip-compressed to stay within git-friendly file sizes
(raw ~58 MB → ~5-8 MB compressed).

Raw .dat files contain facts (measured performance data); only the extracted
numbers are committed. The source .dat files are gitignored because:
  - APC license allows use; re-hosting the full file set is unnecessary.
  - The committed snapshot (factual numbers) is sufficient to reproduce the DB.

APC PER3 file format reference:
  Header block: propeller name (line 1), version string (v2022-xxxx), date.
  Repeated RPM blocks:
      PROP RPM = <N>
      Column header row (V, J, Pe, Ct, Cp, PWR, Torque, Thrust, …)
      Unit row (mph, Adv_Ratio, -, -, -, Hp, In-Lbf, Lbf, W, N-m, N, …)
      Data rows (whitespace-delimited floats)
      (blank line terminates the block)

Header line 1 format: ``<designation>  (<filename>)``
  where <designation> is the canonical propeller name:
  - ``9x6``        → 9" diameter, 6" pitch, no variant
  - ``10.5x4.5``   → 10.5" diameter, 4.5" pitch (decimal; filename: 105x45)
  - ``10x10E``     → 10" diameter, 10" pitch, variant 'E' (electric prop)
  - ``10x10M-JK``  → 10" diameter, 10" pitch, variant 'M-JK' (marine)

We extract SI columns: PWR (W), Torque (N-m), Thrust (N) plus dimensionless J,
Ct, Cp, Pe.  Imperial columns (Hp, In-Lbf, Lbf) are discarded.
"""

from __future__ import annotations

import gzip
import json
import logging
import re
import sys
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any

logger = logging.getLogger(__name__)

REPO_ROOT = Path(__file__).resolve().parent.parent
RAW_DIR = REPO_ROOT / "data" / "apc_raw"
OUTPUT_PATH = REPO_ROOT / "data" / "cots" / "apc_props.json.gz"

SOURCE_URL_BASE = "https://www.apcprop.com/files"
MANUFACTURER = "APC"

# ──────────────────────────────────────────────────────────────────────────────
# Data structures
# ──────────────────────────────────────────────────────────────────────────────


@dataclass
class RpmBlock:
    """One RPM operating point with its measurement table."""

    rpm: int
    samples: list[dict[str, float]] = field(default_factory=list)


@dataclass
class ParsedPropFile:
    """Result of parsing one APC PER3 .dat file."""

    diameter_in: float
    pitch_in: float
    variant: str  # e.g. "" for plain, "E" for electric, "M-JK" for marine, etc.
    source_version: str | None
    rpm_blocks: list[RpmBlock] = field(default_factory=list)


# ──────────────────────────────────────────────────────────────────────────────
# Header-based designation parser (primary, gh-999)
# ──────────────────────────────────────────────────────────────────────────────

# Regex for the header designation token: ``<dia>x<pitch>[<variant>]``
# The variant captures everything after the numeric pitch (including hyphens,
# letters, parentheses — e.g. "E", "M-JK", "EP(F2B)", "-4").
# We stop capturing at whitespace (since the token is whitespace-delimited).
_HEADER_DESIG_RE = re.compile(r"^\s*([0-9]+(?:\.[0-9]+)?)x([0-9]+(?:\.[0-9]+)?)(\S*)")


def parse_header_designation(line: str) -> tuple[float, float, str] | None:
    """Parse the canonical designation from header line 1.

    The first token on the line is ``<dia>x<pitch>[<variant>]``, optionally
    followed by whitespace and a parenthesised filename.

    Returns (diameter_in, pitch_in, variant) or None if unparseable.

    Examples::

        "         9x6                      (9x6.dat)"       → (9.0, 6.0, "")
        "         10.5x4.5                 (105x45.dat)"    → (10.5, 4.5, "")
        "         10x10E                   (10x10E.dat)"    → (10.0, 10.0, "E")
        "         10x10M-JK                (10x10M-JK.dat)" → (10.0, 10.0, "M-JK")
        "         10x5.8EP(F2B)            (10x58EP(F2B).dat)" → (10.0, 5.8, "EP(F2B)")
    """
    if not line:
        return None
    m = _HEADER_DESIG_RE.match(line)
    if not m:
        return None
    try:
        dia = float(m.group(1))
        pitch = float(m.group(2))
    except ValueError:
        return None
    variant = m.group(3).strip()
    return dia, pitch, variant


# ──────────────────────────────────────────────────────────────────────────────
# Filename parser (legacy fallback)
# ──────────────────────────────────────────────────────────────────────────────


def parse_filename(filename: str) -> tuple[float, float] | None:
    """Extract (diameter_in, pitch_in) from a PER3 filename.

    Supports:
      PER3_7x4.dat    → (7.0, 4.0)
      PER3_9x4.5.dat  → (9.0, 4.5)
      PER3_11x5.5.dat → (11.0, 5.5)

    Returns None if the name doesn't match the expected pattern.
    Note: filenames with variant suffixes (PER3_10x10E.dat) and decimal-
    without-dot filenames (PER3_105x45.dat) do NOT parse correctly from the
    filename alone — always prefer the header-based parser.
    """
    name = Path(filename).stem  # strip .dat
    m = re.match(r"PER3_(\d+)x(\d+(?:\.\d+)?)$", name)
    if not m:
        return None
    dia = float(m.group(1))
    pitch = float(m.group(2))
    return dia, pitch


# ──────────────────────────────────────────────────────────────────────────────
# .dat file parser
# ──────────────────────────────────────────────────────────────────────────────

# Column indices in the data rows.
# APC PER3 columns (0-indexed):
#  0: V (mph)  1: J  2: Pe  3: Ct  4: Cp
#  5: PWR (Hp)  6: Torque (In-Lbf)  7: Thrust (Lbf)
#  8: PWR (W)   9: Torque (N-m)     10: Thrust (N)
#  11: THR/PWR  12: Mach  13: Reyn  14: FOM
_COL_J = 1
_COL_PE = 2
_COL_CT = 3
_COL_CP = 4
_COL_PWR_W = 8
_COL_TORQUE_NM = 9
_COL_THRUST_N = 10


def parse_apc_dat_file(path: Path) -> ParsedPropFile:
    """Parse one APC PER3 .dat file and return a ParsedPropFile.

    Diameter, pitch, and variant are read from the file header (line 1),
    not the filename. This correctly handles:
    - Decimal-without-dot filenames (PER3_105x45 → 10.5 × 4.5)
    - Variant suffixes (PER3_10x10E → variant='E')

    Falls back to filename parsing if the header line cannot be parsed.

    Raises ValueError if neither header nor filename yield a valid size.
    """
    text = path.read_text(encoding="ascii", errors="replace")
    lines = text.splitlines()

    diameter_in: float | None = None
    pitch_in: float | None = None
    variant: str = ""
    source_version: str | None = None
    rpm_blocks: list[RpmBlock] = []
    current_block: RpmBlock | None = None
    in_data_section = False  # True after we've passed the unit-header row
    header_parsed = False

    for line in lines:
        stripped = line.strip()

        # ── Header line 1: canonical designation ────────────────────────────
        if not header_parsed and diameter_in is None:
            result = parse_header_designation(line)
            if result is not None:
                diameter_in, pitch_in, variant = result
                header_parsed = True

        # ── Version string ───────────────────────────────────────────────────
        if source_version is None:
            m_ver = re.search(r"(v\d{4}-\d{2,4})", stripped)
            if m_ver:
                source_version = m_ver.group(1)

        # ── RPM block start ──────────────────────────────────────────────────
        m_rpm = re.match(r"PROP\s+RPM\s*=\s*(\d+)", stripped, re.IGNORECASE)
        if m_rpm:
            current_block = RpmBlock(rpm=int(m_rpm.group(1)))
            rpm_blocks.append(current_block)
            in_data_section = False
            continue

        if current_block is None:
            continue

        # ── Unit header row signals start of data ────────────────────────────
        if not in_data_section:
            if stripped.startswith("(mph)"):
                in_data_section = True
            continue

        # ── Blank line ends a data block ─────────────────────────────────────
        if not stripped:
            in_data_section = False
            continue

        # ── Skip column-header rows (contain letters) ─────────────────────────
        if re.search(r"[A-Za-z]", stripped):
            continue

        # ── Parse data row ────────────────────────────────────────────────────
        parts = stripped.split()
        if len(parts) < 11:
            continue

        try:
            j = float(parts[_COL_J])
            pe = float(parts[_COL_PE])
            ct = float(parts[_COL_CT])
            cp = float(parts[_COL_CP])
            pwr_w = float(parts[_COL_PWR_W])
            torque_nm = float(parts[_COL_TORQUE_NM])
            thrust_n = float(parts[_COL_THRUST_N])
        except (ValueError, IndexError):
            logger.warning("Could not parse data row in %s: %r", path.name, stripped)
            continue

        current_block.samples.append(
            {
                "J": round(j, 6),
                "Pe": round(pe, 6),
                "Ct": round(ct, 6),
                "Cp": round(cp, 6),
                "PWR_W": round(pwr_w, 4),
                "Torque_Nm": round(torque_nm, 6),
                "Thrust_N": round(thrust_n, 4),
            }
        )

    # ── Fallback: parse from filename if header failed ────────────────────────
    if diameter_in is None:
        result_fn = parse_filename(path.name)
        if result_fn is None:
            raise ValueError(f"Cannot parse diameter/pitch from header or filename: {path.name}")
        diameter_in, pitch_in = result_fn
        variant = ""
        logger.warning(
            "Header parse failed for %s; fell back to filename (dia=%.1f, pitch=%.1f)",
            path.name,
            diameter_in,
            pitch_in,
        )

    assert diameter_in is not None
    assert pitch_in is not None

    return ParsedPropFile(
        diameter_in=diameter_in,
        pitch_in=pitch_in,
        variant=variant,
        source_version=source_version,
        rpm_blocks=rpm_blocks,
    )


# ──────────────────────────────────────────────────────────────────────────────
# Snapshot record builder
# ──────────────────────────────────────────────────────────────────────────────


def build_snapshot_record(parsed: ParsedPropFile, filename: str) -> dict[str, Any]:
    """Build a snapshot dict for one propeller.

    The 'polars' key holds the per-RPM sample tables — this is the full
    data payload that the DB importer will use.

    The 'specs.variant' field carries the variant suffix (e.g. "E", "M-JK")
    or empty string for standard props.
    """
    # Build a clean size label from the actual (header-parsed) values
    dia_str = f"{parsed.diameter_in:g}"  # "9", "10.5"
    pitch_str = f"{parsed.pitch_in:g}"  # "6", "4.5"
    size_label = f"{dia_str}x{pitch_str}"
    variant = parsed.variant or ""

    # Full designation: "9x6", "10.5x4.5", "10x10E", "10x10M-JK"
    designation = f"{size_label}{variant}"

    name = f"APC {designation}"
    # Slug for model_ref: replace dots and parentheses for URL-safety
    slug = designation.replace(".", "p").replace("(", "").replace(")", "")

    polars = [
        {
            "rpm": block.rpm,
            "samples": block.samples,
        }
        for block in parsed.rpm_blocks
    ]

    return {
        "manufacturer": MANUFACTURER,
        "name": name,
        "component_type": "propeller",
        "model_ref": f"apc/{slug}",
        "source_url": f"{SOURCE_URL_BASE}/PER3_{Path(filename).stem}.dat",
        "source_version": parsed.source_version or "unknown",
        "specs": {
            "diameter_in": parsed.diameter_in,
            "pitch_in": parsed.pitch_in,
            "variant": variant,
            "blades": 2,  # APC standard 2-blade; no other info in file
        },
        "polars": polars,
    }


# ──────────────────────────────────────────────────────────────────────────────
# Batch parse
# ──────────────────────────────────────────────────────────────────────────────


def parse_all(raw_dir: Path = RAW_DIR) -> tuple[list[dict[str, Any]], list[str], list[str]]:
    """Parse all PER3_*.dat files in raw_dir (recursively).

    Returns (records, fetched_names, skipped_names).
    Logs counts and reasons for any skipped files.
    """
    # Search recursively — APC archive uses PERFILES2/ and PERFILES2-MARINE/ subdirs
    dat_files = sorted(raw_dir.rglob("PER3_*.dat"))
    if not dat_files:
        logger.warning("No PER3_*.dat files found in %s", raw_dir)
        return [], [], []

    records: list[dict[str, Any]] = []
    fetched: list[str] = []
    skipped: list[str] = []
    skip_reasons: dict[str, str] = {}

    for path in dat_files:
        if path.stat().st_size == 0:
            reason = "empty file"
            logger.warning("Skipping %s: %s", path.name, reason)
            skipped.append(path.name)
            skip_reasons[path.name] = reason
            continue

        try:
            parsed = parse_apc_dat_file(path)
        except Exception as exc:
            reason = f"parse error: {exc}"
            logger.error("Failed to parse %s: %s", path.name, exc)
            skipped.append(path.name)
            skip_reasons[path.name] = reason
            continue

        if not parsed.rpm_blocks:
            reason = "no RPM blocks"
            logger.warning("No RPM blocks found in %s — skipping", path.name)
            skipped.append(path.name)
            skip_reasons[path.name] = reason
            continue

        total_samples = sum(len(b.samples) for b in parsed.rpm_blocks)
        record = build_snapshot_record(parsed, path.name)
        records.append(record)
        fetched.append(path.name)
        logger.info(
            'Parsed %s: dia=%.4g" pitch=%.4g" variant=%r  %d RPM blocks, %d samples',
            path.name,
            parsed.diameter_in,
            parsed.pitch_in,
            parsed.variant,
            len(parsed.rpm_blocks),
            total_samples,
        )

    if skipped:
        logger.warning(
            "Skipped %d file(s):\n%s",
            len(skipped),
            "\n".join(f"  {name}: {skip_reasons.get(name, 'unknown')}" for name in skipped),
        )

    logger.info("parse_all complete: %d parsed, %d skipped", len(fetched), len(skipped))
    return records, fetched, skipped


def write_snapshot(
    records: list[dict[str, Any]],
    output_path: Path = OUTPUT_PATH,
) -> None:
    """Atomically write the snapshot as gzip JSON.

    Output file extension should be .json.gz; the file is written atomically
    via a .tmp sibling to avoid partial-write corruption.
    """
    output_path.parent.mkdir(parents=True, exist_ok=True)
    tmp = output_path.with_suffix(".tmp.gz")
    payload = json.dumps(records, indent=2, ensure_ascii=False).encode("utf-8")
    with gzip.open(tmp, "wb") as fh:
        fh.write(payload)
    tmp.replace(output_path)
    logger.info("Wrote %d records to %s (gzip)", len(records), output_path)


def main() -> None:
    import argparse

    logging.basicConfig(
        level=logging.INFO,
        format="%(levelname)s: %(message)s",
        stream=sys.stderr,
    )

    parser = argparse.ArgumentParser(description="Parse APC PER3 .dat files → gzip JSON snapshot")
    parser.add_argument(
        "--raw-dir",
        type=Path,
        default=RAW_DIR,
        help="Directory containing PER3_*.dat files (default: data/apc_raw/)",
    )
    parser.add_argument(
        "--output",
        type=Path,
        default=OUTPUT_PATH,
        help="Output gzip path (default: data/cots/apc_props.json.gz)",
    )
    args = parser.parse_args()

    if not args.raw_dir.exists():
        logger.error(
            "Raw directory not found: %s\nExtract APC PER3 files with: 7zz x -y -o%s <zipx-file>",
            args.raw_dir,
            args.raw_dir,
        )
        sys.exit(1)

    records, fetched, skipped = parse_all(args.raw_dir)
    if not records:
        logger.error("No records parsed — check raw files and parser logs")
        sys.exit(1)

    print(f"\nParsed {len(fetched)} props, skipped {len(skipped)} props")
    if skipped:
        print(f"\nSkipped files ({len(skipped)}):")
        for name in skipped:
            print(f"  SKIP  {name}")

    write_snapshot(records, args.output)
    print(f"\nSnapshot written to: {args.output}")


if __name__ == "__main__":
    main()
