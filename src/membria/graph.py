"""FalkorDB graph client for managing reasoning graph."""

import json
import logging
from typing import Optional, Any, List, Dict

from falkordb import FalkorDB, Graph

from membria.config import ConfigManager, FalkorDBConfig
from membria.models import Decision

logger = logging.getLogger(__name__)


class GraphClient:
    """Client for FalkorDB graph operations."""

    def __init__(self, config: Optional[FalkorDBConfig] = None):
        """Initialize graph client from config or default."""
        if config is None:
            config_manager = ConfigManager()
            config = config_manager.get_falkordb_config()

        self.host = config.host
        self.port = config.port
        self.password = config.password
        self.db = config.db
        self.mode = config.mode
        self.db_instance: Optional[FalkorDB] = None
        self.graph: Optional[Graph] = None
        self.connected = False

    def connect(self) -> bool:
        """Connect to FalkorDB instance."""
        try:
            # FalkorDB uses different initialization parameters
            if self.password:
                self.db_instance = FalkorDB(
                    host=self.host,
                    port=self.port,
                    password=self.password
                )
            else:
                self.db_instance = FalkorDB(
                    host=self.host,
                    port=self.port
                )
            self.graph = self.db_instance.select_graph("membria")
            logger.info(f"Connected to FalkorDB at {self.host}:{self.port} (mode: {self.mode})")
            self.connected = True
            return True
        except Exception as e:
            logger.error(f"Failed to connect to FalkorDB: {e}")
            self.connected = False
            return False

    def disconnect(self) -> None:
        """Disconnect from FalkorDB."""
        if self.db_instance:
            self.db_instance.close()
            self.connected = False

    def health_check(self) -> Dict[str, Any]:
        """Check graph health and connectivity."""
        if not self.connected:
            return {
                "status": "disconnected",
                "error": "Not connected",
                "host": self.host,
                "port": self.port,
            }

        try:
            result = self.graph.query("RETURN 1")
            return {
                "status": "healthy",
                "host": self.host,
                "port": self.port,
                "mode": self.mode,
                "connected": True
            }
        except Exception as e:
            return {
                "status": "error",
                "error": str(e),
                "host": self.host,
                "port": self.port,
                "mode": self.mode
            }

    def add_decision(self, decision: Decision) -> bool:
        """Add a decision node to the graph."""
        if not self.connected:
            logger.error("Not connected to graph")
            return False

        try:
            # Escape quotes in statement
            statement = decision.statement.replace("'", "\\'")
            alternatives_json = json.dumps(decision.alternatives).replace("'", "\\'")

            query = f"""
            CREATE (d:Decision {{
                id: '{decision.decision_id}',
                statement: '{statement}',
                alternatives: '{alternatives_json}',
                confidence: {decision.confidence},
                outcome: {'null' if decision.outcome is None else f"'{decision.outcome}'"},
                module: {'null' if decision.module is None else f"'{decision.module}'"},
                created_at: {int(decision.created_at.timestamp())},
                engram_id: {'null' if decision.engram_id is None else f"'{decision.engram_id}'"}
            }})
            RETURN d
            """
            self.graph.query(query)
            logger.info(f"Added decision {decision.decision_id}")
            return True
        except Exception as e:
            logger.error(f"Failed to add decision: {e}")
            return False

    def query(self, cypher: str) -> List[Dict[str, Any]]:
        """Execute a Cypher query."""
        if not self.connected:
            raise RuntimeError("Not connected to graph")

        try:
            result = self.graph.query(cypher)
            # FalkorDB returns results differently than Neo4j
            return result.result_set if hasattr(result, 'result_set') else []
        except Exception as e:
            logger.error(f"Query execution failed: {e}")
            raise

    def get_decisions(self, limit: int = 10, module: Optional[str] = None) -> List[Dict[str, Any]]:
        """Get recent decisions from graph."""
        if not self.connected:
            return []

        try:
            if module:
                query = f"MATCH (d:Decision {{module: '{module}'}}) RETURN d ORDER BY d.created_at DESC LIMIT {limit}"
            else:
                query = f"MATCH (d:Decision) RETURN d ORDER BY d.created_at DESC LIMIT {limit}"

            result = self.graph.query(query)
            return result.result_set if hasattr(result, 'result_set') else []
        except Exception as e:
            logger.error(f"Failed to get decisions: {e}")
            return []

    def get_similar_decisions(self, topic: str, limit: int = 5) -> List[Dict[str, Any]]:
        """Get decisions similar to a topic."""
        if not self.connected:
            return []

        try:
            # Simple text matching - could be enhanced with semantic search
            query = f"""
            MATCH (d:Decision)
            WHERE d.statement CONTAINS '{topic}'
            RETURN d
            ORDER BY d.created_at DESC
            LIMIT {limit}
            """
            result = self.graph.query(query)
            return result.result_set if hasattr(result, 'result_set') else []
        except Exception as e:
            logger.error(f"Failed to get similar decisions: {e}")
            return []
