"""Auto-capture decisions from Claude Code sessions via MCP."""

import logging
from typing import Optional, Dict, Any
from datetime import datetime

from membria.signal_detector import SignalDetector
from membria.haiku_extractor import HaikuExtractor

logger = logging.getLogger(__name__)


class SessionCapturer:
    """Captures and auto-processes decisions from Claude Code sessions."""

    def __init__(self):
        """Initialize session capturer."""
        self.signal_detector = SignalDetector()
        self.haiku_extractor = HaikuExtractor()
        self.session_count = 0

    def capture_session(
        self,
        prompt: str,
        response: str,
        context: Optional[Dict[str, Any]] = None,
    ) -> Dict[str, Any]:
        """
        Capture a Claude Code session (prompt + response).

        This is called automatically when Claude Code generates code.

        Args:
            prompt: User's request/prompt
            response: Claude's response
            context: Optional context (file, module, branch, etc)

        Returns:
            Capture result with signals detected
        """
        self.session_count += 1
        result = {
            "session_id": self.session_count,
            "timestamp": datetime.now().isoformat(),
            "signals_detected": 0,
            "signals": [],
        }

        try:
            # Level 2: Detect signals (zero cost)
            signals = self.signal_detector.detect_from_session(prompt, response)

            if not signals:
                logger.debug(f"No signals detected in session #{self.session_count}")
                return result

            # Save signals to pending queue
            for signal in signals:
                try:
                    signal_id = self.signal_detector.save_signal(signal)
                    result["signals"].append({
                        "id": signal_id,
                        "type": signal["signal_type"],
                        "confidence": signal["confidence"],
                        "module": signal["module"],
                    })
                    logger.info(f"Signal detected: {signal_id} (module: {signal['module']})")
                except Exception as e:
                    logger.error(f"Failed to save signal: {e}")

            result["signals_detected"] = len(result["signals"])

            # Optional: Level 3 auto-extraction if enabled (can be expensive)
            # This would be controlled by a config flag "auto_extract_level3"
            # For now, we just queue signals for manual processing via `membria extractor run --level3`

            logger.info(
                f"Session #{self.session_count}: captured {result['signals_detected']} signal(s)"
            )

        except Exception as e:
            logger.error(f"Failed to capture session: {e}")
            result["error"] = str(e)

        return result

    def get_pending_signals_count(self) -> int:
        """Get number of pending signals awaiting extraction."""
        pending = self.signal_detector.get_pending_signals()
        return len(pending)

    def process_pending(self, level3: bool = False) -> Dict[str, Any]:
        """
        Process pending signals (can be called on-demand or scheduled).

        Args:
            level3: If True, use Haiku for structured extraction

        Returns:
            Processing result
        """
        pending = self.signal_detector.get_pending_signals()

        result = {
            "total_pending": len(pending),
            "processed": 0,
            "extracted": 0,
            "errors": 0,
        }

        if not pending:
            return result

        if level3:
            # Use Haiku for structured extraction
            try:
                extracted_list = self.haiku_extractor.batch_extract(pending)
                result["extracted"] = len(extracted_list)
                result["processed"] = len(pending)
                logger.info(f"Extracted {len(extracted_list)} decisions from {len(pending)} signals")
            except Exception as e:
                logger.error(f"Level 3 extraction failed: {e}")
                result["errors"] = len(pending)
        else:
            # Just mark as processed (Level 2 only)
            for sig in pending:
                try:
                    self.signal_detector.mark_extracted(sig["id"], f"dec_{sig['id'][:16]}")
                    result["processed"] += 1
                except Exception as e:
                    logger.error(f"Failed to mark signal as processed: {e}")
                    result["errors"] += 1

        return result


# Global session capturer instance
_capturer: Optional[SessionCapturer] = None


def get_capturer() -> SessionCapturer:
    """Get or create global session capturer."""
    global _capturer
    if _capturer is None:
        _capturer = SessionCapturer()
    return _capturer


def capture_mcp_session(prompt: str, response: str) -> Dict[str, Any]:
    """
    Capture a session from MCP (public API).

    Called by mcp_server when Claude Code interaction completes.
    """
    capturer = get_capturer()
    return capturer.capture_session(prompt, response)
