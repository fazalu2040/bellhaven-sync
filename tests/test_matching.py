from app.models import CRMAccount, ScrapedLocation
from app.services.matching_service import (
    apply_chow_rule,
    classify_match_pair,
    generate_proposals,
)


def test_confident_match_classification():
    crm = CRMAccount(
        id="crm-1",
        name="Bellhaven Village",
        parent_id="parent-1",
        city="Raleigh",
        state="NC",
        zip_code="27601",
        address="123 Main St",
        lifetime_revenue=1000.0,
        outstanding_ar=50.0,
    )
    location = ScrapedLocation(
        source_name="Bellhaven Village",
        name="Bellhaven Village",
        address="123 Main St",
        city="Raleigh",
        state="NC",
        zip_code="27601",
        care_offerings=["Skilled Nursing"],
    )

    result = classify_match_pair(crm, location)

    assert result["classification"] == "Confident Match"
    assert result["match_score"] >= 0.9


def test_chow_rule_keeps_old_account_and_creates_new_one():
    crm = CRMAccount(
        id="crm-old",
        name="Bellhaven North",
        parent_id="parent-old",
        city="Charlotte",
        state="NC",
        zip_code="28202",
        address="444 Oak Ave",
        lifetime_revenue=5000.0,
        outstanding_ar=1200.0,
    )

    rule = apply_chow_rule(crm, "parent-correct")

    assert rule["create_new_account"] is True
    assert rule["reparent_existing_account"] is False
    assert rule["chow_current_account"] == "new-account-id"


def test_generate_proposals_for_new_account_and_inactive_account():
    crm_accounts = [
        CRMAccount(
            id="crm-1",
            name="Bellhaven East",
            parent_id="parent-1",
            city="Greensboro",
            state="NC",
            zip_code="27401",
            address="11 Pine Rd",
            lifetime_revenue=0.0,
            outstanding_ar=0.0,
        )
    ]
    locations = [
        ScrapedLocation(
            source_name="Bellhaven East",
            name="Bellhaven East",
            address="11 Pine Rd",
            city="Greensboro",
            state="NC",
            zip_code="27401",
            care_offerings=["Assisted Living"],
        ),
        ScrapedLocation(
            source_name="Bellhaven New Care",
            name="Bellhaven New Care",
            address="99 Lake St",
            city="Durham",
            state="NC",
            zip_code="27701",
            care_offerings=["Memory Care"],
        ),
    ]

    proposals = generate_proposals(crm_accounts, locations)

    assert any(p["classification"] == "Confident Match" for p in proposals)
    assert any(p["classification"] == "New Account needed" for p in proposals)


def test_inactive_proposal_evidence_is_clean_and_flat():
    crm_accounts = [
        CRMAccount(
            id="crm-2",
            name="Amberly Estates",
            parent_id="parent-1",
            city="Parma",
            state="OH",
            zip_code="44129",
            address="9735 Maple St",
            lifetime_revenue=0.0,
            outstanding_ar=0.0,
        )
    ]
    locations = [
        ScrapedLocation(
            source_name="Bellhaven North",
            name="Bellhaven North",
            address="222 Cedar Ave",
            city="Cleveland",
            state="OH",
            zip_code="44113",
            care_offerings=["Assisted Living"],
        )
    ]

    proposals = generate_proposals(crm_accounts, locations)
    inactive = next(p for p in proposals if p["classification"] == "Inactive")

    assert "crm_account" not in inactive["evidence"]
    assert "reason" in inactive["evidence"]
    assert inactive["evidence"]["account_id"] == "crm-2"
    assert inactive["evidence"]["account_name"] == "Amberly Estates"
