"""Haiku-based structured extraction for Level 3 - batched decision extraction."""

import json
import logging
from pathlib import Path
from typing import List, Dict, Optional
from datetime import datetime
import sqlite3

try:
    from anthropic import Anthropic
except ImportError:
    Anthropic = None

logger = logging.getLogger(__name__)


EXTRACTION_PROMPT = """You are a decision extraction assistant. Analyze the following text from a software architecture discussion and extract any technical or architectural decision made.

Text to analyze:
{text}

Extract the decision in this exact JSON format (return ONLY valid JSON, no other text):
{{
  "decision_statement": "The chosen approach or recommendation (e.g., 'Use JWT for authentication')",
  "alternatives": ["Alternative 1", "Alternative 2", "Alternative 3"],
  "confidence": 0.85,
  "reasoning": "Why this choice was recommended",
  "module": "Category: auth, db, api, infra, frontend, backend, or general"
}}

If no clear decision is present, return:
{{"decision_statement": null}}
"""


class HaikuExtractor:
    """Extract structured decisions from signals using Claude Haiku."""

    def __init__(self, config_dir: Optional[Path] = None):
        """Initialize Haiku extractor."""
        self.config_dir = config_dir or (Path.home() / ".membria")
        self.extraction_db = self.config_dir / "extractions.db"
        self._init_db()

        # Initialize Anthropic client if available
        self.client = None
        if Anthropic:
            try:
                self.client = Anthropic()
            except Exception as e:
                logger.warning(f"Could not initialize Anthropic client: {e}")

    def _init_db(self) -> None:
        """Initialize SQLite database for extractions."""
        conn = sqlite3.connect(str(self.extraction_db))
        cursor = conn.cursor()

        cursor.execute("""
            CREATE TABLE IF NOT EXISTS extractions (
                id TEXT PRIMARY KEY,
                signal_id TEXT NOT NULL,
                decision_statement TEXT,
                alternatives TEXT,
                confidence REAL,
                reasoning TEXT,
                module TEXT,
                extraction_timestamp DATETIME DEFAULT CURRENT_TIMESTAMP,
                decision_id TEXT
            )
        """)

        cursor.execute("""
            CREATE INDEX IF NOT EXISTS idx_signal_id ON extractions(signal_id)
        """)

        conn.commit()
        conn.close()

    def extract_single(self, signal: Dict) -> Optional[Dict]:
        """
        Extract a single signal using Haiku.

        Args:
            signal: Signal dict with 'id', 'text', 'module'

        Returns:
            Extracted decision dict or None if extraction failed
        """
        if not self.client:
            logger.warning("Anthropic client not available")
            return None

        try:
            prompt = EXTRACTION_PROMPT.format(text=signal.get("text", ""))

            message = self.client.messages.create(
                model="claude-3-5-haiku-20241022",
                max_tokens=500,
                messages=[
                    {"role": "user", "content": prompt}
                ],
            )

            # Parse response
            response_text = message.content[0].text
            extracted = json.loads(response_text)

            # Check if decision was found
            if not extracted.get("decision_statement"):
                return None

            # Add signal reference
            extracted["signal_id"] = signal.get("id")
            extracted["module"] = extracted.get("module", signal.get("module", "general"))

            return extracted

        except json.JSONDecodeError as e:
            logger.error(f"Failed to parse Haiku response: {e}")
            return None
        except Exception as e:
            logger.error(f"Haiku extraction failed: {e}")
            return None

    def batch_extract(self, signals: List[Dict]) -> List[Dict]:
        """
        Extract multiple signals in a single batch.

        Optimizations:
        - Deduplication: skip similar signals
        - Caching: reuse previous extractions
        - Batching: one API call for efficiency (via multiple calls grouped)

        Args:
            signals: List of signal dicts

        Returns:
            List of extracted decisions
        """
        if not self.client:
            logger.warning("Anthropic client not available")
            return []

        # Deduplication: group similar signals
        deduplicated = self._deduplicate_signals(signals)
        logger.info(f"Deduplicating {len(signals)} → {len(deduplicated)} signals")

        # Cache check: skip already extracted
        to_extract = []
        for sig in deduplicated:
            if not self._is_cached(sig["id"]):
                to_extract.append(sig)

        logger.info(f"Skipping {len(deduplicated) - len(to_extract)} cached signals")

        # Extract
        results = []
        for sig in to_extract:
            extracted = self.extract_single(sig)
            if extracted:
                results.append(extracted)
                self._save_extraction(sig["id"], extracted)

        return results

    def save_decision(self, extraction: Dict, decision_id: str) -> bool:
        """Link extraction to decision in graph."""
        try:
            conn = sqlite3.connect(str(self.extraction_db))
            cursor = conn.cursor()

            cursor.execute("""
                UPDATE extractions
                SET decision_id = ?
                WHERE signal_id = ?
            """, (decision_id, extraction.get("signal_id")))

            conn.commit()
            conn.close()
            return True

        except Exception as e:
            logger.error(f"Failed to save decision link: {e}")
            return False

    def _deduplicate_signals(self, signals: List[Dict]) -> List[Dict]:
        """Remove duplicate/similar signals."""
        seen_texts = set()
        unique = []

        for sig in signals:
            # Simple dedup: normalize and check if text is similar
            normalized = sig.get("text", "").lower()[:100]

            if normalized not in seen_texts:
                seen_texts.add(normalized)
                unique.append(sig)

        return unique

    def _is_cached(self, signal_id: str) -> bool:
        """Check if signal was already extracted."""
        try:
            conn = sqlite3.connect(str(self.extraction_db))
            cursor = conn.cursor()

            cursor.execute("SELECT 1 FROM extractions WHERE signal_id = ?", (signal_id,))
            result = cursor.fetchone()
            conn.close()

            return result is not None

        except Exception:
            return False

    def _save_extraction(self, signal_id: str, extraction: Dict) -> bool:
        """Save extraction result to database."""
        try:
            extraction_id = f"ext_{datetime.now().strftime('%Y%m%d%H%M%S')}_{hash(signal_id) % 10000:04d}"

            conn = sqlite3.connect(str(self.extraction_db))
            cursor = conn.cursor()

            cursor.execute("""
                INSERT INTO extractions
                (id, signal_id, decision_statement, alternatives, confidence, reasoning, module)
                VALUES (?, ?, ?, ?, ?, ?, ?)
            """, (
                extraction_id,
                signal_id,
                extraction.get("decision_statement"),
                json.dumps(extraction.get("alternatives", [])),
                extraction.get("confidence", 0.5),
                extraction.get("reasoning", ""),
                extraction.get("module", "general"),
            ))

            conn.commit()
            conn.close()
            return True

        except Exception as e:
            logger.error(f"Failed to save extraction: {e}")
            return False

    def get_pending_extractions(self) -> List[Dict]:
        """Get extractions without linked decisions."""
        try:
            conn = sqlite3.connect(str(self.extraction_db))
            cursor = conn.cursor()

            cursor.execute("""
                SELECT id, signal_id, decision_statement, module
                FROM extractions
                WHERE decision_id IS NULL
                ORDER BY extraction_timestamp DESC
                LIMIT 50
            """)

            rows = cursor.fetchall()
            conn.close()

            return [
                {
                    "id": row[0],
                    "signal_id": row[1],
                    "decision_statement": row[2],
                    "module": row[3],
                }
                for row in rows
            ]

        except Exception as e:
            logger.error(f"Failed to get pending extractions: {e}")
            return []
