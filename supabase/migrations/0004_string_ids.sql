-- SIH26034 migration 0004 — string-id alignment + findings table. ADDITIVE-ONLY
-- in effect (no data loss; existing rows preserved via USING casts).
--
-- Background:
--   * 0001 created PK/FK columns as UUID. The application, however, uses plain
--     TEXT ids everywhere (URL params, filters, JSON evidence/bboxes).
--   * On Postgres this leaks uuid.UUID objects into Python, which crash JSON
--     serialization (evidence/bbox) and break text key lookups.
--   * 0003_findings.sql also failed outright: TEXT fk -> UUID pk is rejected.
-- This migration converts all id / inspection_id columns to TEXT (values
-- preserved), re-creates the foreign keys with the original ON DELETE CASCADE
-- behavior, then creates the findings table that 0003 could not create.
-- Run AFTER 0001_init.sql + 0002_phase2.sql. Safe to re-run (IF EXISTS guards
-- on constraints are handled via DROP IF EXISTS + re-ADD).

-- 1. Drop FKs that reference the columns being converted (auto PG names).
alter table inspection_images drop constraint if exists inspection_images_inspection_id_fkey;
alter table extracted_fields drop constraint if exists extracted_fields_inspection_id_fkey;
alter table rule_results drop constraint if exists rule_results_inspection_id_fkey;
alter table reports drop constraint if exists reports_inspection_id_fkey;

-- 2. Convert PK/FK columns uuid -> text, preserving every existing value.
alter table inspections alter column id type text using id::text;
alter table inspection_images alter column id type text using id::text;
alter table inspection_images alter column inspection_id type text using inspection_id::text;
alter table extracted_fields alter column id type text using id::text;
alter table extracted_fields alter column inspection_id type text using inspection_id::text;
alter table compliance_rules alter column id type text using id::text;
alter table rule_results alter column id type text using id::text;
alter table rule_results alter column inspection_id type text using inspection_id::text;
alter table review_actions alter column id type text using id::text;
alter table audit_logs alter column id type text using id::text;
alter table reports alter column id type text using id::text;
alter table reports alter column inspection_id type text using inspection_id::text;

-- 3. Re-create FKs with the original cascade behavior.
alter table inspection_images
  add constraint inspection_images_inspection_id_fkey
  foreign key (inspection_id) references inspections(id) on delete cascade;
alter table extracted_fields
  add constraint extracted_fields_inspection_id_fkey
  foreign key (inspection_id) references inspections(id) on delete cascade;
alter table rule_results
  add constraint rule_results_inspection_id_fkey
  foreign key (inspection_id) references inspections(id) on delete cascade;
alter table reports
  add constraint reports_inspection_id_fkey
  foreign key (inspection_id) references inspections(id) on delete cascade;

-- 4. Findings table (0003 could never create it — failed on the FK mismatch).
create table if not exists findings (
  id text primary key,
  inspection_id text references inspections(id) on delete cascade,
  kind text default 'CONFLICT',
  field text default '',
  level text default 'MEDIUM',
  title text default '',
  detail text default '',
  evidence jsonb default '[]',
  status text default 'OPEN',
  resolved_by text default '',
  resolved_at timestamptz,
  created_at timestamptz default now()
);
create index if not exists idx_findings_insp on findings(inspection_id);
create index if not exists idx_findings_status on findings(status);
