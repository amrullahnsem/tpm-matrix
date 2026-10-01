-- =====================================================================
-- Migration 002: add the 13 Crusher-specific TPM competencies
--
-- Additive and idempotent. The 10 pre-existing generic TPM competencies
-- are retained, so the matrix grows from 10 to 23 axes.
--
-- NOTE: structural changes (new columns) are applied by seed/migrate.py
-- because SQLite has no "ALTER TABLE ... ADD COLUMN IF NOT EXISTS".
-- This file holds the reference data.
-- =====================================================================

-- ---------------------------------------------------------------------
-- The 13 Crusher competencies (sort_order 101-113 keeps them after the
-- legacy 10, which occupy sort_order 1-10).
-- ---------------------------------------------------------------------
INSERT INTO competencies (id, code, name, category, description, sort_order, is_active) VALUES
 ('comp-101','TPM-CR-01','Crusher TPM Awareness & Pillars','TPM Pillar',
  'Understands the 8 pillars of TPM and the role of the Crusher autonomous maintenance team.',101,1),
 ('comp-102','TPM-CR-02','5S at Crusher Area','Foundational',
  'Sort, Set in order, Shine, Standardise, Sustain across crusher house, skirt and conveyor walkways.',102,1),
 ('comp-103','TPM-CR-03','Visual Check (Vibration, Noise, Leaks)','Inspection',
  'Detects abnormal vibration, noise or leakage during routine patrol using senses and basic aids.',103,1),
 ('comp-104','TPM-CR-04','Cleaning, Lubrication & Tightening (CLIT)','TPM Pillar',
  'Executes routine cleaning, greasing and fastener tightening to standard without guidance.',104,1),
 ('comp-105','TPM-CR-05','Wear Part Inspection','Inspection',
  'Inspects crusher wear parts, liners, mantles and cheek plates; measures wear against limit.',105,1),
 ('comp-106','TPM-CR-06','Conveyor Belt Alignment & Skirt Maintenance','Mechanical',
  'Maintains belt tracking, tension and skirt seals; identifies belt misalignment early.',106,1),
 ('comp-107','TPM-CR-07','Crusher Shutdown SOP & Lock-Out Tag-Out (LOTO)','Safety & Compliance',
  'Executes crusher shutdown SOP and LOTO exactly per procedure; zero deviation.',107,1),
 ('comp-108','TPM-CR-08','Minor Defect Tagging & Reporting','Foundational',
  'Tags minor defects immediately and reports them through the correct channel the same shift.',108,1),
 ('comp-109','TPM-CR-09','PIMPS / Logbook Entry','Management',
  'Maintains accurate and complete PIMPS / logbook entries for routine tasks.',109,1),
 ('comp-110','TPM-CR-10','Preventive Maintenance Scheduling','Management',
  'Plans and schedules preventive maintenance work in the CMMS within agreed windows.',110,1),
 ('comp-111','TPM-CR-11','Root Cause Analysis (RCA)','Engineering',
  'Applies structured RCA (5 Whys, fault tree) to crusher breakdowns and recurrences.',111,1),
 ('comp-112','TPM-CR-12','Crusher Alignment & Gap checking','Mechanical',
  'Checks crusher frame, shaft and liner alignment and the crushing gap setting.',112,1),
 ('comp-113','TPM-CR-13','Electrical MCC & Motor Condition Monitoring','Specialized',
  'Monitors crusher MCC, motor condition, thermal load and electrical protection settings.',113,1)
ON CONFLICT(id) DO UPDATE SET
    code        = excluded.code,
    name        = excluded.name,
    category    = excluded.category,
    description = excluded.description,
    sort_order  = excluded.sort_order;

-- ---------------------------------------------------------------------
-- Required scores for the four existing positions.
--   pos-1 Senior Mechanical Technician - Crusher
--   pos-2 Mechanical Maintenance Technician
--   pos-3 Crusher Operator & Inspector
--   pos-4 Electrical & Automation Specialist
--
-- The requirements are deliberately position-specific: the electrical
-- specialist must be expert (5) on MCC monitoring but only needs basic
-- awareness (1) of crusher alignment, while the mechanical technician is
-- the mirror image. This is what makes the gap analysis meaningful.
-- ---------------------------------------------------------------------
DELETE FROM position_requirements
 WHERE competency_id BETWEEN 'comp-101' AND 'comp-113';

INSERT INTO position_requirements (position_id, competency_id, required_rating) VALUES
 ('pos-1','comp-101',5),('pos-1','comp-102',5),('pos-1','comp-103',5),('pos-1','comp-104',5),
 ('pos-1','comp-105',5),('pos-1','comp-106',4),('pos-1','comp-107',5),('pos-1','comp-108',4),
 ('pos-1','comp-109',4),('pos-1','comp-110',4),('pos-1','comp-111',4),('pos-1','comp-112',5),
 ('pos-1','comp-113',3),

 ('pos-2','comp-101',4),('pos-2','comp-102',4),('pos-2','comp-103',4),('pos-2','comp-104',5),
 ('pos-2','comp-105',4),('pos-2','comp-106',4),('pos-2','comp-107',5),('pos-2','comp-108',4),
 ('pos-2','comp-109',3),('pos-2','comp-110',3),('pos-2','comp-111',3),('pos-2','comp-112',4),
 ('pos-2','comp-113',2),

 ('pos-3','comp-101',4),('pos-3','comp-102',5),('pos-3','comp-103',5),('pos-3','comp-104',4),
 ('pos-3','comp-105',4),('pos-3','comp-106',3),('pos-3','comp-107',5),('pos-3','comp-108',5),
 ('pos-3','comp-109',5),('pos-3','comp-110',3),('pos-3','comp-111',2),('pos-3','comp-112',3),
 ('pos-3','comp-113',1),

 ('pos-4','comp-101',4),('pos-4','comp-102',4),('pos-4','comp-103',3),('pos-4','comp-104',3),
 ('pos-4','comp-105',2),('pos-4','comp-106',2),('pos-4','comp-107',4),('pos-4','comp-108',3),
 ('pos-4','comp-109',3),('pos-4','comp-110',4),('pos-4','comp-111',4),('pos-4','comp-112',1),
 ('pos-4','comp-113',5)
ON CONFLICT(position_id, competency_id) DO UPDATE SET
    required_rating = excluded.required_rating;
