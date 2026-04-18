"""Run all scrapers. Can run once or continuously on a schedule."""
import logging, sys, os
from apscheduler.schedulers.blocking import BlockingScheduler

logging.basicConfig(level=os.getenv("LOG_LEVEL", "INFO"), format="%(asctime)s %(name)s %(levelname)s %(message)s")
logger = logging.getLogger(__name__)

from scrapers.youngdesigners import YoungDesignersIndiaScraper
from scrapers.platforms import HireDesignersScraper, AusterScraper, RemoteSourceScraper, MeetFrankScraper
from scrapers.more_platforms import DribbbleScraper, IntershalaScraper, WellfoundScraper, LinkedInRSSScraper

ALL_SCRAPERS = [
    YoungDesignersIndiaScraper,
    HireDesignersScraper,
    AusterScraper,
    RemoteSourceScraper,
    MeetFrankScraper,
    DribbbleScraper,
    IntershalaScraper,
    WellfoundScraper,
    LinkedInRSSScraper,
]

def run_all():
    logger.info("=== Starting scrape cycle ===")
    for ScraperClass in ALL_SCRAPERS:
        try:
            ScraperClass().run()
        except Exception as e:
            logger.error(f"Failed to run {ScraperClass.__name__}: {e}")
    logger.info("=== Scrape cycle complete ===")

if __name__ == "__main__":
    if "--once" in sys.argv:
        run_all()
    else:
        interval = int(os.getenv("SCRAPE_INTERVAL_MINUTES", "30"))
        logger.info(f"Starting scheduler: every {interval} minutes")
        run_all()  # Run immediately on start
        scheduler = BlockingScheduler()
        scheduler.add_job(run_all, "interval", minutes=interval, id="scrape_all")
        scheduler.start()
