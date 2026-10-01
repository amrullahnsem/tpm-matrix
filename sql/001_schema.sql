-- =====================================================================
-- EFLOW TPM Maintenance Competency Matrix System
-- Canonical schema (SQLite dialect)
--
-- This file is the authoritative reference for the schema. The live
-- database at data/tpm_matrix.db was created from an earlier revision of
-- this schema; apply sql/002_migration_crusher.sql to bring it forward.
--
-- Design notes
--   * Positions/Competencies are the two axes of the matrix.
--   * position_requirements is the "RoleRequirement" join: it defines the
--     RequiredScore (0-5) expected of anyone holding a position.
--   * assessments + assessment_scores are the immutable assessment
--     history (an "AssessmentDetail" is an assessment_scores row).
--   * employee_current_scores is a denormalised cache of the most recent
--     assessment per employee, so dashboards do not have to scan history.
--   * A MISSING employee_current_scores row means "not yet assessed".
--     It is deliberately distinct from rating = 0 ("None"), which is a
--     deliberate supervisor judgement. See app/scoring.py.
-- =====================================================================

PRAGMA foreign_keys = ON;

-- ---------------------------------------------------------------------
-- positions  (a Qualification_Position)
-- ---------------------------------------------------------------------
CREATE TABLE IF NOT EXISTS positions (
    id          TEXT PRIMARY KEY,
    title       TEXT NOT NULL UNIQUE,
    department  TEXT NOT NULL,
    created_at  TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP
);

-- ---------------------------------------------------------------------
-- competencies  (a CompetencyMaster row)
--   sort_order drives the deterministic axis order of the spider chart.
-- ---------------------------------------------------------------------
CREATE TABLE IF NOT EXISTS competencies (
    id           TEXT PRIMARY KEY,
    code         TEXT NOT NULL UNIQUE,
    name         TEXT NOT NULL,
    category     TEXT NOT NULL,
    description  TEXT,
    sort_order   INTEGER NOT NULL DEFAULT 100,
    is_active    INTEGER NOT NULL DEFAULT 1,
    created_at   TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP
);

-- ---------------------------------------------------------------------
-- employees
--   years_of_experience is stored (not derived) because the spec requires
--   it as a first-class field, but seed/derived_values keeps it in sync
--   with join_date. supervisor is free text in the live data (the
--   supervisor is not modelled as an employee record).
-- ---------------------------------------------------------------------
CREATE TABLE IF NOT EXISTS employees (
    id                    TEXT PRIMARY KEY,
    employee_number       TEXT NOT NULL UNIQUE,
    full_name             TEXT NOT NULL,
    email                 TEXT UNIQUE,
    department            TEXT NOT NULL,
    position_id           TEXT NOT NULL REFERENCES positions(id),
    supervisor            TEXT,
    join_date             TEXT,
    years_of_experience   INTEGER,
    is_active             INTEGER NOT NULL DEFAULT 1,
    created_at            TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP
);

-- ---------------------------------------------------------------------
-- position_requirements  (a RoleRequirement row)
--   Maps a position to a competency with the required 0-5 score.
-- ---------------------------------------------------------------------
CREATE TABLE IF NOT EXISTS position_requirements (
    position_id       TEXT NOT NULL REFERENCES positions(id) ON DELETE CASCADE,
    competency_id     TEXT NOT NULL REFERENCES competencies(id) ON DELETE CASCADE,
    required_rating   INTEGER NOT NULL
                        CHECK (required_rating BETWEEN 0 AND 5),
    PRIMARY KEY (position_id, competency_id)
);

-- ---------------------------------------------------------------------
-- assessments  (one supervisor scoring event / cycle for one employee)
--   total_rating, max_possible_rating and overall_percentage are
--   persisted denormalised so historical reports stay stable even if the
--   scoring rules are later revised.
-- ---------------------------------------------------------------------
CREATE TABLE IF NOT EXISTS assessments (
    id                    TEXT PRIMARY KEY,
    employee_id           TEXT NOT NULL REFERENCES employees(id) ON DELETE CASCADE,
    cycle_name            TEXT NOT NULL,
    assessment_date       TEXT NOT NULL,
    assessor_name         TEXT NOT NULL,
    total_rating          INTEGER NOT NULL,
    max_possible_rating   INTEGER NOT NULL,
    overall_percentage    REAL NOT NULL,
    remarks               TEXT,
    created_at            TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP
);

-- ---------------------------------------------------------------------
-- assessment_scores  (an AssessmentDetail row: one per competency)
-- ---------------------------------------------------------------------
CREATE TABLE IF NOT EXISTS assessment_scores (
    assessment_id   TEXT NOT NULL REFERENCES assessments(id) ON DELETE CASCADE,
    competency_id   TEXT NOT NULL REFERENCES competencies(id) ON DELETE CASCADE,
    rating          INTEGER NOT NULL CHECK (rating BETWEEN 0 AND 5),
    percentage      INTEGER NOT NULL CHECK (percentage BETWEEN 0 AND 100),
    PRIMARY KEY (assessment_id, competency_id)
);

-- ---------------------------------------------------------------------
-- employee_current_scores
--   Denormalised "latest assessment" cache keyed by (employee, competency).
--   Absent row  => never assessed.
--   rating = 0  => assessed and judged "None".
-- ---------------------------------------------------------------------
CREATE TABLE IF NOT EXISTS employee_current_scores (
    employee_id     TEXT NOT NULL REFERENCES employees(id) ON DELETE CASCADE,
    competency_id   TEXT NOT NULL REFERENCES competencies(id) ON DELETE CASCADE,
    rating          INTEGER NOT NULL DEFAULT 0 CHECK (rating BETWEEN 0 AND 5),
    percentage      INTEGER NOT NULL DEFAULT 0 CHECK (percentage BETWEEN 0 AND 100),
    assessment_id   TEXT REFERENCES assessments(id) ON DELETE SET NULL,
    updated_at      TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP,
    PRIMARY KEY (employee_id, competency_id)
);

-- ---------------------------------------------------------------------
-- training_records
-- ---------------------------------------------------------------------
CREATE TABLE IF NOT EXISTS training_records (
    id                    TEXT PRIMARY KEY,
    employee_id           TEXT NOT NULL REFERENCES employees(id) ON DELETE CASCADE,
    title                 TEXT NOT NULL,
    provider              TEXT,
    completion_date       TEXT NOT NULL,
    status                TEXT NOT NULL DEFAULT 'Completed',
    reassessment_cycle    TEXT,
    created_at            TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP
);

-- ---------------------------------------------------------------------
-- Indexes for the reporting queries
-- ---------------------------------------------------------------------
CREATE INDEX IF NOT EXISTS idx_employees_position  ON employees(position_id);
CREATE INDEX IF NOT EXISTS idx_employees_dept     ON employees(department);
CREATE INDEX IF NOT EXISTS idx_assessments_emp     ON assessments(employee_id, assessment_date DESC);
CREATE INDEX IF NOT EXISTS idx_scores_emp          ON assessment_scores(assessment_id);
CREATE INDEX IF NOT EXISTS idx_current_scores      ON employee_current_scores(employee_id);
CREATE INDEX IF NOT EXISTS idx_training_emp        ON training_records(employee_id, completion_date DESC);
CREATE INDEX IF NOT EXISTS idx_competencies_sort   ON competencies(sort_order, id);
