#!/usr/bin/env python3
"""Seed propeller polars as COTS components (gh-1012).

Usage:
    poetry run python scripts/seed_propeller_components.py [--dry-run]

Mirrors every row in ``propeller_polars`` into the generic ``components``
catalog as a ``ComponentModel`` of ``component_type='propeller'``, keyed on
the shared ``model_ref``. This makes all APC propellers selectable in the
component picker / BoM.

The seed is idempotent: re-runs upsert by ``model_ref`` and never clobber a
user-entered ``mass_g``. Run ``scripts/import_apc_props.py`` first so the
polars exist.

Options:
    --dry-run   Report what would change without writing to the DB.
"""

from __future__ import annotations

import argparse
import logging
import sys
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(REPO_ROOT))

from app.db.session import SessionLocal  # noqa: E402
from app.services.prop_component_seed import seed_propeller_components  # noqa: E402


def main() -> None:
    logging.basicConfig(
        level=logging.INFO,
        format="%(levelname)s: %(message)s",
        stream=sys.stderr,
    )

    parser = argparse.ArgumentParser(
        description="Seed propeller polars as COTS components into the DB"
    )
    parser.add_argument(
        "--dry-run",
        action="store_true",
        default=False,
        help="Report what would change without committing to the DB",
    )
    args = parser.parse_args()

    db = SessionLocal()
    try:
        result = seed_propeller_components(db)
        if args.dry_run:
            db.rollback()
            print(f"DRY RUN — no DB writes. Would have: {result}")
        else:
            db.commit()
            print(f"Seed complete: {result}")
    except Exception:
        db.rollback()
        raise
    finally:
        db.close()


if __name__ == "__main__":
    main()
