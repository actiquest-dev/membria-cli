"""Storage layer for Engrams and graph data."""

import json
import sqlite3
from pathlib import Path
from typing import Optional, List, Dict, Any
from datetime import datetime
import logging

from membria.models import Engram, Decision

logger = logging.getLogger(__name__)


class EngramStorage:
    """Manages persistent storage of Engrams (session checkpoints)."""

    def __init__(self, storage_dir: Optional[Path] = None):
        """Initialize engram storage."""
        self.storage_dir = storage_dir or (Path.home() / ".membria" / "engrams")
        self.storage_dir.mkdir(parents=True, exist_ok=True)
        self.pending_dir = self.storage_dir / "pending"
        self.pending_dir.mkdir(exist_ok=True)
        self.index_db = self.storage_dir / "index.db"
        self._init_index_db()

    def _init_index_db(self) -> None:
        """Initialize SQLite index database."""
        conn = sqlite3.connect(str(self.index_db))
        cursor = conn.cursor()

        cursor.execute("""
            CREATE TABLE IF NOT EXISTS engrams (
                engram_id TEXT PRIMARY KEY,
                session_id TEXT NOT NULL,
                commit_sha TEXT,
                branch TEXT,
                timestamp DATETIME NOT NULL,
                intent TEXT,
                decisions TEXT,
                file_path TEXT,
                created_at DATETIME DEFAULT CURRENT_TIMESTAMP
            )
        """)

        cursor.execute("""
            CREATE INDEX IF NOT EXISTS idx_timestamp ON engrams(timestamp DESC)
        """)

        cursor.execute("""
            CREATE INDEX IF NOT EXISTS idx_commit ON engrams(commit_sha)
        """)

        cursor.execute("""
            CREATE INDEX IF NOT EXISTS idx_branch ON engrams(branch)
        """)

        conn.commit()
        conn.close()

    def save_engram(self, engram: Engram) -> bool:
        """Save an engram to storage."""
        try:
            # Save JSON file
            file_path = self.pending_dir / f"{engram.engram_id}.json"
            with open(file_path, "w") as f:
                json.dump(self._serialize_engram(engram), f, indent=2, default=str)

            # Update index
            conn = sqlite3.connect(str(self.index_db))
            cursor = conn.cursor()

            decisions_json = json.dumps(engram.decisions_extracted)
            cursor.execute("""
                INSERT OR REPLACE INTO engrams
                (engram_id, session_id, commit_sha, branch, timestamp, intent, decisions, file_path)
                VALUES (?, ?, ?, ?, ?, ?, ?, ?)
            """, (
                engram.engram_id,
                engram.session_id,
                engram.commit_sha,
                engram.branch,
                engram.timestamp.isoformat(),
                engram.summary.intent if engram.summary else None,
                decisions_json,
                str(file_path)
            ))

            conn.commit()
            conn.close()

            logger.info(f"Saved engram {engram.engram_id}")
            return True

        except Exception as e:
            logger.error(f"Failed to save engram: {e}")
            return False

    def load_engram(self, engram_id: str) -> Optional[Engram]:
        """Load an engram from storage."""
        try:
            file_path = self.pending_dir / f"{engram_id}.json"
            if not file_path.exists():
                return None

            with open(file_path) as f:
                data = json.load(f)

            return self._deserialize_engram(data)

        except Exception as e:
            logger.error(f"Failed to load engram {engram_id}: {e}")
            return None

    def list_engrams(self, limit: int = 10, branch: Optional[str] = None) -> List[Dict[str, Any]]:
        """List recent engrams."""
        try:
            conn = sqlite3.connect(str(self.index_db))
            cursor = conn.cursor()

            if branch:
                query = """
                    SELECT engram_id, session_id, commit_sha, branch, timestamp, intent
                    FROM engrams
                    WHERE branch = ?
                    ORDER BY timestamp DESC
                    LIMIT ?
                """
                cursor.execute(query, (branch, limit))
            else:
                query = """
                    SELECT engram_id, session_id, commit_sha, branch, timestamp, intent
                    FROM engrams
                    ORDER BY timestamp DESC
                    LIMIT ?
                """
                cursor.execute(query, (limit,))

            rows = cursor.fetchall()
            conn.close()

            return [
                {
                    "engram_id": row[0],
                    "session_id": row[1],
                    "commit_sha": row[2],
                    "branch": row[3],
                    "timestamp": row[4],
                    "intent": row[5],
                }
                for row in rows
            ]

        except Exception as e:
            logger.error(f"Failed to list engrams: {e}")
            return []

    def search_engrams(self, query: str, limit: int = 10) -> List[Dict[str, Any]]:
        """Search engrams by intent (simple text search)."""
        try:
            conn = sqlite3.connect(str(self.index_db))
            cursor = conn.cursor()

            sql_query = """
                SELECT engram_id, session_id, timestamp, intent
                FROM engrams
                WHERE intent LIKE ?
                ORDER BY timestamp DESC
                LIMIT ?
            """
            cursor.execute(sql_query, (f"%{query}%", limit))

            rows = cursor.fetchall()
            conn.close()

            return [
                {
                    "engram_id": row[0],
                    "session_id": row[1],
                    "timestamp": row[2],
                    "intent": row[3],
                }
                for row in rows
            ]

        except Exception as e:
            logger.error(f"Failed to search engrams: {e}")
            return []

    @staticmethod
    def _serialize_engram(engram: Engram) -> Dict[str, Any]:
        """Convert engram to JSON-serializable dict."""
        return {
            "engram_id": engram.engram_id,
            "session_id": engram.session_id,
            "commit_sha": engram.commit_sha,
            "branch": engram.branch,
            "timestamp": engram.timestamp.isoformat(),
            "agent": {
                "type": engram.agent.type,
                "model": engram.agent.model,
                "session_duration_sec": engram.agent.session_duration_sec,
                "total_tokens": engram.agent.total_tokens,
                "total_cost_usd": engram.agent.total_cost_usd,
            },
            "transcript": [
                {
                    "role": msg.role,
                    "content": msg.content,
                    "timestamp": msg.timestamp.isoformat(),
                    "tool_calls": msg.tool_calls,
                }
                for msg in engram.transcript
            ],
            "files_changed": [
                {
                    "path": fc.path,
                    "action": fc.action,
                    "lines_added": fc.lines_added,
                    "lines_removed": fc.lines_removed,
                }
                for fc in engram.files_changed
            ],
            "decisions_extracted": engram.decisions_extracted,
            "membria_context_injected": engram.membria_context_injected,
            "antipatterns_triggered": engram.antipatterns_triggered,
            "summary": {
                "intent": engram.summary.intent,
                "outcome": engram.summary.outcome,
                "learnings": engram.summary.learnings,
                "friction_points": engram.summary.friction_points,
                "open_items": engram.summary.open_items,
            } if engram.summary else None,
        }

    @staticmethod
    def _deserialize_engram(data: Dict[str, Any]) -> Engram:
        """Convert JSON dict back to Engram object."""
        # Simplified deserialization - in production would be more complete
        from membria.models import AgentInfo, TranscriptMessage, FileChange, EngramSummary

        agent = AgentInfo(
            type=data["agent"]["type"],
            model=data["agent"]["model"],
            session_duration_sec=data["agent"]["session_duration_sec"],
            total_tokens=data["agent"]["total_tokens"],
            total_cost_usd=data["agent"]["total_cost_usd"],
        )

        transcript = [
            TranscriptMessage(
                role=msg["role"],
                content=msg["content"],
                timestamp=datetime.fromisoformat(msg["timestamp"]),
                tool_calls=msg.get("tool_calls", []),
            )
            for msg in data["transcript"]
        ]

        files_changed = [
            FileChange(
                path=fc["path"],
                action=fc["action"],
                lines_added=fc["lines_added"],
                lines_removed=fc["lines_removed"],
            )
            for fc in data["files_changed"]
        ]

        summary = None
        if data.get("summary"):
            summary = EngramSummary(
                intent=data["summary"]["intent"],
                outcome=data["summary"]["outcome"],
                learnings=data["summary"]["learnings"],
                friction_points=data["summary"]["friction_points"],
                open_items=data["summary"]["open_items"],
            )

        return Engram(
            engram_id=data["engram_id"],
            session_id=data["session_id"],
            commit_sha=data["commit_sha"],
            branch=data["branch"],
            timestamp=datetime.fromisoformat(data["timestamp"]),
            agent=agent,
            transcript=transcript,
            files_changed=files_changed,
            decisions_extracted=data["decisions_extracted"],
            membria_context_injected=data["membria_context_injected"],
            antipatterns_triggered=data["antipatterns_triggered"],
            summary=summary,
        )


class DecisionStorage:
    """Manages decision index in SQLite (before/alongside graph)."""

    def __init__(self, storage_dir: Optional[Path] = None):
        """Initialize decision storage."""
        self.db_path = (storage_dir or (Path.home() / ".membria")) / "cache" / "decisions.db"
        self.db_path.parent.mkdir(parents=True, exist_ok=True)
        self._init_db()

    def _init_db(self) -> None:
        """Initialize decisions database."""
        conn = sqlite3.connect(str(self.db_path))
        cursor = conn.cursor()

        cursor.execute("""
            CREATE TABLE IF NOT EXISTS decisions (
                decision_id TEXT PRIMARY KEY,
                statement TEXT NOT NULL,
                alternatives TEXT,
                confidence REAL,
                outcome TEXT,
                created_at DATETIME,
                resolved_at DATETIME,
                module TEXT,
                engram_id TEXT,
                commit_sha TEXT,
                metadata TEXT
            )
        """)

        cursor.execute("""
            CREATE INDEX IF NOT EXISTS idx_outcome ON decisions(outcome)
        """)

        cursor.execute("""
            CREATE INDEX IF NOT EXISTS idx_module ON decisions(module)
        """)

        conn.commit()
        conn.close()

    def save_decision(self, decision: Decision) -> bool:
        """Save decision to index."""
        try:
            conn = sqlite3.connect(str(self.db_path))
            cursor = conn.cursor()

            cursor.execute("""
                INSERT OR REPLACE INTO decisions
                (decision_id, statement, alternatives, confidence, outcome, created_at,
                 resolved_at, module, engram_id, commit_sha, metadata)
                VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
            """, (
                decision.decision_id,
                decision.statement,
                json.dumps(decision.alternatives),
                decision.confidence,
                decision.outcome,
                decision.created_at.isoformat(),
                decision.resolved_at.isoformat() if decision.resolved_at else None,
                decision.module,
                decision.engram_id,
                decision.commit_sha,
                json.dumps(decision.metadata),
            ))

            conn.commit()
            conn.close()
            return True

        except Exception as e:
            logger.error(f"Failed to save decision: {e}")
            return False

    def get_decisions(self, module: Optional[str] = None, limit: int = 10) -> List[Decision]:
        """Get recent decisions."""
        try:
            conn = sqlite3.connect(str(self.db_path))
            cursor = conn.cursor()

            if module:
                cursor.execute("""
                    SELECT * FROM decisions
                    WHERE module = ?
                    ORDER BY created_at DESC
                    LIMIT ?
                """, (module, limit))
            else:
                cursor.execute("""
                    SELECT * FROM decisions
                    ORDER BY created_at DESC
                    LIMIT ?
                """, (limit,))

            rows = cursor.fetchall()
            conn.close()

            decisions = []
            for row in rows:
                decisions.append(Decision(
                    decision_id=row[0],
                    statement=row[1],
                    alternatives=json.loads(row[2]) if row[2] else [],
                    confidence=row[3],
                    outcome=row[4],
                    created_at=datetime.fromisoformat(row[5]),
                    resolved_at=datetime.fromisoformat(row[6]) if row[6] else None,
                    module=row[7],
                    engram_id=row[8],
                    commit_sha=row[9],
                    metadata=json.loads(row[10]) if row[10] else {},
                ))

            return decisions

        except Exception as e:
            logger.error(f"Failed to get decisions: {e}")
            return []
