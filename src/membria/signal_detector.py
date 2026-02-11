"""Signal Detector for Level 2 - Rule-based decision detection."""

import re
import sqlite3
import json
from pathlib import Path
from datetime import datetime
from typing import List, Dict, Optional, Tuple
import logging

logger = logging.getLogger(__name__)


class SignalDetector:
    """Detects decision signals from text without LLM."""

    # Decision signal patterns
    DECISION_SIGNALS = {
        "high": [
            r"i\s+recommend\s+(using|going\s+with|choosing)",
            r"(better|best)\s+(choice|option|approach)\s+(is|would\s+be)",
            r"(chose|selected|picked|went\s+with)\s+\w+\s+(over|instead\s+of|rather\s+than)",
            r"let['\s]s\s+(go\s+with|use|implement|choose)",
            r"should\s+(use|implement|switch\s+to)",
            r"we\s+(will|should)\s+(use|go\s+with|implement)",
        ],
        "medium": [
            r"(comparing|comparison\s+of|versus|vs\.?)",
            r"(pros\s+and\s+cons|trade.?offs?|advantages|disadvantages)",
            r"(alternatives?|options?)\s+(include|are|would\s+be)",
            r"why\s+\w+\s+(over|instead\s+of)",
        ],
    }

    # Module detectors
    MODULE_PATTERNS = {
        "auth": r"(auth|login|jwt|oauth|session|password|token|credential)",
        "db": r"(database|postgres|mongo|redis|sql|orm|migration|schema)",
        "api": r"(rest|graphql|grpc|endpoint|route|middleware|http|api)",
        "infra": r"(docker|kubernetes|deploy|ci.?cd|terraform|container|cloud)",
        "frontend": r"(react|vue|angular|component|jsx|typescript|css)",
        "backend": r"(fastapi|django|flask|node|python|ruby|java)",
    }

    def __init__(self, config_dir: Optional[Path] = None):
        """Initialize Signal Detector."""
        self.config_dir = config_dir or (Path.home() / ".membria")
        self.signals_db = self.config_dir / "signals.db"
        self._init_db()

    def _init_db(self) -> None:
        """Initialize SQLite database for signals."""
        conn = sqlite3.connect(str(self.signals_db))
        cursor = conn.cursor()

        cursor.execute("""
            CREATE TABLE IF NOT EXISTS signals (
                id TEXT PRIMARY KEY,
                timestamp DATETIME DEFAULT CURRENT_TIMESTAMP,
                signal_type TEXT NOT NULL,
                confidence REAL NOT NULL,
                module TEXT,
                raw_text TEXT NOT NULL,
                status TEXT DEFAULT 'pending',
                extracted_decision_id TEXT,
                created_at DATETIME DEFAULT CURRENT_TIMESTAMP
            )
        """)

        cursor.execute("""
            CREATE INDEX IF NOT EXISTS idx_status ON signals(status)
        """)

        cursor.execute("""
            CREATE INDEX IF NOT EXISTS idx_timestamp ON signals(timestamp DESC)
        """)

        conn.commit()
        conn.close()

    def detect(self, text: str) -> List[Dict]:
        """
        Detect decision signals in text.

        Returns:
            List of detected signals with type, confidence, module
        """
        signals = []

        # Check high-confidence patterns
        high_matches = self._match_patterns(text, self.DECISION_SIGNALS["high"])
        if high_matches:
            signals.append({
                "signal_type": "high",
                "confidence": 0.85,
                "text": text,
                "matches": high_matches,
            })

        # Check medium-confidence patterns
        medium_matches = self._match_patterns(text, self.DECISION_SIGNALS["medium"])
        if len(medium_matches) >= 2:  # Need 2+ medium matches
            signals.append({
                "signal_type": "medium",
                "confidence": 0.65,
                "text": text,
                "matches": medium_matches,
            })

        # Detect module for each signal
        for signal in signals:
            signal["module"] = self._detect_module(text)

        return signals

    def detect_from_session(self, prompt: str, response: str) -> List[Dict]:
        """
        Detect signals from a full Claude Code session (prompt + response).

        Returns:
            List of signals from both prompt and response
        """
        signals = []

        # Check response (usually where decisions are explained)
        response_signals = self.detect(response)
        signals.extend(response_signals)

        # Also check prompt for explicit keywords
        prompt_signals = self.detect(prompt)
        for sig in prompt_signals:
            if sig["signal_type"] == "high":  # Only high-confidence from prompts
                signals.append(sig)

        return signals

    def save_signal(self, signal: Dict) -> str:
        """Save detected signal to database."""
        signal_id = f"sig_{datetime.now().strftime('%Y%m%d%H%M%S')}_{hash(signal['text']) % 100000:05d}"

        try:
            conn = sqlite3.connect(str(self.signals_db))
            cursor = conn.cursor()

            cursor.execute("""
                INSERT INTO signals (id, signal_type, confidence, module, raw_text, status)
                VALUES (?, ?, ?, ?, ?, ?)
            """, (
                signal_id,
                signal.get("signal_type", "unknown"),
                signal.get("confidence", 0.5),
                signal.get("module", "general"),
                signal.get("text", ""),
                "pending",
            ))

            conn.commit()
            conn.close()

            logger.info(f"Signal saved: {signal_id}")
            return signal_id

        except Exception as e:
            logger.error(f"Failed to save signal: {e}")
            return ""

    def get_pending_signals(self) -> List[Dict]:
        """Get all pending signals awaiting extraction."""
        try:
            conn = sqlite3.connect(str(self.signals_db))
            cursor = conn.cursor()

            cursor.execute("""
                SELECT id, timestamp, signal_type, confidence, module, raw_text, status
                FROM signals
                WHERE status = 'pending'
                ORDER BY timestamp DESC
            """)

            rows = cursor.fetchall()
            conn.close()

            return [
                {
                    "id": row[0],
                    "timestamp": row[1],
                    "signal_type": row[2],
                    "confidence": row[3],
                    "module": row[4],
                    "text": row[5],
                    "status": row[6],
                }
                for row in rows
            ]

        except Exception as e:
            logger.error(f"Failed to get pending signals: {e}")
            return []

    def get_signal_history(self, limit: int = 50) -> List[Dict]:
        """Get signal detection history."""
        try:
            conn = sqlite3.connect(str(self.signals_db))
            cursor = conn.cursor()

            cursor.execute("""
                SELECT id, timestamp, signal_type, confidence, module, status
                FROM signals
                ORDER BY timestamp DESC
                LIMIT ?
            """, (limit,))

            rows = cursor.fetchall()
            conn.close()

            return [
                {
                    "id": row[0],
                    "timestamp": row[1],
                    "signal_type": row[2],
                    "confidence": row[3],
                    "module": row[4],
                    "status": row[5],
                }
                for row in rows
            ]

        except Exception as e:
            logger.error(f"Failed to get signal history: {e}")
            return []

    def mark_extracted(self, signal_id: str, decision_id: str) -> bool:
        """Mark signal as extracted."""
        try:
            conn = sqlite3.connect(str(self.signals_db))
            cursor = conn.cursor()

            cursor.execute("""
                UPDATE signals
                SET status = 'extracted', extracted_decision_id = ?
                WHERE id = ?
            """, (decision_id, signal_id))

            conn.commit()
            conn.close()
            return True

        except Exception as e:
            logger.error(f"Failed to mark signal as extracted: {e}")
            return False

    def _match_patterns(self, text: str, patterns: List[str]) -> List[str]:
        """Match text against patterns."""
        text_lower = text.lower()
        matches = []

        for pattern in patterns:
            if re.search(pattern, text_lower, re.IGNORECASE):
                matches.append(pattern)

        return matches

    def _detect_module(self, text: str) -> str:
        """Detect which module/domain the decision belongs to."""
        text_lower = text.lower()
        scores = {}

        for module, pattern in self.MODULE_PATTERNS.items():
            if re.search(pattern, text_lower, re.IGNORECASE):
                scores[module] = len(re.findall(pattern, text_lower, re.IGNORECASE))

        if scores:
            return max(scores, key=scores.get)
        return "general"
