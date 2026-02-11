"""MCP (Model Context Protocol) server for Claude Code integration."""

import json
import logging
from typing import Any, Dict

from membria.daemon import MembriaDaemon
from membria.session_capturer import get_capturer

logger = logging.getLogger(__name__)


class MembriaMCPServer:
    """MCP server that provides tools and context injection to Claude Code."""

    def __init__(self):
        """Initialize MCP server."""
        self.daemon = MembriaDaemon()
        self.capturer = get_capturer()  # Auto-capture decisions
        self.running = False

    def start(self) -> bool:
        """Start MCP server."""
        try:
            self.daemon.start()
            self.running = True
            logger.info("MCP server started")
            return True
        except Exception as e:
            logger.error(f"Failed to start MCP server: {e}")
            return False

    def stop(self) -> None:
        """Stop MCP server."""
        try:
            self.daemon.stop()
            self.running = False
            logger.info("MCP server stopped")
        except Exception as e:
            logger.error(f"Failed to stop MCP server: {e}")

    # MCP Tool implementations
    def membria_get_context(self, request: str) -> Dict[str, Any]:
        """
        Tool: Get decision context for a request.
        Called by Claude Code before generating code.
        """
        try:
            context = self.daemon.get_context_for_request(request)
            logger.info(f"Context fetched for request: {request[:50]}...")
            return context
        except Exception as e:
            logger.error(f"Failed to get context: {e}")
            return {"error": str(e)}

    def membria_record_decision(self, statement: str, alternatives: list,
                                confidence: float, module: str = None) -> Dict[str, Any]:
        """
        Tool: Record a decision in reasoning graph.
        Called when Claude Code makes a significant decision.
        """
        try:
            from membria.models import Decision
            import uuid

            decision = Decision(
                decision_id=f"dec_{uuid.uuid4().hex[:12]}",
                statement=statement,
                alternatives=alternatives,
                confidence=confidence,
                module=module
            )

            if self.daemon.record_decision(decision):
                logger.info(f"Decision recorded: {decision.decision_id}")
                return {
                    "status": "success",
                    "decision_id": decision.decision_id,
                    "statement": statement
                }
            else:
                return {"status": "error", "message": "Failed to record decision"}

        except Exception as e:
            logger.error(f"Failed to record decision: {e}")
            return {"error": str(e)}

    def membria_check_patterns(self, code: str, language: str = None) -> Dict[str, Any]:
        """
        Tool: Check code for antipatterns.
        Called during post-generation validation.
        """
        try:
            # TODO: Implement antipattern detection
            antipatterns = []
            logger.info(f"Checked code for patterns: {len(antipatterns)} found")
            return {
                "antipatterns": antipatterns,
                "recommendations": []
            }
        except Exception as e:
            logger.error(f"Failed to check patterns: {e}")
            return {"error": str(e)}

    def membria_link_outcome(self, decision_id: str, outcome: str,
                             pr_url: str = None, incident_id: str = None) -> Dict[str, Any]:
        """
        Tool: Link an outcome to a decision.
        Called when PR merges, CI fails, etc.
        """
        try:
            # TODO: Update decision outcome in graph
            logger.info(f"Outcome linked: {decision_id} -> {outcome}")
            return {
                "status": "success",
                "decision_id": decision_id,
                "outcome": outcome
            }
        except Exception as e:
            logger.error(f"Failed to link outcome: {e}")
            return {"error": str(e)}

    def membria_get_negative_knowledge(self, topic: str) -> Dict[str, Any]:
        """
        Tool: Get negative knowledge (known failures) for a topic.
        Called during pre-generation context fetch.
        """
        try:
            # TODO: Query graph for negative knowledge
            knowledge = []
            logger.info(f"Fetched negative knowledge for topic: {topic}")
            return {
                "topic": topic,
                "negative_knowledge": knowledge
            }
        except Exception as e:
            logger.error(f"Failed to get negative knowledge: {e}")
            return {"error": str(e)}

    def membria_get_calibration(self, domain: str) -> Dict[str, Any]:
        """
        Tool: Get calibration hint for a domain.
        Tells Claude if team tends to be overconfident in this domain.
        """
        try:
            # TODO: Calculate calibration metrics from decisions
            calibration = {
                "domain": domain,
                "overconfidence_gap": 0.0,  # 0 = well-calibrated, positive = overconfident
                "accuracy_rate": 1.0,
                "sample_size": 0
            }
            logger.info(f"Calibration fetched for domain: {domain}")
            return calibration
        except Exception as e:
            logger.error(f"Failed to get calibration: {e}")
            return {"error": str(e)}

    def capture_session(self, prompt: str, response: str) -> Dict[str, Any]:
        """
        Capture a Claude Code session for auto-decision detection.

        Called after Claude generates code. Runs Signal Detector (Level 2)
        to find decision signals without LLM cost.
        """
        result = self.capturer.capture_session(prompt, response)
        if result["signals_detected"] > 0:
            logger.info(f"Auto-captured {result['signals_detected']} decision signal(s)")
        return result

    def handle_tool_call(self, tool_name: str, params: Dict[str, Any]) -> Dict[str, Any]:
        """Universal tool call handler for MCP protocol."""
        handlers = {
            "membria_get_context": lambda p: self.membria_get_context(p.get("request", "")),
            "membria_record_decision": self._handle_record_decision,
            "membria_check_patterns": lambda p: self.membria_check_patterns(
                p.get("code", ""), p.get("language")
            ),
            "membria_link_outcome": self._handle_link_outcome,
            "membria_get_negative_knowledge": lambda p: self.membria_get_negative_knowledge(p.get("topic", "")),
            "membria_get_calibration": lambda p: self.membria_get_calibration(p.get("domain", "")),
        }

        handler = handlers.get(tool_name)
        if handler:
            return handler(params)
        else:
            return {"error": f"Unknown tool: {tool_name}"}

    def _handle_record_decision(self, params: Dict[str, Any]) -> Dict[str, Any]:
        """Handle record_decision parameters."""
        return self.membria_record_decision(
            params.get("statement", ""),
            params.get("alternatives", []),
            params.get("confidence", 0.5),
            params.get("module")
        )

    def _handle_link_outcome(self, params: Dict[str, Any]) -> Dict[str, Any]:
        """Handle link_outcome parameters."""
        return self.membria_link_outcome(
            params.get("decision_id", ""),
            params.get("outcome", ""),
            params.get("pr_url"),
            params.get("incident_id")
        )

    def get_tools_manifest(self) -> list:
        """Return MCP tool definitions for Claude Code."""
        return [
            {
                "name": "membria_get_context",
                "description": "Get decision context and historical patterns for a development request",
                "inputSchema": {
                    "type": "object",
                    "properties": {
                        "request": {"type": "string", "description": "The development request or task"}
                    },
                    "required": ["request"]
                }
            },
            {
                "name": "membria_record_decision",
                "description": "Record a significant decision to the reasoning graph",
                "inputSchema": {
                    "type": "object",
                    "properties": {
                        "statement": {"type": "string", "description": "The decision statement"},
                        "alternatives": {"type": "array", "items": {"type": "string"}, "description": "Alternative options considered"},
                        "confidence": {"type": "number", "description": "Confidence level 0-1"},
                        "module": {"type": "string", "description": "Code module/domain"}
                    },
                    "required": ["statement", "alternatives", "confidence"]
                }
            },
            {
                "name": "membria_get_negative_knowledge",
                "description": "Get known failures and constraints for a topic",
                "inputSchema": {
                    "type": "object",
                    "properties": {
                        "topic": {"type": "string", "description": "The topic to query"}
                    },
                    "required": ["topic"]
                }
            },
            {
                "name": "membria_check_patterns",
                "description": "Check code for known antipatterns",
                "inputSchema": {
                    "type": "object",
                    "properties": {
                        "code": {"type": "string", "description": "Code to check"},
                        "language": {"type": "string", "description": "Programming language"}
                    },
                    "required": ["code"]
                }
            },
            {
                "name": "membria_get_calibration",
                "description": "Get team calibration metrics for a domain",
                "inputSchema": {
                    "type": "object",
                    "properties": {
                        "domain": {"type": "string", "description": "Domain (e.g., 'auth', 'api', 'database')"}
                    },
                    "required": ["domain"]
                }
            },
            {
                "name": "membria_link_outcome",
                "description": "Link an outcome (success/failure) to a decision",
                "inputSchema": {
                    "type": "object",
                    "properties": {
                        "decision_id": {"type": "string", "description": "Decision ID"},
                        "outcome": {"type": "string", "enum": ["success", "failure", "pending"]},
                        "pr_url": {"type": "string", "description": "PR URL if applicable"},
                        "incident_id": {"type": "string", "description": "Incident ID if applicable"}
                    },
                    "required": ["decision_id", "outcome"]
                }
            }
        ]
