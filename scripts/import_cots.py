#!/usr/bin/env python3
"""Import COTS components from a versioned JSON snapshot into the database.

Usage:
    poetry run python scripts/import_cots.py [SNAPSHOT] [--force]

Arguments:
    SNAPSHOT    Path to the JSON snapshot (default: data/cots/dpower.json)
    --force     Overwrite existing rows even if they appear unchanged

Mirrors scripts/backfill_airfoil_low_re.py: single transaction, result
report, no network required. The committed snapshot is the durable reimport
source — no PDFs or network access needed.
"""

from __future__ import annotations

import argparse
import json
import logging
import sys
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(REPO_ROOT))

from app.db.session import SessionLocal  # noqa: E402
from app.services.cots_import import import_snapshot  # noqa: E402

DEFAULT_SNAPSHOT = REPO_ROOT / "data" / "cots" / "dpower.json"


def main() -> None:
    logging.basicConfig(
        level=logging.INFO,
        format="%(levelname)s: %(message)s",
        stream=sys.stderr,
    )

    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument(
        "snapshot",
        nargs="?",
        default=str(DEFAULT_SNAPSHOT),
        help="Path to the JSON snapshot file",
    )
    parser.add_argument(
        "--force",
        action="store_true",
        help="Overwrite existing rows even if they appear unchanged",
    )
    args = parser.parse_args()

    snapshot_path = Path(args.snapshot)
    if not snapshot_path.exists():
        print(f"ERROR: snapshot not found: {snapshot_path}", file=sys.stderr)
        sys.exit(1)

    records = json.loads(snapshot_path.read_text(encoding="utf-8"))
    print(f"Loaded {len(records)} records from {snapshot_path}")

    db = SessionLocal()
    try:
        result = import_snapshot(db, records, force=args.force)
        db.commit()
    except Exception:
        db.rollback()
        logging.exception("Import failed — all changes rolled back")
        sys.exit(1)
    finally:
        db.close()

    print(
        f"Done: imported={result.imported}, updated={result.updated}, "
        f"skipped={result.skipped}, errors={len(result.errors)}"
    )
    if result.errors:
        print("Errors:", file=sys.stderr)
        for err in result.errors:
            print(f"  - {err}", file=sys.stderr)
        sys.exit(1)


if __name__ == "__main__":
    main()
