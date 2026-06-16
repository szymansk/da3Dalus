#!/usr/bin/env python3
"""Enrich the APC snapshot with PE0 weight/inertia/geometry (gh-1000).

Usage:
    poetry run python scripts/enrich_apc_snapshot_pe0.py \
        [--pe0-dir data/apc_raw/PE0-FILES_WEB] \
        [--snapshot data/cots/apc_props.json.gz]

Reads every ``*.PE0`` in ``--pe0-dir``, matches each to the existing snapshot
record by diameter × pitch × variant, and writes weight_g / inertia_kg_m2 /
geometry into the snapshot (atomically, gzip). Unmatched PE0 rows and unit
warnings are logged and reported — never silently dropped.

The raw PE0 files are local/gitignored; the committed snapshot is the durable
reimport source.
"""

from __future__ import annotations

import argparse
import gzip
import json
import logging
import sys
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(REPO_ROOT))

from app.services.prop_polar_enrich import enrich_records_with_pe0  # noqa: E402
from scripts.parse_apc_pe0 import parse_pe0_file  # noqa: E402

DEFAULT_PE0_DIR = REPO_ROOT / "data" / "apc_raw" / "PE0-FILES_WEB"
DEFAULT_SNAPSHOT = REPO_ROOT / "data" / "cots" / "apc_props.json.gz"

logger = logging.getLogger(__name__)


def _load_snapshot(path: Path) -> list[dict]:
    if path.suffix == ".gz":
        with gzip.open(path, "rt", encoding="utf-8") as fh:
            return json.loads(fh.read())
    return json.loads(path.read_text(encoding="utf-8"))


def _write_snapshot(path: Path, records: list[dict]) -> None:
    tmp = path.with_suffix(".tmp.gz")
    with gzip.open(tmp, "wt", encoding="utf-8") as fh:
        fh.write(json.dumps(records, indent=2))
    tmp.replace(path)


def main() -> None:
    logging.basicConfig(level=logging.INFO, format="%(levelname)s: %(message)s", stream=sys.stderr)

    parser = argparse.ArgumentParser(description="Enrich APC snapshot with PE0 weight/inertia")
    parser.add_argument("--pe0-dir", type=Path, default=DEFAULT_PE0_DIR)
    parser.add_argument("--snapshot", type=Path, default=DEFAULT_SNAPSHOT)
    parser.add_argument("--dry-run", action="store_true", default=False)
    args = parser.parse_args()

    if not args.pe0_dir.is_dir():
        print(f"ERROR: PE0 dir not found: {args.pe0_dir}", file=sys.stderr)
        sys.exit(1)
    if not args.snapshot.exists():
        print(f"ERROR: snapshot not found: {args.snapshot}", file=sys.stderr)
        sys.exit(1)

    pe0_files = sorted(args.pe0_dir.rglob("*.PE0"))
    if not pe0_files:
        print(f"ERROR: no .PE0 files under {args.pe0_dir}", file=sys.stderr)
        sys.exit(1)

    pe0_list = []
    parse_errors = 0
    for f in pe0_files:
        try:
            pe0_list.append(parse_pe0_file(f))
        except ValueError as exc:
            parse_errors += 1
            logger.warning("skipping %s: %s", f.name, exc)

    records = _load_snapshot(args.snapshot)
    result = enrich_records_with_pe0(records, pe0_list)

    enriched = sum(1 for r in records if (r.get("specs") or {}).get("weight_g") is not None)
    print(
        f"PE0 parsed={len(pe0_list)} (parse_errors={parse_errors}) | {result} | "
        f"records_with_weight={enriched}/{len(records)}"
    )
    if result.unmatched_names:
        print(f"Unmatched PE0 (first 10): {result.unmatched_names[:10]}")

    if args.dry_run:
        print("DRY RUN — snapshot not written.")
        return

    _write_snapshot(args.snapshot, records)
    print(f"Snapshot enriched and written: {args.snapshot}")


if __name__ == "__main__":
    main()
