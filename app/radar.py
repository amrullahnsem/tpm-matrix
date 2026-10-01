"""Spider (radar) chart rendering for the employee competency dashboard.

Renders a dependency-free SVG with:

* one axis per competency, every axis scaled 0-100% (5 rungs of 20%),
* an overlaid "Required" polygon and "Current" polygon so gaps are visible
  immediately at a glance,
* never-assessed competencies drawn as a *broken* current polygon plus a
  hollow marker, rather than being plotted at zero - a zero would read as
  "rated as None", which is a materially different statement.

The same geometry function feeds the HTML dashboard and the PDF exporter, so
the printed report and the screen never disagree.
"""

from __future__ import annotations

import math
from dataclasses import dataclass
from typing import Sequence
from xml.sax.saxutils import escape

from .scoring import CompetencyScore, GapStatus, assess_gap

# --- palette ---------------------------------------------------------------
INK = "#1f2933"
MUTED = "#7b8794"
GRID = "#dfe3e8"
CURRENT_FILL = "rgba(31,111,235,0.22)"
CURRENT_STROKE = "#1f6feb"
REQUIRED_FILL = "rgba(240,180,41,0.16)"
REQUIRED_STROKE = "#b8860b"
UNASSESSED_STROKE = "#9aa5b1"
RING_LABELS = ("0", "20", "40", "60", "80", "100")


@dataclass(frozen=True, slots=True)
class RadarGeometry:
    cx: float
    cy: float
    radius: float
    angles: tuple[float, ...]

    def point(self, index: int, fraction: float) -> tuple[float, float]:
        radians = math.radians(self.angles[index])
        return (
            self.cx + self.radius * fraction * math.cos(radians),
            self.cy + self.radius * fraction * math.sin(radians),
        )


def build_geometry(count: int, size: int) -> RadarGeometry:
    """Centre the chart and space the axes evenly, starting at 12 o'clock."""
    if count < 3:
        raise ValueError("a radar chart needs at least 3 axes")
    cx = size / 2
    cy = size / 2
    radius = size * 0.36
    step = 360 / count
    return RadarGeometry(cx, cy, radius, tuple(-90 + i * step for i in range(count)))


def _wrap_label(text: str, width: int = 20) -> list[str]:
    """Greedy word wrap into at most two lines so 23 axes stay legible."""
    if len(text) <= width:
        return [text]
    words, lines, current = text.split(), [], ""
    for word in words:
        candidate = f"{current} {word}".strip()
        if len(candidate) <= width or not current:
            current = candidate
        else:
            lines.append(current)
            current = word
    lines.append(current)
    if len(lines) > 2:
        lines = [lines[0], " ".join(lines[1:])]
    return [line[: width + 6] for line in lines]


def _polygon(points: Sequence[tuple[float, float]]) -> str:
    return " ".join(f"{x:.2f},{y:.2f}" for x, y in points)


def _contiguous_runs(flags: Sequence[bool]) -> list[list[int]]:
    """Wrap-around contiguous runs where ``flags[i]`` is True.

    Needed so the current-score polygon breaks at never-assessed axes
    instead of drawing a line straight across unknown ground.
    """
    n = len(flags)
    if not any(flags):
        return []
    if all(flags):
        return [list(range(n))]
    start = next(i for i in range(n) if not flags[i] and flags[(i - 1) % n])
    runs: list[list[int]] = []
    current: list[int] = []
    for offset in range(n):
        i = (start + offset) % n
        if flags[i]:
            current.append(i)
        else:
            if len(current) >= 2:
                runs.append(current)
            current = []
    if len(current) >= 2:
        runs.append(current)
    return runs


def render_radar_svg(
    scores: Sequence[CompetencyScore],
    *,
    size: int = 1000,
    employee_name: str = "",
    show_legend: bool = True,
) -> str:
    """Render the dual-polygon spider chart as an SVG document string."""
    if not scores:
        return (
            '<svg xmlns="http://www.w3.org/2000/svg" width="400" height="120">'
            f'<text x="200" y="60" text-anchor="middle" fill="{MUTED}" '
            'font-family="Segoe UI,Arial,sans-serif" font-size="14">'
            "No competencies to plot</text></svg>"
        )

    count = len(scores)
    geometry = build_geometry(count, size)
    gaps = [assess_gap(score) for score in scores]

    assessed_flags = [score.rating_score is not None for score in scores]
    unassessed = sum(1 for flag in assessed_flags if not flag)

    parts: list[str] = [
        f'<svg xmlns="http://www.w3.org/2000/svg" width="{size}" height="{size}" '
        f'viewBox="0 0 {size} {size}" role="img" '
        f'aria-label="Competency spider chart for {escape(employee_name or "employee")}">',
        '<defs>',
        '  <style>'
        f'    .lbl {{ font-family:Segoe UI,Arial,sans-serif; font-size:11px; fill:{INK}; }}'
        f'    .tick {{ font-family:Segoe UI,Arial,sans-serif; font-size:9px; fill:{MUTED}; }}'
        '  </style>',
        '</defs>',
        f'<rect width="{size}" height="{size}" fill="#ffffff"/>',
    ]

    # --- concentric grid rings at 20% intervals --------------------------
    for step in range(1, 6):
        fraction = step / 5
        ring_points = [geometry.point(i, fraction) for i in range(count)]
        parts.append(
            f'<polygon points="{_polygon(ring_points)}" fill="none" '
            f'stroke="{GRID}" stroke-width="1"/>'
        )
    parts.append(
        f'<circle cx="{geometry.cx:.2f}" cy="{geometry.cy:.2f}" r="2" fill="{MUTED}"/>'
    )

    # --- axis spokes + labels --------------------------------------------
    for index, score in enumerate(scores):
        outer = geometry.point(index, 1.0)
        parts.append(
            f'<line x1="{geometry.cx:.2f}" y1="{geometry.cy:.2f}" '
            f'x2="{outer[0]:.2f}" y2="{outer[1]:.2f}" stroke="{GRID}" stroke-width="1"/>'
        )

    # --- required polygon ------------------------------------------------
    required_points = [geometry.point(i, score.required_percentage / 100) for i, score in enumerate(scores)]
    parts.append(
        f'<polygon points="{_polygon(required_points)}" fill="{REQUIRED_FILL}" '
        f'stroke="{REQUIRED_STROKE}" stroke-width="2" stroke-dasharray="7 4" '
        'stroke-linejoin="round"/>'
    )

    # --- current polygon, broken at unassessed axes ----------------------
    for run in _contiguous_runs(assessed_flags):
        points = [
            geometry.point(i, scores[i].current_percentage / 100) for i in run
        ]
        parts.append(
            f'<polygon points="{_polygon(points)}" fill="{CURRENT_FILL}" '
            f'stroke="{CURRENT_STROKE}" stroke-width="2.5" stroke-linejoin="round"/>'
        )

    # --- per-axis value markers -----------------------------------------
    for index, score in enumerate(scores):
        gap = gaps[index]
        if gap.status is GapStatus.UNASSESSED:
            x, y = geometry.point(index, 1.0)
            parts.append(
                f'<circle cx="{x:.2f}" cy="{y:.2f}" r="5" fill="#ffffff" '
                f'stroke="{UNASSESSED_STROKE}" stroke-width="2" stroke-dasharray="2 2"/>'
            )
            continue
        x, y = geometry.point(index, score.current_percentage / 100)
        marker = "#c0392b" if gap.status is GapStatus.GAP else "#1e7e34"
        parts.append(f'<circle cx="{x:.2f}" cy="{y:.2f}" r="3.5" fill="{marker}"/>')

    # --- axis labels -----------------------------------------------------
    label_radius = geometry.radius + 26
    for index, score in enumerate(scores):
        radians = math.radians(geometry.angles[index])
        x = geometry.cx + label_radius * math.cos(radians)
        y = geometry.cy + label_radius * math.sin(radians)
        cosine = math.cos(radians)
        sine = math.sin(radians)
        anchor = "start" if cosine > 0.12 else "end" if cosine < -0.12 else "middle"
        if sine > 0.25:
            dy, valign = 3.0, "hanging"
        elif sine < -0.25:
            dy, valign = 3.0, "auto"
        else:
            dy, valign = 0.0, "middle"

        lines = _wrap_label(score.competency_name)
        for line_index, line in enumerate(lines):
            parts.append(
                f'<text x="{x:.2f}" y="{y + dy + line_index * 12:.2f}" '
                f'text-anchor="{anchor}" dominant-baseline="{valign}" class="lbl">'
                f"{escape(line)}</text>"
            )

    # --- ring tick labels -------------------------------------------------
    for step, label in enumerate(RING_LABELS, start=1):
        x = geometry.cx + 6
        y = geometry.cy - geometry.radius * (step / 5) + 3
        parts.append(f'<text x="{x:.2f}" y="{y:.2f}" class="tick">{label}</text>')

    # --- header + legend ---------------------------------------------------
    parts.append(
        f'<text x="{size / 2:.2f}" y="28" text-anchor="middle" class="lbl" '
        f'style="font-size:15px;font-weight:600">Crusher TPM Competency Matrix'
        f"{f' - {escape(employee_name)}' if employee_name else ''}</text>"
    )

    if unassessed:
        parts.append(
            f'<text x="{size / 2:.2f}" y="{size - 14}" text-anchor="middle" '
            f'class="tick" fill="#c0392b">'
            f"{unassessed} of {count} competencies not yet assessed "
            f"(current polygon is incomplete)</text>"
        )

    if show_legend:
        entries = (
            (CURRENT_STROKE, "Current competency", False),
            (REQUIRED_STROKE, "Required for position", True),
            (UNASSESSED_STROKE, "Not yet assessed", None),
        )
        legend_y = size - (44 if unassessed else 26)
        for index, (colour, label, dashed) in enumerate(entries):
            x = size / 2 - 230 + index * 155
            dash = ' stroke-dasharray="5 3"' if dashed else ""
            parts.append(
                f'<rect x="{x:.2f}" y="{legend_y - 8}" width="16" height="9" fill="none" '
                f'stroke="{colour}" stroke-width="2"{dash} rx="2"/>'
            )
            parts.append(
                f'<text x="{x + 22:.2f}" y="{legend_y}" class="tick">{escape(label)}</text>'
            )

    parts.append("</svg>")
    return "\n".join(parts)
