-- SIH26034 Supabase Postgres schema (also usable as migration)
-- Run: supabase db push  OR  psql $DATABASE_URL -f supabase/migrations/0001_init.sql
create extension if not exists "pgcrypto";

create table if not exists inspections (
  id uuid primary key default gen_random_uuid(),
  officer_id text default 'officer-demo',
  officer_email text default 'officer@gov.in',
  status text default 'CREATED',
  compliance_status text default 'PENDING',
  product_name text default '',
  is_demo boolean default false,
  created_at timestamptz default now(),
  updated_at timestamptz default now()
);
create table if not exists inspection_images (
  id uuid primary key default gen_random_uuid(),
  inspection_id uuid references inspections(id) on delete cascade,
  storage_path text default '',
  original_filename text default '',
  mime_type text default '',
  width int default 0, height int default 0,
  created_at timestamptz default now()
);
create index if not exists idx_images_insp on inspection_images(inspection_id);
create table if not exists extracted_fields (
  id uuid primary key default gen_random_uuid(),
  inspection_id uuid references inspections(id) on delete cascade,
  field text, value text default '', confidence float default 0,
  source text default '', status text default 'OK', bbox jsonb default '{}',
  is_corrected boolean default false, original_value text default '',
  created_at timestamptz default now()
);
create index if not exists idx_fields_insp on extracted_fields(inspection_id);
create table if not exists compliance_rules (
  id uuid primary key default gen_random_uuid(),
  rule_code text unique, rule_version text default '1.0.0',
  title text default '', description text default '', requirement text default '',
  severity text default 'WARNING', source_reference text default '',
  is_demo_rule boolean default true, active boolean default true
);
create table if not exists rule_results (
  id uuid primary key default gen_random_uuid(),
  inspection_id uuid references inspections(id) on delete cascade,
  rule_code text, rule_version text default '1.0.0', status text default 'REVIEW',
  severity text default 'WARNING', field text default '', expected text default '',
  observed text default '', explanation text default '', evidence jsonb default '{}',
  created_at timestamptz default now()
);
create index if not exists idx_results_insp on rule_results(inspection_id);
create table if not exists review_actions (
  id uuid primary key default gen_random_uuid(),
  inspection_id uuid references inspections(id) on delete cascade,
  actor text default '', action text default '', field text default '',
  before text default '', after text default '', reason text default '',
  created_at timestamptz default now()
);
create table if not exists audit_logs (
  id uuid primary key default gen_random_uuid(),
  inspection_id text default '', event text, actor text default 'system',
  before jsonb default '{}', after jsonb default '{}', reason text default '',
  created_at timestamptz default now()
);
create index if not exists idx_audit_insp on audit_logs(inspection_id);
create table if not exists reports (
  id uuid primary key default gen_random_uuid(),
  inspection_id uuid references inspections(id) on delete cascade,
  pdf_path text default '', generated_by text default '',
  created_at timestamptz default now()
);
-- Storage bucket (create via dashboard or API):
-- insert into storage.buckets (id, name, public) values ('inspection-images','inspection-images', false);
