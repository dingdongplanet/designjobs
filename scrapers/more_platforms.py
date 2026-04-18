"""Dribbble Jobs, Internshala, Wellfound, LinkedIn RSS scrapers."""
import requests
from bs4 import BeautifulSoup
from playwright.sync_api import sync_playwright
from .base import BaseScraper, Job
from datetime import datetime
import re


class DribbbleScraper(BaseScraper):
    SOURCE_ID = "dribbble"
    URL = "https://dribbble.com/jobs"

    DESIGN_TERMS = ["designer", "design", "ui", "ux", "brand", "motion", "visual", "creative", "art director", "illustration"]

    def scrape(self) -> list[Job]:
        jobs = []
        for page_num in range(1, 5):
            try:
                r = requests.get(
                    f"{self.URL}?page={page_num}",
                    headers={"User-Agent": "Mozilla/5.0 (compatible; designjobs-bot/1.0)"},
                    timeout=15,
                )
                soup = BeautifulSoup(r.text, "lxml")
                cards = soup.select(".job-listing, .job-board-job, article, [class*=job-card]")

                for card in cards:
                    title_el = card.select_one("h2, h3, .job-title, [class*=title]")
                    company_el = card.select_one(".company, .employer, [class*=company]")
                    link_el = card.select_one("a[href]")
                    location_el = card.select_one(".location, [class*=location]")
                    desc_el = card.select_one("p, .description, .excerpt")
                    date_el = card.select_one("time, .date, [class*=date]")

                    title = title_el.get_text(strip=True) if title_el else None
                    if not title or not any(t in title.lower() for t in self.DESIGN_TERMS):
                        continue

                    company = company_el.get_text(strip=True) if company_el else "Company"
                    href = link_el["href"] if link_el else self.URL
                    full_url = href if href.startswith("http") else "https://dribbble.com" + href
                    location = location_el.get_text(strip=True) if location_el else "Worldwide"
                    desc = desc_el.get_text(strip=True) if desc_el else None
                    date_str = date_el.get("datetime") or date_el.get_text(strip=True) if date_el else None

                    is_remote = "remote" in (location or "").lower() or "anywhere" in (location or "").lower()
                    work_type = "remote" if is_remote else "onsite"

                    jobs.append(Job(
                        title=title,
                        company=company,
                        source_id=self.SOURCE_ID,
                        source_listing_url=full_url,
                        apply_url=full_url,
                        description=desc,
                        city=location,
                        region="global",
                        work_type=work_type,
                        is_remote=is_remote,
                        salary_currency="USD",
                        posted_at=self._parse_date(date_str),
                    ))
            except Exception as e:
                break
        return jobs

    def _parse_date(self, s):
        if not s:
            return datetime.now()
        try:
            return datetime.fromisoformat(s.replace("Z", "+00:00"))
        except:
            return datetime.now()


class IntershalaScraper(BaseScraper):
    SOURCE_ID = "internshala"
    BASE = "https://internshala.com"
    CATEGORIES = [
        "/jobs/graphic-design-jobs/",
        "/jobs/ui-ux-design-jobs/",
        "/jobs/design-jobs/",
    ]

    def scrape(self) -> list[Job]:
        jobs = []
        seen = set()
        for cat in self.CATEGORIES:
            try:
                r = requests.get(
                    self.BASE + cat,
                    headers={"User-Agent": "Mozilla/5.0 (compatible; designjobs-bot/1.0)"},
                    timeout=15,
                )
                soup = BeautifulSoup(r.text, "lxml")
                cards = soup.select(".individual_internship, .job_card, [class*=individual]")

                for card in cards:
                    title_el = card.select_one(".job-title, .profile, h3, [class*=job_title]")
                    company_el = card.select_one(".company_name, .company, [class*=company]")
                    location_el = card.select_one(".location_link, [class*=location]")
                    salary_el = card.select_one(".stipend, .salary, [class*=salary]")
                    link_el = card.select_one("a[href]")
                    date_el = card.select_one(".posted-time, [class*=date], time")

                    title = title_el.get_text(strip=True) if title_el else None
                    if not title:
                        continue

                    company = company_el.get_text(strip=True) if company_el else "Company"
                    href = link_el["href"] if link_el else cat
                    full_url = href if href.startswith("http") else self.BASE + href

                    if full_url in seen:
                        continue
                    seen.add(full_url)

                    location = location_el.get_text(strip=True) if location_el else "India"
                    salary_raw = salary_el.get_text(strip=True) if salary_el else None
                    posted_raw = date_el.get_text(strip=True) if date_el else None

                    is_remote = "work from home" in (location or "").lower() or "remote" in (location or "").lower()

                    jobs.append(Job(
                        title=title,
                        company=company,
                        source_id=self.SOURCE_ID,
                        source_listing_url=full_url,
                        apply_url=full_url,
                        salary_text=salary_raw,
                        salary_currency="INR",
                        city=location if not is_remote else None,
                        region="india",
                        country="India",
                        work_type="remote" if is_remote else "onsite",
                        is_remote=is_remote,
                        posted_at=datetime.now(),
                    ))
            except Exception as e:
                continue
        return jobs


class WellfoundScraper(BaseScraper):
    SOURCE_ID = "wellfound"
    URL = "https://wellfound.com/role/r/designer"

    def scrape(self) -> list[Job]:
        jobs = []
        with sync_playwright() as p:
            browser = p.chromium.launch(headless=True)
            page = browser.new_page(user_agent="Mozilla/5.0 (compatible; designjobs-bot/1.0)")
            page.goto(self.URL, wait_until="networkidle", timeout=30000)
            page.wait_for_timeout(3000)

            cards = page.query_selector_all("[data-test*=job], [class*=job-listing], article, [class*=JobCard]")
            for card in cards[:40]:
                try:
                    title = self._t(card, ["[class*=title]","h2","h3","strong"])
                    company = self._t(card, ["[class*=company]","[class*=startup]","em","[class*=name]"])
                    link = card.query_selector("a")
                    href = link.get_attribute("href") if link else self.URL
                    salary = self._t(card, ["[class*=salary]","[class*=compensation]","[class*=pay]"])
                    location = self._t(card, ["[class*=location]","[class*=city]"])
                    equity = self._t(card, ["[class*=equity]"])

                    if not title:
                        continue

                    full_url = href if href and href.startswith("http") else "https://wellfound.com" + (href or "")
                    is_remote = "remote" in (location or "").lower()

                    sal_text = salary
                    if equity and salary:
                        sal_text = f"{salary} + {equity} equity"

                    jobs.append(Job(
                        title=title,
                        company=company or "Startup",
                        source_id=self.SOURCE_ID,
                        source_listing_url=full_url,
                        apply_url=full_url,
                        salary_text=sal_text,
                        salary_currency="USD",
                        city=location,
                        region="global",
                        work_type="remote" if is_remote else "hybrid",
                        is_remote=is_remote,
                        sector="startup",
                        posted_at=datetime.now(),
                    ))
                except:
                    continue
            browser.close()
        return jobs

    def _t(self, el, sels):
        for s in sels:
            try:
                f = el.query_selector(s)
                if f:
                    t = f.inner_text().strip()
                    if t: return t
            except: continue
        return None


class LinkedInRSSScraper(BaseScraper):
    """LinkedIn job search via their RSS/JSON feed (no auth needed for public search)."""
    SOURCE_ID = "linkedin"

    SEARCHES = [
        {"q": "graphic designer", "location": "India", "region": "india"},
        {"q": "UI UX designer", "location": "India", "region": "india"},
        {"q": "brand designer", "location": "India", "region": "india"},
        {"q": "motion designer", "location": "India", "region": "india"},
        {"q": "product designer", "location": "India", "region": "india"},
        {"q": "UI designer", "location": "Worldwide", "region": "global"},
        {"q": "brand designer", "location": "United States", "region": "us"},
    ]

    def scrape(self) -> list[Job]:
        jobs = []
        seen = set()
        for s in self.SEARCHES:
            try:
                # LinkedIn public job search JSON (unauthenticated, limited results)
                url = (
                    "https://www.linkedin.com/jobs-guest/jobs/api/seeMoreJobPostings/search"
                    f"?keywords={requests.utils.quote(s['q'])}"
                    f"&location={requests.utils.quote(s['location'])}"
                    "&trk=public_jobs_jobs-search-bar_search-submit"
                    "&position=1&pageNum=0"
                )
                r = requests.get(url, headers={
                    "User-Agent": "Mozilla/5.0 (compatible; designjobs-bot/1.0)",
                    "Accept": "text/html,application/xhtml+xml",
                }, timeout=15)
                soup = BeautifulSoup(r.text, "lxml")
                cards = soup.select("li, .job-search-card, [class*=job-card]")

                for card in cards:
                    title_el = card.select_one("h3, .job-title, [class*=title]")
                    company_el = card.select_one("h4, .company-name, [class*=company]")
                    location_el = card.select_one(".job-location, [class*=location]")
                    link_el = card.select_one("a[href]")
                    date_el = card.select_one("time, [class*=date]")

                    title = title_el.get_text(strip=True) if title_el else None
                    if not title:
                        continue

                    href = link_el["href"] if link_el else "https://linkedin.com/jobs"
                    clean_url = href.split("?")[0] if href else href

                    if clean_url in seen:
                        continue
                    seen.add(clean_url)

                    company = company_el.get_text(strip=True) if company_el else "Company"
                    location = location_el.get_text(strip=True) if location_el else s["location"]
                    date_str = date_el.get("datetime") if date_el else None

                    is_remote = "remote" in (location or "").lower()

                    jobs.append(Job(
                        title=title,
                        company=company,
                        source_id=self.SOURCE_ID,
                        source_listing_url=clean_url,
                        apply_url=clean_url,
                        city=location,
                        region=s["region"],
                        work_type="remote" if is_remote else "onsite",
                        is_remote=is_remote,
                        salary_currency="INR" if s["region"] == "india" else "USD",
                        posted_at=self._parse(date_str),
                    ))
            except Exception as e:
                continue
        return jobs

    def _parse(self, s):
        if not s:
            return datetime.now()
        try:
            return datetime.fromisoformat(s.replace("Z", "+00:00"))
        except:
            return datetime.now()
