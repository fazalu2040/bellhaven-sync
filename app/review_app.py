from __future__ import annotations

import json

import streamlit as st

from app.main import sync_once
from app.services.review_service import ReviewService
from app.services.writeback_service import WritebackService


def render_proposal(proposal: dict) -> None:
    st.markdown(f"### {proposal['classification']} — {proposal['proposal_id']}")
    st.write(f"CRM Account: {proposal.get('crm_account_id')}")
    st.write(f"Match Score: {proposal.get('match_score')}")
    st.write(f"Action: {proposal.get('action_type')}")
    st.json(proposal.get("evidence", {}))

    if st.button("Approve", key=f"approve-{proposal['proposal_id']}"):
        try:
            proposal["status"] = "approved"
            ReviewService().approve(proposal["proposal_id"], note="Approved via local review app")
            output = WritebackService().apply_approved_proposal(proposal)
            st.success(f"Approved and applied: {output}")
        except Exception as exc:  # pragma: no cover - UI safety path
            ReviewService().reject(proposal["proposal_id"], note=f"Write-back failed: {exc}")
            st.error(f"Write-back failed: {exc}")

    if st.button("Reject", key=f"reject-{proposal['proposal_id']}"):
        ReviewService().reject(proposal["proposal_id"], note="Rejected via local review app")
        st.warning("Proposal rejected and removed from the pending queue.")


def main() -> None:
    st.title("Bellhaven CRM Sync Review")
    st.caption("Review each suggested change before writing it back to the CRM.")

    if "loaded" not in st.session_state:
        st.session_state.loaded = False

    if not st.session_state.loaded:
        if st.button("Load proposals"):
            proposals = sync_once()
            st.session_state.proposals = proposals
            st.session_state.loaded = True

    if st.session_state.get("proposals"):
        for proposal in st.session_state["proposals"]:
            render_proposal(proposal)
    else:
        st.info("No proposals loaded yet. Click Load proposals to generate the review queue.")


if __name__ == "__main__":
    main()
