"""Young Designers India scraper — youngdesignersindia.com"""
from playwright.sync_api import sync_playwright
from .base import BaseScraper, Job
from datetime import datetime
import re

class YoungDesignersIndiaScraper(BaseScraper):
    SOURCE_ID = "youngdesigners"
    BASE_URL = "https://www.youngdesignersindia.com"

    def scrape(self) -> list[Job]:
        jobs = []
        with sync_playwright() as p:
            browser = p.chromium.launch(headless=True)
            page = browser.new_page(user_agent="Mozilla/5.0 (compatible; designjobs-bot/1.0)")
            page.goto(self.BASE_URL, wait_until="networkidle", timeout=30000)
            page.wait_for_timeout(2000)

            # Collect job card links
            cards = page.query_selector_all("a[href*='job'], a[href*='career'], .job-card, .listing-card, article")
            seen = set()
            links = []
            for card in cards:
                href = card.get_attribute("href") or ""
                if href and href not in seen and len(href) > 10:
                    seen.add(href)
                    links.append(href if href.startswith("http") else self.BASE_URL + href)

            for link in links[:40]:
                try:
                    page.goto(link, wait_until="domcontentloaded", timeout=15000)
                    page.wait_for_timeout(800)
                    body = page.content()

                    title = self._extract(page, ["h1", ".job-title", ".role-title"])
                    company = self._extract(page, [".company", ".employer", ".org-name", "h2"])
                    desc = self._extract(page, [".description", ".job-desc", ".content", "article"])
                    location = self._extract(page, [".location", ".city", "[class*=location]"])
                    salary_raw = self._extract(page, [".salary", "[class*=salary]", "[class*=ctc]"])
                    work_raw = (self._extract(page, [".work-type", "[class*=remote]"]) or "").lower()

                    if not title or not company:
                        continue

                    work_type = "remote" if "remote" in work_raw else ("hybrid" if "hybrid" in work_raw else "onsite")
                    city, country = self._parse_location(location or "India")

                    jobs.append(Job(
                        title=title.strip(),
                        company=company.strip(),
                        source_id=self.SOURCE_ID,
                        source_listing_url=link,
                        apply_url=link,
                        description=desc,
                        salary_text=salary_raw,
                        work_type=work_type,
                        city=city,
                        country=country or "India",
                        region="india",
                        posted_at=datetime.now(),
                    ))
                except Exception as e:
                    continue

            browser.close()
        return jobs

    def _extract(self, page, selectors):
        for sel in selectors:
            try:
                el = page.query_selector(sel)
                if el:
                    text = el.inner_text().strip()
                    if text and len(text) > 2:
                        return text
            except:
                continue
        return None

    def _parse_location(self, raw):
        raw = raw.strip()
        if "," in raw:
            parts = raw.split(",")
            return parts[0].strip(), parts[-1].strip()
        return raw, "India"
