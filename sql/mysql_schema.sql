-- =====================================================================
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


-- =====================================================================
-- Seed Data Export
-- =====================================================================

SET FOREIGN_KEY_CHECKS = 0;

-- Data for table `positions`
INSERT INTO `positions` (`id`, `title`, `department`, `created_at`) VALUES ('pos-1', 'Senior Mechanical Technician - Crusher', 'Crusher Maintenance', '2026-09-28 02:17:24');
INSERT INTO `positions` (`id`, `title`, `department`, `created_at`) VALUES ('pos-2', 'Mechanical Maintenance Technician', 'Crusher Maintenance', '2026-09-28 02:17:24');
INSERT INTO `positions` (`id`, `title`, `department`, `created_at`) VALUES ('pos-3', 'Crusher Operator & Inspector', 'Operations & TPM', '2026-09-28 02:17:24');
INSERT INTO `positions` (`id`, `title`, `department`, `created_at`) VALUES ('pos-4', 'Electrical & Automation Specialist', 'Crusher Maintenance', '2026-09-28 02:17:24');

-- Data for table `competencies`
INSERT INTO `competencies` (`id`, `code`, `name`, `category`, `description`, `is_active`, `created_at`, `sort_order`) VALUES ('comp-1', 'TPM-AM-01', 'Autonomous Maintenance', 'TPM Pillar', 'Operator cleaning, inspection, routine lubrication, and basic tightening.', 1, '2026-09-28 02:17:24', 2);
INSERT INTO `competencies` (`id`, `code`, `name`, `category`, `description`, `is_active`, `created_at`, `sort_order`) VALUES ('comp-2', 'TPM-PM-02', 'Planned Maintenance', 'TPM Pillar', 'Scheduled maintenance cycles, MTBF/MTTR tracking, overhaul procedures.', 1, '2026-09-28 02:17:24', 7);
INSERT INTO `competencies` (`id`, `code`, `name`, `category`, `description`, `is_active`, `created_at`, `sort_order`) VALUES ('comp-3', 'TPM-EI-03', 'Equipment Inspection', 'Inspection', 'Vibration, temperature, wear analysis of bearings, liners, and crusher jaws.', 1, '2026-09-28 02:17:24', 4);
INSERT INTO `competencies` (`id`, `code`, `name`, `category`, `description`, `is_active`, `created_at`, `sort_order`) VALUES ('comp-4', 'TPM-LUB-04', 'Lubrication', 'Mechanical', 'Lube spec selection, greasing frequency, oil sampling, contamination checks.', 1, '2026-09-28 02:17:24', 5);
INSERT INTO `competencies` (`id`, `code`, `name`, `category`, `description`, `is_active`, `created_at`, `sort_order`) VALUES ('comp-5', 'TPM-TB-05', 'Troubleshooting', 'Diagnostics', 'Hydraulic pressure drops, mechanical jams, sensor error diagnostics.', 1, '2026-09-28 02:17:24', 10);
INSERT INTO `competencies` (`id`, `code`, `name`, `category`, `description`, `is_active`, `created_at`, `sort_order`) VALUES ('comp-6', 'TPM-ME-06', 'Mechanical & Electrical Maintenance', 'Specialized', 'Motor alignment, drive belt tensioning, electrical interlock safety.', 1, '2026-09-28 02:17:24', 6);
INSERT INTO `competencies` (`id`, `code`, `name`, `category`, `description`, `is_active`, `created_at`, `sort_order`) VALUES ('comp-7', 'TPM-SF-07', 'Safety Procedures', 'Safety & Compliance', 'LOTO (Lockout/Tagout), confined space entry, crusher isolation protocol.', 1, '2026-09-28 02:17:24', 9);
INSERT INTO `competencies` (`id`, `code`, `name`, `category`, `description`, `is_active`, `created_at`, `sort_order`) VALUES ('comp-8', 'TPM-RCA-08', 'Root Cause Analysis', 'Engineering', '5-Why methodology, fishbone diagrams, recurring breakdown prevention.', 1, '2026-09-28 02:17:24', 8);
INSERT INTO `competencies` (`id`, `code`, `name`, `category`, `description`, `is_active`, `created_at`, `sort_order`) VALUES ('comp-9', 'TPM-5S-09', '5S & Workplace Organisation', 'Foundational', 'Tool shadowing, red tagging, standard work area maintenance.', 1, '2026-09-28 02:17:24', 1);
INSERT INTO `competencies` (`id`, `code`, `name`, `category`, `description`, `is_active`, `created_at`, `sort_order`) VALUES ('comp-10', 'TPM-DOC-10', 'TPM Documentation', 'Management', 'One Point Lessons (OPL), maintenance logbooks, EFLOW work orders.', 1, '2026-09-28 02:17:24', 3);
INSERT INTO `competencies` (`id`, `code`, `name`, `category`, `description`, `is_active`, `created_at`, `sort_order`) VALUES ('comp-101', 'TPM-CR-01', 'Crusher TPM Awareness & Pillars', 'TPM Pillar', 'Understands the 8 pillars of TPM and the role of the Crusher autonomous maintenance team.', 1, '2026-09-28 02:24:10', 101);
INSERT INTO `competencies` (`id`, `code`, `name`, `category`, `description`, `is_active`, `created_at`, `sort_order`) VALUES ('comp-102', 'TPM-CR-02', '5S at Crusher Area', 'Foundational', 'Sort, Set in order, Shine, Standardise, Sustain across crusher house, skirt and conveyor walkways.', 1, '2026-09-28 02:24:10', 102);
INSERT INTO `competencies` (`id`, `code`, `name`, `category`, `description`, `is_active`, `created_at`, `sort_order`) VALUES ('comp-103', 'TPM-CR-03', 'Visual Check (Vibration, Noise, Leaks)', 'Inspection', 'Detects abnormal vibration, noise or leakage during routine patrol using senses and basic aids.', 1, '2026-09-28 02:24:10', 103);
INSERT INTO `competencies` (`id`, `code`, `name`, `category`, `description`, `is_active`, `created_at`, `sort_order`) VALUES ('comp-104', 'TPM-CR-04', 'Cleaning, Lubrication & Tightening (CLIT)', 'TPM Pillar', 'Executes routine cleaning, greasing and fastener tightening to standard without guidance.', 1, '2026-09-28 02:24:10', 104);
INSERT INTO `competencies` (`id`, `code`, `name`, `category`, `description`, `is_active`, `created_at`, `sort_order`) VALUES ('comp-105', 'TPM-CR-05', 'Wear Part Inspection', 'Inspection', 'Inspects crusher wear parts, liners, mantles and cheek plates; measures wear against limit.', 1, '2026-09-28 02:24:10', 105);
INSERT INTO `competencies` (`id`, `code`, `name`, `category`, `description`, `is_active`, `created_at`, `sort_order`) VALUES ('comp-106', 'TPM-CR-06', 'Conveyor Belt Alignment & Skirt Maintenance', 'Mechanical', 'Maintains belt tracking, tension and skirt seals; identifies belt misalignment early.', 1, '2026-09-28 02:24:10', 106);
INSERT INTO `competencies` (`id`, `code`, `name`, `category`, `description`, `is_active`, `created_at`, `sort_order`) VALUES ('comp-107', 'TPM-CR-07', 'Crusher Shutdown SOP & Lock-Out Tag-Out (LOTO)', 'Safety & Compliance', 'Executes crusher shutdown SOP and LOTO exactly per procedure; zero deviation.', 1, '2026-09-28 02:24:10', 107);
INSERT INTO `competencies` (`id`, `code`, `name`, `category`, `description`, `is_active`, `created_at`, `sort_order`) VALUES ('comp-108', 'TPM-CR-08', 'Minor Defect Tagging & Reporting', 'Foundational', 'Tags minor defects immediately and reports them through the correct channel the same shift.', 1, '2026-09-28 02:24:10', 108);
INSERT INTO `competencies` (`id`, `code`, `name`, `category`, `description`, `is_active`, `created_at`, `sort_order`) VALUES ('comp-109', 'TPM-CR-09', 'PIMPS / Logbook Entry', 'Management', 'Maintains accurate and complete PIMPS / logbook entries for routine tasks.', 1, '2026-09-28 02:24:10', 109);
INSERT INTO `competencies` (`id`, `code`, `name`, `category`, `description`, `is_active`, `created_at`, `sort_order`) VALUES ('comp-110', 'TPM-CR-10', 'Preventive Maintenance Scheduling', 'Management', 'Plans and schedules preventive maintenance work in the CMMS within agreed windows.', 1, '2026-09-28 02:24:10', 110);
INSERT INTO `competencies` (`id`, `code`, `name`, `category`, `description`, `is_active`, `created_at`, `sort_order`) VALUES ('comp-111', 'TPM-CR-11', 'Root Cause Analysis (RCA)', 'Engineering', 'Applies structured RCA (5 Whys, fault tree) to crusher breakdowns and recurrences.', 1, '2026-09-28 02:24:10', 111);
INSERT INTO `competencies` (`id`, `code`, `name`, `category`, `description`, `is_active`, `created_at`, `sort_order`) VALUES ('comp-112', 'TPM-CR-12', 'Crusher Alignment & Gap checking', 'Mechanical', 'Checks crusher frame, shaft and liner alignment and the crushing gap setting.', 1, '2026-09-28 02:24:10', 112);
INSERT INTO `competencies` (`id`, `code`, `name`, `category`, `description`, `is_active`, `created_at`, `sort_order`) VALUES ('comp-113', 'TPM-CR-13', 'Electrical MCC & Motor Condition Monitoring', 'Specialized', 'Monitors crusher MCC, motor condition, thermal load and electrical protection settings.', 1, '2026-09-28 02:24:10', 113);

-- Data for table `employees`
INSERT INTO `employees` (`id`, `employee_number`, `full_name`, `email`, `department`, `position_id`, `supervisor`, `join_date`, `is_active`, `created_at`, `years_of_experience`) VALUES ('emp-101', 'EMP/CRU/0101', 'Mohd Ridzuan Bin Hashim', 'ridzuan.hashim@eflow.internal', 'Crusher Maintenance', 'pos-1', 'Abdul Aziz Bin Abdullah (aziz)', '2021-03-15', 1, '2026-09-28 02:17:24', 5);
INSERT INTO `employees` (`id`, `employee_number`, `full_name`, `email`, `department`, `position_id`, `supervisor`, `join_date`, `is_active`, `created_at`, `years_of_experience`) VALUES ('emp-102', 'EMP/CRU/0102', 'Ahmad Faizal Bin Othman', 'faizal.othman@eflow.internal', 'Crusher Maintenance', 'pos-2', 'Abdul Aziz Bin Abdullah (aziz)', '2022-07-01', 1, '2026-09-28 02:17:24', 4);
INSERT INTO `employees` (`id`, `employee_number`, `full_name`, `email`, `department`, `position_id`, `supervisor`, `join_date`, `is_active`, `created_at`, `years_of_experience`) VALUES ('emp-103', 'EMP/CRU/0103', 'Tan Wei Lun', 'weilun.tan@eflow.internal', 'Operations & TPM', 'pos-3', 'Abdul Aziz Bin Abdullah (aziz)', '2023-01-10', 1, '2026-09-28 02:17:24', 3);
INSERT INTO `employees` (`id`, `employee_number`, `full_name`, `email`, `department`, `position_id`, `supervisor`, `join_date`, `is_active`, `created_at`, `years_of_experience`) VALUES ('emp-104', 'EMP/CRU/0104', 'Siva Kumar a/l Raman', 'siva.kumar@eflow.internal', 'Crusher Maintenance', 'pos-4', 'Abdul Aziz Bin Abdullah (aziz)', '2020-05-18', 1, '2026-09-28 02:17:24', 6);
INSERT INTO `employees` (`id`, `employee_number`, `full_name`, `email`, `department`, `position_id`, `supervisor`, `join_date`, `is_active`, `created_at`, `years_of_experience`) VALUES ('emp-105', 'EMP/CRU/0105', 'Mohamad Amirul Bin Zakaria', 'amirul.zakaria@eflow.internal', 'Crusher Maintenance', 'pos-2', 'Abdul Aziz Bin Abdullah (aziz)', '2024-02-01', 1, '2026-09-28 02:17:24', 2);

-- Data for table `position_requirements`
INSERT INTO `position_requirements` (`position_id`, `competency_id`, `required_rating`) VALUES ('pos-1', 'comp-1', 5);
INSERT INTO `position_requirements` (`position_id`, `competency_id`, `required_rating`) VALUES ('pos-1', 'comp-2', 5);
INSERT INTO `position_requirements` (`position_id`, `competency_id`, `required_rating`) VALUES ('pos-1', 'comp-3', 5);
INSERT INTO `position_requirements` (`position_id`, `competency_id`, `required_rating`) VALUES ('pos-1', 'comp-4', 4);
INSERT INTO `position_requirements` (`position_id`, `competency_id`, `required_rating`) VALUES ('pos-1', 'comp-5', 5);
INSERT INTO `position_requirements` (`position_id`, `competency_id`, `required_rating`) VALUES ('pos-1', 'comp-6', 5);
INSERT INTO `position_requirements` (`position_id`, `competency_id`, `required_rating`) VALUES ('pos-1', 'comp-7', 5);
INSERT INTO `position_requirements` (`position_id`, `competency_id`, `required_rating`) VALUES ('pos-1', 'comp-8', 4);
INSERT INTO `position_requirements` (`position_id`, `competency_id`, `required_rating`) VALUES ('pos-1', 'comp-9', 4);
INSERT INTO `position_requirements` (`position_id`, `competency_id`, `required_rating`) VALUES ('pos-1', 'comp-10', 4);
INSERT INTO `position_requirements` (`position_id`, `competency_id`, `required_rating`) VALUES ('pos-2', 'comp-1', 4);
INSERT INTO `position_requirements` (`position_id`, `competency_id`, `required_rating`) VALUES ('pos-2', 'comp-2', 4);
INSERT INTO `position_requirements` (`position_id`, `competency_id`, `required_rating`) VALUES ('pos-2', 'comp-3', 4);
INSERT INTO `position_requirements` (`position_id`, `competency_id`, `required_rating`) VALUES ('pos-2', 'comp-4', 4);
INSERT INTO `position_requirements` (`position_id`, `competency_id`, `required_rating`) VALUES ('pos-2', 'comp-5', 4);
INSERT INTO `position_requirements` (`position_id`, `competency_id`, `required_rating`) VALUES ('pos-2', 'comp-6', 4);
INSERT INTO `position_requirements` (`position_id`, `competency_id`, `required_rating`) VALUES ('pos-2', 'comp-7', 5);
INSERT INTO `position_requirements` (`position_id`, `competency_id`, `required_rating`) VALUES ('pos-2', 'comp-8', 3);
INSERT INTO `position_requirements` (`position_id`, `competency_id`, `required_rating`) VALUES ('pos-2', 'comp-9', 4);
INSERT INTO `position_requirements` (`position_id`, `competency_id`, `required_rating`) VALUES ('pos-2', 'comp-10', 3);
INSERT INTO `position_requirements` (`position_id`, `competency_id`, `required_rating`) VALUES ('pos-3', 'comp-1', 4);
INSERT INTO `position_requirements` (`position_id`, `competency_id`, `required_rating`) VALUES ('pos-3', 'comp-2', 3);
INSERT INTO `position_requirements` (`position_id`, `competency_id`, `required_rating`) VALUES ('pos-3', 'comp-3', 4);
INSERT INTO `position_requirements` (`position_id`, `competency_id`, `required_rating`) VALUES ('pos-3', 'comp-4', 4);
INSERT INTO `position_requirements` (`position_id`, `competency_id`, `required_rating`) VALUES ('pos-3', 'comp-5', 3);
INSERT INTO `position_requirements` (`position_id`, `competency_id`, `required_rating`) VALUES ('pos-3', 'comp-6', 3);
INSERT INTO `position_requirements` (`position_id`, `competency_id`, `required_rating`) VALUES ('pos-3', 'comp-7', 5);
INSERT INTO `position_requirements` (`position_id`, `competency_id`, `required_rating`) VALUES ('pos-3', 'comp-8', 2);
INSERT INTO `position_requirements` (`position_id`, `competency_id`, `required_rating`) VALUES ('pos-3', 'comp-9', 5);
INSERT INTO `position_requirements` (`position_id`, `competency_id`, `required_rating`) VALUES ('pos-3', 'comp-10', 3);
INSERT INTO `position_requirements` (`position_id`, `competency_id`, `required_rating`) VALUES ('pos-4', 'comp-1', 3);
INSERT INTO `position_requirements` (`position_id`, `competency_id`, `required_rating`) VALUES ('pos-4', 'comp-2', 4);
INSERT INTO `position_requirements` (`position_id`, `competency_id`, `required_rating`) VALUES ('pos-4', 'comp-3', 4);
INSERT INTO `position_requirements` (`position_id`, `competency_id`, `required_rating`) VALUES ('pos-4', 'comp-4', 3);
INSERT INTO `position_requirements` (`position_id`, `competency_id`, `required_rating`) VALUES ('pos-4', 'comp-5', 5);
INSERT INTO `position_requirements` (`position_id`, `competency_id`, `required_rating`) VALUES ('pos-4', 'comp-6', 5);
INSERT INTO `position_requirements` (`position_id`, `competency_id`, `required_rating`) VALUES ('pos-4', 'comp-7', 5);
INSERT INTO `position_requirements` (`position_id`, `competency_id`, `required_rating`) VALUES ('pos-4', 'comp-8', 4);
INSERT INTO `position_requirements` (`position_id`, `competency_id`, `required_rating`) VALUES ('pos-4', 'comp-9', 4);
INSERT INTO `position_requirements` (`position_id`, `competency_id`, `required_rating`) VALUES ('pos-4', 'comp-10', 4);
INSERT INTO `position_requirements` (`position_id`, `competency_id`, `required_rating`) VALUES ('pos-1', 'comp-101', 5);
INSERT INTO `position_requirements` (`position_id`, `competency_id`, `required_rating`) VALUES ('pos-1', 'comp-102', 5);
INSERT INTO `position_requirements` (`position_id`, `competency_id`, `required_rating`) VALUES ('pos-1', 'comp-103', 5);
INSERT INTO `position_requirements` (`position_id`, `competency_id`, `required_rating`) VALUES ('pos-1', 'comp-104', 5);
INSERT INTO `position_requirements` (`position_id`, `competency_id`, `required_rating`) VALUES ('pos-1', 'comp-105', 5);
INSERT INTO `position_requirements` (`position_id`, `competency_id`, `required_rating`) VALUES ('pos-1', 'comp-106', 4);
INSERT INTO `position_requirements` (`position_id`, `competency_id`, `required_rating`) VALUES ('pos-1', 'comp-107', 5);
INSERT INTO `position_requirements` (`position_id`, `competency_id`, `required_rating`) VALUES ('pos-1', 'comp-108', 4);
INSERT INTO `position_requirements` (`position_id`, `competency_id`, `required_rating`) VALUES ('pos-1', 'comp-109', 4);
INSERT INTO `position_requirements` (`position_id`, `competency_id`, `required_rating`) VALUES ('pos-1', 'comp-110', 4);
INSERT INTO `position_requirements` (`position_id`, `competency_id`, `required_rating`) VALUES ('pos-1', 'comp-111', 4);
INSERT INTO `position_requirements` (`position_id`, `competency_id`, `required_rating`) VALUES ('pos-1', 'comp-112', 5);
INSERT INTO `position_requirements` (`position_id`, `competency_id`, `required_rating`) VALUES ('pos-1', 'comp-113', 3);
INSERT INTO `position_requirements` (`position_id`, `competency_id`, `required_rating`) VALUES ('pos-2', 'comp-101', 4);
INSERT INTO `position_requirements` (`position_id`, `competency_id`, `required_rating`) VALUES ('pos-2', 'comp-102', 4);
INSERT INTO `position_requirements` (`position_id`, `competency_id`, `required_rating`) VALUES ('pos-2', 'comp-103', 4);
INSERT INTO `position_requirements` (`position_id`, `competency_id`, `required_rating`) VALUES ('pos-2', 'comp-104', 5);
INSERT INTO `position_requirements` (`position_id`, `competency_id`, `required_rating`) VALUES ('pos-2', 'comp-105', 4);
INSERT INTO `position_requirements` (`position_id`, `competency_id`, `required_rating`) VALUES ('pos-2', 'comp-106', 4);
INSERT INTO `position_requirements` (`position_id`, `competency_id`, `required_rating`) VALUES ('pos-2', 'comp-107', 5);
INSERT INTO `position_requirements` (`position_id`, `competency_id`, `required_rating`) VALUES ('pos-2', 'comp-108', 4);
INSERT INTO `position_requirements` (`position_id`, `competency_id`, `required_rating`) VALUES ('pos-2', 'comp-109', 3);
INSERT INTO `position_requirements` (`position_id`, `competency_id`, `required_rating`) VALUES ('pos-2', 'comp-110', 3);
INSERT INTO `position_requirements` (`position_id`, `competency_id`, `required_rating`) VALUES ('pos-2', 'comp-111', 3);
INSERT INTO `position_requirements` (`position_id`, `competency_id`, `required_rating`) VALUES ('pos-2', 'comp-112', 4);
INSERT INTO `position_requirements` (`position_id`, `competency_id`, `required_rating`) VALUES ('pos-2', 'comp-113', 2);
INSERT INTO `position_requirements` (`position_id`, `competency_id`, `required_rating`) VALUES ('pos-3', 'comp-101', 4);
INSERT INTO `position_requirements` (`position_id`, `competency_id`, `required_rating`) VALUES ('pos-3', 'comp-102', 5);
INSERT INTO `position_requirements` (`position_id`, `competency_id`, `required_rating`) VALUES ('pos-3', 'comp-103', 5);
INSERT INTO `position_requirements` (`position_id`, `competency_id`, `required_rating`) VALUES ('pos-3', 'comp-104', 4);
INSERT INTO `position_requirements` (`position_id`, `competency_id`, `required_rating`) VALUES ('pos-3', 'comp-105', 4);
INSERT INTO `position_requirements` (`position_id`, `competency_id`, `required_rating`) VALUES ('pos-3', 'comp-106', 3);
INSERT INTO `position_requirements` (`position_id`, `competency_id`, `required_rating`) VALUES ('pos-3', 'comp-107', 5);
INSERT INTO `position_requirements` (`position_id`, `competency_id`, `required_rating`) VALUES ('pos-3', 'comp-108', 5);
INSERT INTO `position_requirements` (`position_id`, `competency_id`, `required_rating`) VALUES ('pos-3', 'comp-109', 5);
INSERT INTO `position_requirements` (`position_id`, `competency_id`, `required_rating`) VALUES ('pos-3', 'comp-110', 3);
INSERT INTO `position_requirements` (`position_id`, `competency_id`, `required_rating`) VALUES ('pos-3', 'comp-111', 2);
INSERT INTO `position_requirements` (`position_id`, `competency_id`, `required_rating`) VALUES ('pos-3', 'comp-112', 3);
INSERT INTO `position_requirements` (`position_id`, `competency_id`, `required_rating`) VALUES ('pos-3', 'comp-113', 1);
INSERT INTO `position_requirements` (`position_id`, `competency_id`, `required_rating`) VALUES ('pos-4', 'comp-101', 4);
INSERT INTO `position_requirements` (`position_id`, `competency_id`, `required_rating`) VALUES ('pos-4', 'comp-102', 4);
INSERT INTO `position_requirements` (`position_id`, `competency_id`, `required_rating`) VALUES ('pos-4', 'comp-103', 3);
INSERT INTO `position_requirements` (`position_id`, `competency_id`, `required_rating`) VALUES ('pos-4', 'comp-104', 3);
INSERT INTO `position_requirements` (`position_id`, `competency_id`, `required_rating`) VALUES ('pos-4', 'comp-105', 2);
INSERT INTO `position_requirements` (`position_id`, `competency_id`, `required_rating`) VALUES ('pos-4', 'comp-106', 2);
INSERT INTO `position_requirements` (`position_id`, `competency_id`, `required_rating`) VALUES ('pos-4', 'comp-107', 4);
INSERT INTO `position_requirements` (`position_id`, `competency_id`, `required_rating`) VALUES ('pos-4', 'comp-108', 3);
INSERT INTO `position_requirements` (`position_id`, `competency_id`, `required_rating`) VALUES ('pos-4', 'comp-109', 3);
INSERT INTO `position_requirements` (`position_id`, `competency_id`, `required_rating`) VALUES ('pos-4', 'comp-110', 4);
INSERT INTO `position_requirements` (`position_id`, `competency_id`, `required_rating`) VALUES ('pos-4', 'comp-111', 4);
INSERT INTO `position_requirements` (`position_id`, `competency_id`, `required_rating`) VALUES ('pos-4', 'comp-112', 1);
INSERT INTO `position_requirements` (`position_id`, `competency_id`, `required_rating`) VALUES ('pos-4', 'comp-113', 5);

-- Data for table `assessments`
INSERT INTO `assessments` (`id`, `employee_id`, `cycle_name`, `assessment_date`, `assessor_name`, `total_rating`, `max_possible_rating`, `overall_percentage`, `remarks`, `created_at`) VALUES ('ass-01', 'emp-101', '2025 Q3 Baseline Assessment', '2025-08-01', 'Abdul Aziz Bin Abdullah (aziz)', 34, 50, 68.0, 'Initial baseline established according to Crusher Rev02 sheet.', '2026-09-28 02:17:24');
INSERT INTO `assessments` (`id`, `employee_id`, `cycle_name`, `assessment_date`, `assessor_name`, `total_rating`, `max_possible_rating`, `overall_percentage`, `remarks`, `created_at`) VALUES ('ass-02', 'emp-101', '2026 Q2 Periodic Review', '2026-06-20', 'Abdul Aziz Bin Abdullah (aziz)', 39, 50, 78.0, 'Notable improvement in Autonomous Maintenance and Safety. Lubrication and Troubleshooting remain primary gaps.', '2026-09-28 02:17:24');

-- Data for table `employee_current_scores`
INSERT INTO `employee_current_scores` (`employee_id`, `competency_id`, `rating`, `percentage`, `updated_at`, `assessment_id`) VALUES ('emp-101', 'comp-1', 5, 100, '2026-09-28 02:17:24', NULL);
INSERT INTO `employee_current_scores` (`employee_id`, `competency_id`, `rating`, `percentage`, `updated_at`, `assessment_id`) VALUES ('emp-101', 'comp-2', 4, 80, '2026-09-28 02:17:24', NULL);
INSERT INTO `employee_current_scores` (`employee_id`, `competency_id`, `rating`, `percentage`, `updated_at`, `assessment_id`) VALUES ('emp-101', 'comp-3', 5, 100, '2026-09-28 02:17:24', NULL);
INSERT INTO `employee_current_scores` (`employee_id`, `competency_id`, `rating`, `percentage`, `updated_at`, `assessment_id`) VALUES ('emp-101', 'comp-4', 2, 40, '2026-09-28 02:17:24', NULL);
INSERT INTO `employee_current_scores` (`employee_id`, `competency_id`, `rating`, `percentage`, `updated_at`, `assessment_id`) VALUES ('emp-101', 'comp-5', 3, 60, '2026-09-28 02:17:24', NULL);
INSERT INTO `employee_current_scores` (`employee_id`, `competency_id`, `rating`, `percentage`, `updated_at`, `assessment_id`) VALUES ('emp-101', 'comp-6', 4, 80, '2026-09-28 02:17:24', NULL);
INSERT INTO `employee_current_scores` (`employee_id`, `competency_id`, `rating`, `percentage`, `updated_at`, `assessment_id`) VALUES ('emp-101', 'comp-7', 5, 100, '2026-09-28 02:17:24', NULL);
INSERT INTO `employee_current_scores` (`employee_id`, `competency_id`, `rating`, `percentage`, `updated_at`, `assessment_id`) VALUES ('emp-101', 'comp-8', 3, 60, '2026-09-28 02:17:24', NULL);
INSERT INTO `employee_current_scores` (`employee_id`, `competency_id`, `rating`, `percentage`, `updated_at`, `assessment_id`) VALUES ('emp-101', 'comp-9', 4, 80, '2026-09-28 02:17:24', NULL);
INSERT INTO `employee_current_scores` (`employee_id`, `competency_id`, `rating`, `percentage`, `updated_at`, `assessment_id`) VALUES ('emp-101', 'comp-10', 4, 80, '2026-09-28 02:17:24', NULL);
INSERT INTO `employee_current_scores` (`employee_id`, `competency_id`, `rating`, `percentage`, `updated_at`, `assessment_id`) VALUES ('emp-102', 'comp-1', 4, 80, '2026-09-28 02:17:24', NULL);
INSERT INTO `employee_current_scores` (`employee_id`, `competency_id`, `rating`, `percentage`, `updated_at`, `assessment_id`) VALUES ('emp-102', 'comp-2', 4, 80, '2026-09-28 02:17:24', NULL);
INSERT INTO `employee_current_scores` (`employee_id`, `competency_id`, `rating`, `percentage`, `updated_at`, `assessment_id`) VALUES ('emp-102', 'comp-3', 4, 80, '2026-09-28 02:17:24', NULL);
INSERT INTO `employee_current_scores` (`employee_id`, `competency_id`, `rating`, `percentage`, `updated_at`, `assessment_id`) VALUES ('emp-102', 'comp-4', 4, 80, '2026-09-28 02:17:24', NULL);
INSERT INTO `employee_current_scores` (`employee_id`, `competency_id`, `rating`, `percentage`, `updated_at`, `assessment_id`) VALUES ('emp-102', 'comp-5', 3, 60, '2026-09-28 02:17:24', NULL);
INSERT INTO `employee_current_scores` (`employee_id`, `competency_id`, `rating`, `percentage`, `updated_at`, `assessment_id`) VALUES ('emp-102', 'comp-6', 4, 80, '2026-09-28 02:17:24', NULL);
INSERT INTO `employee_current_scores` (`employee_id`, `competency_id`, `rating`, `percentage`, `updated_at`, `assessment_id`) VALUES ('emp-102', 'comp-7', 5, 100, '2026-09-28 02:17:24', NULL);
INSERT INTO `employee_current_scores` (`employee_id`, `competency_id`, `rating`, `percentage`, `updated_at`, `assessment_id`) VALUES ('emp-102', 'comp-8', 2, 40, '2026-09-28 02:17:24', NULL);
INSERT INTO `employee_current_scores` (`employee_id`, `competency_id`, `rating`, `percentage`, `updated_at`, `assessment_id`) VALUES ('emp-102', 'comp-9', 4, 80, '2026-09-28 02:17:24', NULL);
INSERT INTO `employee_current_scores` (`employee_id`, `competency_id`, `rating`, `percentage`, `updated_at`, `assessment_id`) VALUES ('emp-102', 'comp-10', 3, 60, '2026-09-28 02:17:24', NULL);
INSERT INTO `employee_current_scores` (`employee_id`, `competency_id`, `rating`, `percentage`, `updated_at`, `assessment_id`) VALUES ('emp-103', 'comp-1', 4, 80, '2026-09-28 02:17:24', NULL);
INSERT INTO `employee_current_scores` (`employee_id`, `competency_id`, `rating`, `percentage`, `updated_at`, `assessment_id`) VALUES ('emp-103', 'comp-2', 3, 60, '2026-09-28 02:17:24', NULL);
INSERT INTO `employee_current_scores` (`employee_id`, `competency_id`, `rating`, `percentage`, `updated_at`, `assessment_id`) VALUES ('emp-103', 'comp-3', 4, 80, '2026-09-28 02:17:24', NULL);
INSERT INTO `employee_current_scores` (`employee_id`, `competency_id`, `rating`, `percentage`, `updated_at`, `assessment_id`) VALUES ('emp-103', 'comp-4', 3, 60, '2026-09-28 02:17:24', NULL);
INSERT INTO `employee_current_scores` (`employee_id`, `competency_id`, `rating`, `percentage`, `updated_at`, `assessment_id`) VALUES ('emp-103', 'comp-5', 2, 40, '2026-09-28 02:17:24', NULL);
INSERT INTO `employee_current_scores` (`employee_id`, `competency_id`, `rating`, `percentage`, `updated_at`, `assessment_id`) VALUES ('emp-103', 'comp-6', 3, 60, '2026-09-28 02:17:24', NULL);
INSERT INTO `employee_current_scores` (`employee_id`, `competency_id`, `rating`, `percentage`, `updated_at`, `assessment_id`) VALUES ('emp-103', 'comp-7', 5, 100, '2026-09-28 02:17:24', NULL);
INSERT INTO `employee_current_scores` (`employee_id`, `competency_id`, `rating`, `percentage`, `updated_at`, `assessment_id`) VALUES ('emp-103', 'comp-8', 2, 40, '2026-09-28 02:17:24', NULL);
INSERT INTO `employee_current_scores` (`employee_id`, `competency_id`, `rating`, `percentage`, `updated_at`, `assessment_id`) VALUES ('emp-103', 'comp-9', 5, 100, '2026-09-28 02:17:24', NULL);
INSERT INTO `employee_current_scores` (`employee_id`, `competency_id`, `rating`, `percentage`, `updated_at`, `assessment_id`) VALUES ('emp-103', 'comp-10', 3, 60, '2026-09-28 02:17:24', NULL);
INSERT INTO `employee_current_scores` (`employee_id`, `competency_id`, `rating`, `percentage`, `updated_at`, `assessment_id`) VALUES ('emp-104', 'comp-1', 3, 60, '2026-09-28 02:17:24', NULL);
INSERT INTO `employee_current_scores` (`employee_id`, `competency_id`, `rating`, `percentage`, `updated_at`, `assessment_id`) VALUES ('emp-104', 'comp-2', 4, 80, '2026-09-28 02:17:24', NULL);
INSERT INTO `employee_current_scores` (`employee_id`, `competency_id`, `rating`, `percentage`, `updated_at`, `assessment_id`) VALUES ('emp-104', 'comp-3', 4, 80, '2026-09-28 02:17:24', NULL);
INSERT INTO `employee_current_scores` (`employee_id`, `competency_id`, `rating`, `percentage`, `updated_at`, `assessment_id`) VALUES ('emp-104', 'comp-4', 3, 60, '2026-09-28 02:17:24', NULL);
INSERT INTO `employee_current_scores` (`employee_id`, `competency_id`, `rating`, `percentage`, `updated_at`, `assessment_id`) VALUES ('emp-104', 'comp-5', 5, 100, '2026-09-28 02:17:24', NULL);
INSERT INTO `employee_current_scores` (`employee_id`, `competency_id`, `rating`, `percentage`, `updated_at`, `assessment_id`) VALUES ('emp-104', 'comp-6', 5, 100, '2026-09-28 02:17:24', NULL);
INSERT INTO `employee_current_scores` (`employee_id`, `competency_id`, `rating`, `percentage`, `updated_at`, `assessment_id`) VALUES ('emp-104', 'comp-7', 5, 100, '2026-09-28 02:17:24', NULL);
INSERT INTO `employee_current_scores` (`employee_id`, `competency_id`, `rating`, `percentage`, `updated_at`, `assessment_id`) VALUES ('emp-104', 'comp-8', 4, 80, '2026-09-28 02:17:24', NULL);
INSERT INTO `employee_current_scores` (`employee_id`, `competency_id`, `rating`, `percentage`, `updated_at`, `assessment_id`) VALUES ('emp-104', 'comp-9', 4, 80, '2026-09-28 02:17:24', NULL);
INSERT INTO `employee_current_scores` (`employee_id`, `competency_id`, `rating`, `percentage`, `updated_at`, `assessment_id`) VALUES ('emp-104', 'comp-10', 4, 80, '2026-09-28 02:17:24', NULL);
INSERT INTO `employee_current_scores` (`employee_id`, `competency_id`, `rating`, `percentage`, `updated_at`, `assessment_id`) VALUES ('emp-105', 'comp-1', 3, 60, '2026-09-28 02:17:24', NULL);
INSERT INTO `employee_current_scores` (`employee_id`, `competency_id`, `rating`, `percentage`, `updated_at`, `assessment_id`) VALUES ('emp-105', 'comp-2', 2, 40, '2026-09-28 02:17:24', NULL);
INSERT INTO `employee_current_scores` (`employee_id`, `competency_id`, `rating`, `percentage`, `updated_at`, `assessment_id`) VALUES ('emp-105', 'comp-3', 3, 60, '2026-09-28 02:17:24', NULL);
INSERT INTO `employee_current_scores` (`employee_id`, `competency_id`, `rating`, `percentage`, `updated_at`, `assessment_id`) VALUES ('emp-105', 'comp-4', 2, 40, '2026-09-28 02:17:24', NULL);
INSERT INTO `employee_current_scores` (`employee_id`, `competency_id`, `rating`, `percentage`, `updated_at`, `assessment_id`) VALUES ('emp-105', 'comp-5', 2, 40, '2026-09-28 02:17:24', NULL);
INSERT INTO `employee_current_scores` (`employee_id`, `competency_id`, `rating`, `percentage`, `updated_at`, `assessment_id`) VALUES ('emp-105', 'comp-6', 3, 60, '2026-09-28 02:17:24', NULL);
INSERT INTO `employee_current_scores` (`employee_id`, `competency_id`, `rating`, `percentage`, `updated_at`, `assessment_id`) VALUES ('emp-105', 'comp-7', 4, 80, '2026-09-28 02:17:24', NULL);
INSERT INTO `employee_current_scores` (`employee_id`, `competency_id`, `rating`, `percentage`, `updated_at`, `assessment_id`) VALUES ('emp-105', 'comp-8', 1, 20, '2026-09-28 02:17:24', NULL);
INSERT INTO `employee_current_scores` (`employee_id`, `competency_id`, `rating`, `percentage`, `updated_at`, `assessment_id`) VALUES ('emp-105', 'comp-9', 4, 80, '2026-09-28 02:17:24', NULL);
INSERT INTO `employee_current_scores` (`employee_id`, `competency_id`, `rating`, `percentage`, `updated_at`, `assessment_id`) VALUES ('emp-105', 'comp-10', 2, 40, '2026-09-28 02:17:24', NULL);

-- Data for table `training_records`
INSERT INTO `training_records` (`id`, `employee_id`, `title`, `provider`, `completion_date`, `status`, `reassessment_cycle`, `created_at`) VALUES ('trn-1', 'emp-101', 'TPM Pillar 1 - Autonomous Maintenance Workshop', 'Malaysia TPM Institute', '2025-11-14', 'Completed', '2026 Q2 Periodic Review', '2026-09-28 02:17:24');
INSERT INTO `training_records` (`id`, `employee_id`, `title`, `provider`, `completion_date`, `status`, `reassessment_cycle`, `created_at`) VALUES ('trn-2', 'emp-101', 'Advanced Crusher LOTO & Confined Space Safety', 'Internal EFLOW Safety Academy', '2026-02-18', 'Completed', '2026 Q2 Periodic Review', '2026-09-28 02:17:24');
INSERT INTO `training_records` (`id`, `employee_id`, `title`, `provider`, `completion_date`, `status`, `reassessment_cycle`, `created_at`) VALUES ('trn-3', 'emp-102', 'Industrial Lubricant Analysis & Contamination Control', 'Castrol Technical Services', '2026-01-22', 'Completed', '2026 Q1 Assessment', '2026-09-28 02:17:24');
INSERT INTO `training_records` (`id`, `employee_id`, `title`, `provider`, `completion_date`, `status`, `reassessment_cycle`, `created_at`) VALUES ('trn-4', 'emp-104', 'Siemens S7 PLC & Crusher Automation Diagnostics', 'Siemens Malaysia', '2025-09-10', 'Completed', '2026 Q2 Periodic Review', '2026-09-28 02:17:24');

SET FOREIGN_KEY_CHECKS = 1;
