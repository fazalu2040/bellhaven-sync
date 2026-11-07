import json
import sqlite3
from pathlib import Path
from typing import Any


class ReviewDatabase:
    def __init__(self, db_path: str):
        self.db_path = Path(db_path)
        self.db_path.parent.mkdir(parents=True, exist_ok=True)
        self.init_db()

    def _connect(self) -> sqlite3.Connection:
        conn = sqlite3.connect(self.db_path)
        conn.row_factory = sqlite3.Row
        return conn

    def init_db(self) -> None:
        with self._connect() as conn:
            conn.execute(
                """
                CREATE TABLE IF NOT EXISTS proposals (
                    proposal_id TEXT PRIMARY KEY,
                    fingerprint TEXT UNIQUE,
                    crm_account_id TEXT,
                    classification TEXT,
                    action_type TEXT,
                    match_score REAL,
                    target_parent_id TEXT,
                    new_account_id TEXT,
                    evidence TEXT,
                    status TEXT DEFAULT 'pending',
                    decision_note TEXT DEFAULT ''
                )
                """
            )
            conn.execute(
                """
                CREATE TABLE IF NOT EXISTS decisions (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    proposal_id TEXT,
                    status TEXT,
                    decision_note TEXT,
                    approved_by TEXT,
                    created_at TEXT DEFAULT CURRENT_TIMESTAMP,
                    FOREIGN KEY (proposal_id) REFERENCES proposals(proposal_id)
                )
                """
            )

    def save_proposals(self, proposals: list[dict[str, Any]]) -> int:
        saved = 0
        with self._connect() as conn:
            for proposal in proposals:
                evidence = json.dumps(proposal.get("evidence") or {}, sort_keys=True)
                try:
                    conn.execute(
                        """
                        INSERT OR IGNORE INTO proposals (
                            proposal_id, fingerprint, crm_account_id, classification, action_type,
                            match_score, target_parent_id, new_account_id, evidence, status, decision_note
                        ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
                        """,
                        (
                            proposal.get("proposal_id"),
                            proposal.get("fingerprint"),
                            proposal.get("crm_account_id"),
                            proposal.get("classification"),
                            proposal.get("action_type"),
                            float(proposal.get("match_score") or 0.0),
                            proposal.get("target_parent_id"),
                            proposal.get("new_account_id"),
                            evidence,
                            proposal.get("status") or "pending",
                            proposal.get("decision_note") or "",
                        ),
                    )
                    saved += conn.total_changes
                except sqlite3.Error:
                    continue
        return saved

    def get_pending_proposals(self) -> list[dict[str, Any]]:
        with self._connect() as conn:
            rows = conn.execute(
                "SELECT * FROM proposals WHERE status = 'pending' ORDER BY proposal_id"
            ).fetchall()
        return [self._row_to_dict(row) for row in rows]

    def approve_proposal(self, proposal_id: str, approved_by: str = "local-reviewer", note: str = "") -> None:
        with self._connect() as conn:
            conn.execute(
                "UPDATE proposals SET status = 'approved', decision_note = ? WHERE proposal_id = ?",
                (note, proposal_id),
            )
            conn.execute(
                "INSERT INTO decisions (proposal_id, status, decision_note, approved_by) VALUES (?, 'approved', ?, ?)",
                (proposal_id, note, approved_by),
            )

    def reject_proposal(self, proposal_id: str, approved_by: str = "local-reviewer", note: str = "") -> None:
        with self._connect() as conn:
            conn.execute(
                "UPDATE proposals SET status = 'rejected', decision_note = ? WHERE proposal_id = ?",
                (note, proposal_id),
            )
            conn.execute(
                "INSERT INTO decisions (proposal_id, status, decision_note, approved_by) VALUES (?, 'rejected', ?, ?)",
                (proposal_id, note, approved_by),
            )

    @staticmethod
    def _row_to_dict(row: sqlite3.Row) -> dict[str, Any]:
        return {
            "proposal_id": row["proposal_id"],
            "fingerprint": row["fingerprint"],
            "crm_account_id": row["crm_account_id"],
            "classification": row["classification"],
            "action_type": row["action_type"],
            "match_score": row["match_score"],
            "target_parent_id": row["target_parent_id"],
            "new_account_id": row["new_account_id"],
            "evidence": json.loads(row["evidence"] or "{}"),
            "status": row["status"],
            "decision_note": row["decision_note"],
        }
