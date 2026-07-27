"""Touch Index query helpers.

All public functions accept a list of file paths and return structured dicts.
Engine is optional; if omitted a fresh engine is obtained via db.get_engine().
"""

from __future__ import annotations

import logging
from dataclasses import dataclass, field
from typing import Sequence

from sqlalchemy import text
from sqlalchemy.engine import Engine
from sqlalchemy.exc import ProgrammingError

from .db import get_engine

_log = logging.getLogger(__name__)


@dataclass
class FRImpact:
    fr_identifier: str
    fr_owner_agent_id: str
    fr_issue_id: str


@dataclass
class RegressionRisk:
    bug_identifier: str
    bug_issue_id: str


@dataclass
class BlastRadiusData:
    fr_impact_set: list[FRImpact] = field(default_factory=list)
    regression_set: list[RegressionRisk] = field(default_factory=list)
    downstream_set: list = field(default_factory=list)
    downstream_note: str = "Phase 2 dep graph not yet available"


def query_blast_radius(
    file_paths: Sequence[str],
    engine: Engine | None = None,
) -> BlastRadiusData:
    """Query the Touch Index for all three impact sets given a list of file paths."""
    if not file_paths:
        return BlastRadiusData()

    _owned = engine is None
    if _owned:
        engine = get_engine()

    paths = list(file_paths)
    with engine.connect() as conn:
        fr_impact = _query_fr_impact(conn, paths)
        regression = _query_regression(conn, paths)
        downstream = _query_downstream(conn, paths)

    if _owned:
        engine.dispose()

    return BlastRadiusData(
        fr_impact_set=fr_impact,
        regression_set=regression,
        downstream_set=downstream,
    )


def _query_fr_impact(conn, file_paths: list[str]) -> list[FRImpact]:
    try:
        rows = conn.execute(
            text(
                """
                SELECT DISTINCT fr_identifier, fr_owner_agent_id::text, fr_issue_id::text
                FROM   touch_index_fr_files
                WHERE  file_path = ANY(:paths)
                ORDER  BY fr_identifier
                """
            ),
            {"paths": file_paths},
        ).fetchall()
    except ProgrammingError as exc:
        # BTCAAAAA-41534: Touch Index tables may be missing in environments
        # where the schema hasn't been initialized yet (e.g. blast-radius
        # worker CI with a fresh Postgres service container). Treat as empty
        # so the worker reports zero blast radius instead of raising — the
        # monitor only opens auto-alerts on real errors, not on missing data.
        # Roll back the aborted transaction so the next sub-query
        # (regression, downstream) can run on a clean connection state;
        # otherwise Postgres raises `InFailedSqlTransaction` on any query
        # after an aborted statement and the worker reports issues_with_errors=1
        # even though only one of the three sub-queries is missing.
        conn.rollback()
        _log.debug("touch_index_fr_files unavailable: %s", exc)
        return []
    return [
        FRImpact(
            fr_identifier=row.fr_identifier,
            fr_owner_agent_id=row.fr_owner_agent_id,
            fr_issue_id=row.fr_issue_id,
        )
        for row in rows
    ]


def _query_regression(conn, file_paths: list[str]) -> list[RegressionRisk]:
    try:
        rows = conn.execute(
            text(
                """
                SELECT DISTINCT bug_identifier, bug_issue_id::text
                FROM   touch_index_bug_files
                WHERE  file_path = ANY(:paths)
                ORDER  BY bug_identifier
                """
            ),
            {"paths": file_paths},
        ).fetchall()
    except ProgrammingError as exc:
        # See _query_fr_impact — same graceful-degrade pattern (incl. rollback).
        conn.rollback()
        _log.debug("touch_index_bug_files unavailable: %s", exc)
        return []
    return [
        RegressionRisk(
            bug_identifier=row.bug_identifier,
            bug_issue_id=row.bug_issue_id,
        )
        for row in rows
    ]


def _query_downstream(conn, file_paths: list[str]) -> list:
    """Phase 2 stub — return empty list if dep graph is not populated or schema is missing."""
    try:
        count = conn.execute(text("SELECT COUNT(*) FROM touch_index_file_deps")).scalar()
    except ProgrammingError as exc:
        # See _query_fr_impact — same graceful-degrade pattern (incl. rollback).
        conn.rollback()
        _log.debug("touch_index_file_deps unavailable: %s", exc)
        return []
    if not count:
        return []

    try:
        rows = conn.execute(
            text(
                """
                SELECT DISTINCT dep_file
                FROM   touch_index_file_deps
                WHERE  source_file = ANY(:paths)
                ORDER  BY dep_file
                """
            ),
            {"paths": file_paths},
        ).fetchall()
    except ProgrammingError as exc:
        # See _query_fr_impact — same graceful-degrade pattern (incl. rollback).
        conn.rollback()
        _log.debug("touch_index_file_deps query failed: %s", exc)
        return []
    return [row.dep_file for row in rows]


def to_json_dict(data: BlastRadiusData) -> dict:
    """Serialize BlastRadiusData to the JSON response shape defined in the API spec."""
    return {
        "fr_impact_set": [
            {
                "fr_identifier": fr.fr_identifier,
                "fr_owner_agent_id": fr.fr_owner_agent_id,
                "fr_issue_id": fr.fr_issue_id,
            }
            for fr in data.fr_impact_set
        ],
        "regression_set": [
            {
                "bug_identifier": r.bug_identifier,
                "bug_issue_id": r.bug_issue_id,
            }
            for r in data.regression_set
        ],
        "downstream_set": data.downstream_set,
        "downstream_note": data.downstream_note if not data.downstream_set else None,
    }
