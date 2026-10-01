"""Database access for the TPM Competency Matrix.

All SQL lives here. It returns plain dataclasses / dicts and hands the
computation to :mod:`app.scoring`, so the scoring rules stay testable
without a database.
"""

from __future__ import annotations

import datetime as dt
import os
import sqlite3
import uuid
from contextlib import contextmanager
from dataclasses import asdict, dataclass
from pathlib import Path
from typing import Iterator, Sequence

from .scoring import (
    CompetencyScore,
    GapResult,
    OverallResult,
    analyse_gaps,
    calculate_overall,
    rating_to_percentage,
    summarise_department,
    DepartmentSummary,
)

ROOT = Path(__file__).resolve().parent.parent
DB_PATH = Path(os.getenv("TPM_DATABASE_PATH", str(ROOT / "data" / "tpm_matrix.db")))


def camelize(data: dict[str, object]) -> dict[str, object]:
    """Convert snake_case keys to camelCase for the JSON API.

    Applied to every serialised response so the browser never has to deal
    with a mix of ``overall_percentage`` and ``overallPercentage``.
    """
    result: dict[str, object] = {}
    for key, value in data.items():
        head, *rest = key.split("_")
        result[head + "".join(word.title() for word in rest)] = value
    return result


@dataclass(frozen=True, slots=True)
class Employee:
    id: str
    employee_number: str
    full_name: str
    email: str | None
    department: str
    position_id: str
    position_title: str
    supervisor: str | None
    join_date: str | None
    years_of_experience: int | None

    def to_dict(self) -> dict[str, object]:
        return camelize(asdict(self))


@dataclass(frozen=True, slots=True)
class Competency:
    id: str
    code: str
    name: str
    category: str
    description: str | None
    sort_order: int

    def to_dict(self) -> dict[str, object]:
        return camelize(asdict(self))


@dataclass(frozen=True, slots=True)
class Assessment:
    id: str
    employee_id: str
    cycle_name: str
    assessment_date: str
    assessor_name: str
    total_rating: int
    max_possible_rating: int
    overall_percentage: float
    remarks: str | None

    def to_dict(self) -> dict[str, object]:
        return camelize(asdict(self))


@dataclass(frozen=True, slots=True)
class TrainingRecord:
    id: str
    employee_id: str
    title: str
    provider: str | None
    completion_date: str
    status: str
    reassessment_cycle: str | None

    def to_dict(self) -> dict[str, object]:
        return camelize(asdict(self))


@dataclass(slots=True)
class EmployeeProfile:
    """Everything the employee dashboard needs, precomputed."""

    employee: Employee
    scores: list[CompetencyScore]
    gaps: list[GapResult]
    overall: OverallResult
    assessments: list[Assessment]
    training: list[TrainingRecord]

    @property
    def action_items(self) -> list[GapResult]:
        return [gap for gap in self.gaps if gap.is_actionable]

    def to_dict(self) -> dict[str, object]:
        return {
            "employee": self.employee.to_dict(),
            "overall": {
                "percentage": self.overall.percentage,
                "totalRating": self.overall.total_rating,
                "maxPossibleRating": self.overall.max_possible_rating,
                "assessedCount": self.overall.assessed_count,
                "unassessedCount": self.overall.unassessed_count,
                "coveragePercentage": round(self.overall.coverage_percentage, 2),
                "isComplete": self.overall.is_complete,
            },
            "scores": [
                {
                    "competencyId": score.competency_id,
                    "competencyName": score.competency_name,
                    "category": score.category,
                    "requiredScore": score.required_score,
                    "ratingScore": score.rating_score,
                    "currentPercentage": score.current_percentage,
                    "requiredPercentage": score.required_percentage,
                    "shortfall": score.shortfall,
                }
                for score in self.scores
            ],
            "gaps": [gap.to_dict() for gap in self.gaps],
            "assessments": [camelize(asdict(a)) for a in self.assessments],
            "training": [camelize(asdict(t)) for t in self.training],
        }


class Repository:
    """Thin data-access facade over the SQLite database."""

    def __init__(self, db_path: Path | str = DB_PATH) -> None:
        self.db_path = Path(db_path)

    @contextmanager
    def connect(self) -> Iterator[sqlite3.Connection]:
        conn = sqlite3.connect(self.db_path)
        conn.row_factory = sqlite3.Row
        conn.execute("PRAGMA foreign_keys = ON")
        try:
            yield conn
        finally:
            conn.close()

    # -- reference data -------------------------------------------------

    def list_competencies(self, active_only: bool = True) -> list[Competency]:
        sql = "SELECT * FROM competencies"
        if active_only:
            sql += " WHERE is_active = 1"
        sql += " ORDER BY sort_order, id"
        with self.connect() as conn:
            return [Competency(**_row_to_competency(r)) for r in conn.execute(sql)]

    def list_employees(self, department: str | None = None) -> list[Employee]:
        sql = """
            SELECT e.*, p.title AS position_title
            FROM employees e
            JOIN positions p ON p.id = e.position_id
            WHERE e.is_active = 1
        """
        params: list[object] = []
        if department:
            sql += " AND e.department = ?"
            params.append(department)
        sql += " ORDER BY e.employee_number"
        with self.connect() as conn:
            return [_row_to_employee(r) for r in conn.execute(sql, params)]

    def get_employee(self, employee_id: str) -> Employee | None:
        with self.connect() as conn:
            row = conn.execute(
                """
                SELECT e.*, p.title AS position_title
                FROM employees e JOIN positions p ON p.id = e.position_id
                WHERE e.id = ?
                """,
                (employee_id,),
            ).fetchone()
        return _row_to_employee(row) if row else None

    def list_positions(self) -> list[dict[str, object]]:
        with self.connect() as conn:
            return [dict(r) for r in conn.execute("SELECT * FROM positions ORDER BY id")]

    def list_departments(self) -> list[str]:
        with self.connect() as conn:
            return [
                r[0]
                for r in conn.execute(
                    "SELECT DISTINCT department FROM employees WHERE is_active = 1 ORDER BY department"
                )
            ]

    # -- matrix ---------------------------------------------------------

    def build_matrix(
        self, employee_id: str, conn: sqlite3.Connection | None = None
    ) -> tuple[list[CompetencyScore], OverallResult, list[GapResult]]:
        """Assemble the full requirement-vs-rating matrix for one employee.

        The axis set is the union of every competency carrying a requirement
        for the employee's position, plus any competency the employee has
        actually been assessed on. That way a newly introduced competency
        shows up as UNASSESSED instead of silently vanishing.
        """
        if conn is not None:
            return self._build_matrix_with(employee_id, conn)
        with self.connect() as owned:
            return self._build_matrix_with(employee_id, owned)

    def _build_matrix_with(
        self, employee_id: str, conn: sqlite3.Connection
    ) -> tuple[list[CompetencyScore], OverallResult, list[GapResult]]:
        employee = conn.execute(
            """
            SELECT e.*, p.title AS position_title
            FROM employees e JOIN positions p ON p.id = e.position_id
            WHERE e.id = ?
            """,
            (employee_id,),
        ).fetchone()
        if employee is None:
            raise LookupError(f"employee {employee_id!r} not found")

        requirements = {
            r["competency_id"]: r["required_rating"]
            for r in conn.execute(
                "SELECT competency_id, required_rating FROM position_requirements WHERE position_id = ?",
                (employee["position_id"],),
            )
        }
        ratings = {
            r["competency_id"]: r["rating"]
            for r in conn.execute(
                "SELECT competency_id, rating FROM employee_current_scores WHERE employee_id = ?",
                (employee_id,),
            )
        }

        competencies = {
            r["id"]: r
            for r in conn.execute("SELECT * FROM competencies WHERE is_active = 1")
        }

        # Deterministic axis order: sort_order, then id. The union keeps a
        # competency visible if it is either required or already assessed.
        axis_ids = set(requirements) | set(ratings)
        ordered = sorted(axis_ids, key=lambda cid: (competencies[cid]["sort_order"], cid))

        scores: list[CompetencyScore] = []
        for competency_id in ordered:
            meta = competencies[competency_id]
            scores.append(
                CompetencyScore(
                    competency_id=competency_id,
                    competency_name=meta["name"],
                    category=meta["category"],
                    # No requirement for this position => 0, so it never
                    # registers as a gap.
                    required_score=requirements.get(competency_id, 0),
                    rating_score=ratings.get(competency_id),
                )
            )

        overall = calculate_overall(
            [s.rating_score for s in scores],
            required_only=[s.required_score > 0 for s in scores],
        )
        return scores, overall, analyse_gaps(scores)

    def get_profile(self, employee_id: str) -> EmployeeProfile:
        with self.connect() as conn:
            row = conn.execute(
                """
                SELECT e.*, p.title AS position_title
                FROM employees e JOIN positions p ON p.id = e.position_id
                WHERE e.id = ?
                """,
                (employee_id,),
            ).fetchone()
            if row is None:
                raise LookupError(f"employee {employee_id!r} not found")

            scores, overall, gaps = self._build_matrix_with(employee_id, conn)

            assessments = [
                Assessment(**dict(r))
                for r in conn.execute(
                    """
                    SELECT id, employee_id, cycle_name, assessment_date, assessor_name,
                           total_rating, max_possible_rating, overall_percentage, remarks
                    FROM assessments WHERE employee_id = ?
                    ORDER BY assessment_date DESC
                    """,
                    (employee_id,),
                )
            ]

            training = [
                TrainingRecord(**dict(r))
                for r in conn.execute(
                    """
                    SELECT id, employee_id, title, provider, completion_date,
                           status, reassessment_cycle
                    FROM training_records WHERE employee_id = ?
                    ORDER BY completion_date DESC
                    """,
                    (employee_id,),
                )
            ]

        return EmployeeProfile(
            employee=_row_to_employee(row),
            scores=scores,
            gaps=gaps,
            overall=overall,
            assessments=assessments,
            training=training,
        )

    # -- writes ---------------------------------------------------------

    def record_assessment(
        self,
        *,
        employee_id: str,
        assessor_name: str,
        cycle_name: str,
        assessment_date: str | None,
        ratings: dict[str, int],
        remarks: str | None = None,
    ) -> Assessment:
        """Persist an assessment and refresh the employee's current scores.

        Writes assessment + assessment_scores + employee_current_scores in a
        single transaction, recomputing the denormalised totals from the
        scores actually supplied so they can never drift.
        """
        from .scoring import validate_rating

        if not ratings:
            raise ValueError("an assessment must contain at least one competency rating")
        for competency_id, rating in ratings.items():
            validate_rating(rating)

        assessment_date = assessment_date or dt.date.today().isoformat()

        with self.connect() as conn:
            if conn.execute("SELECT 1 FROM employees WHERE id = ?", (employee_id,)).fetchone() is None:
                raise LookupError(f"employee {employee_id!r} not found")

            known = {
                r[0] for r in conn.execute("SELECT id FROM competencies WHERE is_active = 1")
            }
            unknown = set(ratings) - known
            if unknown:
                raise ValueError(f"unknown or inactive competencies: {sorted(unknown)}")

            total = sum(ratings.values())
            maximum = len(ratings) * 5
            percentage = round(total / maximum * 100, 2) if maximum else 0.0
            assessment_id = f"ass-{uuid.uuid4().hex[:12]}"

            with conn:
                conn.execute(
                    """
                    INSERT INTO assessments
                        (id, employee_id, cycle_name, assessment_date, assessor_name,
                         total_rating, max_possible_rating, overall_percentage, remarks)
                    VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)
                    """,
                    (
                        assessment_id,
                        employee_id,
                        cycle_name,
                        assessment_date,
                        assessor_name,
                        total,
                        maximum,
                        percentage,
                        remarks,
                    ),
                )
                conn.executemany(
                    """
                    INSERT INTO assessment_scores (assessment_id, competency_id, rating, percentage)
                    VALUES (?, ?, ?, ?)
                    """,
                    [
                        (assessment_id, cid, rating, rating_to_percentage(rating))
                        for cid, rating in ratings.items()
                    ],
                )
                conn.executemany(
                    """
                    INSERT INTO employee_current_scores
                        (employee_id, competency_id, rating, percentage, assessment_id, updated_at)
                    VALUES (?, ?, ?, ?, ?, CURRENT_TIMESTAMP)
                    ON CONFLICT(employee_id, competency_id) DO UPDATE SET
                        rating = excluded.rating,
                        percentage = excluded.percentage,
                        assessment_id = excluded.assessment_id,
                        updated_at = CURRENT_TIMESTAMP
                    """,
                    [
                        (employee_id, cid, rating, rating_to_percentage(rating), assessment_id)
                        for cid, rating in ratings.items()
                    ],
                )

        return self.get_assessment(assessment_id)

    def get_assessment(self, assessment_id: str) -> Assessment:
        with self.connect() as conn:
            row = conn.execute(
                """
                SELECT id, employee_id, cycle_name, assessment_date, assessor_name,
                       total_rating, max_possible_rating, overall_percentage, remarks
                FROM assessments WHERE id = ?
                """,
                (assessment_id,),
            ).fetchone()
        if row is None:
            raise LookupError(f"assessment {assessment_id!r} not found")
        return Assessment(**dict(row))

    def get_assessment_scores(self, assessment_id: str) -> list[dict[str, object]]:
        with self.connect() as conn:
            return [
                dict(r)
                for r in conn.execute(
                    """
                    SELECT s.competency_id, c.code, c.name, c.category,
                           s.rating, s.percentage
                    FROM assessment_scores s
                    JOIN competencies c ON c.id = s.competency_id
                    WHERE s.assessment_id = ?
                    ORDER BY c.sort_order
                    """,
                    (assessment_id,),
                )
            ]

    # -- reporting aggregates -------------------------------------------

    def department_summary(self, department: str) -> DepartmentSummary:
        employees = self.list_employees(department=department)
        overalls: list[OverallResult] = []
        all_gaps: list[GapResult] = []
        for employee in employees:
            _, overall, gaps = self.build_matrix(employee.id)
            overalls.append(overall)
            all_gaps.extend(gaps)
        return summarise_department(department, overalls, all_gaps)

    def training_needs(self, department: str | None = None) -> list[dict[str, object]]:
        """One row per employee/competency gap, most urgent first."""
        rows: list[dict[str, object]] = []
        for employee in self.list_employees(department=department):
            _, _, gaps = self.build_matrix(employee.id)
            for gap in gaps:
                if not gap.is_actionable:
                    continue
                rows.append(
                    {
                        "employeeId": employee.id,
                        "employeeNumber": employee.employee_number,
                        "employeeName": employee.full_name,
                        "department": employee.department,
                        "positionTitle": employee.position_title,
                        "supervisor": employee.supervisor,
                        **gap.to_dict(),
                    }
                )
        rows.sort(key=lambda r: (str(r["priority"]), -int(r["shortfall"])))
        return rows

    def progress_history(self, employee_id: str) -> list[dict[str, object]]:
        """Overall % per assessment over time, for the progress report.

        Note: the two assessments already in the database predate the app and
        have no assessment_scores rows, so this can only chart the overall
        percentage for them - not per-competency movement.
        """
        with self.connect() as conn:
            rows = list(
                conn.execute(
                    """
                    SELECT id, cycle_name, assessment_date, assessor_name, total_rating,
                           max_possible_rating, overall_percentage,
                           (SELECT COUNT(*) FROM assessment_scores s
                             WHERE s.assessment_id = assessments.id) AS detail_rows
                    FROM assessments WHERE employee_id = ?
                    ORDER BY assessment_date
                    """,
                    (employee_id,),
                )
            )
        history: list[dict[str, object]] = []
        previous: float | None = None
        for index, row in enumerate(rows):
            percentage = float(row["overall_percentage"])
            history.append(
                {
                    "assessmentId": row["id"],
                    "cycleName": row["cycle_name"],
                    "assessmentDate": row["assessment_date"],
                    "assessorName": row["assessor_name"],
                    "totalRating": row["total_rating"],
                    "maxPossibleRating": row["max_possible_rating"],
                    "overallPercentage": percentage,
                    "deltaPercentage": None if previous is None else round(percentage - previous, 2),
                    "hasPerCompetencyDetail": row["detail_rows"] > 0,
                    "isFirst": index == 0,
                }
            )
            previous = percentage
        return history


# ---------------------------------------------------------------------------
# row adapters
# ---------------------------------------------------------------------------

def _row_to_competency(row: sqlite3.Row) -> dict[str, object]:
    return {
        "id": row["id"],
        "code": row["code"],
        "name": row["name"],
        "category": row["category"],
        "description": row["description"],
        "sort_order": row["sort_order"],
    }


def _row_to_employee(row: sqlite3.Row) -> Employee:
    return Employee(
        id=row["id"],
        employee_number=row["employee_number"],
        full_name=row["full_name"],
        email=row["email"],
        department=row["department"],
        position_id=row["position_id"],
        position_title=row["position_title"],
        supervisor=row["supervisor"],
        join_date=row["join_date"],
        years_of_experience=row["years_of_experience"],
    )
