"""Core scoring and gap-analysis logic for the TPM Competency Matrix.

This module is deliberately free of any database or framework dependency so
it can be unit tested and reused by the API, the report generators and any
future import/export tooling.

The three rules from the specification are implemented here:

1. Rating conversion scale (0-5 -> 0-100%).
2. Overall competency = (total rating / maximum possible rating) * 100.
3. Gap analysis: compare RequiredScore against RatingScore.

Unassessed vs. zero
-------------------
The specification defines ``0 = None = 0%`` as a deliberate supervisor
judgement. A competency the supervisor has *never assessed* is a different
state and must not be collapsed onto 0, because doing so would:

  * understate an employee's genuine standing competency, and
  * flood the training-needs report with false "training required" rows for
    competencies that nobody has looked at yet.

A missing score is therefore modelled explicitly as ``None`` and reported
as ``UNASSESSED``; it counts towards a separate "assessment coverage"
figure instead of dragging the overall percentage to zero.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from enum import StrEnum
from typing import Iterable, Sequence

__all__ = [
    "MAX_RATING",
    "MIN_RATING",
    "RATING_SCALE",
    "RatingDescriptor",
    "GapStatus",
    "Priority",
    "CompetencyScore",
    "OverallResult",
    "GapResult",
    "validate_rating",
    "rating_to_percentage",
    "rating_to_label",
    "percentage_to_rating",
    "calculate_overall",
    "assess_gap",
    "analyse_gaps",
    "summarise_department",
]

MIN_RATING = 0
MAX_RATING = 5


class RatingDescriptor:
    """One rung of the 0-5 competency scale."""

    __slots__ = ("rating", "percentage", "label")

    def __init__(self, rating: int, percentage: int, label: str) -> None:
        self.rating = rating
        self.percentage = percentage
        self.label = label

    def __repr__(self) -> str:  # pragma: no cover - debugging aid
        return f"RatingDescriptor({self.rating}, {self.percentage}%, {self.label!r})"


#: The specification's rating conversion scale.
RATING_SCALE: dict[int, RatingDescriptor] = {
    5: RatingDescriptor(5, 100, "Expert"),
    4: RatingDescriptor(4, 80, "Highly Competent"),
    3: RatingDescriptor(3, 60, "Reasonably Competent"),
    2: RatingDescriptor(2, 40, "Under Training / Needs Refresher"),
    1: RatingDescriptor(1, 20, "Low or Very Basic"),
    0: RatingDescriptor(0, 0, "None"),
}


class GapStatus(StrEnum):
    """Outcome of comparing current rating against the position requirement."""

    ACHIEVED = "Achieved"
    GAP = "Gap"
    UNASSESSED = "Unassessed"


class Priority(StrEnum):
    """Training/assessment priority band, ordered most urgent first."""

    CRITICAL = "Critical"
    HIGH = "High"
    MEDIUM = "Medium"
    LOW = "Low"


#: Category whose shortfalls must always escalate to CRITICAL.
SAFETY_CATEGORIES: frozenset[str] = frozenset({"Safety & Compliance"})

_PRIORITY_ORDER: dict[Priority, int] = {
    Priority.CRITICAL: 0,
    Priority.HIGH: 1,
    Priority.MEDIUM: 2,
    Priority.LOW: 3,
}


# ---------------------------------------------------------------------------
# Rule 1 - rating conversion scale
# ---------------------------------------------------------------------------

def validate_rating(rating: int) -> int:
    """Return ``rating`` if it is a whole number in 0..5, else raise ValueError."""
    if isinstance(rating, bool) or not isinstance(rating, int):
        raise ValueError(f"rating must be an integer, got {rating!r}")
    if not MIN_RATING <= rating <= MAX_RATING:
        raise ValueError(f"rating must be between {MIN_RATING} and {MAX_RATING}, got {rating}")
    return rating


def rating_to_percentage(rating: int) -> int:
    """Convert a 0-5 rating to its 0-100 percentage (5 -> 100, 4 -> 80, ...)."""
    return RATING_SCALE[validate_rating(rating)].percentage


def rating_to_label(rating: int) -> str:
    """Human readable descriptor for a rating (e.g. ``Highly Competent``)."""
    return RATING_SCALE[validate_rating(rating)].label


def percentage_to_rating(percentage: float) -> int:
    """Inverse of :func:`rating_to_percentage`; snaps to the nearest scale rung."""
    if not 0 <= percentage <= 100:
        raise ValueError(f"percentage must be between 0 and 100, got {percentage}")
    return min(MAX_RATING, round(percentage / 20))


# ---------------------------------------------------------------------------
# Rule 2 - overall competency
# ---------------------------------------------------------------------------

@dataclass(frozen=True, slots=True)
class OverallResult:
    """Outcome of the overall competency calculation.

    ``percentage`` is computed over *assessed* competencies only. Use
    ``assessed_count``/``total_count`` to judge how much of the matrix that
    figure actually covers.
    """

    total_rating: int
    max_possible_rating: int
    percentage: float
    assessed_count: int
    unassessed_count: int
    labels: tuple[str, ...] = field(default=(), repr=False)

    @property
    def total_count(self) -> int:
        return self.assessed_count + self.unassessed_count

    @property
    def coverage_percentage(self) -> float:
        """Share of the required matrix that has actually been assessed."""
        if not self.total_count:
            return 0.0
        return self.assessed_count / self.total_count * 100

    @property
    def is_complete(self) -> bool:
        return self.unassessed_count == 0

    def __str__(self) -> str:  # pragma: no cover - display helper
        return f"{self.percentage:.1f}%"


def calculate_overall(
    ratings: Sequence[int | None],
    *,
    required_only: Sequence[bool] | None = None,
) -> OverallResult:
    """Compute the overall competency percentage for a set of ratings.

    Args:
        ratings: Ratings in 0..5, or ``None`` where never assessed.
        required_only: Optional parallel sequence of booleans marking which
            entries carry a position requirement. Competencies with no
            requirement are excluded from the calculation, because scoring
            an employee against a competency their role never asks for
            would distort the figure. ``None`` means "use every entry".

    Example:
        Ten competencies assessed, total rating 40, max 50 -> 80.0.
    """
    if required_only is not None and len(required_only) != len(ratings):
        raise ValueError("required_only must be the same length as ratings")

    total_rating = 0
    assessed_count = 0
    unassessed_count = 0
    max_possible_rating = 0
    labels: list[str] = []

    for index, rating in enumerate(ratings):
        if required_only is not None and not required_only[index]:
            continue
        if rating is None:
            unassessed_count += 1
            continue
        validate_rating(rating)
        total_rating += rating
        assessed_count += 1
        max_possible_rating += MAX_RATING
        labels.append(rating_to_label(rating))

    percentage = (
        (total_rating / max_possible_rating) * 100 if max_possible_rating else 0.0
    )

    return OverallResult(
        total_rating=total_rating,
        max_possible_rating=max_possible_rating,
        percentage=round(percentage, 2),
        assessed_count=assessed_count,
        unassessed_count=unassessed_count,
        labels=tuple(labels),
    )


# ---------------------------------------------------------------------------
# Rule 3 - gap analysis
# ---------------------------------------------------------------------------

@dataclass(frozen=True, slots=True)
class CompetencyScore:
    """One axis of the matrix: a requirement and the employee's rating."""

    competency_id: str
    competency_name: str
    category: str
    required_score: int
    rating_score: int | None

    def __post_init__(self) -> None:
        validate_rating(self.required_score)
        if self.rating_score is not None:
            validate_rating(self.rating_score)

    @property
    def current_percentage(self) -> int | None:
        return None if self.rating_score is None else rating_to_percentage(self.rating_score)

    @property
    def required_percentage(self) -> int:
        """Required score expressed on the same 0-100 scale as a rating.

        Because the conversion scale is linear (5 -> 100, 4 -> 80, ...) this
        is always ``required_score * 20``, which is what lets the radar chart
        overlay both polygons on one 0-100 axis.
        """
        return rating_to_percentage(self.required_score)

    @property
    def shortfall(self) -> int:
        """Rating points below the requirement, floored at 0."""
        if self.rating_score is None:
            return self.required_score
        return max(0, self.required_score - self.rating_score)


@dataclass(frozen=True, slots=True)
class GapResult:
    """Gap-analysis verdict for a single competency."""

    competency_id: str
    competency_name: str
    category: str
    required_score: int
    rating_score: int | None
    status: GapStatus
    priority: Priority
    shortfall: int
    current_percentage: int | None
    required_percentage: int
    gap_percentage: int
    sort_key: tuple[int, int, int]

    @property
    def is_actionable(self) -> bool:
        """True when this row needs supervisor attention."""
        return self.status is not GapStatus.ACHIEVED

    def to_dict(self) -> dict[str, object]:
        return {
            "competencyId": self.competency_id,
            "competencyName": self.competency_name,
            "category": self.category,
            "requiredScore": self.required_score,
            "ratingScore": self.rating_score,
            "status": str(self.status),
            "priority": str(self.priority),
            "shortfall": self.shortfall,
            "currentPercentage": self.current_percentage,
            "requiredPercentage": self.required_percentage,
            "gapPercentage": self.gap_percentage,
        }


def assess_gap(score: CompetencyScore) -> GapResult:
    """Apply Rule 3 to a single competency and assign a training priority.

    Priority banding:

    * ``UNASSESSED`` with a requirement > 0 -> CRITICAL. The gap is unknown,
      so the very first action is to assess it, not to train it.
    * Gap where the requirement is the maximum (5) or the competency is
      safety-critical -> CRITICAL.
    * Gap of 2 points or more -> HIGH, a single point -> MEDIUM.
    * Achieved -> LOW.
    """
    if score.rating_score is None:
        status = GapStatus.UNASSESSED
    elif score.rating_score < score.required_score:
        status = GapStatus.GAP
    else:
        status = GapStatus.ACHIEVED

    shortfall = score.shortfall

    if status is GapStatus.ACHIEVED:
        priority = Priority.LOW
    elif status is GapStatus.UNASSESSED:
        priority = Priority.CRITICAL
    elif score.required_score == MAX_RATING or score.category in SAFETY_CATEGORIES:
        priority = Priority.CRITICAL
    elif shortfall >= 2:
        priority = Priority.HIGH
    else:
        priority = Priority.MEDIUM

    current_pct = score.current_percentage
    required_pct = score.required_percentage
    gap_pct = 0 if current_pct is None else max(0, required_pct - current_pct)

    return GapResult(
        competency_id=score.competency_id,
        competency_name=score.competency_name,
        category=score.category,
        required_score=score.required_score,
        rating_score=score.rating_score,
        status=status,
        priority=priority,
        shortfall=shortfall,
        current_percentage=current_pct,
        required_percentage=required_pct,
        gap_percentage=gap_pct,
        sort_key=(_PRIORITY_ORDER[priority], -shortfall, -score.required_score),
    )


def analyse_gaps(scores: Iterable[CompetencyScore]) -> list[GapResult]:
    """Assess every competency, most urgent first."""
    results = [assess_gap(score) for score in scores]
    results.sort(key=lambda result: result.sort_key)
    return results


@dataclass(frozen=True, slots=True)
class DepartmentSummary:
    """Aggregate roll-up used by the department competency report."""

    department: str
    employee_count: int
    average_percentage: float
    minimum_percentage: float
    maximum_percentage: float
    achieved_count: int
    gap_count: int
    unassessed_count: int
    critical_gap_count: int


def summarise_department(
    department: str,
    overalls: Sequence[OverallResult],
    gaps: Sequence[GapResult],
) -> DepartmentSummary:
    """Roll employee overalls and per-competency gaps up to one department."""
    percentages = [result.percentage for result in overalls]
    return DepartmentSummary(
        department=department,
        employee_count=len(overalls),
        average_percentage=round(sum(percentages) / len(percentages), 2) if percentages else 0.0,
        minimum_percentage=min(percentages, default=0.0),
        maximum_percentage=max(percentages, default=0.0),
        achieved_count=sum(1 for gap in gaps if gap.status is GapStatus.ACHIEVED),
        gap_count=sum(1 for gap in gaps if gap.status is GapStatus.GAP),
        unassessed_count=sum(1 for gap in gaps if gap.status is GapStatus.UNASSESSED),
        critical_gap_count=sum(
            1 for gap in gaps if gap.is_actionable and gap.priority is Priority.CRITICAL
        ),
    )
