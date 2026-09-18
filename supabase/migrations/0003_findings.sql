-- SIH26034 migration 0003 — cross-image intelligence findings. ADDITIVE ONLY.
-- Run: supabase db push  OR  psql $DATABASE_URL -f supabase/migrations/0003_findings.sql
-- (Local SQLite dev DB regenerates via SQLAlchemy create_all; no action needed.)

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
