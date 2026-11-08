from __future__ import annotations

import json

import streamlit as st

from app.main import sync_once
from app.services.review_service import ReviewService
from app.services.writeback_service import WritebackService


def render_proposal(proposal: dict) -> None:
    classification = proposal.get("classification", "Review")
    proposal_id = proposal.get("proposal_id", "unknown")
    crm_account_id = proposal.get("crm_account_id") or "N/A"
    match_score = proposal.get("match_score") or "N/A"
    action_type = proposal.get("action_type") or "review"
    source = proposal.get("source") or "CRM"
    created_at = proposal.get("created_at") or "—"
    evidence = proposal.get("evidence") or {}
    evidence_json = json.dumps(evidence, indent=2, ensure_ascii=False, default=str)

    st.markdown(
        f"""
        <div class="proposal-shell">
          <table class="proposal-table">
            <thead>
              <tr>
                <th>Proposal</th>
                <th>CRM Account</th>
                <th>Match Score</th>
                <th>Action</th>
                <th>Source</th>
                <th>Decision</th>
              </tr>
            </thead>
            <tbody>
              <tr>
                <td>
                  <span class="proposal-badge {classification.lower()}">{classification}</span>
                  <div class="proposal-id">{proposal_id}</div>
                  <small>{created_at}</small>
                </td>
                <td>{crm_account_id}</td>
                <td>{match_score}</td>
                <td>{action_type}</td>
                <td>{source}</td>
                <td>
                  <div class="decision-badge">Ready for review</div>
                </td>
              </tr>
            </tbody>
          </table>
        </div>
        """,
        unsafe_allow_html=True,
    )

    with st.container():
        review_col, action_col = st.columns([2.3, 1.1])

        with review_col:
            with st.expander("Open evidence JSON", expanded=True):
                st.code(evidence_json, language="json")

        with action_col:
            st.markdown("<div class='proposal-actions'>", unsafe_allow_html=True)
            approve_col, reject_col = st.columns(2)

            with approve_col:
                if st.button("Approve", key=f"approve-{proposal_id}", use_container_width=True):
                    try:
                        proposal["status"] = "approved"
                        ReviewService().approve(proposal_id, note="Approved via local review app")
                        output = WritebackService().apply_approved_proposal(proposal)
                        st.success(f"Approved and applied: {output}")
                    except Exception as exc:  # pragma: no cover - UI safety path
                        ReviewService().reject(proposal_id, note=f"Write-back failed: {exc}")
                        st.error(f"Write-back failed: {exc}")

            with reject_col:
                if st.button("Reject", key=f"reject-{proposal_id}", use_container_width=True):
                    ReviewService().reject(proposal_id, note="Rejected via local review app")
                    st.warning("Proposal rejected and removed from the pending queue.")

            st.markdown("</div>", unsafe_allow_html=True)

    st.markdown("---")


def main() -> None:
    st.markdown(
        """
        <style>
            .block-container {
                padding-top: 2rem;
                padding-bottom: 2rem;
            }
            .proposal-shell {
                background: linear-gradient(135deg, rgba(15, 118, 110, 0.18), rgba(30, 64, 175, 0.22));
                border: 1px solid rgba(147, 197, 253, 0.35);
                border-radius: 1rem;
                overflow: hidden;
                box-shadow: 0 20px 40px rgba(13, 38, 76, 0.32);
                margin-bottom: 1rem;
                backdrop-filter: blur(8px);
            }
            .proposal-table {
                width: 100%;
                border-collapse: collapse;
                background: rgba(15, 23, 42, 0.75);
            }
            .proposal-table th,
            .proposal-table td {
                padding: 0.9rem 0.85rem;
                border-bottom: 1px solid rgba(148, 163, 184, 0.18);
                text-align: left;
                vertical-align: top;
                color: #e2e8f0;
            }
            .proposal-table thead th {
                background: linear-gradient(180deg, rgba(96, 165, 250, 0.18), rgba(15, 23, 42, 0.82));
                color: #dbeafe;
                font-weight: 700;
                text-transform: uppercase;
                letter-spacing: 0.08em;
                font-size: 0.72rem;
            }
            .proposal-table tbody td {
                background: rgba(15, 23, 42, 0.4);
                font-size: 0.9rem;
            }
            .proposal-table td small {
                display: block;
                margin-top: 0.35rem;
                color: #93c5fd;
            }
            .proposal-badge {
                display: inline-flex;
                align-items: center;
                border-radius: 999px;
                padding: 0.38rem 0.8rem;
                font-size: 0.64rem;
                font-weight: 700;
                letter-spacing: 0.08em;
                text-transform: uppercase;
                border: 1px solid transparent;
                margin-bottom: 0.5rem;
            }
            .proposal-badge.review {
                background: rgba(59, 130, 246, 0.18);
                color: #dbeafe;
                border-color: rgba(147, 197, 253, 0.45);
            }
            .proposal-badge.create {
                background: rgba(16, 185, 129, 0.16);
                color: #bbf7d0;
                border-color: rgba(52, 211, 153, 0.42);
            }
            .proposal-badge.update {
                background: rgba(245, 158, 11, 0.16);
                color: #fef3c7;
                border-color: rgba(251, 191, 36, 0.42);
            }
            .proposal-badge.delete {
                background: rgba(239, 68, 68, 0.16);
                color: #fecaca;
                border-color: rgba(248, 113, 113, 0.42);
            }
            .proposal-id {
                display: block;
                color: #f8fafc;
                font-weight: 600;
                margin-bottom: 0.15rem;
            }
            [data-testid="stExpander"] {
                border: 1px solid rgba(147, 197, 253, 0.2);
                border-radius: 0.8rem;
                background: rgba(15, 23, 42, 0.5);
                overflow: hidden;
            }
            .proposal-actions {
                margin-top: 0.35rem;
                padding-top: 0.4rem;
            }
            .decision-badge {
                display: inline-flex;
                align-items: center;
                border-radius: 999px;
                padding: 0.4rem 0.7rem;
                font-size: 0.68rem;
                font-weight: 700;
                letter-spacing: 0.04em;
                background: rgba(96, 165, 250, 0.15);
                color: #dbeafe;
                border: 1px solid rgba(147, 197, 253, 0.3);
            }
            .stButton > button {
                border-radius: 0.7rem;
                font-weight: 700;
                border: 1px solid rgba(147, 197, 253, 0.2);
                transition: all 0.2s ease;
            }
            .stButton > button:hover {
                transform: translateY(-1px);
                box-shadow: 0 12px 20px rgba(30, 64, 175, 0.2);
            }
            div[data-testid="stHorizontalBlock"] {
                gap: 0.75rem;
            }
        </style>
        """,
        unsafe_allow_html=True,
    )

    st.title("Bellhaven CRM Sync Review")
    st.caption("Review each suggested change before writing it back to the CRM.")
    st.markdown("---")
    if "loaded" not in st.session_state:
        st.session_state.loaded = False

    if not st.session_state.loaded:
        if st.button("Load proposals", type="primary"):
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
