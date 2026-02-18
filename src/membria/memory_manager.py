"""Memory Manager: store, retrieve, update, forget."""

from dataclasses import dataclass
from datetime import datetime
from typing import Any, Dict, List, Optional

from membria.graph import GraphClient
from membria.models import Decision, NegativeKnowledge
from membria.memory_policy import MemoryPolicy


@dataclass
class MemoryItem:
    """Normalized memory item for retrieval."""
    id: str
    statement: str
    confidence: float
    created_at: int
    outcome: Optional[str] = None
    score: float = 0.0
    memory_type: Optional[str] = None
    memory_subject: Optional[str] = None


class MemoryManager:
    """Centralized memory lifecycle manager."""

    def __init__(self, graph_client: GraphClient, policy: Optional[MemoryPolicy] = None):
        self.graph = graph_client
        self.policy = policy or MemoryPolicy()

    def store_decision(
        self,
        decision: Decision,
        memory_type: str = "episodic",
        memory_subject: str = "agent",
        ttl_days: Optional[int] = None,
        source: Optional[str] = None,
    ) -> bool:
        decision.memory_type = memory_type
        decision.memory_subject = memory_subject
        decision.ttl_days = ttl_days or self.policy.get_ttl(memory_type)
        decision.last_verified_at = datetime.utcnow()
        decision.source = source or decision.created_by
        return self.graph.add_decision(decision)

    def store_negative_knowledge(
        self,
        nk: NegativeKnowledge,
        memory_type: str = "semantic",
        memory_subject: str = "agent",
        ttl_days: Optional[int] = None,
    ) -> bool:
        nk.memory_type = memory_type
        nk.memory_subject = memory_subject
        nk.ttl_days = ttl_days or self.policy.get_ttl(memory_type)
        nk.last_verified_at = datetime.utcnow()
        return self.graph.add_negative_knowledge(nk)

    def retrieve_decisions(
        self,
        domain: str,
        limit: int = 5,
        relevance: float = 1.0,
    ) -> List[MemoryItem]:
        if not self.graph.connected:
            return []

        query = """
        MATCH (d:Decision {module: $domain})
        WHERE d.is_active IS NULL OR d.is_active = true
          AND ($tenant_id IS NULL OR d.tenant_id = $tenant_id)
          AND ($team_id IS NULL OR d.team_id = $team_id)
          AND ($project_id IS NULL OR d.project_id = $project_id)
        RETURN d.id, d.statement, d.confidence, d.created_at, d.outcome,
               d.memory_type, d.memory_subject, d.ttl_days, d.actual_success_rate
        ORDER BY d.created_at DESC
        LIMIT $limit
        """
        rows = self.graph.query(query, {
            "domain": domain,
            "limit": limit,
            "tenant_id": self.graph._namespace.get("tenant_id"),
            "team_id": self.graph._namespace.get("team_id"),
            "project_id": self.graph._namespace.get("project_id"),
        }) or []
        items = []
        for row in rows:
            created_at = int(row[3]) if row[3] else 0
            ttl_days = row[7] if len(row) > 7 else None
            impact = float(row[8]) if len(row) > 8 and row[8] is not None else 0.5
            freshness = self.policy.freshness(created_at, ttl_days)
            score = self.policy.score(relevance, float(row[2] or 0.5), freshness, impact)
            items.append(
                MemoryItem(
                    id=row[0],
                    statement=row[1],
                    confidence=float(row[2] or 0.5),
                    created_at=created_at,
                    outcome=row[4],
                    score=score,
                    memory_type=row[5],
                    memory_subject=row[6],
                )
            )
        items.sort(key=lambda i: i.score, reverse=True)
        return items

    def retrieve_negative_knowledge(
        self,
        domain: Optional[str] = None,
        limit: int = 5,
    ) -> List[Dict[str, Any]]:
        if not self.graph.connected:
            return []

        if domain:
            query = """
            MATCH (nk:NegativeKnowledge {domain: $domain})
            WHERE (nk.is_active IS NULL OR nk.is_active = true)
              AND ($tenant_id IS NULL OR nk.tenant_id = $tenant_id)
              AND ($team_id IS NULL OR nk.team_id = $team_id)
              AND ($project_id IS NULL OR nk.project_id = $project_id)
            RETURN nk.id, nk.hypothesis, nk.conclusion, nk.severity, nk.recommendation, nk.discovered_at, nk.ttl_days
            ORDER BY nk.severity DESC, nk.discovered_at DESC
            LIMIT $limit
            """
            params = {
                "domain": domain,
                "limit": limit,
                "tenant_id": self.graph._namespace.get("tenant_id"),
                "team_id": self.graph._namespace.get("team_id"),
                "project_id": self.graph._namespace.get("project_id"),
            }
        else:
            query = """
            MATCH (nk:NegativeKnowledge)
            WHERE (nk.is_active IS NULL OR nk.is_active = true)
              AND ($tenant_id IS NULL OR nk.tenant_id = $tenant_id)
              AND ($team_id IS NULL OR nk.team_id = $team_id)
              AND ($project_id IS NULL OR nk.project_id = $project_id)
            RETURN nk.id, nk.hypothesis, nk.conclusion, nk.severity, nk.recommendation, nk.discovered_at, nk.ttl_days
            ORDER BY nk.severity DESC, nk.discovered_at DESC
            LIMIT $limit
            """
            params = {
                "limit": limit,
                "tenant_id": self.graph._namespace.get("tenant_id"),
                "team_id": self.graph._namespace.get("team_id"),
                "project_id": self.graph._namespace.get("project_id"),
            }

        rows = self.graph.query(query, params) or []
        alerts = []
        for row in rows:
            alerts.append({
                "id": row[0],
                "hypothesis": row[1],
                "conclusion": row[2],
                "severity": row[3],
                "recommendation": row[4],
                "discovered_at": row[5],
                "ttl_days": row[6],
            })
        return alerts

    def update_decision(self, decision_id: str, updates: Dict[str, Any]) -> bool:
        if "last_verified_at" not in updates:
            updates["last_verified_at"] = int(datetime.utcnow().timestamp())
        return self.graph.update_decision_memory(decision_id, updates)

    def update_negative_knowledge(self, nk_id: str, updates: Dict[str, Any]) -> bool:
        if "last_verified_at" not in updates:
            updates["last_verified_at"] = int(datetime.utcnow().timestamp())
        return self.graph.update_negative_knowledge_memory(nk_id, updates)

    def forget_decision(self, decision_id: str, reason: str) -> bool:
        return self.graph.update_decision_memory(
            decision_id,
            {"is_active": False, "deprecated_reason": reason, "last_verified_at": int(datetime.utcnow().timestamp())},
        )

    def forget_negative_knowledge(self, nk_id: str, reason: str) -> bool:
        return self.graph.update_negative_knowledge_memory(
            nk_id,
            {"is_active": False, "deprecated_reason": reason, "last_verified_at": int(datetime.utcnow().timestamp())},
        )
