"""FastAPI — design.jobs REST API."""
import os
from datetime import datetime, timezone
from typing import Optional
from fastapi import FastAPI, Query, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from supabase import create_client
from dotenv import load_dotenv
from pydantic import BaseModel

load_dotenv()

app = FastAPI(title="design.jobs API", version="1.0.0")

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],   # Tighten in production
    allow_methods=["GET"],
    allow_headers=["*"],
)

db = create_client(os.environ["SUPABASE_URL"], os.environ["SUPABASE_KEY"])


# ─── Health ──────────────────────────────────────────────────────────────────
@app.get("/health")
def health():
    return {"status": "ok", "ts": datetime.now(timezone.utc).isoformat()}


# ─── Sources ─────────────────────────────────────────────────────────────────
@app.get("/sources")
def get_sources():
    res = db.table("sources").select("*").eq("active", True).execute()
    # Enrich with live counts
    enriched = []
    for src in res.data:
        count_res = (
            db.table("jobs")
            .select("id", count="exact")
            .eq("source_id", src["id"])
            .eq("is_active", True)
            .execute()
        )
        src["live_count"] = count_res.count or 0
        enriched.append(src)
    return enriched


# ─── Jobs list ───────────────────────────────────────────────────────────────
@app.get("/jobs")
def get_jobs(
    q: Optional[str] = Query(None, description="Full-text search"),
    role: Optional[str] = Query(None, description="ui|brand|graphic|motion|ux|creative"),
    work: Optional[str] = Query(None, description="remote|onsite|hybrid"),
    region: Optional[str] = Query(None, description="india|us|europe|apac|global"),
    source: Optional[str] = Query(None, description="source id"),
    sector: Optional[str] = Query(None, description="tech|agency|startup|fmcg|finance|media"),
    experience: Optional[str] = Query(None, description="fresher|junior|mid|senior"),
    is_new: Optional[bool] = Query(None),
    featured: Optional[bool] = Query(None),
    salary_min: Optional[float] = Query(None),
    salary_max: Optional[float] = Query(None),
    sort: str = Query("newest", description="newest|oldest|salary_high|salary_low"),
    page: int = Query(1, ge=1),
    per_page: int = Query(20, ge=1, le=100),
):
    query = db.table("jobs").select("*").eq("is_active", True)

    if q:
        query = query.text_search("title,company,description", q, config="english")
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
    if salary_min is not None:
        query = query.gte("salary_min", salary_min)
    if salary_max is not None:
        query = query.lte("salary_max", salary_max)

    # Sorting
   sort_map = {
    "newest": ("posted_at", "desc"),
    "oldest": ("posted_at", "asc"),
    "salary_high": ("salary_max", "desc"),
    "salary_low": ("salary_min", "asc"),
}
col, direction = sort_map.get(sort, sort_map["newest"])
query = query.order(col, desc=(direction == "desc"))

    # Pagination
    offset = (page - 1) * per_page
    query = query.range(offset, offset + per_page - 1)

    # Count (separate query without range)
    count_query = db.table("jobs").select("id", count="exact").eq("is_active", True)
    if role: count_query = count_query.eq("role_type", role)
    if work: count_query = count_query.eq("work_type", work)
    if region: count_query = count_query.eq("region", region)
    if source: count_query = count_query.eq("source_id", source)
    total = count_query.execute().count or 0

    res = query.execute()

    return {
        "jobs": res.data,
        "total": total,
        "page": page,
        "per_page": per_page,
        "pages": (total + per_page - 1) // per_page,
    }


# ─── Single job ──────────────────────────────────────────────────────────────
@app.get("/jobs/{job_id}")
def get_job(job_id: str):
    res = db.table("jobs").select("*").eq("id", job_id).single().execute()
    if not res.data:
        raise HTTPException(status_code=404, detail="Job not found")
    return res.data


# ─── Stats ───────────────────────────────────────────────────────────────────
@app.get("/stats")
def get_stats():
    total = db.table("jobs").select("id", count="exact").eq("is_active", True).execute().count or 0
    remote = db.table("jobs").select("id", count="exact").eq("is_active", True).eq("work_type", "remote").execute().count or 0
    new_today = db.table("jobs").select("id", count="exact").eq("is_active", True).eq("is_new", True).execute().count or 0
    india = db.table("jobs").select("id", count="exact").eq("is_active", True).eq("region", "india").execute().count or 0
    sources_res = db.table("sources").select("id", count="exact").eq("active", True).execute()

    return {
        "total_jobs": total,
        "remote_jobs": remote,
        "new_today": new_today,
        "india_jobs": india,
        "active_sources": sources_res.count or 0,
        "last_updated": datetime.now(timezone.utc).isoformat(),
    }


# ─── Scrape logs ─────────────────────────────────────────────────────────────
@app.get("/logs")
def get_logs(limit: int = Query(20, le=100)):
    res = db.table("scrape_logs").select("*").order("started_at", ascending=False).limit(limit).execute()
    return res.data
