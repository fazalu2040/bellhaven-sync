from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any, Optional


@dataclass
class CRMAccount:
    id: str
    name: str
    parent_id: Optional[str] = None
    city: str = ""
    state: str = ""
    zip_code: str = ""
    address: str = ""
    lifetime_revenue: float = 0.0
    outstanding_ar: float = 0.0
    active: bool = True
    raw: dict[str, Any] = field(default_factory=dict)

    @classmethod
    def from_raw(cls, payload: dict[str, Any]) -> "CRMAccount":
        raw = payload or {}
        return cls(
            id=str(raw.get("id") or raw.get("account_id") or raw.get("crm_id") or ""),
            name=str(raw.get("name") or "").strip(),
            parent_id=(str(raw.get("parent_id") or raw.get("parentAccountId") or "") or None),
            city=str(raw.get("city") or raw.get("billing_city") or "").strip(),
            state=str(raw.get("state") or raw.get("billing_state") or "").strip(),
            zip_code=str(raw.get("zip") or raw.get("postal_code") or raw.get("billing_zip") or "").strip(),
            address=str(raw.get("address") or raw.get("street") or raw.get("billing_address") or "").strip(),
            lifetime_revenue=float(raw.get("lifetime_revenue") or 0.0),
            outstanding_ar=float(raw.get("outstanding_ar") or 0.0),
            active=bool(raw.get("active", True)),
            raw=raw,
        )


@dataclass
class ScrapedLocation:
    source_name: str
    name: str
    address: str
    city: str
    state: str
    zip_code: str
    care_offerings: list[str] = field(default_factory=list)
    raw: dict[str, Any] = field(default_factory=dict)

    @classmethod
    def from_raw(cls, payload: dict[str, Any]) -> "ScrapedLocation":
        name = str(payload.get("name") or payload.get("source_name") or "").strip()
        return cls(
            source_name=str(payload.get("source_name") or name),
            name=name,
            address=str(payload.get("address") or "").strip(),
            city=str(payload.get("city") or "").strip(),
            state=str(payload.get("state") or "").strip(),
            zip_code=str(payload.get("zip") or payload.get("zip_code") or "").strip(),
            care_offerings=[str(item).strip() for item in payload.get("care_offerings", []) if str(item).strip()],
            raw=payload,
        )


@dataclass
class Proposal:
    proposal_id: str
    fingerprint: str
    crm_account_id: Optional[str]
    classification: str
    action_type: str
    match_score: float
    target_parent_id: Optional[str] = None
    new_account_id: Optional[str] = None
    evidence: dict[str, Any] = field(default_factory=dict)
    status: str = "pending"
    decision_note: str = ""

    def to_db_row(self) -> dict[str, Any]:
        return {
            "proposal_id": self.proposal_id,
            "fingerprint": self.fingerprint,
            "crm_account_id": self.crm_account_id,
            "classification": self.classification,
            "action_type": self.action_type,
            "match_score": self.match_score,
            "target_parent_id": self.target_parent_id,
            "new_account_id": self.new_account_id,
            "evidence": self.evidence,
            "status": self.status,
            "decision_note": self.decision_note,
        }
