-- SIH26034 migration 0002 — Phase 2: provider provenance, normalization,
-- per-image source tracking, verified rule metadata. ADDITIVE ONLY.
-- Run: supabase db push  OR  psql $DATABASE_URL -f supabase/migrations/0002_phase2.sql
-- (Local SQLite dev DB regenerates via SQLAlchemy create_all; no action needed.)

alter table inspections
  add column if not exists provider text default '',
  add column if not exists rule_version_used text default '';

alter table inspection_images
  add column if not exists processed_path text default '',
  add column if not exists role text default '';

alter table extracted_fields
  add column if not exists normalized_value text default '',
  add column if not exists source_image_id text default '';

alter table compliance_rules
  add column if not exists rule_status text default 'UNVERIFIED',
  add column if not exists source_document text default '',
  add column if not exists source_section text default '',
  add column if not exists source_url text default '',
  add column if not exists verification_notes text default '';

alter table rule_results
  add column if not exists rule_status text default 'UNVERIFIED',
  add column if not exists source_url text default '';
