"""Coverage test for clone_aeroplane_subgraph (gh-904).

This test introspects the SQLAlchemy metadata to find every table that has
a (direct OR transitive) FK path to the ``aeroplanes`` table, then asserts
that each such table is listed in either ``CLONED_TABLES`` or
``EXCLUDED_TABLES`` in the clone service.

Purpose: if a future migration adds a new aeroplane-related table and the
developer forgets to update the clone service, this test fails — preventing
silent data loss on clone operations.
"""

from __future__ import annotations

import pytest
from sqlalchemy import MetaData, create_engine
from sqlalchemy.pool import StaticPool

from app.db.base import Base

# Import all models to ensure they are registered with Base.metadata.
import app.models.aeroplanemodel  # noqa: F401
import app.models.airfoil  # noqa: F401
import app.models.airfoil_low_re  # noqa: F401
import app.models.analysismodels  # noqa: F401
# avl_geometry_events is event-listener code, not a model with its own table
import app.models.avl_geometry_file  # noqa: F401
import app.models.component  # noqa: F401
import app.models.component_tree  # noqa: F401
import app.models.component_type  # noqa: F401
import app.models.computation_config  # noqa: F401
import app.models.construction_part  # noqa: F401
import app.models.construction_plan  # noqa: F401
import app.models.flight_envelope_model  # noqa: F401
import app.models.flightprofilemodel  # noqa: F401
import app.models.mission_objective  # noqa: F401
import app.models.mission_preset  # noqa: F401
import app.models.stability_result  # noqa: F401
import app.models.tessellation_cache  # noqa: F401

from app.services.aeroplane_clone_service import CLONED_TABLES, EXCLUDED_TABLES


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------


def _build_fk_graph(metadata: MetaData) -> dict[str, set[str]]:
    """Return a mapping: table_name → set of table names it has FKs TO."""
    graph: dict[str, set[str]] = {}
    for table in metadata.tables.values():
        targets: set[str] = set()
        for fk in table.foreign_keys:
            targets.add(fk.column.table.name)
        graph[table.name] = targets
    return graph


def _tables_with_transitive_fk_to(
    root: str, fk_graph: dict[str, set[str]]
) -> set[str]:
    """BFS/DFS: collect all tables that can reach *root* via FK edges.

    We walk the graph in the direction «this table has an FK that points to
    that table», collecting every table from which *root* is reachable.
    """
    # Invert the graph: for each table T, collect all tables that point TO T.
    reverse: dict[str, set[str]] = {t: set() for t in fk_graph}
    for src, targets in fk_graph.items():
        for tgt in targets:
            if tgt in reverse:
                reverse[tgt].add(src)

    # BFS from root
    visited: set[str] = set()
    queue = [root]
    while queue:
        node = queue.pop()
        if node in visited:
            continue
        visited.add(node)
        queue.extend(reverse.get(node, []))

    # Exclude the root itself — the test is about *other* tables
    visited.discard(root)
    return visited


# ---------------------------------------------------------------------------
# Test
# ---------------------------------------------------------------------------


class TestCloneCoverage:
    """Every table with a transitive FK to aeroplanes must be in one of the
    two registry sets defined in the clone service."""

    def test_all_aeroplane_related_tables_are_classified(self):
        """Introspect SQLAlchemy metadata; assert complete coverage.

        If this test fails, a table linked to aeroplanes is not listed in
        either CLONED_TABLES or EXCLUDED_TABLES.  Add it to the appropriate
        set in aeroplane_clone_service.py with a reason.

        KNOWN BLIND SPOT — STRING-FK TABLES:
        This BFS introspection walks SQLAlchemy ``ForeignKey`` objects.
        Tables whose aeroplane reference is stored as a plain ``String``
        column (no SQLAlchemy ForeignKey constraint) are INVISIBLE to this
        traversal and will NOT be flagged by this test even if unclassified.
        Those tables must be added to CLONED_TABLES or EXCLUDED_TABLES
        manually.  Current string-FK tables (as of gh-904):
          • ``component_tree``   (aeroplane_id = VARCHAR/UUID, in CLONED_TABLES)
          • ``construction_plans`` (soft string FK, in EXCLUDED_TABLES)
          • ``construction_parts`` (string aeroplane_id, in EXCLUDED_TABLES)
        """
        # Build an in-memory SQLite and create all tables so the metadata is
        # fully populated (foreign_keys are resolved).
        engine = create_engine(
            "sqlite://",
            connect_args={"check_same_thread": False},
            poolclass=StaticPool,
        )
        Base.metadata.create_all(bind=engine)
        metadata = Base.metadata

        fk_graph = _build_fk_graph(metadata)
        related_tables = _tables_with_transitive_fk_to("aeroplanes", fk_graph)

        # Include the root itself — it must also be in CLONED_TABLES.
        all_tables_to_classify = related_tables | {"aeroplanes"}

        classified = set(CLONED_TABLES) | set(EXCLUDED_TABLES.keys())

        unclassified = all_tables_to_classify - classified
        assert not unclassified, (
            "The following tables have a FK path to 'aeroplanes' but are not "
            "listed in CLONED_TABLES or EXCLUDED_TABLES in "
            "aeroplane_clone_service.py.  Add each table to the appropriate "
            "set with a reason string.\n\n"
            f"Unclassified tables: {sorted(unclassified)}"
        )

    def test_cloned_and_excluded_are_disjoint(self):
        """A table cannot be in both CLONED_TABLES and EXCLUDED_TABLES."""
        overlap = set(CLONED_TABLES) & set(EXCLUDED_TABLES.keys())
        assert not overlap, (
            f"Tables appear in both CLONED_TABLES and EXCLUDED_TABLES: {overlap}"
        )

    def test_excluded_tables_have_non_empty_reasons(self):
        """Every entry in EXCLUDED_TABLES must have a non-empty reason string."""
        empty = [t for t, reason in EXCLUDED_TABLES.items() if not reason.strip()]
        assert not empty, f"EXCLUDED_TABLES entries with empty reasons: {empty}"
