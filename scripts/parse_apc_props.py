#!/usr/bin/env python3
"""Parse APC PER3 propeller performance .dat files → data/cots/apc_props.json.

Usage:
    poetry run python scripts/parse_apc_props.py [--raw-dir <path>] [--output <path>]

Raw APC PER3 .dat files must be in:
    data/apc_raw/   (default; gitignored)

The script writes (or overwrites) data/cots/apc_props.json with a list of
propeller records in the snapshot format — the durable reimport source.

Raw .dat files contain facts (measured performance data); only the extracted
numbers are committed. The source .dat files are gitignored because:
  - APC license allows use; re-hosting the full file set is unnecessary.
  - The committed snapshot (factual numbers) is sufficient to reproduce the DB.

APC PER3 file format reference:
  Header block: propeller name, version string (v2022-xxxx), date.
  Repeated RPM blocks:
      PROP RPM = <N>
      Column header row (V, J, Pe, Ct, Cp, PWR, Torque, Thrust, …)
      Unit row (mph, Adv_Ratio, -, -, -, Hp, In-Lbf, Lbf, W, N-m, N, …)
      Data rows (whitespace-delimited floats)
      (blank line terminates the block)

We extract SI columns: PWR (W), Torque (N-m), Thrust (N) plus dimensionless J,
Ct, Cp, Pe.  Imperial columns (Hp, In-Lbf, Lbf) are discarded.
"""

from __future__ import annotations

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
OUTPUT_PATH = REPO_ROOT / "data" / "cots" / "apc_props.json"

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
    source_version: str | None
    rpm_blocks: list[RpmBlock] = field(default_factory=list)


# ──────────────────────────────────────────────────────────────────────────────
# Filename parser
# ──────────────────────────────────────────────────────────────────────────────


def parse_filename(filename: str) -> tuple[float, float] | None:
    """Extract (diameter_in, pitch_in) from a PER3 filename.

    Supports:
      PER3_7x4.dat    → (7.0, 4.0)
      PER3_9x4.5.dat  → (9.0, 4.5)
      PER3_11x5.5.dat → (11.0, 5.5)

    Returns None if the name doesn't match the expected pattern.
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

    Raises ValueError if the filename cannot be parsed.
    """
    result = parse_filename(path.name)
    if result is None:
        raise ValueError(f"Cannot parse diameter/pitch from filename: {path.name}")
    diameter_in, pitch_in = result

    text = path.read_text(encoding="ascii", errors="replace")
    lines = text.splitlines()

    source_version: str | None = None
    rpm_blocks: list[RpmBlock] = []
    current_block: RpmBlock | None = None
    in_data_section = False  # True after we've passed the unit-header row

    for line in lines:
        stripped = line.strip()

        # Extract version string from header (e.g. "v2022-0915")
        if source_version is None:
            m_ver = re.search(r"(v\d{4}-\d{2,4})", stripped)
            if m_ver:
                source_version = m_ver.group(1)

        # Start of a new RPM block
        m_rpm = re.match(r"PROP\s+RPM\s*=\s*(\d+)", stripped, re.IGNORECASE)
        if m_rpm:
            current_block = RpmBlock(rpm=int(m_rpm.group(1)))
            rpm_blocks.append(current_block)
            in_data_section = False
            continue

        if current_block is None:
            continue

        # The unit row starts with "(mph)" — next lines are data
        if not in_data_section:
            if stripped.startswith("(mph)"):
                in_data_section = True
            continue

        # Blank line → end of this RPM block's data
        if not stripped:
            in_data_section = False
            continue

        # Skip lines that look like column headers (contain letters)
        if re.search(r"[A-Za-z]", stripped):
            continue

        # Parse data row
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

    return ParsedPropFile(
        diameter_in=diameter_in,
        pitch_in=pitch_in,
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
    """
    # Derive a clean size label like "9x6" from the filename
    m = re.match(r"PER3_(\d+x[\d.]+)\.dat", filename)
    size_label = m.group(1) if m else f"{parsed.diameter_in:.0f}x{parsed.pitch_in}"
    name = f"APC {size_label}"
    slug = size_label.replace(".", "p")  # "9x4.5" → "9x4p5"

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
        "source_url": f"{SOURCE_URL_BASE}/PER3_{size_label}.dat",
        "source_version": parsed.source_version or "unknown",
        "specs": {
            "diameter_in": parsed.diameter_in,
            "pitch_in": parsed.pitch_in,
            "blades": 2,  # APC standard 2-blade; no other info in file
        },
        "polars": polars,
    }


# ──────────────────────────────────────────────────────────────────────────────
# Batch parse
# ──────────────────────────────────────────────────────────────────────────────


def parse_all(raw_dir: Path = RAW_DIR) -> tuple[list[dict[str, Any]], list[str], list[str]]:
    """Parse all PER3_*.dat files in raw_dir.

    Returns (records, fetched_names, skipped_names).
    """
    dat_files = sorted(raw_dir.glob("PER3_*.dat"))
    if not dat_files:
        logger.warning("No PER3_*.dat files found in %s", raw_dir)
        return [], [], []

    records: list[dict[str, Any]] = []
    fetched: list[str] = []
    skipped: list[str] = []

    for path in dat_files:
        if path.stat().st_size == 0:
            logger.warning("Skipping empty file: %s", path.name)
            skipped.append(path.name)
            continue

        try:
            parsed = parse_apc_dat_file(path)
        except Exception as exc:
            logger.error("Failed to parse %s: %s", path.name, exc)
            skipped.append(path.name)
            continue

        if not parsed.rpm_blocks:
            logger.warning("No RPM blocks found in %s — skipping", path.name)
            skipped.append(path.name)
            continue

        total_samples = sum(len(b.samples) for b in parsed.rpm_blocks)
        record = build_snapshot_record(parsed, path.name)
        records.append(record)
        fetched.append(path.name)
        logger.info(
            "Parsed %s: %d RPM blocks, %d samples",
            path.name,
            len(parsed.rpm_blocks),
            total_samples,
        )

    return records, fetched, skipped


def write_snapshot(
    records: list[dict[str, Any]],
    output_path: Path = OUTPUT_PATH,
) -> None:
    """Atomically write the snapshot JSON."""
    output_path.parent.mkdir(parents=True, exist_ok=True)
    tmp = output_path.with_suffix(".tmp.json")
    tmp.write_text(json.dumps(records, indent=2, ensure_ascii=False), encoding="utf-8")
    tmp.replace(output_path)
    logger.info("Wrote %d records to %s", len(records), output_path)


def main() -> None:
    import argparse

    logging.basicConfig(
        level=logging.INFO,
        format="%(levelname)s: %(message)s",
        stream=sys.stderr,
    )

    parser = argparse.ArgumentParser(description="Parse APC PER3 .dat files → JSON snapshot")
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
        help="Output JSON path (default: data/cots/apc_props.json)",
    )
    args = parser.parse_args()

    if not args.raw_dir.exists():
        logger.error(
            "Raw directory not found: %s\n"
            "Download APC PER3 files (e.g. with scripts/fetch_apc_props.py) first.",
            args.raw_dir,
        )
        sys.exit(1)

    records, fetched, skipped = parse_all(args.raw_dir)
    if not records:
        logger.error("No records parsed — check raw files and parser logs")
        sys.exit(1)

    print(f"\nParsed {len(fetched)} props:")
    for name in fetched:
        print(f"  OK  {name}")
    if skipped:
        print(f"\nSkipped {len(skipped)} props:")
        for name in skipped:
            print(f"  SKIP  {name}")

    write_snapshot(records, args.output)
    print(f"\nSnapshot written to: {args.output}")


if __name__ == "__main__":
    main()
