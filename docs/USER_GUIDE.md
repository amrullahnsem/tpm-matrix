# Hume EFLOW - TPM Maintenance Competency Matrix
## User Guide & Standard Operating Procedure (SOP)

---

## 1. System Overview

The **EFLOW TPM Maintenance Competency Matrix** is a dedicated web-based assessment and analytics platform designed for Hume Cement's Crusher Maintenance Division. It empowers supervisors and engineering management to:

- Assess technicians and operators across **23 specific TPM and Crusher maintenance competencies**.
- Compare current competency levels against **role-specific baseline requirements**.
- Visualize skill coverage and balance with dynamic **23-axis Spider (Radar) Charts**.
- Automatically pinpoint **competency shortfalls** and assign priority rankings.
- Generate and export **5 management reports** in **PDF** and **Excel (XLSX)** format.

---

## 2. Accessing the System

Ensure the server is running on localhost (Port 8000):
- **Web Application URL:** [http://localhost:8000](http://localhost:8000)
- **API Documentation:** [http://localhost:8000/docs](http://localhost:8000/docs)

---

## 3. Core Modules & How to Use Them

### 3.1. Employee Directory (`/`)
* **URL:** [http://localhost:8000/](http://localhost:8000/)
* **Purpose:** View all active personnel in the Crusher maintenance division.
* **How to Use:**
  1. The table lists employee number, full name, position, department, assigned supervisor, and tenure/experience.
  2. Click **"Dashboard"** to view an employee's detailed skill analysis and radar chart.
  3. Click **"Assess"** to record a new assessment cycle for that employee.

---

### 3.2. Competency Dashboard (`/employee/{id}`)
* **Example URL:** [http://localhost:8000/employee/emp-101](http://localhost:8000/employee/emp-101)
* **Key Components:**
  1. **Profile Header & KPI Cards:**
     - **Overall Competency (%):** Average rating score across all *assessed* competencies.
     - **Total Rating:** Sum of current rating points vs. maximum possible points.
     - **Assessed Coverage:** Ratio of competencies evaluated (e.g. `10/23`).
  2. **Spider (Radar) Chart:**
     - **Blue Solid Polygon:** Current assessed rating for the employee.
     - **Grey Dotted Line:** Required baseline score for their position.
     - **Chart Breaks / Hollow Circles:** Competencies that have **not yet been assessed** (distinct from a score of 0).
  3. **Individual Competency Ratings Table:**
     - Full list of all 23 competencies grouped into categories (Autonomous Maintenance, Mechanical, Electrical, Hydraulic, Lubrication, Safety, etc.).
     - Shows Current Rating, Required Rating, Status (*Achieved*, *Gap*, or *Unassessed*), Priority band, and Shortfall.
  4. **Identified Competency Gaps & Action Items:**
     - Filtered list highlighting competencies needing immediate supervisor or training intervention.
  5. **Assessment & Training History:**
     - Chronological record of historical assessment cycles and recorded training records.

---

### 3.3. Conducting a Supervisor Assessment (`/assess/{id}`)
* **Example URL:** [http://localhost:8000/assess/emp-101](http://localhost:8000/assess/emp-101)
* **Step-by-Step Instructions:**
  1. **Fill in Assessment Metadata:**
     - **Assessment Cycle:** Select the cycle (e.g., `2026-Q1`, `2026-Q2`, `Annual 2026`).
     - **Assessment Date:** Current date or date of physical inspection.
     - **Assessor:** Name or ID of the conducting supervisor.
  2. **Score Competencies (0 to 5):**
     - For each competency, select the observed level from the dropdown:
       * `-- not assessed --` : Keep unassessed if not evaluated during this cycle.
       * `0 - None (0%)` : Has no knowledge or capability.
       * `1 - Low or Very Basic (20%)` : Requires constant direct supervision.
       * `2 - Under Training (40%)` : Performs basic tasks with regular assistance.
       * `3 - Reasonably Competent (60%)` : Performs standard tasks independently.
       * `4 - Highly Competent (80%)` : Fluent execution; troubleshoots non-routine faults.
       * `5 - Expert (100%)` : Master level; trains and mentors others.
  3. **Monitor the Live Scoring Bar (Bottom of screen):**
     - As ratings are adjusted, the sticky bottom bar dynamically calculates:
       * **Live Overall Competency %**
       * **Total Score / Max Possible**
       * **Assessment Coverage %**
  4. **Add Remarks & Submit:**
     - Enter overall observations, development areas, or justification notes in the **Remarks** field.
     - Click **"Submit assessment"**.
     - The employee's profile and database scores will update immediately.

---

### 3.4. Generating Reports & Exports (`/reports`)
* **URL:** [http://localhost:8000/reports](http://localhost:8000/reports)
* **Available Reports:**

| # | Report Name | Description & Use Case | Formats |
|---|---|---|---|
| **1** | **Individual Competency Report** | Complete profile for one employee, including **embedded spider chart**, all 23 competencies, gap analysis, and training history. | PDF, Excel |
| **2** | **Department Competency Report** | Department roll-up ranking employees by score, team average per competency, and identifying overall team strengths/weaknesses. | PDF, Excel |
| **3** | **Competency Gap Report** | Highlights all staff falling below required levels, sorted by shortfall severity and urgency. | PDF, Excel |
| **4** | **Training Needs Report** | Aggregates individual gaps into an actionable department training plan (number of staff affected and suggested courses). | PDF, Excel |
| **5** | **Competency Progress Report** | Tracks evaluation progress across cycles, showing percentage growth and score changes over time. | PDF, Excel |

* **How to Download:**
  1. Select the target **Employee** or **Department** from the respective dropdown.
  2. Click **"Download PDF"** for formal review/printing or **"Download Excel"** for data analysis.

---

## 4. Scoring Logic & Methodological Rules

### 4.1. Rating Conversion Table
| Level | Descriptor | Percentage | Operational Meaning |
|:---:|---|:---:|---|
| **5** | Expert | **100%** | Subject matter expert, can lead improvements & train others |
| **4** | Highly Competent | **80%** | Independent, handles complex maintenance & troubleshooting |
| **3** | Reasonably Competent | **60%** | Meets baseline requirements for standard operation |
| **2** | Under Training | **40%** | Developing skills, requires supervision |
| **1** | Low / Very Basic | **20%** | Minimal awareness, apprentice/helper level |
| **0** | None | **0%** | Deliberate assessment: zero knowledge/skill |
| **-** | *Not Assessed* | *N/A* | Skipped / not evaluated yet |

### 4.2. Why "Unassessed" is NOT Zero
In TPM matrices, treating an unassessed skill as `0` would falsely indicate severe incompetence and distort training budgets.
- **Unassessed competencies are excluded from the Overall % calculation.**
- On the **Spider Chart**, unassessed axes are rendered with a broken line and hollow circle rather than a flat line at 0.
- In the **Training Needs Report**, unassessed competencies prompt: *"Schedule assessment first"* before allocating training budget.

### 4.3. Gap Priority Banding
Gaps between current and required scores are categorized automatically:
* **Critical:** Any Unassessed skill for a required role, any requirement at Level 5, or any shortfall in **Safety & Compliance**.
* **High:** Rating shortfall of $\ge 2$ points below requirement.
* **Medium:** Rating shortfall of $1$ point below requirement.
* **Low / Achieved:** Meets or exceeds requirement.

---

## 5. Technical Administration & Maintenance

### Starting the Server
```powershell
# From the project root (c:\eflow-tpm-matrix)
python run.py --port 8000
```

### CLI Utilities
```powershell
# Apply database migrations
python seed\migrate.py

# Re-generate all 5 report sample files in batch
python run.py --reports

# Run automated tests
pytest
```
