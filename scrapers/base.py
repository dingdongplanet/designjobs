"""Base scraper — all platform scrapers inherit from this."""
import hashlib, os, re, logging
from abc import ABC, abstractmethod
from datetime import datetime, timezone
from dataclasses import dataclass, field
from typing import Optional
from dotenv import load_dotenv
from supabase import create_client, Client

load_dotenv()
logger = logging.getLogger(__name__)

@dataclass
class Job:
    title: str
    company: str
    source_id: str
    source_listing_url: str

    apply_url: Optional[str] = None
    apply_email: Optional[str] = None
    apply_type: str = "link"

    role_type: Optional[str] = None      # ui | brand | graphic | motion | ux | creative
    sector: Optional[str] = None
    work_type: Optional[str] = None      # remote | onsite | hybrid
    experience: Optional[str] = None

    city: Optional[str] = None
    country: Optional[str] = None
    region: Optional[str] = None        # india | us | europe | apac | global
    is_remote: bool = False

    salary_min: Optional[float] = None
    salary_max: Optional[float] = None
    salary_currency: str = "INR"
    salary_text: Optional[str] = None

    description: Optional[str] = None
    skills: list = field(default_factory=list)
    keywords: list = field(default_factory=list)
    logo_url: Optional[str] = None

    posted_at: Optional[datetime] = None
    featured: bool = False

    @property
    def dedup_hash(self) -> str:
        raw = (self.title.lower().strip() + self.company.lower().strip() + self.source_id).encode()
        return hashlib.sha256(raw).hexdigest()

    def to_dict(self) -> dict:
        return {
            "dedup_hash": self.dedup_hash,
            "title": self.title,
            "company": self.company,
            "source_id": self.source_id,
            "source_listing_url": self.source_listing_url,
            "apply_url": self.apply_url,
            "apply_email": self.apply_email,
            "apply_type": self.apply_type,
            "role_type": self.role_type or self._infer_role(),
            "sector": self.sector,
            "work_type": self.work_type or self._infer_work_type(),
            "experience": self.experience,
            "city": self.city,
            "country": self.country,
            "region": self.region,
            "is_remote": self.is_remote or self.work_type == "remote",
            "salary_min": self.salary_min,
            "salary_max": self.salary_max,
            "salary_currency": self.salary_currency,
            "salary_text": self.salary_text,
            "description": self.description,
            "skills": self.skills or self._infer_skills(),
            "keywords": self.keywords,
            "logo_url": self.logo_url,
            "posted_at": self.posted_at.isoformat() if self.posted_at else None,
            "featured": self.featured,
            "is_active": True,
            "is_new": self._is_new(),
        }

    def _is_new(self) -> bool:
        if not self.posted_at:
            return False
        diff = datetime.now(timezone.utc) - self.posted_at.astimezone(timezone.utc)
        return diff.total_seconds() < 48 * 3600

    def _infer_role(self) -> str:
        t = self.title.lower()
        if any(w in t for w in ["ui ", "ux ", "product designer", "interface", "interaction"]):
            return "ui"
        if any(w in t for w in ["brand", "identity", "visual design"]):
            return "brand"
        if any(w in t for w in ["motion", "animation", "after effect"]):
            return "motion"
        if any(w in t for w in ["graphic", "print", "packaging"]):
            return "graphic"
        if any(w in t for w in ["research", "researcher", "usability"]):
            return "ux"
        if any(w in t for w in ["creative director", "art director", "cd ", "head of design"]):
            return "creative"
        return "other"

    def _infer_work_type(self) -> str:
        combined = ((self.title or "") + (self.description or "")).lower()
        if "remote" in combined and "hybrid" not in combined:
            return "remote"
        if "hybrid" in combined:
            return "hybrid"
        return "onsite"

    def _infer_skills(self) -> list:
        SKILL_KEYWORDS = [
            "figma", "sketch", "adobe xd", "invision",
            "illustrator", "photoshop", "indesign", "after effects",
            "cinema 4d", "blender", "lottie", "rive",
            "procreate", "framer", "principle",
            "brand identity", "design systems", "typography",
            "user research", "wireframing", "prototyping",
            "packaging design", "motion design", "illustration",
        ]
        text = ((self.title or "") + " " + (self.description or "")).lower()
        return [s for s in SKILL_KEYWORDS if s in text]


class BaseScraper(ABC):
    SOURCE_ID: str = ""

    def __init__(self):
        self.db: Client = create_client(
            os.environ["SUPABASE_URL"],
            os.environ["SUPABASE_KEY"],
        )
        self.log_id = None

    def _start_log(self):
        res = self.db.table("scrape_logs").insert({
            "source_id": self.SOURCE_ID,
            "status": "running",
        }).execute()
        self.log_id = res.data[0]["id"]

    def _finish_log(self, found: int, new: int, updated: int, error: str = None):
        self.db.table("scrape_logs").update({
            "finished_at": datetime.now(timezone.utc).isoformat(),
            "jobs_found": found,
            "jobs_new": new,
            "jobs_updated": updated,
            "status": "error" if error else "success",
            "error_message": error,
        }).eq("id", self.log_id).execute()
        self.db.table("sources").update({
            "last_scraped_at": datetime.now(timezone.utc).isoformat(),
            "total_scraped": self.db.table("jobs").select("id", count="exact").eq("source_id", self.SOURCE_ID).execute().count or 0,
        }).eq("id", self.SOURCE_ID).execute()

    def upsert_jobs(self, jobs: list[Job]) -> tuple[int, int]:
        new_count = updated_count = 0
        for job in jobs:
            try:
                res = self.db.table("jobs").upsert(
                    job.to_dict(),
                    on_conflict="dedup_hash",
                    returning="representation",
                ).execute()
                # Check if it was an insert or update via created_at == updated_at
                if res.data:
                    row = res.data[0]
                    delta = abs((datetime.fromisoformat(row["updated_at"]) -
                                 datetime.fromisoformat(row["created_at"])).total_seconds())
                    if delta < 2:
                        new_count += 1
                    else:
                        updated_count += 1
            except Exception as e:
                logger.warning(f"Upsert failed for {job.title} @ {job.company}: {e}")
        return new_count, updated_count

    def run(self):
        self._start_log()
        jobs, error = [], None
        try:
            logger.info(f"[{self.SOURCE_ID}] Starting scrape...")
            jobs = self.scrape()
            new, updated = self.upsert_jobs(jobs)
            logger.info(f"[{self.SOURCE_ID}] Done. {len(jobs)} found, {new} new, {updated} updated.")
            self._finish_log(len(jobs), new, updated)
        except Exception as e:
            logger.error(f"[{self.SOURCE_ID}] Error: {e}", exc_info=True)
            self._finish_log(len(jobs), 0, 0, str(e))

    @abstractmethod
    def scrape(self) -> list[Job]:
        """Return list of Job objects scraped from the source."""
        ...
