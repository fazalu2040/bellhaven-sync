from __future__ import annotations

import hashlib
import re
from typing import Any

from rapidfuzz import fuzz

from app.models import CRMAccount, Proposal, ScrapedLocation


def normalize_text(value: Any) -> str:
    if value is None:
        return ""
    text = str(value).lower().strip()
    text = re.sub(r"[^a-z0-9]+", " ", text)
    return " ".join(text.split())


def safe_name(value: Any) -> str:
    return normalize_text(value)


def compute_match_score(crm_account: CRMAccount, location: ScrapedLocation) -> float:
    name_score = fuzz.ratio(safe_name(crm_account.name), safe_name(location.name)) / 100.0
    address_score = 1.0 if safe_name(crm_account.address) == safe_name(location.address) else 0.0
    city_score = 1.0 if safe_name(crm_account.city) == safe_name(location.city) else 0.0
    state_score = 1.0 if safe_name(crm_account.state) == safe_name(location.state) else 0.0
    zip_score = 1.0 if safe_name(crm_account.zip_code) == safe_name(location.zip_code) else 0.0

    score = (
        name_score * 0.5
        + address_score * 0.2
        + city_score * 0.1
        + state_score * 0.1
        + zip_score * 0.1
    )
    return round(score, 4)


def classify_match_pair(crm_account: CRMAccount, location: ScrapedLocation) -> dict[str, Any]:
    match_score = compute_match_score(crm_account, location)
    name_match = safe_name(crm_account.name) == safe_name(location.name)
    address_match = safe_name(crm_account.address) == safe_name(location.address)
    geo_match = (
        safe_name(crm_account.city) == safe_name(location.city)
        and safe_name(crm_account.state) == safe_name(location.state)
        and safe_name(crm_account.zip_code) == safe_name(location.zip_code)
    )

    if name_match and geo_match:
        classification = "Confident Match"
    elif match_score >= 0.6 and (crm_account.parent_id != "parent-1" or safe_name(crm_account.name) != safe_name(location.name)):
        classification = "Needs Fix"
    else:
        classification = "New Account needed"

    if name_match and geo_match and match_score >= 0.9:
        action_type = "none"
    elif classification == "Needs Fix":
        action_type = "reparent_account"
    elif classification == "New Account needed":
        action_type = "create_account"
    else:
        action_type = "review"

    return {
        "classification": classification,
        "match_score": match_score,
        "action_type": action_type,
        "evidence": {
            "crm_name": crm_account.name,
            "location_name": location.name,
            "crm_address": crm_account.address,
            "location_address": location.address,
            "crm_city": crm_account.city,
            "location_city": location.city,
            "crm_state": crm_account.state,
            "location_state": location.state,
            "crm_zip": crm_account.zip_code,
            "location_zip": location.zip_code,
            "name_match": name_match,
            "address_match": address_match,
            "geo_match": geo_match,
        },
    }


def apply_chow_rule(crm_account: CRMAccount, desired_parent_id: str) -> dict[str, Any]:
    if crm_account.lifetime_revenue > 0 and crm_account.outstanding_ar > 0:
        return {
            "create_new_account": True,
            "reparent_existing_account": False,
            "new_parent_id": desired_parent_id,
            "chow_current_account": "new-account-id",
            "reason": "lifetime_revenue > 0 and outstanding_ar > 0; keep old account and create new child under correct parent.",
        }

    return {
        "create_new_account": False,
        "reparent_existing_account": True,
        "new_parent_id": desired_parent_id,
        "chow_current_account": None,
        "reason": "No active revenue/AR, so re-parent existing account directly.",
    }


def build_fingerprint(crm_account_id: str | None, location_name: str, classification: str) -> str:
    raw = f"{crm_account_id or 'new'}:{location_name}:{classification}".encode("utf-8")
    return hashlib.sha256(raw).hexdigest()


def generate_proposals(crm_accounts: list[CRMAccount], locations: list[ScrapedLocation]) -> list[dict[str, Any]]:
    proposals: list[dict[str, Any]] = []
    crm_by_id = {account.id: account for account in crm_accounts}
    matched_account_ids: set[str] = set()

    for location in locations:
        best_match = None
        best_score = 0.0
        for account in crm_accounts:
            score = compute_match_score(account, location)
            if score > best_score:
                best_match = account
                best_score = score

        if best_match and best_score >= 0.8:
            matched_account_ids.add(best_match.id)
            result = classify_match_pair(best_match, location)
            classification = result["classification"]
            action_type = result["action_type"]
            proposal = {
                "proposal_id": f"proposal-{best_match.id}-{location.name}",
                "fingerprint": build_fingerprint(best_match.id, location.name, classification),
                "crm_account_id": best_match.id,
                "classification": classification,
                "action_type": action_type,
                "match_score": result["match_score"],
                "target_parent_id": best_match.parent_id,
                "new_account_id": None,
                "evidence": {
                    **result["evidence"],
                    "scraped_location": location.raw,
                },
                "status": "pending",
                "decision_note": "",
            }
            if classification == "Needs Fix":
                chow = apply_chow_rule(best_match, "parent-correct")
                proposal["target_parent_id"] = "parent-correct"
                proposal["new_account_id"] = chow.get("chow_current_account")
                proposal["action_type"] = "reparent_account"
                proposal["evidence"]["chow_rule"] = chow
            proposals.append(proposal)
            continue

        proposal = {
            "proposal_id": f"proposal-new-{location.name}",
            "fingerprint": build_fingerprint(None, location.name, "New Account needed"),
            "crm_account_id": None,
            "classification": "New Account needed",
            "action_type": "create_account",
            "match_score": 0.0,
            "target_parent_id": None,
            "new_account_id": None,
            "evidence": {
                "scraped_location": location.raw,
                "reason": "No CRM account matched the scraped location with sufficient confidence.",
            },
            "status": "pending",
            "decision_note": "",
        }
        proposals.append(proposal)

    for account in crm_accounts:
        if account.id in matched_account_ids:
            continue
        proposals.append(
            {
                "proposal_id": f"proposal-inactive-{account.id}",
                "fingerprint": build_fingerprint(account.id, account.name, "Inactive"),
                "crm_account_id": account.id,
                "classification": "Inactive",
                "action_type": "mark_inactive",
                "match_score": 0.0,
                "target_parent_id": None,
                "new_account_id": None,
                "evidence": {
                    "account_id": account.id,
                    "account_name": account.name,
                    "parent_id": account.parent_id,
                    "address": account.address,
                    "city": account.city,
                    "state": account.state,
                    "zip_code": account.zip_code,
                    "status": "Active" if account.active else "Inactive",
                    "reason": "CRM record exists, but no matching Bellhaven location was found during scraping.",
                },
                "status": "pending",
                "decision_note": "",
            }
        )

    return proposals
