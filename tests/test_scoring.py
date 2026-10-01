"""Unit tests for the scoring and gap-analysis rules."""

from __future__ import annotations

import pytest

from app.scoring import (
    MAX_RATING,
    CompetencyScore,
    GapStatus,
    Priority,
    analyse_gaps,
    assess_gap,
    calculate_overall,
    percentage_to_rating,
    rating_to_label,
    rating_to_percentage,
    summarise_department,
    validate_rating,
)


class TestRatingScale:
    def test_spec_conversion_table(self):
        assert rating_to_percentage(5) == 100
        assert rating_to_percentage(4) == 80
        assert rating_to_percentage(3) == 60
        assert rating_to_percentage(2) == 40
        assert rating_to_percentage(1) == 20
        assert rating_to_percentage(0) == 0

    def test_spec_labels(self):
        assert rating_to_label(5) == "Expert"
        assert rating_to_label(4) == "Highly Competent"
        assert rating_to_label(3) == "Reasonably Competent"
        assert rating_to_label(2) == "Under Training / Needs Refresher"
        assert rating_to_label(1) == "Low or Very Basic"
        assert rating_to_label(0) == "None"

    @pytest.mark.parametrize("bad", [-1, 6, 99])
    def test_out_of_range_rejected(self, bad):
        with pytest.raises(ValueError):
            validate_rating(bad)

    @pytest.mark.parametrize("bad", [2.5, "4", None, True])
    def test_non_integer_rejected(self, bad):
        with pytest.raises(ValueError):
            validate_rating(bad)

    def test_percentage_round_trips(self):
        for rating in range(MAX_RATING + 1):
            assert percentage_to_rating(rating_to_percentage(rating)) == rating


class TestOverallCalculation:
    def test_spec_worked_example(self):
        """10 competencies, total 40, max 50 -> 80%."""
        ratings = [5, 5, 5, 5, 5, 4, 4, 3, 2, 2]
        result = calculate_overall(ratings)
        assert result.total_rating == 40
        assert result.max_possible_rating == 50
        assert result.percentage == 80.0
        assert result.assessed_count == 10
        assert result.unassessed_count == 0
        assert result.is_complete

    def test_all_experts_is_100(self):
        assert calculate_overall([5] * 13).percentage == 100.0

    def test_all_zero_is_0(self):
        result = calculate_overall([0] * 5)
        assert result.percentage == 0.0
        assert result.total_rating == 0

    def test_unassessed_is_excluded_not_zeroed(self):
        """A never-assessed competency must not deflate the score."""
        assessed = calculate_overall([4, 4, 5, 5, 4, 5])
        with_holes = calculate_overall([4, 4, 5, 5, 4, 5, None, None, None])

        assert with_holes.percentage == assessed.percentage == 90.0
        assert assessed.total_rating == 27
        assert assessed.max_possible_rating == 30
        assert with_holes.assessed_count == 6
        assert with_holes.unassessed_count == 3
        assert not with_holes.is_complete
        assert with_holes.coverage_percentage == pytest.approx(66.67, abs=0.01)

    def test_explicit_zero_is_not_treated_as_unassessed(self):
        result = calculate_overall([0, 0, 0, 0, 0])
        assert result.unassessed_count == 0
        assert result.assessed_count == 5
        assert result.percentage == 0.0

    def test_competencies_without_requirement_are_excluded(self):
        ratings = [5, 5, 5, 5]
        required = [True, True, False, False]
        result = calculate_overall(ratings, required_only=required)
        assert result.total_rating == 10
        assert result.max_possible_rating == 10
        assert result.percentage == 100.0

    def test_empty_input(self):
        result = calculate_overall([])
        assert result.percentage == 0.0
        assert result.total_count == 0
        assert result.coverage_percentage == 0.0

    def test_mismatched_required_mask_rejected(self):
        with pytest.raises(ValueError):
            calculate_overall([4, 4], required_only=[True])


class TestGapAnalysis:
    def test_achieved_when_current_meets_required(self):
        result = assess_gap(_score(required=3, rating=3))
        assert result.status is GapStatus.ACHIEVED
        assert result.shortfall == 0
        assert result.gap_percentage == 0
        assert result.priority is Priority.LOW
        assert not result.is_actionable

    def test_achieved_when_current_exceeds_required(self):
        result = assess_gap(_score(required=2, rating=5))
        assert result.status is GapStatus.ACHIEVED

    def test_gap_detected_with_shortfall(self):
        result = assess_gap(_score(required=5, rating=3))
        assert result.status is GapStatus.GAP
        assert result.shortfall == 2
        assert result.gap_percentage == 40  # 100% required - 60% current
        assert result.is_actionable

    def test_maximum_requirement_escalates_to_critical(self):
        result = assess_gap(_score(required=5, rating=4, category="Mechanical"))
        assert result.status is GapStatus.GAP
        assert result.priority is Priority.CRITICAL

    def test_safety_category_escalates_to_critical(self):
        result = assess_gap(
            _score(required=3, rating=2, category="Safety & Compliance")
        )
        assert result.priority is Priority.CRITICAL

    def test_small_gap_is_medium(self):
        result = assess_gap(_score(required=4, rating=3, category="Mechanical"))
        assert result.priority is Priority.MEDIUM
        assert result.shortfall == 1

    def test_large_gap_is_high(self):
        result = assess_gap(_score(required=4, rating=2, category="Mechanical"))
        assert result.priority is Priority.HIGH

    def test_unassessed_is_flagged_not_scored_as_zero(self):
        result = assess_gap(_score(required=4, rating=None))
        assert result.status is GapStatus.UNASSESSED
        assert result.priority is Priority.CRITICAL
        assert result.current_percentage is None
        assert result.is_actionable

    def test_results_sorted_most_urgent_first(self):
        results = analyse_gaps(
            [
                _score("a", required=2, rating=2),  # Achieved
                _score("b", required=4, rating=3),  # Medium
                _score("c", required=5, rating=2),  # Critical
                _score("d", required=3, rating=None),  # Critical
                _score("e", required=4, rating=2),  # High
            ]
        )
        assert [r.competency_id for r in results] == ["c", "d", "e", "b", "a"]
        assert all(
            results[i].priority is not Priority.CRITICAL or results[i + 1].priority is not Priority.CRITICAL
            for i in range(len(results) - 1)
            if results[i].priority is not results[i + 1].priority
        )

    def test_to_dict_is_serialisable(self):
        payload = assess_gap(_score(required=5, rating=3)).to_dict()
        assert payload["status"] == "Gap"
        assert payload["priority"] == "Critical"
        assert payload["shortfall"] == 2


class TestDepartmentSummary:
    def test_roll_up(self):
        overalls = [calculate_overall([4, 4, 4, 4, 4]), calculate_overall([2, 2, 2, 2, 2])]
        gaps = [
            assess_gap(_score(required=3, rating=3)),
            assess_gap(_score(required=5, rating=2)),
            assess_gap(_score(required=4, rating=None)),
        ]
        summary = summarise_department("Crusher Maintenance", overalls, gaps)

        assert summary.employee_count == 2
        assert summary.average_percentage == 60.0
        assert summary.minimum_percentage == 40.0
        assert summary.maximum_percentage == 80.0
        assert summary.achieved_count == 1
        assert summary.gap_count == 1
        assert summary.unassessed_count == 1
        assert summary.critical_gap_count == 2

    def test_empty_department(self):
        summary = summarise_department("Empty", [], [])
        assert summary.average_percentage == 0.0
        assert summary.employee_count == 0


def _score(
    competency_id: str = "comp-x",
    *,
    required: int,
    rating: int | None,
    category: str = "Mechanical",
) -> CompetencyScore:
    return CompetencyScore(
        competency_id=competency_id,
        competency_name=f"Competency {competency_id}",
        category=category,
        required_score=required,
        rating_score=rating,
    )
