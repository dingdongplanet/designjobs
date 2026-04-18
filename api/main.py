import os
from datetime import datetime, timezone
from typing import Optional
from fastapi import FastAPI, Query, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from supabase import create_client
from dotenv import load_dotenv

load_dotenv()

app = FastAPI(title="design.jobs API", version="1.0.0")

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_methods=["GET"],
    allow_headers=["*"],
)

db = create_client(os.environ["SUPABASE_URL"], os.environ["SUPABASE_KEY"])


@app.get("/health")
def health():
    return {"status": "ok", "ts": datetime.now(timezone.utc).isoformat()}


@app.get("/sources")
def get_sources():
    res = db.table("sources").select("*").eq("active", True).execute()
    return res.data


@app.get("/stats")
def get_stats():
    total = db.table("jobs").select("id", count="exact").eq("is_active", True).execute().count or 0
    remote = db.table("jobs").select("id", count="exact").eq("is_active", True).eq("work_type", "remote").execute().count or 0
    new_today = db.table("jobs").select("id", count="exact").eq("is_active", True).eq("is_new", True).execute().count or 0
    india = db.table("jobs").select("id", count="exact").eq("is_active", True).eq("region", "india").execute().count or 0
    return {
        "total_jobs": total,
        "remote_jobs": remote,
        "new_today": new_today,
        "india_jobs": india,
        "last_updated": datetime.now(timezone.utc).isoformat(),
    }


@app.get("/jobs")
def get_jobs(
    q: Optional[str] = Query(None),
    role: Optional[str] = Query(None),
    work: Optional[str] = Query(None),
    region: Optional[str] = Query(None),
    source: Optional[str] = Query(None),
    sector: Optional[str] = Query(None),
    experience: Optional[str] = Query(None),
    is_new: Optional[bool] = Query(None),
    featured: Optional[bool] = Query(None),
    sort: str = Query("newest"),
    page: int = Query(1, ge=1),
    per_page: int = Query(20, ge=1, le=100),
):
    query = db.table("jobs").select("*").eq("is_active", True)

    if role:
        query = query.eq("role_type", role)
    if work:
        query = query.eq("work_type", work)
    if region:
        query = query.eq("region", region)
    if source:
        query = query.eq("source_id", source)
    if sector:
        query = query.eq("sector", sector)
    if experience:
        query = query.eq("experience", experience)
    if is_new is not None:
        query = query.eq("is_new", is_new)
    if featured is not None:
        query = query.eq("featured", featured)

    if sort == "newest":
        query = query.order("posted_at", desc=True)
    elif sort == "oldest":
        query = query.order("posted_at", desc=False)
    elif sort == "salary_high":
        query = query.order("salary_max", desc=True)
    elif sort == "salary_low":
        query = query.order("salary_min", desc=False)
    else:
        query = query.order("posted_at", desc=True)

    offset = (page - 1) * per_page
    query = query.range(offset, offset + per_page - 1)

    res = query.execute()
    total = db.table("jobs").select("id", count="exact").eq("is_active", True).execute().count or 0

    return {
        "jobs": res.data,
        "total": total,
        "page": page,
        "per_page": per_page,
        "pages": (total + per_page - 1) // per_page,
    }


@app.get("/jobs/{job_id}")
def get_job(job_id: str):
    res = db.table("jobs").select("*").eq("id", job_id).single().execute()
    if not res.data:
        raise HTTPException(status_code=404, detail="Job not found")
    return res.data


@app.get("/logs")
def get_logs(limit: int = Query(20, le=100)):
    res = db.table("scrape_logs").select("*").order("started_at", desc=True).limit(limit).execute()
    return res.data
