"""Export SQLite database schema and data to MySQL compatible SQL script."""

import sqlite3
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
DB_PATH = ROOT / "data" / "tpm_matrix.db"
OUTPUT_FILE = ROOT / "sql" / "mysql_schema.sql"

SCHEMA_SQL = """-- =====================================================================
-- EFLOW TPM Maintenance Competency Matrix System
-- Canonical schema for MySQL / MariaDB (HeidiSQL compatible)
-- =====================================================================

CREATE DATABASE IF NOT EXISTS `tpm_matrix` 
  DEFAULT CHARACTER SET utf8mb4 
  DEFAULT COLLATE utf8mb4_unicode_ci;

USE `tpm_matrix`;

SET FOREIGN_KEY_CHECKS = 0;

-- ---------------------------------------------------------------------
-- positions
-- ---------------------------------------------------------------------
DROP TABLE IF EXISTS `positions`;
CREATE TABLE `positions` (
    `id` VARCHAR(64) NOT NULL PRIMARY KEY,
    `title` VARCHAR(255) NOT NULL UNIQUE,
    `department` VARCHAR(255) NOT NULL,
    `created_at` DATETIME NOT NULL DEFAULT CURRENT_TIMESTAMP
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4;

-- ---------------------------------------------------------------------
-- competencies
-- ---------------------------------------------------------------------
DROP TABLE IF EXISTS `competencies`;
CREATE TABLE `competencies` (
    `id` VARCHAR(64) NOT NULL PRIMARY KEY,
    `code` VARCHAR(64) NOT NULL UNIQUE,
    `name` VARCHAR(255) NOT NULL,
    `category` VARCHAR(100) NOT NULL,
    `description` TEXT,
    `sort_order` INT NOT NULL DEFAULT 100,
    `is_active` TINYINT(1) NOT NULL DEFAULT 1,
    `created_at` DATETIME NOT NULL DEFAULT CURRENT_TIMESTAMP,
    KEY `idx_competencies_sort` (`sort_order`, `id`)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4;

-- ---------------------------------------------------------------------
-- employees
-- ---------------------------------------------------------------------
DROP TABLE IF EXISTS `employees`;
CREATE TABLE `employees` (
    `id` VARCHAR(64) NOT NULL PRIMARY KEY,
    `employee_number` VARCHAR(64) NOT NULL UNIQUE,
    `full_name` VARCHAR(255) NOT NULL,
    `email` VARCHAR(255) UNIQUE,
    `department` VARCHAR(255) NOT NULL,
    `position_id` VARCHAR(64) NOT NULL,
    `supervisor` VARCHAR(255),
    `join_date` DATE,
    `years_of_experience` INT,
    `is_active` TINYINT(1) NOT NULL DEFAULT 1,
    `created_at` DATETIME NOT NULL DEFAULT CURRENT_TIMESTAMP,
    KEY `idx_employees_position` (`position_id`),
    KEY `idx_employees_dept` (`department`),
    CONSTRAINT `fk_emp_position` FOREIGN KEY (`position_id`) REFERENCES `positions` (`id`) ON UPDATE CASCADE
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4;

-- ---------------------------------------------------------------------
-- position_requirements
-- ---------------------------------------------------------------------
DROP TABLE IF EXISTS `position_requirements`;
CREATE TABLE `position_requirements` (
    `position_id` VARCHAR(64) NOT NULL,
    `competency_id` VARCHAR(64) NOT NULL,
    `required_rating` TINYINT NOT NULL CHECK (`required_rating` BETWEEN 0 AND 5),
    PRIMARY KEY (`position_id`, `competency_id`),
    CONSTRAINT `fk_req_pos` FOREIGN KEY (`position_id`) REFERENCES `positions` (`id`) ON DELETE CASCADE,
    CONSTRAINT `fk_req_comp` FOREIGN KEY (`competency_id`) REFERENCES `competencies` (`id`) ON DELETE CASCADE
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4;

-- ---------------------------------------------------------------------
-- assessments
-- ---------------------------------------------------------------------
DROP TABLE IF EXISTS `assessments`;
CREATE TABLE `assessments` (
    `id` VARCHAR(64) NOT NULL PRIMARY KEY,
    `employee_id` VARCHAR(64) NOT NULL,
    `cycle_name` VARCHAR(100) NOT NULL,
    `assessment_date` DATE NOT NULL,
    `assessor_name` VARCHAR(255) NOT NULL,
    `total_rating` INT NOT NULL,
    `max_possible_rating` INT NOT NULL,
    `overall_percentage` DECIMAL(5,2) NOT NULL,
    `remarks` TEXT,
    `created_at` DATETIME NOT NULL DEFAULT CURRENT_TIMESTAMP,
    KEY `idx_assessments_emp` (`employee_id`, `assessment_date`),
    CONSTRAINT `fk_assess_emp` FOREIGN KEY (`employee_id`) REFERENCES `employees` (`id`) ON DELETE CASCADE
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4;

-- ---------------------------------------------------------------------
-- assessment_scores
-- ---------------------------------------------------------------------
DROP TABLE IF EXISTS `assessment_scores`;
CREATE TABLE `assessment_scores` (
    `assessment_id` VARCHAR(64) NOT NULL,
    `competency_id` VARCHAR(64) NOT NULL,
    `rating` TINYINT NOT NULL CHECK (`rating` BETWEEN 0 AND 5),
    `percentage` DECIMAL(5,2) NOT NULL,
    PRIMARY KEY (`assessment_id`, `competency_id`),
    CONSTRAINT `fk_ascore_assess` FOREIGN KEY (`assessment_id`) REFERENCES `assessments` (`id`) ON DELETE CASCADE,
    CONSTRAINT `fk_ascore_comp` FOREIGN KEY (`competency_id`) REFERENCES `competencies` (`id`) ON DELETE CASCADE
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4;

-- ---------------------------------------------------------------------
-- employee_current_scores
-- ---------------------------------------------------------------------
DROP TABLE IF EXISTS `employee_current_scores`;
CREATE TABLE `employee_current_scores` (
    `employee_id` VARCHAR(64) NOT NULL,
    `competency_id` VARCHAR(64) NOT NULL,
    `rating` TINYINT NOT NULL DEFAULT 0 CHECK (`rating` BETWEEN 0 AND 5),
    `percentage` DECIMAL(5,2) NOT NULL DEFAULT 0,
    `assessment_id` VARCHAR(64) NULL,
    `updated_at` DATETIME NOT NULL DEFAULT CURRENT_TIMESTAMP,
    PRIMARY KEY (`employee_id`, `competency_id`),
    CONSTRAINT `fk_cscore_emp` FOREIGN KEY (`employee_id`) REFERENCES `employees` (`id`) ON DELETE CASCADE,
    CONSTRAINT `fk_cscore_comp` FOREIGN KEY (`competency_id`) REFERENCES `competencies` (`id`) ON DELETE CASCADE,
    CONSTRAINT `fk_cscore_assess` FOREIGN KEY (`assessment_id`) REFERENCES `assessments` (`id`) ON DELETE SET NULL
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4;

-- ---------------------------------------------------------------------
-- training_records
-- ---------------------------------------------------------------------
DROP TABLE IF EXISTS `training_records`;
CREATE TABLE `training_records` (
    `id` VARCHAR(64) NOT NULL PRIMARY KEY,
    `employee_id` VARCHAR(64) NOT NULL,
    `title` VARCHAR(255) NOT NULL,
    `provider` VARCHAR(255),
    `completion_date` DATE NOT NULL,
    `status` VARCHAR(50) NOT NULL DEFAULT 'Completed',
    `reassessment_cycle` VARCHAR(100),
    `created_at` DATETIME NOT NULL DEFAULT CURRENT_TIMESTAMP,
    KEY `idx_training_emp` (`employee_id`, `completion_date`),
    CONSTRAINT `fk_train_emp` FOREIGN KEY (`employee_id`) REFERENCES `employees` (`id`) ON DELETE CASCADE
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4;

SET FOREIGN_KEY_CHECKS = 1;
"""


def format_val(val) -> str:
    if val is None:
        return "NULL"
    if isinstance(val, (int, float)):
        return str(val)
    val_str = str(val).replace("\\", "\\\\").replace("'", "\\'")
    return f"'{val_str}'"


def export():
    conn = sqlite3.connect(DB_PATH)
    conn.row_factory = sqlite3.Row
    out = [SCHEMA_SQL, "\n-- =====================================================================",
           "-- Seed Data Export",
           "-- =====================================================================\n",
           "SET FOREIGN_KEY_CHECKS = 0;\n"]

    tables = [
        "positions",
        "competencies",
        "employees",
        "position_requirements",
        "assessments",
        "assessment_scores",
        "employee_current_scores",
        "training_records",
    ]

    for table in tables:
        rows = conn.execute(f"SELECT * FROM {table}").fetchall()
        if not rows:
            continue
        cols = [k for k in rows[0].keys()]
        cols_str = ", ".join(f"`{c}`" for c in cols)
        out.append(f"-- Data for table `{table}`")
        for row in rows:
            vals_str = ", ".join(format_val(row[c]) for c in cols)
            out.append(f"INSERT INTO `{table}` ({cols_str}) VALUES ({vals_str});")
        out.append("")

    out.append("SET FOREIGN_KEY_CHECKS = 1;\n")
    OUTPUT_FILE.write_text("\n".join(out), encoding="utf-8")
    print(f"Generated: {OUTPUT_FILE} ({OUTPUT_FILE.stat().st_size} bytes)")


if __name__ == "__main__":
    export()
