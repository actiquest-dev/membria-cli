"""Main daemon component orchestrating all Membria services."""

import asyncio
import logging
from pathlib import Path
from typing import Optional
import json

from membria.config import ConfigManager
from membria.graph import GraphClient
from membria.storage import EngramStorage, DecisionStorage
from membria.models import Engram, Decision

logger = logging.getLogger(__name__)


class MembriaDaemon:
    """Main daemon that orchestrates MCP server, graph, cache, and engrams."""

    def __init__(self):
        """Initialize daemon."""
        self.config = ConfigManager()
        self.graph_client: Optional[GraphClient] = None
        self.engram_storage = EngramStorage()
        self.decision_storage = DecisionStorage()
        self.running = False

    def initialize(self) -> bool:
        """Initialize all daemon components."""
        try:
            logger.info("Initializing Membria daemon...")

            # Create graph client
            self.graph_client = GraphClient(self.config.get_falkordb_config())

            # Connect to graph
            if not self.graph_client.connect():
                logger.warning("Graph connection failed, operating in offline mode")

            logger.info("Daemon initialized successfully")
            return True

        except Exception as e:
            logger.error(f"Failed to initialize daemon: {e}")
            return False

    def start(self) -> None:
        """Start daemon services."""
        try:
            if not self.initialize():
                logger.error("Failed to initialize daemon")
                return

            self.running = True
            logger.info("Membria daemon started")

            # TODO: Start MCP server
            # TODO: Start sync service for offline mode
            # TODO: Start engram monitor

        except Exception as e:
            logger.error(f"Failed to start daemon: {e}")
            self.running = False

    def stop(self) -> None:
        """Stop daemon services."""
        try:
            if self.graph_client:
                self.graph_client.disconnect()

            self.running = False
            logger.info("Membria daemon stopped")

        except Exception as e:
            logger.error(f"Failed to stop daemon: {e}")

    def health_check(self) -> dict:
        """Check health of all components."""
        status = {
            "daemon_running": self.running,
            "graph": self.graph_client.health_check() if self.graph_client else {"status": "not initialized"},
        }
        return status

    def record_decision(self, decision: Decision) -> bool:
        """Record a decision to graph and storage."""
        try:
            # Save to local storage first
            if self.decision_storage.save_decision(decision):
                logger.info(f"Saved decision {decision.decision_id}")

            # Try to push to graph if connected
            if self.graph_client and self.graph_client.connected:
                if self.graph_client.add_decision(decision):
                    logger.info(f"Added decision to graph {decision.decision_id}")
                    return True
            else:
                # Store for later sync
                logger.info(f"Decision queued for later graph sync")
                return True

            return False

        except Exception as e:
            logger.error(f"Failed to record decision: {e}")
            return False

    def save_engram(self, engram: Engram) -> bool:
        """Save an engram (session checkpoint)."""
        try:
            if self.engram_storage.save_engram(engram):
                logger.info(f"Saved engram {engram.engram_id}")
                return True
            return False
        except Exception as e:
            logger.error(f"Failed to save engram: {e}")
            return False

    def get_context_for_request(self, topic: str) -> dict:
        """Get context for a development request (MCP tool)."""
        context = {
            "task_type": "decision",
            "context": {
                "similar_decisions": [],
                "negative_knowledge": [],
                "calibration": {},
                "antipatterns": []
            },
            "interventions": []
        }

        if self.graph_client and self.graph_client.connected:
            try:
                # Get similar decisions
                context["context"]["similar_decisions"] = self.graph_client.get_similar_decisions(topic)

                # TODO: Get negative knowledge
                # TODO: Get calibration data
                # TODO: Get antipatterns

            except Exception as e:
                logger.error(f"Failed to fetch context: {e}")

        return context

    def sync_pending_data(self) -> dict:
        """Sync offline mode queue with cloud (if available)."""
        # TODO: Implement sync logic
        return {
            "decisions_synced": 0,
            "engrams_synced": 0,
            "status": "pending implementation"
        }
