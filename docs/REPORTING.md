# Reporting & Export Notes

All five required reports are implemented in `app/reports.py`, each producing
a **PDF** and an **Excel** file.

| # | Report | Function | Contents |
|---|--------|----------|----------|
| 1 | Individual Competency | `individual_competency_report` | Header, **embedded spider chart**, full 23-axis matrix, gaps, assessment + training history |
| 2 | Department Competency | `department_competency_report` | Department roll-up, employees ranked by %, team average per competency |
| 3 | Competency Gap | `competency_gap_report` | Every shortfall, priority-banded, most urgent first |
| 4 | Training Needs | `training_needs_report` | Gaps grouped by competency into an actual training plan (staff affected, "schedule assessment" vs "schedule training") |
| 5 | Competency Progress | `competency_progress_report` | Assessment-over-assessment trend with delta in percentage points |

## Libraries used, and why

| Concern | Library | Rationale |
|---------|---------|-----------|
| PDF layout | `reportlab` | Pure Python — no system install, works on a locked-down plant server. |
| Chart → PDF | `svglib` | Converts the SVG from `app/radar.py` into a ReportLab `Drawing`, so the printed chart and the on-screen chart share one geometry implementation and cannot drift apart. |
| Excel | `openpyxl` | Maintained, supports styling, freeze panes and autofilter. |

The substitution points are deliberately narrow: `_write_pdf()` and
`_write_workbook()` are the only functions that touch ReportLab and openpyxl.
Swapping either library does not touch the report *content* logic.

## Alternatives, if you prefer them

**PDF**
- *WeasyPrint / Chromium headless* — author reports in HTML+CSS instead. Far
  better typographic control and easier to hand to a designer, at the cost of
  a native dependency (`weasyprint` needs Pango; headless Chrome needs a
  browser). You already have Edge available on this machine, so
  `msedge --headless --print-to-pdf` is a zero-install path to that route.
- *xhtml2pdf* — pure Python, lower fidelity, no external deps.
- *Docx/Pptx* — if the audience actually wants Word or PowerPoint rather than PDF.

**Excel**
- *xlsxwriter* — better charting and conditional formatting, write-only.
- *Tabulator (JS)* — if you want the grid rendered client-side instead.

**Charting (for the browser dashboard)**
The dashboard currently serves a server-rendered SVG, which works with no
JavaScript build step at all. If you later want a React dashboard (Node was
not available on this machine, so none was built), use:
- `react-chartjs-2` + `chart.js` radar scale, or
- `recharts` `<RadarChart>`, or
- `visx` / `D3` for full control.

Whichever you pick, keep the two rules the SVG renderer already enforces:
every axis is 0–100%, and an unassessed competency must render as a *break in
the polygon* plus a hollow marker — never as a zero.

## Known limitation

The two assessments that predate this application (`ass-01`, `ass-02`) have
no rows in `assessment_scores`, so the progress report can only trend them at
the **overall percentage** level. `progress_history()` exposes
`hasPerCompetencyDetail` per cycle, and the report prints a caveat. Recording
new assessments through the app populates the detail, after which
per-competency trending becomes available. The historical detail is not
recoverable from the current database.
