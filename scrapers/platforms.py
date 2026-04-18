"""HireDesigners.in scraper"""
from playwright.sync_api import sync_playwright
from .base import BaseScraper, Job
from datetime import datetime

class HireDesignersScraper(BaseScraper):
    SOURCE_ID = "hiredesigners"
    BASE_URL = "https://hiredesigners.in"

    def scrape(self) -> list[Job]:
        jobs = []
        with sync_playwright() as p:
            browser = p.chromium.launch(headless=True)
            page = browser.new_page(user_agent="Mozilla/5.0 (compatible; designjobs-bot/1.0)")
            page.goto(self.BASE_URL, wait_until="networkidle", timeout=30000)
            page.wait_for_timeout(2000)

            cards = page.query_selector_all(".job, .listing, article, .card, [class*=job]")
            for card in cards[:50]:
                try:
                    title_el = card.query_selector("h2, h3, .title, .job-title, strong")
                    company_el = card.query_selector(".company, .employer, .org")
                    link_el = card.query_selector("a")
                    desc_el = card.query_selector("p, .desc, .summary")
                    location_el = card.query_selector(".location, .city, .place")

                    title = title_el.inner_text().strip() if title_el else None
                    company = company_el.inner_text().strip() if company_el else "Not specified"
                    href = link_el.get_attribute("href") if link_el else self.BASE_URL
                    desc = desc_el.inner_text().strip() if desc_el else None
                    location = location_el.inner_text().strip() if location_el else "India"

                    if not title:
                        continue

                    full_url = href if href and href.startswith("http") else self.BASE_URL + (href or "")
                    jobs.append(Job(
                        title=title,
                        company=company,
                        source_id=self.SOURCE_ID,
                        source_listing_url=full_url,
                        apply_url=full_url,
                        description=desc,
                        city=location,
                        country="India",
                        region="india",
                        posted_at=datetime.now(),
                    ))
                except:
                    continue
            browser.close()
        return jobs


"""Auster.network scraper"""
class AusterScraper(BaseScraper):
    SOURCE_ID = "auster"
    URL = "https://auster.network/opportunities"

    def scrape(self) -> list[Job]:
        jobs = []
        with sync_playwright() as p:
            browser = p.chromium.launch(headless=True)
            page = browser.new_page(user_agent="Mozilla/5.0 (compatible; designjobs-bot/1.0)")
            page.goto(self.URL, wait_until="networkidle", timeout=30000)
            page.wait_for_timeout(3000)

            # Auster is likely React/Next.js — wait for dynamic content
            page.wait_for_selector("article, .card, .opportunity, [class*=job], [class*=opportunity]", timeout=10000)
            cards = page.query_selector_all("article, .card, .opportunity, [class*=opportunity]")

            for card in cards[:50]:
                try:
                    title = self._text(card, ["h2","h3",".title","strong","[class*=title]"])
                    company = self._text(card, [".company","[class*=company]","em",".org"])
                    link = card.query_selector("a")
                    href = link.get_attribute("href") if link else self.URL
                    desc = self._text(card, ["p",".desc","[class*=desc]"])
                    work_raw = (self._text(card, [".remote","[class*=work]","[class*=type]"]) or "").lower()
                    posted_raw = self._text(card, ["time",".date","[class*=date]","[class*=posted]"])

                    if not title:
                        continue

                    work_type = "remote" if "remote" in work_raw else ("hybrid" if "hybrid" in work_raw else "onsite")
                    full_url = href if href and href.startswith("http") else "https://auster.network" + (href or "")

                    jobs.append(Job(
                        title=title,
                        company=company or "Studio",
                        source_id=self.SOURCE_ID,
                        source_listing_url=full_url,
                        apply_url=full_url,
                        description=desc,
                        work_type=work_type,
                        is_remote=(work_type == "remote"),
                        region="india",
                        country="India",
                        posted_at=datetime.now(),
                    ))
                except:
                    continue
            browser.close()
        return jobs

    def _text(self, el, selectors):
        for s in selectors:
            try:
                found = el.query_selector(s)
                if found:
                    t = found.inner_text().strip()
                    if t:
                        return t
            except:
                continue
        return None


"""RemoteSource scraper"""
class RemoteSourceScraper(BaseScraper):
    SOURCE_ID = "remotesource"
    URL = "https://www.remotesource.com"

    def scrape(self) -> list[Job]:
        jobs = []
        with sync_playwright() as p:
            browser = p.chromium.launch(headless=True)
            page = browser.new_page(user_agent="Mozilla/5.0 (compatible; designjobs-bot/1.0)")
            # Try design category
            page.goto(f"{self.URL}/jobs/design", wait_until="networkidle", timeout=30000)
            page.wait_for_timeout(2000)

            cards = page.query_selector_all("article, .job-card, .listing, [class*=job]")
            for card in cards[:50]:
                try:
                    title = self._t(card, ["h2","h3",".title",".job-title"])
                    company = self._t(card, [".company",".employer","[class*=company]"])
                    link = card.query_selector("a")
                    href = (link.get_attribute("href") if link else None) or self.URL
                    salary = self._t(card, [".salary","[class*=salary]","[class*=compensation]"])
                    location = self._t(card, [".location","[class*=location]"])
                    desc = self._t(card, ["p",".excerpt",".desc"])
                    posted = self._t(card, ["time","[class*=date]"])

                    if not title:
                        continue

                    full_url = href if href.startswith("http") else self.URL + href

                    jobs.append(Job(
                        title=title,
                        company=company or "Company",
                        source_id=self.SOURCE_ID,
                        source_listing_url=full_url,
                        apply_url=full_url,
                        description=desc,
                        salary_text=salary,
                        city=location,
                        region="global",
                        work_type="remote",
                        is_remote=True,
                        salary_currency="USD",
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


"""MeetFrank scraper"""
class MeetFrankScraper(BaseScraper):
    SOURCE_ID = "meetfrank"
    URL = "https://meetfrank.com/latest-jobs"

    def scrape(self) -> list[Job]:
        jobs = []
        with sync_playwright() as p:
            browser = p.chromium.launch(headless=True)
            page = browser.new_page(user_agent="Mozilla/5.0 (compatible; designjobs-bot/1.0)")
            page.goto(self.URL, wait_until="networkidle", timeout=30000)
            page.wait_for_timeout(3000)

            # Search for design roles
            try:
                search = page.query_selector("input[type=search], input[placeholder*=search], input[placeholder*=job]")
                if search:
                    search.fill("designer")
                    page.keyboard.press("Enter")
                    page.wait_for_timeout(2000)
            except:
                pass

            cards = page.query_selector_all("[class*=job], [class*=listing], article, .card")
            for card in cards[:50]:
                try:
                    title = self._t(card, ["h2","h3","[class*=title]","strong"])
                    company = self._t(card, ["[class*=company]","[class*=employer]","em"])
                    link = card.query_selector("a")
                    href = link.get_attribute("href") if link else self.URL
                    salary = self._t(card, ["[class*=salary]","[class*=compensation]"])
                    location = self._t(card, ["[class*=location]","[class*=city]"])
                    work_raw = (self._t(card, ["[class*=remote]","[class*=work]"]) or "").lower()

                    if not title:
                        continue

                    full_url = href if href and href.startswith("http") else "https://meetfrank.com" + (href or "")
                    work_type = "remote" if "remote" in work_raw else ("hybrid" if "hybrid" in work_raw else "onsite")

                    jobs.append(Job(
                        title=title,
                        company=company or "Company",
                        source_id=self.SOURCE_ID,
                        source_listing_url=full_url,
                        apply_url=full_url,
                        salary_text=salary,
                        city=location,
                        region="global",
                        work_type=work_type,
                        salary_currency="EUR",
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
