# design.jobs — Full Stack Backend

A real-time design job aggregator pulling from 9 platforms.

## Stack
- **Scrapers** — Python + Playwright (headless browser for JS-heavy sites)
- **Database** — Supabase (Postgres) with deduplication logic
- **API** — FastAPI with search, filter, and pagination
- **Scheduler** — APScheduler (scrapes every 30 min)
- **Frontend** — the HTML/JS board from Claude connects to this API

## Quick Start

### 1. Clone and install
```bash
git clone <your-repo>
cd designjobs
pip install -r requirements.txt
playwright install chromium
```

### 2. Set environment variables
```bash
cp .env.example .env
# Fill in SUPABASE_URL, SUPABASE_KEY
```

### 3. Run database migration
```bash
python supabase/migrate.py
```

### 4. Run scrapers once to seed data
```bash
python scrapers/run_all.py
```

### 5. Start the API
```bash
uvicorn api.main:app --reload --port 8000
```

### 6. (Optional) Docker
```bash
docker-compose up --build
```

## Platforms Covered
| Platform | Method | Frequency |
|---|---|---|
| youngdesignersindia.com | Playwright (JS render) | 30 min |
| hiredesigners.in | Playwright | 30 min |
| auster.network | Playwright | 30 min |
| remotesource.com | Playwright | 30 min |
| meetfrank.com | Playwright | 30 min |
| dribbble.com/jobs | Requests + BeautifulSoup | 30 min |
| internshala.com | Requests + BeautifulSoup | 30 min |
| wellfound.com | Playwright | 60 min |
| linkedin.com | RSS feed parser | 15 min |

## API Endpoints
- `GET /jobs` — all jobs with filters
- `GET /jobs/{id}` — single job detail
- `GET /sources` — platform stats
- `GET /health` — healthcheck

## Deduplication
Jobs are deduplicated by `(title_normalized + company_normalized + source)` hash.
