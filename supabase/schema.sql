-- design.jobs — Supabase schema
-- Run this in your Supabase SQL editor or via migrate.py

-- Enable full text search extension
create extension if not exists pg_trgm;

-- ─── SOURCES table ───────────────────────────────────────────
create table if not exists sources (
  id text primary key,
  name text not null,
  url text not null,
  color text default '#888888',
  region text default 'global',   -- 'india' | 'global' | 'us' | 'europe'
  active boolean default true,
  last_scraped_at timestamptz,
  total_scraped int default 0,
  created_at timestamptz default now()
);

insert into sources (id, name, url, color, region) values
  ('youngdesigners', 'Young Designers India', 'https://www.youngdesignersindia.com/', '#E24B4A', 'india'),
  ('hiredesigners',  'HireDesigners.in',      'https://hiredesigners.in/',            '#D85A30', 'india'),
  ('auster',         'Auster.network',         'https://auster.network/opportunities', '#534AB7', 'india'),
  ('remotesource',   'RemoteSource',           'https://www.remotesource.com/',        '#1D9E75', 'global'),
  ('meetfrank',      'MeetFrank',              'https://meetfrank.com/latest-jobs',    '#185FA5', 'global'),
  ('dribbble',       'Dribbble Jobs',          'https://dribbble.com/jobs',            '#EA4C89', 'global'),
  ('internshala',    'Internshala',            'https://internshala.com/jobs/design-jobs/', '#E24B4A', 'india'),
  ('wellfound',      'Wellfound',              'https://wellfound.com/role/r/designer','#111111', 'global'),
  ('linkedin',       'LinkedIn',               'https://www.linkedin.com/jobs/',        '#0A66C2', 'global')
on conflict (id) do nothing;

-- ─── JOBS table ──────────────────────────────────────────────
create table if not exists jobs (
  id uuid primary key default gen_random_uuid(),
  dedup_hash text unique not null,   -- sha256(lower(title)+lower(company)+source)

  -- Core fields
  title text not null,
  company text not null,
  source_id text references sources(id),
  apply_url text,
  apply_email text,
  apply_type text default 'link',    -- 'link' | 'email'

  -- Classification
  role_type text,      -- 'ui' | 'brand' | 'graphic' | 'motion' | 'ux' | 'creative' | 'other'
  sector text,         -- 'tech' | 'agency' | 'startup' | 'fmcg' | 'finance' | 'media' | 'ngo'
  work_type text,      -- 'remote' | 'onsite' | 'hybrid'
  experience text,     -- 'fresher' | 'junior' | 'mid' | 'senior'

  -- Location
  city text,
  country text,
  region text,         -- 'india' | 'us' | 'europe' | 'apac' | 'global'
  is_remote boolean default false,

  -- Salary
  salary_min numeric,
  salary_max numeric,
  salary_currency text default 'INR',
  salary_text text,    -- raw string e.g. "₹12–18 LPA" or "$80k–$120k"

  -- Content
  description text,
  skills text[],       -- e.g. {'Figma','Illustrator','Brand Identity'}
  keywords text[],

  -- Dates
  posted_at timestamptz,           -- original post date from source
  scraped_at timestamptz default now(),
  expires_at timestamptz,
  is_active boolean default true,

  -- Meta
  logo_url text,
  source_listing_url text,         -- direct link to the job on source site
  featured boolean default false,
  is_new boolean default false,    -- posted within last 48h

  created_at timestamptz default now(),
  updated_at timestamptz default now()
);

-- ─── INDEXES ─────────────────────────────────────────────────
create index if not exists jobs_source_id_idx on jobs(source_id);
create index if not exists jobs_role_type_idx on jobs(role_type);
create index if not exists jobs_work_type_idx on jobs(work_type);
create index if not exists jobs_region_idx on jobs(region);
create index if not exists jobs_sector_idx on jobs(sector);
create index if not exists jobs_posted_at_idx on jobs(posted_at desc);
create index if not exists jobs_is_active_idx on jobs(is_active);
create index if not exists jobs_is_new_idx on jobs(is_new);

-- Full text search index
create index if not exists jobs_fts_idx on jobs
  using gin(to_tsvector('english', coalesce(title,'') || ' ' || coalesce(company,'') || ' ' || coalesce(description,'')));

-- Trigram index for fuzzy search
create index if not exists jobs_title_trgm_idx on jobs using gin(title gin_trgm_ops);
create index if not exists jobs_company_trgm_idx on jobs using gin(company gin_trgm_ops);

-- ─── AUTO-UPDATE updated_at ──────────────────────────────────
create or replace function update_updated_at()
returns trigger as $$
begin new.updated_at = now(); return new; end;
$$ language plpgsql;

create trigger jobs_updated_at
  before update on jobs
  for each row execute function update_updated_at();

-- ─── AUTO-MARK is_new ────────────────────────────────────────
-- Runs every hour via pg_cron or just recomputed on API side
create or replace function refresh_is_new()
returns void as $$
  update jobs set is_new = (posted_at > now() - interval '48 hours')
  where is_active = true;
$$ language sql;

-- ─── SCRAPE LOGS table ───────────────────────────────────────
create table if not exists scrape_logs (
  id uuid primary key default gen_random_uuid(),
  source_id text references sources(id),
  started_at timestamptz default now(),
  finished_at timestamptz,
  jobs_found int default 0,
  jobs_new int default 0,
  jobs_updated int default 0,
  status text default 'running',  -- 'running' | 'success' | 'error'
  error_message text
);
