#!/usr/bin/env python3
"""Fetch APC PER3 .dat files for the catalog-relevant prop set.

Usage:
    poetry run python scripts/fetch_apc_props.py [--output-dir <path>]

Downloads from https://www.apcprop.com/files/PER3_<DxP>.dat for the prop
sizes referenced by the D-Power AL/D-Drive catalog recommendations.

Output files go to data/apc_raw/ (gitignored).  After fetching, run:
    poetry run python scripts/parse_apc_props.py

to regenerate data/cots/apc_props.json.

Notes:
  - Rate-limited to 5 req/s (0.2s between downloads).
  - APC raw .dat files are license-free; only the factual snapshot is committed.
  - If a prop is not in the APC catalog, it is logged as SKIP and omitted.
"""

from __future__ import annotations

import logging
import sys
import time
from pathlib import Path
from urllib.request import urlopen, Request
from urllib.error import URLError, HTTPError

logger = logging.getLogger(__name__)

REPO_ROOT = Path(__file__).resolve().parent.parent
DEFAULT_OUTPUT_DIR = REPO_ROOT / "data" / "apc_raw"

APC_BASE_URL = "https://www.apcprop.com/files"

# Catalog-relevant prop sizes (D-Power AL/D-Drive recommended props).
# Format: "DxP" where D = diameter (in), P = pitch (in).
# Half-integer pitches are encoded as decimals (e.g. "9x4.5").
CATALOG_PROPS = [
    # 7" (common sport and trainer small props)
    "7x4",
    "7x5",
    "7x6",
    # 8" (mid-small props)
    "8x4",
    "8x4.5",
    "8x5",
    "8x6",
    # 9" (mid-range)
    "9x4.5",
    "9x5",
    "9x6",
    "9x7",
    # 10"
    "10x5",
    "10x7",
    # 11"
    "11x5.5",
    "11x7",
    # 12"
    "12x6",
    "12x8",
    # 13"
    "13x6",
    "13x8",
    # 14"
    "14x7",
    "14x10",
    # 15"
    "15x10",
    # 16"
    "16x8",
    # 17"
    "17x10",
    "17x11",
    "17x12",
    # 18"
    "18x8",
    # 19"
    "19x8",
    # 20"
    "20x13",
]

_HEADERS = {
    "User-Agent": "da3Dalus-apc-fetcher/1.0 (catalog import; +https://github.com/szymansk/da3Dalus)",
}


def fetch_one(size: str, output_dir: Path) -> bool:
    """Fetch one PER3 file.  Returns True if successful, False if not available."""
    filename = f"PER3_{size}.dat"
    url = f"{APC_BASE_URL}/{filename}"
    out = output_dir / filename

    try:
        req = Request(url, headers=_HEADERS)
        with urlopen(req, timeout=15) as resp:
            data = resp.read()

        if len(data) < 100:  # file must be non-trivially sized
            logger.warning("SKIP: %s — response too short (%d bytes)", size, len(data))
            return False

        output_dir.mkdir(parents=True, exist_ok=True)
        out.write_bytes(data)
        logger.info("OK:   %s  (%d bytes)", filename, len(data))
        return True

    except HTTPError as exc:
        if exc.code == 404:
            logger.info("SKIP: %s — not in APC catalog (404)", size)
        else:
            logger.warning("SKIP: %s — HTTP %d", size, exc.code)
        return False
    except URLError as exc:
        logger.error("SKIP: %s — network error: %s", size, exc.reason)
        return False


def fetch_all(
    props: list[str] = CATALOG_PROPS,
    output_dir: Path = DEFAULT_OUTPUT_DIR,
    delay_s: float = 0.2,
) -> tuple[list[str], list[str]]:
    """Fetch all catalog props.  Returns (fetched_names, skipped_names)."""
    fetched: list[str] = []
    skipped: list[str] = []

    for size in props:
        ok = fetch_one(size, output_dir)
        if ok:
            fetched.append(size)
        else:
            skipped.append(size)
        time.sleep(delay_s)

    return fetched, skipped


def main() -> None:
    import argparse

    logging.basicConfig(
        level=logging.INFO,
        format="%(levelname)s: %(message)s",
        stream=sys.stderr,
    )

    parser = argparse.ArgumentParser(description="Fetch APC PER3 .dat files")
    parser.add_argument(
        "--output-dir",
        type=Path,
        default=DEFAULT_OUTPUT_DIR,
        help=f"Output directory (default: {DEFAULT_OUTPUT_DIR})",
    )
    args = parser.parse_args()

    print(f"Fetching {len(CATALOG_PROPS)} catalog props from apcprop.com ...")
    fetched, skipped = fetch_all(output_dir=args.output_dir)

    print(f"\nFetched: {len(fetched)}")
    for name in fetched:
        print(f"  OK    {name}")
    print(f"\nSkipped: {len(skipped)} (not in APC catalog or network unavailable)")
    for name in skipped:
        print(f"  SKIP  {name}")

    print(f"\nRaw files in: {args.output_dir}")
    print("Next: poetry run python scripts/parse_apc_props.py")


if __name__ == "__main__":
    main()
