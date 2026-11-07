from __future__ import annotations

from app.integrations.crm_client import CRMClient


class WritebackService:
    def __init__(self, crm_client: CRMClient | None = None):
        self.crm_client = crm_client or CRMClient()

    def _scraped_location(self, proposal: dict) -> dict:
        evidence = proposal.get("evidence", {})
        return evidence.get("scraped_location") or {}

    def apply_approved_proposal(self, proposal: dict) -> dict:
        action_type = proposal.get("action_type")
        if action_type == "create_account":
            location = self._scraped_location(proposal)
            name = (
                location.get("name")
                or location.get("location_name")
                or location.get("source_name")
                or location.get("text")
                or proposal.get("proposal_id")
                or "Bellhaven Location"
            )
            name = str(name).strip()
            if len(name) > 120:
                name = name[:120].strip()

            payload = {
                "name": name,
                "address": location.get("address") or "",
                "city": location.get("city") or "",
                "state": location.get("state") or "",
                "zip": location.get("zip") or location.get("zip_code") or "",
                "care_offerings": location.get("care_offerings") or [],
                "status": "Active",
            }
            payload = {key: value for key, value in payload.items() if value not in (None, "", [], {})}
            return self.crm_client.create_account(payload)

        if action_type == "reparent_account":
            crm_id = proposal.get("crm_account_id")
            payload = {
                "parent_id": proposal.get("target_parent_id"),
                "status": "Active",
                "note": proposal.get("decision_note") or "Parent account updated after review.",
            }
            payload = {key: value for key, value in payload.items() if value not in (None, "", [], {})}
            return self.crm_client.update_account(crm_id, payload)

        if action_type == "mark_inactive":
            crm_id = proposal.get("crm_account_id")
            payload = {
                "status": "Inactive",
                "active": False,
                "note": proposal.get("decision_note") or "Marked inactive because no matching Bellhaven location was found.",
            }
            payload = {key: value for key, value in payload.items() if value not in (None, "", [], {})}
            return self.crm_client.update_account(crm_id, payload)

        if action_type == "mark_duplicate":
            crm_id = proposal.get("crm_account_id")
            payload = {
                "status": "Inactive",
                "active": False,
                "duplicate_of_account": proposal.get("new_account_id") or proposal.get("target_parent_id"),
                "note": proposal.get("decision_note") or "Duplicate record. Marked inactive and linked to surviving account.",
            }
            payload = {key: value for key, value in payload.items() if value not in (None, "", [], {})}
            return self.crm_client.update_account(crm_id, payload)

        return {"status": "skipped", "action_type": action_type, "proposal_id": proposal.get("proposal_id")}

    def apply_approved_proposals(self, proposals: list[dict]) -> list[dict]:
        results: list[dict] = []
        for proposal in proposals:
            if proposal.get("status") != "approved":
                results.append({"proposal_id": proposal.get("proposal_id"), "status": "not_approved"})
                continue
            results.append(self.apply_approved_proposal(proposal))
        return results
