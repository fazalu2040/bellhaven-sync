from __future__ import annotations

from typing import Any

from app.config import settings
from app.storage.db import ReviewDatabase


class ReviewService:
    def __init__(self, db_path: str | None = None):
        self.db = ReviewDatabase(db_path or settings.db_path)

    def save_proposals(self, proposals: list[dict[str, Any]]) -> int:
        return self.db.save_proposals(proposals)

    def get_pending_proposals(self) -> list[dict[str, Any]]:
        return self.db.get_pending_proposals()

    def approve(self, proposal_id: str, note: str = "") -> None:
        self.db.approve_proposal(proposal_id, note=note)

    def reject(self, proposal_id: str, note: str = "") -> None:
        self.db.reject_proposal(proposal_id, note=note)
