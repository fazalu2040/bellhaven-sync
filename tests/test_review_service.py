import requests

from app.integrations.crm_client import CRMClient
from app.services.review_service import ReviewService
from app.services.writeback_service import WritebackService


def test_review_service_is_idempotent_for_duplicate_proposals(tmp_path):
    db_path = tmp_path / "review.db"
    service = ReviewService(db_path=str(db_path))

    first = {
        "proposal_id": "dup-1",
        "fingerprint": "abc123",
        "crm_account_id": "crm-1",
        "classification": "Needs Fix",
        "action_type": "reparent_account",
        "evidence": {"source": "fixture"},
        "status": "pending",
    }

    second = {
        "proposal_id": "dup-1",
        "fingerprint": "abc123",
        "crm_account_id": "crm-1",
        "classification": "Needs Fix",
        "action_type": "reparent_account",
        "evidence": {"source": "fixture"},
        "status": "pending",
    }

    service.save_proposals([first, second])

    pending = service.get_pending_proposals()
    assert len(pending) == 1
    assert pending[0]["proposal_id"] == "dup-1"


def test_update_account_uses_patch_first_with_405_fallback(monkeypatch):
    client = CRMClient(base_url="https://example.com/api/v1", token="token")
    calls = []

    class FakeResponse:
        def __init__(self, status_code: int):
            self.status_code = status_code
            self.text = ""

        def raise_for_status(self):
            if self.status_code >= 400:
                raise requests.exceptions.HTTPError(f"status {self.status_code}")

        def json(self):
            return {"status": "ok"}

    def fake_request(method, url, **kwargs):
        calls.append(method)
        if method == "PATCH":
            return FakeResponse(405)
        return FakeResponse(200)

    monkeypatch.setattr(client.session, "request", fake_request)

    result = client.update_account("acct-123", {"active": False})

    assert calls == ["PATCH", "PUT"]
    assert result == {"status": "ok"}


def test_writeback_service_uses_fallback_name_for_create_account():
    class DummyCRMClient:
        def __init__(self):
            self.created = []

        def create_account(self, payload):
            self.created.append(payload)
            return {"status": "ok", "payload": payload}

    client = DummyCRMClient()
    service = WritebackService(crm_client=client)
    proposal = {
        "proposal_id": "proposal-new-fallback",
        "action_type": "create_account",
        "status": "approved",
        "evidence": {
            "scraped_location": {
                "source_url": "https://example.com",
                "text": "Bellhaven community with assisted living and rehabilitation support.",
            }
        },
    }

    result = service.apply_approved_proposal(proposal)

    assert result["status"] == "ok"
    assert client.created[0]["name"] == "Bellhaven community with assisted living and rehabilitation support."
    assert client.created[0]["status"] == "Active"


def test_writeback_service_sets_duplicate_fields_and_inactive_status():
    class DummyCRMClient:
        def __init__(self):
            self.payloads = []

        def update_account(self, account_id, payload):
            self.payloads.append({"account_id": account_id, "payload": payload})
            return {"status": "ok", "account_id": account_id}

    client = DummyCRMClient()
    service = WritebackService(crm_client=client)
    proposal = {
        "proposal_id": "dup-1",
        "crm_account_id": "acct-old",
        "action_type": "mark_duplicate",
        "new_account_id": "acct-new",
        "decision_note": "Duplicate of surviving account.",
        "status": "approved",
    }

    result = service.apply_approved_proposal(proposal)

    assert result["account_id"] == "acct-old"
    assert client.payloads[0]["payload"]["duplicate_of_account"] == "acct-new"
    assert client.payloads[0]["payload"]["status"] == "Inactive"
    assert client.payloads[0]["payload"]["active"] is False
