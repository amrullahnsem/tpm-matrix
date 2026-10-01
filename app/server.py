"""FastAPI application: employee dashboard, assessment form, reports, JSON API.

Run with:
    python -m uvicorn app.server:app --reload --port 8000
"""

from __future__ import annotations

import datetime as dt
import os
from dataclasses import asdict
from pathlib import Path

from fastapi import FastAPI, Form, HTTPException, Request
from fastapi.responses import FileResponse, HTMLResponse, JSONResponse, Response
from fastapi.templating import Jinja2Templates

from . import reports as report_builder
from .radar import render_radar_svg
from .repository import Repository, camelize
from .scoring import RATING_SCALE, calculate_overall

ROOT = Path(__file__).resolve().parent.parent
TEMPLATES_DIR = Path(__file__).resolve().parent / "templates"
OUTPUT_DIR = Path(os.getenv("TPM_REPORTS_DIR", ROOT / "data" / "reports"))
OUTPUT_DIR.mkdir(parents=True, exist_ok=True)

app = FastAPI(
    title="Hume TPM Maintenance Competency Matrix",
    description="Assess, track and visualise Crusher division maintenance competency.",
    version="1.0.0",
)
templates = Jinja2Templates(directory=str(TEMPLATES_DIR))
repo = Repository()


def _rating_options() -> list[dict[str, object]]:
    return [
        {"value": rating, "label": f"{rating} - {descriptor.label} ({descriptor.percentage}%)"}
        for rating, descriptor in sorted(RATING_SCALE.items(), reverse=True)
    ]


# ---------------------------------------------------------------------------
# HTML views
# ---------------------------------------------------------------------------

@app.get("/", response_class=HTMLResponse)
def employee_list(request: Request):
    return templates.TemplateResponse(
        request, "employees.html",
        {
            "employees": repo.list_employees(),
            "departments": repo.list_departments(),
            "today": dt.date.today().isoformat(),
        },
    )


@app.get("/employee/{employee_id}", response_class=HTMLResponse)
def employee_dashboard(request: Request, employee_id: str):
    try:
        profile = repo.get_profile(employee_id)
    except LookupError:
        raise HTTPException(status_code=404, detail=f"Employee {employee_id} not found")
    return templates.TemplateResponse(
        request, "dashboard.html",
        {
            "profile": profile,
            "employee": profile.employee,
            "today": dt.date.today().isoformat(),
        },
    )


@app.get("/employee/{employee_id}/chart.svg")
def employee_chart(employee_id: str, size: int = 1000):
    try:
        profile = repo.get_profile(employee_id)
    except LookupError:
        raise HTTPException(status_code=404, detail=f"Employee {employee_id} not found")
    svg = render_radar_svg(profile.scores, size=size, employee_name=profile.employee.full_name)
    return Response(svg, media_type="image/svg+xml")


@app.get("/assess/{employee_id}", response_class=HTMLResponse)
def assessment_form(request: Request, employee_id: str):
    try:
        profile = repo.get_profile(employee_id)
    except LookupError:
        raise HTTPException(status_code=404, detail=f"Employee {employee_id} not found")
    return templates.TemplateResponse(
        request, "assess.html",
        {
            "profile": profile,
            "employee": profile.employee,
            "ratings": _rating_options(),
            "cycles": ["2026 Q3 Periodic Review", "2026 Q4 Periodic Review", "2027 Q1 Periodic Review"],
            "today": dt.date.today().isoformat(),
            "saved": request.query_params.get("saved") == "1",
        },
    )


@app.post("/assess/{employee_id}")
def submit_assessment(
    request: Request,
    employee_id: str,
    cycle_name: str = Form(...),
    assessor_name: str = Form(...),
    assessment_date: str = Form(...),
    remarks: str = Form(""),
    **raw_ratings: str,
):
    ratings: dict[str, int] = {}
    for key, value in raw_ratings.items():
        if key.startswith("rating_") and value not in ("", None):
            ratings[key.removeprefix("rating_")] = int(value)
    try:
        repo.record_assessment(
            employee_id=employee_id,
            assessor_name=assessor_name,
            cycle_name=cycle_name,
            assessment_date=assessment_date,
            ratings=ratings,
            remarks=remarks or None,
        )
    except (LookupError, ValueError) as exc:
        raise HTTPException(status_code=400, detail=str(exc))
    return templates.TemplateResponse(
        request, "assess.html",
        {
            "profile": repo.get_profile(employee_id),
            "employee": repo.get_profile(employee_id).employee,
            "ratings": _rating_options(),
            "cycles": ["2026 Q3 Periodic Review", "2026 Q4 Periodic Review", "2027 Q1 Periodic Review"],
            "today": dt.date.today().isoformat(),
            "saved": True,
        },
    )


@app.get("/reports", response_class=HTMLResponse)
def reports_index(request: Request):
    return templates.TemplateResponse(
        request, "reports.html",
        {
            "employees": repo.list_employees(),
            "departments": repo.list_departments(),
            "today": dt.date.today().isoformat(),
        },
    )


@app.get("/reports/{kind}/download")
def download_report(kind: str, employee: str | None = None, department: str | None = None, fmt: str = "pdf"):
    """Generate (or re-generate) a report on demand and stream it back."""
    if fmt not in ("pdf", "xlsx"):
        raise HTTPException(status_code=400, detail="fmt must be pdf or xlsx")
    wanted = (fmt,)
    try:
        if kind == "individual":
            if not employee:
                raise HTTPException(status_code=400, detail="employee is required")
            artifact = report_builder.individual_competency_report(repo, employee, OUTPUT_DIR, fmt=wanted)
        elif kind == "department":
            if not department:
                raise HTTPException(status_code=400, detail="department is required")
            artifact = report_builder.department_competency_report(repo, department, OUTPUT_DIR, fmt=wanted)
        elif kind == "gap":
            artifact = report_builder.competency_gap_report(repo, OUTPUT_DIR, department=department, fmt=wanted)
        elif kind == "training":
            artifact = report_builder.training_needs_report(repo, OUTPUT_DIR, department=department, fmt=wanted)
        elif kind == "progress":
            if not employee:
                raise HTTPException(status_code=400, detail="employee is required")
            artifact = report_builder.competency_progress_report(repo, employee, OUTPUT_DIR, fmt=wanted)
        else:
            raise HTTPException(status_code=404, detail=f"unknown report '{kind}'")
    except LookupError as exc:
        raise HTTPException(status_code=404, detail=str(exc))

    path = artifact.pdf if fmt == "pdf" else artifact.xlsx
    if path is None or not Path(path).exists():
        raise HTTPException(status_code=500, detail="report generation failed")
    media = "application/pdf" if fmt == "pdf" else "application/vnd.openxmlformats-officedocument.spreadsheetml.sheet"
    return FileResponse(path, media_type=media, filename=Path(path).name)


# ---------------------------------------------------------------------------
# JSON API
# ---------------------------------------------------------------------------

@app.get("/api/employees")
def api_employees(department: str | None = None):
    return {"employees": [e.to_dict() for e in repo.list_employees(department=department)]}


@app.get("/api/employees/{employee_id}")
def api_employee(employee_id: str):
    try:
        return repo.get_profile(employee_id).to_dict()
    except LookupError:
        raise HTTPException(status_code=404, detail=f"Employee {employee_id} not found")


@app.get("/api/employees/{employee_id}/gaps")
def api_employee_gaps(employee_id: str, actionable_only: bool = False):
    try:
        gaps = repo.get_profile(employee_id).gaps
    except LookupError:
        raise HTTPException(status_code=404, detail=f"Employee {employee_id} not found")
    if actionable_only:
        gaps = [g for g in gaps if g.is_actionable]
    return {"gaps": [g.to_dict() for g in gaps]}


@app.get("/api/competencies")
def api_competencies():
    return {"competencies": [c.to_dict() for c in repo.list_competencies()]}


@app.get("/api/positions")
def api_positions():
    return {"positions": repo.list_positions()}


@app.get("/api/departments")
def api_departments():
    summaries = [
        camelize(asdict(repo.department_summary(department)))
        for department in repo.list_departments()
    ]
    return {"departments": summaries}


@app.get("/api/scoring/rating-scale")
def api_rating_scale():
    return {
        "scale": [
            {"rating": r, "percentage": d.percentage, "label": d.label}
            for r, d in sorted(RATING_SCALE.items(), reverse=True)
        ]
    }


@app.post("/api/scoring/preview")
async def api_score_preview(request: Request):
    """Live overall-competency preview for the assessment form.

    The browser posts the current form state and the *server* runs the same
    scoring engine used at submission time, so the number a supervisor sees
    before saving can never disagree with the number stored afterwards.
    """
    payload = await request.json()
    ratings = payload.get("ratings", {})
    required = payload.get("required", {})
    if not isinstance(ratings, dict) or not isinstance(required, dict):
        return JSONResponse({"error": "ratings and required must be objects"}, status_code=400)

    # The axis set must be the union of both maps: a competency that carries a
    # requirement but has not been rated yet has to appear in the denominator
    # and be counted as unassessed. Keying off `ratings` alone would report
    # 100% coverage before the supervisor has rated anything.
    keys = list(dict.fromkeys([*required, *ratings]))
    series: list[int | None] = []
    mask: list[bool] = []
    for key in keys:
        mask.append(bool(required.get(key, 0)))
        value = ratings.get(key)
        series.append(None if value in (None, "", "unassessed") else int(value))

    result = calculate_overall(series, required_only=mask)
    return {
        "overallPercentage": result.percentage,
        "totalRating": result.total_rating,
        "maxPossibleRating": result.max_possible_rating,
        "assessedCount": result.assessed_count,
        "unassessedCount": result.unassessed_count,
        "coveragePercentage": round(result.coverage_percentage, 2),
    }


@app.post("/api/assessments")
async def api_create_assessment(request: Request):
    payload = await request.json()
    try:
        assessment = repo.record_assessment(
            employee_id=payload["employeeId"],
            assessor_name=payload["assessorName"],
            cycle_name=payload["cycleName"],
            assessment_date=payload.get("assessmentDate"),
            ratings={k: int(v) for k, v in payload["ratings"].items()},
            remarks=payload.get("remarks"),
        )
    except KeyError as exc:
        return JSONResponse({"error": f"missing field {exc}"}, status_code=400)
    except (LookupError, ValueError) as exc:
        return JSONResponse({"error": str(exc)}, status_code=400)
    return {"assessment": assessment.to_dict()}


# ---------------------------------------------------------------------------
# Health check endpoints
# ---------------------------------------------------------------------------

@app.get("/healthz", tags=["System"])
@app.get("/api/health", tags=["System"])
def health_check():
    """Liveness and readiness probe for Docker / Kubernetes / load balancers."""
    return {
        "status": "ok",
        "app": "eflow-tpm-matrix",
        "version": app.version,
        "database": "connected" if repo.db_path.exists() else "not_found",
    }

