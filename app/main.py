from __future__ import annotations

import argparse
import json
from pathlib import Path

from app.config import settings
from app.integrations.crm_client import CRMClient
from app.integrations.scraper import BellhavenScraper
from app.models import CRMAccount, ScrapedLocation
from app.services.matching_service import generate_proposals
from app.services.review_service import ReviewService


def fetch_and_normalize_accounts() -> list[CRMAccount]:
    client = CRMClient()
    raw_accounts = client.fetch_accounts()
    return [CRMAccount.from_raw(item) for item in raw_accounts]


def fetch_and_normalize_locations() -> list[ScrapedLocation]:
    scraper = BellhavenScraper(settings.bellhaven_base_url)
    html = scraper.fetch_page()
    locations = scraper.parse_locations(html)
    for location in locations:
        location.raw = {"source_url": settings.bellhaven_base_url, **location.raw}
    return locations


def sync_once() -> list[dict]:
    accounts = fetch_and_normalize_accounts()
    locations = fetch_and_normalize_locations()
    proposals = generate_proposals(accounts, locations)
    review_service = ReviewService()
    review_service.save_proposals(proposals)
    return proposals


def main() -> None:
    parser = argparse.ArgumentParser(description="Bellhaven CRM sync assessment pipeline")
    parser.add_argument("command", choices=["sync", "inspect"], help="Choose a pipeline action.")
    args = parser.parse_args()

    if args.command == "sync":
        proposals = sync_once()
        print(json.dumps(proposals, indent=2, default=str)[:4000])
    else:
        print("Use the Streamlit review app for local approval: streamlit run app/review_app.py")


if __name__ == "__main__":
    main()
