# EFLOW - TPM Maintenance Competency Matrix System

Web system for supervisors to assess, track and visualise the competency of
Crusher-division maintenance staff against a role-based requirement matrix.

```
sql/001_schema.sql              authoritative schema (reference)
sql/002_migration_crusher.sql   the 13 Crusher competencies + required scores
seed/migrate.py                 idempotent migration runner
app/scoring.py                  rating scale, overall %, gap analysis  (no DB deps)
app/repository.py               all SQL lives here
app/radar.py                    spider chart -> dependency-free SVG
app/reports.py                  5 reports -> PDF (reportlab) + Excel (openpyxl)
app/server.py                   FastAPI: dashboard, assessment form, JSON API
app/templates/                  Jinja2 views
tests/                          102 tests
docs/REPORTING.md               report contents + library alternatives
```

## Setup

```powershell
python -m pip install fastapi uvicorn jinja2 openpyxl reportlab svglib pytest
python seed\migrate.py          # apply migrations (safe to re-run)
python run.py                   # http://127.0.0.1:8000
```

`run.py` also takes `--migrate` and `--reports` (regenerate all five reports
without starting the server).

## Routes

| Path | Purpose |
|------|---------|
| `/` | Employee list |
| `/employee/{id}` | Dashboard: header, spider chart, ratings, gaps, history |
| `/employee/{id}/chart.svg?size=` | Spider chart as SVG |
| `/assess/{id}` | Supervisor assessment form with live overall-% preview |
| `/reports` | PDF / Excel downloads for all five reports |

JSON API: `/api/employees`, `/api/employees/{id}`, `/api/employees/{id}/gaps`,
`/api/competencies`, `/api/positions`, `/api/departments`,
`/api/scoring/rating-scale`, `POST /api/scoring/preview`,
`POST /api/assessments`. Interactive docs at `/docs`.

## Scoring rules

Rating conversion: `5=100%`, `4=80%`, `3=60%`, `2=40%`, `1=20%`, `0=0%`
(Expert / Highly Competent / Reasonably Competent / Under Training /
Low or Very Basic / None).

Overall = `(total rating / maximum possible rating) × 100`. Ten competencies
with a total of 40 out of a maximum 50 = 80%.

Gap analysis compares the position's `required_rating` with the employee's
`rating_score`. `current >= required` → **Achieved**; `current < required` →
**Gap** with a numeric shortfall. A competency nobody has assessed is
**Unassessed**, not 0.

### Why unassessed is not zero

The spec defines `0 = None = 0%` as a deliberate supervisor judgement.
Collapsing "never assessed" onto 0 would understate the employee and flood
the training-needs report with false "training required" rows. Instead:

- unassessed competencies are **excluded from the overall percentage**, which
  is computed over assessed competencies only;
- **assessment coverage** is reported alongside it (`10/23 assessed, 43.5%`);
- on the spider chart the current polygon **breaks** at an unassessed axis and
  a hollow marker is drawn — a plotted 0 would read as "rated as None";
- in the training-needs report they appear as *"Schedule assessment first"*,
  which is the correct next action — you cannot train a gap you have not
  measured.

Gap priority banding: `Unassessed` or a maximum requirement (5) or a
Safety & Compliance shortfall → **Critical**; shortfall ≥ 2 → **High**;
shortfall 1 → **Medium**; achieved → **Low**.

## Data model notes

The database already existed with real Crusher data (5 employees, 4
positions, 10 generic TPM competencies, 92 requirement rows). The 13 Crusher
competencies from the specification were **added** alongside the existing 10
rather than replacing them, giving a **23-axis** matrix. The migration is
additive and idempotent, and a backup of the original file is at
`data/tpm_matrix.db.bak-20260928`.

Also added: `employees.years_of_experience` (backfilled from `join_date`),
`competencies.sort_order` (stable radar axis order), and
`employee_current_scores.assessment_id` (traceability from a current score
back to the assessment that produced it).

Two known data gaps, both pre-existing rather than introduced here:

1. `assessment_scores` is empty, so the two historical assessments
   (`ass-01`, `ass-02`) have no per-competency breakdown. The progress report
   can therefore only trend them at the overall-percentage level. This is not
   recoverable from the current database; new assessments recorded through the
   app do populate it.
2. `employees.supervisor` and `employees.department` are free text rather
   than foreign keys, and `positions` has a `department` column that can
   disagree with `employees.department`. Worth normalising if you later want
   supervisor-scoped logins or department hierarchies.
