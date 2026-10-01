"""Idempotent migration runner for the TPM Competency Matrix.

Applies, in order:
  1. Structural changes SQLite cannot express as ``IF NOT EXISTS``:
     - employees.years_of_experience
     - competencies.sort_order
     - employee_current_scores.assessment_id
     - the reporting indexes
  2. sql/002_migration_crusher.sql (the 13 Crusher competencies + required
     scores for the four existing positions)
  3. Backfills: sort_order for legacy competencies and
     years_of_experience derived from join_date.

Safe to run repeatedly. Back up the database first if you care.
"""

from __future__ import annotations

import datetime as dt
import os
import sqlite3
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
DB_PATH = Path(os.getenv("TPM_DATABASE_PATH", str(ROOT / "data" / "tpm_matrix.db")))
MIGRATION_SQL = ROOT / "sql" / "002_migration_crusher.sql"

NEW_COLUMNS: tuple[tuple[str, str, str], ...] = (
    ("employees", "years_of_experience", "INTEGER"),
    ("competencies", "sort_order", "INTEGER NOT NULL DEFAULT 100"),
    ("employee_current_scores", "assessment_id", "TEXT"),
)

INDEXES: tuple[str, ...] = (
    "CREATE INDEX IF NOT EXISTS idx_employees_position ON employees(position_id)",
    "CREATE INDEX IF NOT EXISTS idx_employees_dept ON employees(department)",
    "CREATE INDEX IF NOT EXISTS idx_assessments_emp ON assessments(employee_id, assessment_date DESC)",
    "CREATE INDEX IF NOT EXISTS idx_scores_emp ON assessment_scores(assessment_id)",
    "CREATE INDEX IF NOT EXISTS idx_current_scores ON employee_current_scores(employee_id)",
    "CREATE INDEX IF NOT EXISTS idx_training_emp ON training_records(employee_id, completion_date DESC)",
    "CREATE INDEX IF NOT EXISTS idx_competencies_sort ON competencies(sort_order, id)",
)


def _columns(conn: sqlite3.Connection, table: str) -> set[str]:
    return {row[1] for row in conn.execute(f"PRAGMA table_info({table})")}


def add_missing_columns(conn: sqlite3.Connection) -> list[str]:
    added: list[str] = []
    for table, column, ddl in NEW_COLUMNS:
        if column not in _columns(conn, table):
            conn.execute(f"ALTER TABLE {table} ADD COLUMN {column} {ddl}")
            added.append(f"{table}.{column}")
    return added


def apply_data_migration(conn: sqlite3.Connection) -> None:
    conn.executescript(MIGRATION_SQL.read_text(encoding="utf-8"))


def backfill(conn: sqlite3.Connection) -> None:
    """Legacy competencies default to sort_order 100; spread them 1..N in id order."""
    legacy = conn.execute(
        "SELECT id FROM competencies WHERE sort_order = 100 ORDER BY code"
    ).fetchall()
    for index, (competency_id,) in enumerate(legacy, start=1):
        conn.execute(
            "UPDATE competencies SET sort_order = ? WHERE id = ?", (index, competency_id)
        )

    """years_of_experience is derived from join_date, as of today."""
    today = dt.date.today()
    rows = conn.execute(
        "SELECT id, join_date FROM employees WHERE years_of_experience IS NULL"
        "  AND join_date IS NOT NULL AND join_date <> ''"
    ).fetchall()
    for employee_id, join_date in rows:
        try:
            joined = dt.date.fromisoformat(join_date)
        except ValueError:
            continue
        years = max(0, today.year - joined.year - ((today.month, today.day) < (joined.month, joined.day)))
        conn.execute(
            "UPDATE employees SET years_of_experience = ? WHERE id = ?", (years, employee_id)
        )


def main() -> None:
    conn = sqlite3.connect(DB_PATH)
    try:
        conn.execute("PRAGMA foreign_keys = ON")
        with conn:
            added = add_missing_columns(conn)
            for statement in INDEXES:
                conn.execute(statement)
            apply_data_migration(conn)
            backfill(conn)

        counts = {
            table: conn.execute(f"SELECT COUNT(*) FROM {table}").fetchone()[0]
            for table in (
                "positions",
                "competencies",
                "employees",
                "position_requirements",
                "employee_current_scores",
                "assessments",
                "assessment_scores",
                "training_records",
            )
        }
        print(f"migrated {DB_PATH}")
        print("columns added:", ", ".join(added) if added else "(none - already current)")
        for table, count in counts.items():
            print(f"  {table:26} {count}")
    finally:
        conn.close()


if __name__ == "__main__":
    main()
