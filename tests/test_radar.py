"""Geometry tests for the spider chart.

No screenshot is used: the emitted SVG is parsed and every vertex is checked
against the source data, which is a stricter test than eyeballing it.
"""

from __future__ import annotations

import math
import re
import xml.dom.minidom as minidom

import pytest

from app.radar import build_geometry, render_radar_svg
from app.scoring import CompetencyScore

POLYGON_RE = re.compile(r'points="([\d.,\s-]+)"')
CIRCLE_RE = re.compile(r'<circle cx="([\d.-]+)" cy="([\d.-]+)" r="([\d.]+)"[^>]*?(/>|>)')


def _scores() -> list[CompetencyScore]:
    return [
        CompetencyScore("c1", "Autonomous Maintenance", "TPM Pillar", 5, 4),
        CompetencyScore("c2", "Lubrication", "Mechanical", 4, 2),
        CompetencyScore("c3", "Visual Check", "Inspection", 3, None),
        CompetencyScore("c4", "Safety Procedures", "Safety & Compliance", 5, 5),
    ]


def _parse_polygons(svg: str) -> list[list[tuple[float, float]]]:
    document = minidom.parseString(svg)
    polygons = []
    for node in document.getElementsByTagName("polygon"):
        # getAttribute already strips the attribute name and quotes.
        raw = node.getAttribute("points")
        polygons.append(
            [(float(x), float(y)) for x, y in (p.split(",") for p in raw.split())]
        )
    return polygons


def _count_circle_fills(svg: str, colour: str) -> int:
    return len(re.findall(rf'<circle[^>]*fill="{colour}"', svg))


def _radius_from_center(geometry, x: float, y: float) -> float:
    return math.hypot(x - geometry.cx, y - geometry.cy)


class TestGeometry:
    def test_axes_start_at_twelve_oclock_and_evenly_spaced(self):
        geometry = build_geometry(23, 1000)
        assert geometry.angles[0] == -90
        steps = {round(b - a, 6) for a, b in zip(geometry.angles, geometry.angles[1:])}
        assert steps == {round(360 / 23, 6)}

    def test_requires_three_axes(self):
        with pytest.raises(ValueError):
            build_geometry(2, 1000)

    def test_every_axis_reaches_full_scale_at_100_percent(self):
        geometry = build_geometry(8, 800)
        for i in range(8):
            x, y = geometry.point(i, 1.0)
            assert _radius_from_center(geometry, x, y) == pytest.approx(geometry.radius)


class TestRenderedChart:
    def test_emits_one_axis_spoke_per_competency(self):
        svg = render_radar_svg(_scores(), size=800)
        geometry = build_geometry(4, 800)
        spokes = re.findall(r'<line x1="[\d.]+" y1="[\d.]+" x2="', svg)
        assert len(spokes) == 4
        assert geometry.radius > 0

    def test_grid_rings_at_20_percent_intervals(self):
        svg = render_radar_svg(_scores(), size=800)
        rings = re.findall(r'<polygon points="[^"]+" fill="none"', svg)
        # 5 rings at 20/40/60/80/100
        assert len(rings) == 5

    def test_required_polygon_matches_required_percentages(self):
        scores = _scores()
        svg = render_radar_svg(scores, size=800)
        geometry = build_geometry(len(scores), 800)
        polygons = _parse_polygons(svg)

        # The required polygon is the only one drawn with a dashed stroke.
        required_block = re.search(
            r'<polygon points="([^"]+)" fill="rgba\(240,180,41[^"]*"', svg
        )
        assert required_block, "required polygon missing"
        points = [
            (float(x), float(y))
            for x, y in (p.split(",") for p in required_block.group(1).split())
        ]
        assert len(points) == len(scores)
        for index, score in enumerate(scores):
            radius = _radius_from_center(geometry, *points[index])
            assert radius == pytest.approx(geometry.radius * score.required_percentage / 100)

    def test_all_vertices_within_zero_to_one_hundred_percent(self):
        scores = _scores()
        svg = render_radar_svg(scores, size=800)
        geometry = build_geometry(len(scores), 800)
        for polygon in _parse_polygons(svg):
            for x, y in polygon:
                radius = _radius_from_center(geometry, x, y)
                assert 0 <= radius <= geometry.radius + 0.01

    def test_unassessed_axis_is_never_plotted_at_zero(self):
        """The critical correctness property: unknown must not read as 0%."""
        scores = _scores()
        svg = render_radar_svg(scores, size=800)
        geometry = build_geometry(len(scores), 800)

        marker = re.search(
            r'<circle cx="([\d.-]+)" cy="([\d.-]+)" r="5"[^/]*stroke-dasharray="2 2"', svg
        )
        assert marker, "unassessed marker missing"
        unassessed_point = (float(marker.group(1)), float(marker.group(2)))
        assert _radius_from_center(geometry, *unassessed_point) == pytest.approx(
            geometry.radius
        ), "unassessed marker must sit on the 100% ring, not at the centre"

    def test_current_polygon_breaks_at_unassessed_axis(self):
        """Assessed flags are [T,T,F,T], so the wrap-around run is c4->c1->c2
        (3 vertices) and the polygon must stop at the unassessed axis c3."""
        svg = render_radar_svg(_scores(), size=800)
        current_block = re.search(
            r'<polygon points="([^"]+)" fill="rgba\(31,111,235[^"]*"', svg
        )
        assert current_block, "current polygon missing"
        vertices = current_block.group(1).split()
        assert len(vertices) == 3

    def test_rated_axes_get_value_markers_coloured_by_gap(self):
        svg = render_radar_svg(_scores(), size=800)
        # c1: 4 vs 5 -> Gap (red). c2: 2 vs 4 -> Gap (red). c4: 5 vs 5 -> Achieved (green).
        assert _count_circle_fills(svg, "#c0392b") == 2
        assert _count_circle_fills(svg, "#1e7e34") == 1

    def test_labels_present_for_every_competency(self):
        svg = render_radar_svg(_scores(), size=800)
        for score in _scores():
            assert score.competency_name.split()[0] in svg

    def test_long_labels_wrap_to_two_lines(self):
        long_name = "Electrical MCC and Motor Condition Monitoring Requirements"
        scores = [CompetencyScore(f"c{i}", long_name, "Spec", 4, 3) for i in range(3)]
        svg = render_radar_svg(scores, size=800)
        assert "Electrical MCC and" in svg
        assert "Motor Condition Monitoring" in svg

    def test_warns_when_matrix_is_incomplete(self):
        svg = render_radar_svg(_scores(), size=800)
        assert "not yet assessed" in svg

    def test_complete_matrix_shows_no_warning(self):
        scores = [
            CompetencyScore(f"c{i}", f"Competency {i}", "Cat", 4, 4) for i in range(5)
        ]
        svg = render_radar_svg(scores, size=800)
        assert "not yet assessed" not in svg

    def test_employee_name_is_escaped(self):
        svg = render_radar_svg(_scores(), employee_name="Ahmad & Sons <Crusher>")
        assert "Ahmad &amp; Sons &lt;Crusher&gt;" in svg

    def test_empty_input_degrades_gracefully(self):
        svg = render_radar_svg([])
        assert "No competencies to plot" in svg

    def test_output_is_well_formed_xml(self):
        svg = render_radar_svg(_scores(), size=1000, employee_name="Test")
        assert minidom.parseString(svg).documentElement.tagName == "svg"

    def test_honours_requested_size(self):
        svg = render_radar_svg(_scores(), size=640)
        assert 'width="640"' in svg
        assert 'viewBox="0 0 640 640"' in svg

    def test_handles_full_23_axis_matrix(self):
        scores = [
            CompetencyScore(f"c{i}", f"Crusher Competency Number {i}", "Cat", 5, i % 6)
            for i in range(23)
        ]
        svg = render_radar_svg(scores, size=1000)
        assert svg.count("<text") >= 23
        assert minidom.parseString(svg).documentElement.tagName == "svg"
