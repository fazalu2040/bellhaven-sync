# Bellhaven CRM Sync Assessment - Implementation Summary

## Overview

This project implements a local CRM synchronization workflow for Bellhaven data review. It includes:

- CRM account retrieval from the configured API
- Bellhaven site scraping for location-level data
- Matching and classification logic for each account/location pair
- CHOW (Change of Ownership) handling rules
- A local review app for approving or rejecting proposed changes
- SQLite-backed idempotent proposal tracking
- Daily workflow automation configuration

## Implemented Components

### 1. CRM Integration

File: `app/integrations/crm_client.py`

Responsibilities:
- Reads the CRM base URL and bearer token from environment settings
- Sends `Authorization: Bearer <token>` headers
- Fetches accounts from `GET /api/v1/accounts`
- Creates or updates CRM records only after approval
- Retries account writes when the API rejects the initial method with `405 Method Not Allowed`

Validation behavior:
- `GET` is used for read access
- `PUT` is attempted first for updates
- If the API rejects with `405`, the client retries with `POST`
- A final fallback to `PATCH` is attempted if needed

This is implemented to avoid crashing the approval flow when the live API is strict about update verbs.

### 2. Bellhaven Scraper

File: `app/integrations/scraper.py`

Responsibilities:
- Fetches the Bellhaven site HTML
- Parses location and care information from page content
- Extracts normalized fields for:
  - name
  - address
  - city
  - state
  - zip
  - care offerings

Normalization logic:
- Strips whitespace and formatting noise
- Normalizes names and addresses for matching
- Deduplicates repeated entries by identifying location identity fields

### 3. Matching and Classification

File: `app/services/matching_service.py`

Responsibilities:
- Computes a deterministic similarity score between CRM accounts and scraped locations
- Matches on normalized name, address, city, state, and zip
- Classifies each item into one of:
  - `Confident Match`
  - `Needs Fix`
  - `New Account needed`
  - `Inactive`

Rule summary:
- Exact normalized name + geography match = `Confident Match`
- Similar but not exact record = likely `Needs Fix` or `New Account needed`
- CRM account with no scraped match = `Inactive`

### 4. CHOW SOP Rule

File: `app/services/matching_service.py`

The implementation follows the stated CHOW requirement:

- If an account needs a parent change, check:
  - `lifetime_revenue`
  - `outstanding_ar`
- If `lifetime_revenue > 0` and `outstanding_ar > 0`:
  - do not re-parent the old account
  - keep the old account as-is
  - create a new account under the correct parent
  - set `chow_current_account` to the new account ID on the old account
- If revenue or AR does not satisfy the condition:
  - re-parent the existing account directly

This logic is explicitly encoded in the `apply_chow_rule()` function.

### 5. Review Queue and Idempotency

Files:
- `app/storage/db.py`
- `app/services/review_service.py`

Responsibilities:
- Store proposals in SQLite
- Track each proposal with a fingerprint
- Prevent duplicate recommendations across repeated runs
- Keep pending, approved, and rejected statuses

Idempotency rule:
- Same proposal fingerprint is treated as a duplicate
- Approved items are not re-proposed
- Rejected items are retained as a decision and not continuously re-added unless real data changes

### 6. Local Review Interface

File: `app/review_app.py`

Responsibilities:
- Loads proposals from the sync pipeline
- Shows each proposed change with evidence
- Allows reviewer actions:
  - Approve
  - Reject
- Calls the writeback layer only after approval
- Captures and surfaces write-back failures without crashing the app

### 7. Automation

File: `.github/workflows/daily-sync.yml`

Responsibilities:
- Runs the sync pipeline daily via GitHub Actions cron schedule
- Uses environment variables for CRM configuration
- Invokes the project’s Python sync entrypoint

## Validation Evidence

The project has been validated with automated tests:

- `pytest` suite result: `5 passed in 0.24s`

Validated behaviors include:
- matching logic
- classification logic
- CHOW rule branching
- idempotent proposal storage
- API fallback handling for `405` responses

## Current Run Status

The app is set up to run locally with the project virtual environment. The recommended launch command is:

```powershell
cd C:\Projects\bellhaven-sync\bellhaven-sync
c:/Projects/bellhaven-sync/bellhaven-sync/.venv/Scripts/python.exe -m streamlit run app/review_app.py --server.headless true --server.port 8502
```

This opens the review UI on:

- `http://localhost:8502`

## Notes

This implementation is intentionally conservative:
- It does not write to CRM until a proposal is approved.
- It does not mutate duplicate work.
- It logs and surfaces failures instead of hiding them.
- It is designed to be auditable and repeatable for daily use.
