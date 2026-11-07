# Bellhaven Sync Assessment

This project contains a backend pipeline and local review app for CRM account synchronization with Bellhaven location data.

## Features

- Fetches CRM accounts from the configured API using the bearer token.
- Scrapes Bellhaven locations from the public site.
- Normalizes and matches CRM records with scraped locations.
- Classifies changes into Confident Match, Needs Fix, New Account needed, or Inactive.
- Applies the CHOW rule for parent changes with revenue / AR safeguards.
- Stores proposals in a local SQLite database.
- Lets a reviewer approve or reject proposals in a local Streamlit UI.
- Writes only approved changes back to the CRM.
- Prevents duplicate proposals through a deterministic proposal fingerprint.

## Quickstart

1. Install dependencies:

   python -m pip install -r requirements.txt

2. Copy the environment template:

   copy .env.example .env

3. Run a sync pass:

   python -m app.main sync

4. Start the local review app:

   streamlit run app/review_app.py

## Sample architecture

- app/main.py — sync entrypoint and CLI
- app/integrations/crm_client.py — CRM API client
- app/integrations/scraper.py — Bellhaven site scraper
- app/services/matching_service.py — matching and CHOW logic
- app/services/review_service.py — local decision tracking
- app/services/writeback_service.py — approved writes back to the CRM
- app/review_app.py — local approval UI
- .github/workflows/daily-sync.yml — daily automation sample
