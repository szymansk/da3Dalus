#!/usr/bin/env python3
"""Import APC propeller polars from snapshot → database.

Usage:
    poetry run python scripts/import_apc_props.py [--snapshot <path>] [--force]

Reads the versioned factual snapshot (data/cots/apc_props.json.gz by default) and
upserts propeller polar records into the database via the idempotent
import service.

This script is the reimport source: the snapshot is the durable truth; no
network access, no raw .dat files required after the snapshot is committed.

Options:
    --snapshot PATH   Path to apc_props.json.gz (default: data/cots/apc_props.json.gz)
    --force           Overwrite existing rows even if source_version matches
    --dry-run         Parse snapshot and report what would change; no DB writes
"""

from __future__ import annotations

import argparse
import logging
import sys
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(REPO_ROOT))

from app.db.session import SessionLocal  # noqa: E402
from app.services.prop_polar_import import import_prop_polars, load_snapshot  # noqa: E402

DEFAULT_SNAPSHOT = REPO_ROOT / "data" / "cots" / "apc_props.json.gz"


def main() -> None:
    logging.basicConfig(
        level=logging.INFO,
        format="%(levelname)s: %(message)s",
        stream=sys.stderr,
    )

    parser = argparse.ArgumentParser(description="Import APC propeller polars into the DB")
    parser.add_argument(
        "--snapshot",
        type=Path,
        default=DEFAULT_SNAPSHOT,
        help=f"Path to apc_props.json.gz (default: {DEFAULT_SNAPSHOT})",
    )
    parser.add_argument(
        "--force",
        action="store_true",
        default=False,
        help="Overwrite existing rows even if source_version matches",
    )
    parser.add_argument(
        "--dry-run",
        action="store_true",
        default=False,
        help="Report what would change without writing to the DB",
    )
    args = parser.parse_args()

    if not args.snapshot.exists():
        print(f"ERROR: Snapshot not found: {args.snapshot}", file=sys.stderr)
        print(
            "Run scripts/parse_apc_props.py first to generate the snapshot,\n"
            "or fetch the committed snapshot via git pull.",
            file=sys.stderr,
        )
        sys.exit(1)

    records = load_snapshot(args.snapshot)
    print(f"Snapshot: {args.snapshot.name}  ({len(records)} props)")

    if args.dry_run:
        print("\nDry run — no DB writes.")
        for r in records:
            polars = r.get("polars", [])
            total = sum(len(p.get("samples", [])) for p in polars)
            variant = r.get("specs", {}).get("variant", "")
            variant_str = f"  variant={variant!r}" if variant else ""
            print(
                f'  {r["name"]:25s}  diameter={r["specs"].get("diameter_in")}"  '
                f'pitch={r["specs"].get("pitch_in")}"'
                f"{variant_str}  "
                f"{len(polars)} RPM blocks  {total} samples"
            )
        return

    db = SessionLocal()
    try:
        result = import_prop_polars(db, records, force=args.force)
        db.commit()
        print(f"\nDone: {result}")
        if result.errors:
            print(f"\nErrors ({len(result.errors)}):")
            for err in result.errors:
                print(f"  {err}")
        sys.exit(1 if result.errors else 0)
    except Exception:
        db.rollback()
        logging.exception("Import failed — rolled back")
        sys.exit(1)
    finally:
        db.close()


if __name__ == "__main__":
    main()
