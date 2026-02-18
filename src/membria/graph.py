"""FalkorDB graph client for managing reasoning graph."""

import json
import logging
from typing import Optional, Any, List, Dict, Iterable

from falkordb import FalkorDB, Graph

from membria.config import ConfigManager, FalkorDBConfig
from membria.models import (
    Decision,
    CodeChange,
    Outcome,
    NegativeKnowledge,
    Antipattern,
    Engram,
)
from membria.security import sanitize_text, sanitize_list

logger = logging.getLogger(__name__)


def escape_string(s: str) -> str:
    """Safely escape string for Cypher queries."""
    return s.replace("\\", "\\\\").replace('"', '\\"')


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
        cfg = ConfigManager().config
        self._namespace = {
            "tenant_id": getattr(cfg, "tenant_id", "default"),
            "team_id": getattr(cfg, "team_id", "default"),
            "project_id": getattr(cfg, "project_id", "default"),
        }

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
        self.db_instance = None
        self.graph = None
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
            # Safely escape strings
            statement = escape_string(sanitize_text(decision.statement, max_len=400))
            created_by = escape_string(sanitize_text(decision.created_by, max_len=80))
            alternatives = sanitize_list(decision.alternatives, max_len=200)
            role_id = escape_string(sanitize_text(decision.role_id or "", max_len=80)) if decision.role_id else None
            assignment_id = escape_string(sanitize_text(decision.assignment_id or "", max_len=80)) if decision.assignment_id else None

            query = """
            CREATE (d:Decision {
                id: $id,
                statement: $statement,
                alternatives: $alternatives,
                confidence: $confidence,
                module: $module,
                created_at: $created_at,
                created_by: $created_by,
                role_id: $role_id,
                assignment_id: $assignment_id,
                tenant_id: $tenant_id,
                team_id: $team_id,
                project_id: $project_id,
                outcome: $outcome,
                resolved_at: $resolved_at,
                actual_success_rate: $actual_success_rate,
                engram_id: $engram_id,
                commit_sha: $commit_sha,
                memory_type: $memory_type,
                memory_subject: $memory_subject,
                ttl_days: $ttl_days,
                last_verified_at: $last_verified_at,
                is_active: $is_active,
                deprecated_reason: $deprecated_reason,
                source: $source
            })
            RETURN d
            """
            params = {
                "id": decision.decision_id,
                "statement": statement,
                "alternatives": json.dumps(alternatives),
                "confidence": decision.confidence,
                "module": escape_string(sanitize_text(decision.module, max_len=80)),
                "created_at": int(decision.created_at.timestamp()),
                "created_by": created_by,
                "role_id": role_id,
                "assignment_id": assignment_id,
                "tenant_id": self._namespace['tenant_id'],
                "team_id": self._namespace['team_id'],
                "project_id": self._namespace['project_id'],
                "outcome": escape_string(decision.outcome) if decision.outcome is not None else None,
                "resolved_at": int(decision.resolved_at.timestamp()) if decision.resolved_at is not None else None,
                "actual_success_rate": decision.actual_success_rate,
                "engram_id": escape_string(decision.engram_id) if decision.engram_id is not None else None,
                "commit_sha": escape_string(decision.commit_sha) if decision.commit_sha is not None else None,
                "memory_type": escape_string(sanitize_text(decision.memory_type, max_len=32)) if decision.memory_type is not None else None,
                "memory_subject": escape_string(sanitize_text(decision.memory_subject, max_len=32)) if decision.memory_subject is not None else None,
                "ttl_days": decision.ttl_days,
                "last_verified_at": int(decision.last_verified_at.timestamp()) if decision.last_verified_at is not None else None,
                "is_active": decision.is_active,
                "deprecated_reason": escape_string(sanitize_text(decision.deprecated_reason, max_len=200)) if decision.deprecated_reason is not None else None,
                "source": escape_string(sanitize_text(decision.source, max_len=80)) if decision.source is not None else None
            }
            self.graph.query(query, params)
            logger.info(f"Added decision {decision.decision_id}")
            return True
        except Exception as e:
            logger.error(f"Failed to add decision: {e}")
            return False

    def add_engram(self, engram: Engram) -> bool:
        """Add an engram (session checkpoint) node to the graph."""
        if not self.connected:
            logger.error("Not connected to graph")
            return False

        try:
            query = """
            CREATE (e:Engram {
                id: $id,
                session_id: $session_id,
                commit_sha: $commit_sha,
                branch: $branch,
                created_at: $created_at,
                session_duration_sec: $session_duration_sec,
                agent_type: $agent_type,
                agent_model: $agent_model,
                decisions_extracted: $decisions_extracted,
                files_changed: $files_changed,
                total_tokens: $total_tokens,
                tenant_id: $tenant_id,
                team_id: $team_id,
                project_id: $project_id
            })
            RETURN e
            """
            params = {
                "id": engram.engram_id,
                "session_id": escape_string(engram.session_id),
                "commit_sha": escape_string(engram.commit_sha),
                "branch": escape_string(engram.branch),
                "created_at": int(engram.timestamp.timestamp()),
                "session_duration_sec": engram.agent.session_duration_sec,
                "agent_type": escape_string(engram.agent.type),
                "agent_model": escape_string(engram.agent.model),
                "decisions_extracted": len(engram.decisions_extracted),
                "files_changed": len(engram.files_changed),
                "total_tokens": engram.agent.total_tokens,
                "tenant_id": self._namespace['tenant_id'],
                "team_id": self._namespace['team_id'],
                "project_id": self._namespace['project_id']
            }
            self.graph.query(query, params)
            logger.info(f"Added engram {engram.engram_id}")
            return True
        except Exception as e:
            logger.error(f"Failed to add engram: {e}")
            return False

    def add_code_change(self, change: CodeChange) -> bool:
        """Add a code change (commit) node to the graph."""
        if not self.connected:
            logger.error("Not connected to graph")
            return False

        try:
            query = """
            CREATE (c:CodeChange {
                id: $id,
                commit_sha: $commit_sha,
                files_changed: $files_changed,
                timestamp: $timestamp,
                author: $author,
                decision_id: $decision_id,
                outcome: $outcome,
                reverted_by: $reverted_by,
                days_to_revert: $days_to_revert,
                lines_added: $lines_added,
                lines_removed: $lines_removed,
                tenant_id: $tenant_id,
                team_id: $team_id,
                project_id: $project_id
            })
            RETURN c
            """
            params = {
                "id": change.change_id,
                "commit_sha": escape_string(change.commit_sha),
                "files_changed": json.dumps(change.files_changed),
                "timestamp": int(change.timestamp.timestamp()),
                "author": escape_string(change.author),
                "decision_id": escape_string(change.decision_id) if change.decision_id is not None else None,
                "outcome": escape_string(change.outcome) if change.outcome is not None else None,
                "reverted_by": escape_string(change.reverted_by) if change.reverted_by is not None else None,
                "days_to_revert": change.days_to_revert,
                "lines_added": change.lines_added,
                "lines_removed": change.lines_removed,
                "tenant_id": self._namespace['tenant_id'],
                "team_id": self._namespace['team_id'],
                "project_id": self._namespace['project_id']
            }
            self.graph.query(query, params)
            logger.info(f"Added code change {change.change_id}")
            return True
        except Exception as e:
            logger.error(f"Failed to add code change: {e}")
            return False

    def add_outcome(self, outcome: Outcome) -> bool:
        """Add an outcome node to the graph."""
        if not self.connected:
            logger.error("Not connected to graph")
            return False

        try:
            query = """
            CREATE (o:Outcome {
                id: $id,
                status: $status,
                evidence: $evidence,
                measured_at: $measured_at,
                performance_impact: $performance_impact,
                reliability: $reliability,
                maintenance_cost: $maintenance_cost,
                code_change_id: $code_change_id,
                tenant_id: $tenant_id,
                team_id: $team_id,
                project_id: $project_id,
                ttl_days: $ttl_days,
                is_active: $is_active,
                deprecated_reason: $deprecated_reason
            })
            RETURN o
            """
            params = {
                "id": outcome.outcome_id,
                "status": escape_string(outcome.status),
                "evidence": escape_string(outcome.evidence),
                "measured_at": int(outcome.measured_at.timestamp()),
                "performance_impact": outcome.performance_impact,
                "reliability": outcome.reliability,
                "maintenance_cost": outcome.maintenance_cost,
                "code_change_id": escape_string(outcome.code_change_id) if outcome.code_change_id is not None else None,
                "tenant_id": self._namespace['tenant_id'],
                "team_id": self._namespace['team_id'],
                "project_id": self._namespace['project_id'],
                "ttl_days": outcome.ttl_days,
                "is_active": outcome.is_active,
                "deprecated_reason": escape_string(outcome.deprecated_reason) if outcome.deprecated_reason is not None else None
            }
            self.graph.query(query, params)
            logger.info(f"Added outcome {outcome.outcome_id}")
            return True
        except Exception as e:
            logger.error(f"Failed to add outcome: {e}")
            return False

    def add_negative_knowledge(self, nk: NegativeKnowledge) -> bool:
        """Add a negative knowledge node to the graph."""
        if not self.connected:
            logger.error("Not connected to graph")
            return False

        try:
            query = """
            CREATE (nk:NegativeKnowledge {
                id: $id,
                hypothesis: $hypothesis,
                conclusion: $conclusion,
                evidence: $evidence,
                domain: $domain,
                severity: $severity,
                discovered_at: $discovered_at,
                expires_at: $expires_at,
                blocks_pattern: $blocks_pattern,
                recommendation: $recommendation,
                source: $source,
                tenant_id: $tenant_id,
                team_id: $team_id,
                project_id: $project_id,
                memory_type: $memory_type,
                memory_subject: $memory_subject,
                ttl_days: $ttl_days,
                last_verified_at: $last_verified_at,
                is_active: $is_active,
                deprecated_reason: $deprecated_reason
            })
            RETURN nk
            """
            params = {
                "id": nk.nk_id,
                "hypothesis": escape_string(sanitize_text(nk.hypothesis, max_len=400)),
                "conclusion": escape_string(sanitize_text(nk.conclusion, max_len=400)),
                "evidence": escape_string(sanitize_text(nk.evidence, max_len=800)),
                "domain": escape_string(sanitize_text(nk.domain, max_len=80)),
                "severity": escape_string(sanitize_text(nk.severity, max_len=20)),
                "discovered_at": int(nk.discovered_at.timestamp()),
                "expires_at": int(nk.expires_at.timestamp()) if nk.expires_at is not None else None,
                "blocks_pattern": escape_string(sanitize_text(nk.blocks_pattern, max_len=120)) if nk.blocks_pattern is not None else None,
                "recommendation": escape_string(sanitize_text(nk.recommendation, max_len=400)),
                "source": escape_string(sanitize_text(nk.source, max_len=80)),
                "tenant_id": self._namespace['tenant_id'],
                "team_id": self._namespace['team_id'],
                "project_id": self._namespace['project_id'],
                "memory_type": escape_string(sanitize_text(nk.memory_type, max_len=32)) if nk.memory_type is not None else None,
                "memory_subject": escape_string(sanitize_text(nk.memory_subject, max_len=32)) if nk.memory_subject is not None else None,
                "ttl_days": nk.ttl_days,
                "last_verified_at": int(nk.last_verified_at.timestamp()) if nk.last_verified_at is not None else None,
                "is_active": nk.is_active,
                "deprecated_reason": escape_string(sanitize_text(nk.deprecated_reason, max_len=200)) if nk.deprecated_reason is not None else None
            }
            self.graph.query(query, params)
            logger.info(f"Added negative knowledge {nk.nk_id}")
            return True
        except Exception as e:
            logger.error(f"Failed to add negative knowledge: {e}")
            return False

    def update_decision_memory(self, decision_id: str, updates: Dict[str, Any]) -> bool:
        """Update memory metadata for a Decision node."""
        if not self.connected:
            logger.error("Not connected to graph")
            return False

        allowed = {
            "memory_type",
            "memory_subject",
            "ttl_days",
            "last_verified_at",
            "is_active",
            "deprecated_reason",
            "source",
            "factcheck_status",
        }
        safe_updates = {k: v for k, v in updates.items() if k in allowed}
        if not safe_updates:
            return False

        try:
            set_clauses = []
            params = {"id": decision_id}
            for idx, (key, value) in enumerate(safe_updates.items()):
                param_key = f"v{idx}"
                set_clauses.append(f"d.{key} = ${param_key}")
                params[param_key] = value

            query = f"""
            MATCH (d:Decision {{id: $id}})
            SET {", ".join(set_clauses)}
            RETURN d
            """
            self.graph.query(query, params)
            return True
        except Exception as e:
            logger.error(f"Failed to update decision memory: {e}")
            return False

    def update_negative_knowledge_memory(self, nk_id: str, updates: Dict[str, Any]) -> bool:
        """Update memory metadata for a NegativeKnowledge node."""
        if not self.connected:
            logger.error("Not connected to graph")
            return False

        allowed = {
            "memory_type",
            "memory_subject",
            "ttl_days",
            "last_verified_at",
            "is_active",
            "deprecated_reason",
        }
        safe_updates = {k: v for k, v in updates.items() if k in allowed}
        if not safe_updates:
            return False

        try:
            set_clauses = []
            params = {"id": nk_id}
            for idx, (key, value) in enumerate(safe_updates.items()):
                param_key = f"v{idx}"
                set_clauses.append(f"nk.{key} = ${param_key}")
                params[param_key] = value

            query = f"""
            MATCH (nk:NegativeKnowledge {{id: $id}})
            SET {", ".join(set_clauses)}
            RETURN nk
            """
            self.graph.query(query, params)
            return True
        except Exception as e:
            logger.error(f"Failed to update negative knowledge memory: {e}")
            return False

    def add_antipattern(self, ap: Antipattern) -> bool:
        """Add an antipattern node to the graph."""
        if not self.connected:
            logger.error("Not connected to graph")
            return False

        try:
            query = """
            CREATE (ap:AntiPattern {
                id: $id,
                name: $name,
                category: $category,
                severity: $severity,
                repos_affected: $repos_affected,
                occurrence_count: $occurrence_count,
                removal_rate: $removal_rate,
                avg_days_to_removal: $avg_days_to_removal,
                keywords: $keywords,
                regex_pattern: $regex_pattern,
                example_bad: $example_bad,
                example_good: $example_good,
                first_seen: $first_seen,
                found_by: $found_by,
                source: $source,
                recommendation: $recommendation,
                tenant_id: $tenant_id,
                team_id: $team_id,
                project_id: $project_id
            })
            RETURN ap
            """
            params = {
                "id": ap.pattern_id,
                "name": escape_string(ap.name),
                "category": escape_string(ap.category),
                "severity": escape_string(ap.severity),
                "repos_affected": ap.repos_affected,
                "occurrence_count": ap.occurrence_count,
                "removal_rate": ap.removal_rate,
                "avg_days_to_removal": ap.avg_days_to_removal,
                "keywords": json.dumps(ap.keywords),
                "regex_pattern": escape_string(ap.regex_pattern),
                "example_bad": escape_string(ap.example_bad),
                "example_good": escape_string(ap.example_good),
                "first_seen": int(ap.first_seen.timestamp()),
                "found_by": escape_string(ap.found_by),
                "source": escape_string(ap.source),
                "recommendation": escape_string(ap.recommendation),
                "tenant_id": self._namespace['tenant_id'],
                "team_id": self._namespace['team_id'],
                "project_id": self._namespace['project_id']
            }
            self.graph.query(query, params)
            logger.info(f"Added antipattern {ap.pattern_id}")
            return True
        except Exception as e:
            logger.error(f"Failed to add antipattern: {e}")
            return False

    def add_document(self, doc) -> bool:
        """Add a Document node to the graph."""
        if not self.connected:
            logger.error("Not connected to graph")
            return False
        try:
            cypher = doc.to_cypher_create()
            self.graph.query(cypher)
            return True
        except Exception as e:
            logger.error(f"Failed to add document: {e}")
            return False

    # ---------------------------------------------------------------------
    # Squad / Profile / Role orchestration
    # ---------------------------------------------------------------------

    def upsert_workspace(self, workspace_id: str, name: str, description: Optional[str] = None) -> bool:
        """Create or update a workspace node."""
        if not self.connected:
            logger.error("Not connected to graph")
            return False
        try:
            created_at = int(__import__("time").time())
            query = """
            MERGE (w:Workspace {id: $id, tenant_id: $tenant_id, team_id: $team_id})
            SET w.name = $name,
                w.description = $description,
                w.created_at = coalesce(w.created_at, $created_at)
            RETURN w
            """
            self.query(
                query,
                {
                    "id": workspace_id,
                    "name": sanitize_text(name, max_len=120),
                    "description": sanitize_text(description or "", max_len=400),
                    "created_at": created_at,
                    "tenant_id": self._namespace["tenant_id"],
                    "team_id": self._namespace["team_id"],
                },
            )
            return True
        except Exception as e:
            logger.error(f"Failed to upsert workspace: {e}")
            return False

    def upsert_project(
        self,
        project_id: str,
        name: str,
        workspace_id: Optional[str] = None,
        description: Optional[str] = None,
    ) -> bool:
        """Create or update a project node, optionally link to workspace."""
        if not self.connected:
            logger.error("Not connected to graph")
            return False
        try:
            created_at = int(__import__("time").time())
            if workspace_id:
                query = """
                MERGE (w:Workspace {id: $workspace_id, tenant_id: $tenant_id, team_id: $team_id})
                MERGE (p:Project {id: $id, tenant_id: $tenant_id, team_id: $team_id})
                SET p.name = $name,
                    p.description = $description,
                    p.created_at = coalesce(p.created_at, $created_at)
                MERGE (w)-[:HAS_PROJECT]->(p)
                RETURN p
                """
                params = {
                    "workspace_id": workspace_id,
                    "id": project_id,
                    "name": sanitize_text(name, max_len=120),
                    "description": sanitize_text(description or "", max_len=400),
                    "created_at": created_at,
                    "tenant_id": self._namespace["tenant_id"],
                    "team_id": self._namespace["team_id"],
                }
            else:
                query = """
                MERGE (p:Project {id: $id, tenant_id: $tenant_id, team_id: $team_id})
                SET p.name = $name,
                    p.description = $description,
                    p.created_at = coalesce(p.created_at, $created_at)
                RETURN p
                """
                params = {
                    "id": project_id,
                    "name": sanitize_text(name, max_len=120),
                    "description": sanitize_text(description or "", max_len=400),
                    "created_at": created_at,
                    "tenant_id": self._namespace["tenant_id"],
                    "team_id": self._namespace["team_id"],
                }
            self.query(query, params)
            return True
        except Exception as e:
            logger.error(f"Failed to upsert project: {e}")
            return False

    def upsert_profile(
        self,
        profile_id: str,
        name: str,
        config_path: str,
        checksum: Optional[str] = None,
        provider: Optional[str] = None,
        model: Optional[str] = None,
        allowlist_path: Optional[str] = None,
    ) -> bool:
        """Create or update a profile node."""
        if not self.connected:
            logger.error("Not connected to graph")
            return False
        try:
            updated_at = int(__import__("time").time())
            query = """
            MERGE (p:Profile {id: $id, tenant_id: $tenant_id, team_id: $team_id, project_id: $project_id})
            SET p.name = $name,
                p.config_path = $config_path,
                p.checksum = $checksum,
                p.provider = $provider,
                p.model = $model,
                p.allowlist_path = $allowlist_path,
                p.updated_at = $updated_at
            RETURN p
            """
            self.query(
                query,
                {
                    "id": profile_id,
                    "name": sanitize_text(name, max_len=120),
                    "config_path": sanitize_text(config_path, max_len=240),
                    "checksum": sanitize_text(checksum or "", max_len=120),
                    "provider": sanitize_text(provider or "", max_len=80),
                    "model": sanitize_text(model or "", max_len=120),
                    "allowlist_path": sanitize_text(allowlist_path or "", max_len=240),
                    "updated_at": updated_at,
                    "tenant_id": self._namespace["tenant_id"],
                    "team_id": self._namespace["team_id"],
                    "project_id": self._namespace["project_id"],
                },
            )
            return True
        except Exception as e:
            logger.error(f"Failed to upsert profile: {e}")
            return False

    def upsert_role(
        self,
        role_id: str,
        name: str,
        description: Optional[str] = None,
        prompt_path: Optional[str] = None,
        context_policy: Optional[Dict[str, Any]] = None,
    ) -> bool:
        """Create or update a role node."""
        if not self.connected:
            logger.error("Not connected to graph")
            return False
        try:
            policy_json = ""
            if context_policy is not None:
                try:
                    policy_json = json.dumps(context_policy)
                except Exception:
                    policy_json = ""
            query = """
            MERGE (r:Role {id: $id, tenant_id: $tenant_id, team_id: $team_id})
            SET r.name = $name,
                r.description = $description,
                r.prompt_path = $prompt_path,
                r.context_policy = $context_policy
            RETURN r
            """
            self.query(
                query,
                {
                    "id": role_id,
                    "name": sanitize_text(name, max_len=120),
                    "description": sanitize_text(description or "", max_len=400),
                    "prompt_path": sanitize_text(prompt_path or "", max_len=240),
                    "context_policy": sanitize_text(policy_json, max_len=2000),
                    "tenant_id": self._namespace["tenant_id"],
                    "team_id": self._namespace["team_id"],
                },
            )
            return True
        except Exception as e:
            logger.error(f"Failed to upsert role: {e}")
            return False

    def get_role(self, role_name: str) -> Optional[Dict[str, Any]]:
        """Fetch role by id or name."""
        if not self.connected:
            logger.error("Not connected to graph")
            return None
        try:
            role_id = f"role_{role_name}"
            query = """
            MATCH (r:Role {id: $id, tenant_id: $tenant_id, team_id: $team_id})
            RETURN r
            """
            result = self.graph.query(
                query,
                {
                    "id": role_id,
                    "tenant_id": self._namespace["tenant_id"],
                    "team_id": self._namespace["team_id"],
                }
            )
            if result and result.result_set and len(result.result_set) > 0:
                row = result.result_set[0]
                if row and len(row) > 0:
                    node = row[0]
                    return {
                        "id": node.properties.get("id", ""),
                        "name": node.properties.get("name", role_name),
                        "description": node.properties.get("description", ""),
                        "prompt_path": node.properties.get("prompt_path", ""),
                        "context_policy": node.properties.get("context_policy", ""),
                    }
            return None
        except Exception as e:
            logger.error(f"Failed to get role {role_name}: {e}")
            return None

    def link_role_docshot(self, role_name: str, doc_shot_id: str) -> bool:
        """Link Role to DocShot."""
        if not self.connected:
            logger.error("Not connected to graph")
            return False
        try:
            role_id = f"role_{role_name}"
            query = """
            MERGE (r:Role {id: $role_id, tenant_id: $tenant_id, team_id: $team_id})
            MERGE (ds:DocShot {id: $doc_shot_id})
            MERGE (r)-[:ROLE_USES_DOCSHOT]->(ds)
            RETURN ds
            """
            self.query(
                query,
                {
                    "role_id": role_id,
                    "doc_shot_id": doc_shot_id,
                    "tenant_id": self._namespace["tenant_id"],
                    "team_id": self._namespace["team_id"],
                },
            )
            return True
        except Exception as e:
            logger.error(f"Failed to link role docshot: {e}")
            return False

    def link_role_skill(self, role_name: str, skill_id: str) -> bool:
        """Link Role to Skill."""
        if not self.connected:
            logger.error("Not connected to graph")
            return False
        try:
            role_id = f"role_{role_name}"
            query = """
            MERGE (r:Role {id: $role_id, tenant_id: $tenant_id, team_id: $team_id})
            MATCH (s:Skill {id: $skill_id})
            MERGE (r)-[:ROLE_USES_SKILL]->(s)
            RETURN s
            """
            self.query(
                query,
                {
                    "role_id": role_id,
                    "skill_id": skill_id,
                    "tenant_id": self._namespace["tenant_id"],
                    "team_id": self._namespace["team_id"],
                },
            )
            return True
        except Exception as e:
            logger.error(f"Failed to link role skill: {e}")
            return False

    def link_role_nk(self, role_name: str, nk_id: str) -> bool:
        """Link Role to NegativeKnowledge."""
        if not self.connected:
            logger.error("Not connected to graph")
            return False
        try:
            role_id = f"role_{role_name}"
            query = """
            MERGE (r:Role {id: $role_id, tenant_id: $tenant_id, team_id: $team_id})
            MATCH (nk:NegativeKnowledge {id: $nk_id})
            MERGE (r)-[:ROLE_USES_NK]->(nk)
            RETURN nk
            """
            self.query(
                query,
                {
                    "role_id": role_id,
                    "nk_id": nk_id,
                    "tenant_id": self._namespace["tenant_id"],
                    "team_id": self._namespace["team_id"],
                },
            )
            return True
        except Exception as e:
            logger.error(f"Failed to link role NK: {e}")
            return False

    def get_role_links(self, role_name: str) -> Dict[str, Any]:
        """Fetch role-linked DocShots, Skills, and NegativeKnowledge."""
        if not self.connected:
            logger.error("Not connected to graph")
            return {"docshots": [], "skills": [], "negative_knowledge": []}

        try:
            role_id = f"role_{role_name}"

            # Fetch linked DocShots
            docshots_query = """
            MATCH (r:Role {id: $role_id, tenant_id: $tenant_id, team_id: $team_id})-[:ROLE_USES_DOCSHOT]->(ds:DocShot)
            RETURN ds.id as id, ds.doc_count as doc_count, ds.created_at as created_at
            LIMIT 10
            """
            docshots_result = self.graph.query(docshots_query, {
                "role_id": role_id,
                "tenant_id": self._namespace["tenant_id"],
                "team_id": self._namespace["team_id"],
            })
            docshots = [dict(zip(["id", "doc_count", "created_at"], row)) for row in (docshots_result.result_set or [])]

            # Fetch linked Skills
            skills_query = """
            MATCH (r:Role {id: $role_id, tenant_id: $tenant_id, team_id: $team_id})-[:ROLE_USES_SKILL]->(s:Skill)
            RETURN s.id as id, s.name as name, s.procedure as procedure, s.quality_score as quality_score
            LIMIT 10
            """
            skills_result = self.graph.query(skills_query, {
                "role_id": role_id,
                "tenant_id": self._namespace["tenant_id"],
                "team_id": self._namespace["team_id"],
            })
            skills = [dict(zip(["id", "name", "procedure", "quality_score"], row)) for row in (skills_result.result_set or [])]

            # Fetch linked NegativeKnowledge
            nk_query = """
            MATCH (r:Role {id: $role_id, tenant_id: $tenant_id, team_id: $team_id})-[:ROLE_USES_NK]->(nk:NegativeKnowledge)
            RETURN nk.id as id, nk.hypothesis as hypothesis, nk.recommendation as recommendation, nk.is_active as is_active
            LIMIT 10
            """
            nk_result = self.graph.query(nk_query, {
                "role_id": role_id,
                "tenant_id": self._namespace["tenant_id"],
                "team_id": self._namespace["team_id"],
            })
            negative_knowledge = [dict(zip(["id", "hypothesis", "recommendation", "is_active"], row)) for row in (nk_result.result_set or [])]

            return {
                "docshots": docshots,
                "skills": skills,
                "negative_knowledge": negative_knowledge,
            }
        except Exception as e:
            logger.error(f"Failed to get role links for {role_name}: {e}")
            return {"docshots": [], "skills": [], "negative_knowledge": []}

    def unlink_role_docshot(self, role_name: str, doc_shot_id: str) -> bool:
        """Remove Role -> DocShot link."""
        if not self.connected:
            logger.error("Not connected to graph")
            return False
        try:
            role_id = f"role_{role_name}"
            query = """
            MATCH (r:Role {id: $role_id, tenant_id: $tenant_id, team_id: $team_id})-[rel:ROLE_USES_DOCSHOT]->(ds:DocShot {id: $doc_shot_id})
            DELETE rel
            RETURN ds
            """
            self.query(
                query,
                {
                    "role_id": role_id,
                    "doc_shot_id": doc_shot_id,
                    "tenant_id": self._namespace["tenant_id"],
                    "team_id": self._namespace["team_id"],
                },
            )
            return True
        except Exception as e:
            logger.error(f"Failed to unlink role docshot: {e}")
            return False

    def unlink_role_skill(self, role_name: str, skill_id: str) -> bool:
        """Remove Role -> Skill link."""
        if not self.connected:
            logger.error("Not connected to graph")
            return False
        try:
            role_id = f"role_{role_name}"
            query = """
            MATCH (r:Role {id: $role_id, tenant_id: $tenant_id, team_id: $team_id})-[rel:ROLE_USES_SKILL]->(s:Skill {id: $skill_id})
            DELETE rel
            RETURN s
            """
            self.query(
                query,
                {
                    "role_id": role_id,
                    "skill_id": skill_id,
                    "tenant_id": self._namespace["tenant_id"],
                    "team_id": self._namespace["team_id"],
                },
            )
            return True
        except Exception as e:
            logger.error(f"Failed to unlink role skill: {e}")
            return False

    def unlink_role_nk(self, role_name: str, nk_id: str) -> bool:
        """Remove Role -> NegativeKnowledge link."""
        if not self.connected:
            logger.error("Not connected to graph")
            return False
        try:
            role_id = f"role_{role_name}"
            query = """
            MATCH (r:Role {id: $role_id, tenant_id: $tenant_id, team_id: $team_id})-[rel:ROLE_USES_NK]->(nk:NegativeKnowledge {id: $nk_id})
            DELETE rel
            RETURN nk
            """
            self.query(
                query,
                {
                    "role_id": role_id,
                    "nk_id": nk_id,
                    "tenant_id": self._namespace["tenant_id"],
                    "team_id": self._namespace["team_id"],
                },
            )
            return True
        except Exception as e:
            logger.error(f"Failed to unlink role NK: {e}")
            return False
        role_id = f"role_{role_name}"
        try:
            docshots = self.query(
                """
                MATCH (r:Role {id: $role_id, tenant_id: $tenant_id, team_id: $team_id})
                OPTIONAL MATCH (r)-[:ROLE_USES_DOCSHOT]->(ds:DocShot)
                RETURN ds
                """,
                {"role_id": role_id, "tenant_id": self._namespace["tenant_id"], "team_id": self._namespace["team_id"]},
            )
            skills = self.query(
                """
                MATCH (r:Role {id: $role_id, tenant_id: $tenant_id, team_id: $team_id})
                OPTIONAL MATCH (r)-[:ROLE_USES_SKILL]->(s:Skill)
                RETURN s
                """,
                {"role_id": role_id, "tenant_id": self._namespace["tenant_id"], "team_id": self._namespace["team_id"]},
            )
            nks = self.query(
                """
                MATCH (r:Role {id: $role_id, tenant_id: $tenant_id, team_id: $team_id})
                OPTIONAL MATCH (r)-[:ROLE_USES_NK]->(nk:NegativeKnowledge)
                RETURN nk
                """,
                {"role_id": role_id, "tenant_id": self._namespace["tenant_id"], "team_id": self._namespace["team_id"]},
            )
            return {
                "docshots": [row[0] for row in docshots if row and row[0]],
                "skills": [row[0] for row in skills if row and row[0]],
                "negative_knowledge": [row[0] for row in nks if row and row[0]],
            }
        except Exception as e:
            logger.error(f"Failed to get role links: {e}")
            return {"docshots": [], "skills": [], "negative_knowledge": []}
        try:
            role_id = f"role_{role_name}"
            query = """
            MATCH (r:Role {tenant_id: $tenant_id, team_id: $team_id})
            WHERE r.id = $role_id OR r.name = $role_name
            RETURN r
            LIMIT 1
            """
            rows = self.query(
                query,
                {
                    "tenant_id": self._namespace["tenant_id"],
                    "team_id": self._namespace["team_id"],
                    "role_id": role_id,
                    "role_name": role_name,
                },
            )
            return rows[0][0] if rows else None
        except Exception as e:
            logger.error(f"Failed to get role: {e}")
            return None

    def create_squad(
        self,
        squad_id: str,
        name: str,
        strategy: str,
        project_id: Optional[str] = None,
    ) -> bool:
        """Create a squad and link to project if provided."""
        if not self.connected:
            logger.error("Not connected to graph")
            return False
        try:
            created_at = int(__import__("time").time())
            if project_id:
                query = """
                MERGE (p:Project {id: $project_id, tenant_id: $tenant_id, team_id: $team_id})
                MERGE (s:Squad {id: $id, tenant_id: $tenant_id, team_id: $team_id})
                SET s.name = $name,
                    s.strategy = $strategy,
                    s.project_id = $project_id,
                    s.created_at = coalesce(s.created_at, $created_at)
                MERGE (p)-[:USES_SQUAD]->(s)
                RETURN s
                """
                params = {
                    "project_id": project_id,
                    "id": squad_id,
                    "name": sanitize_text(name, max_len=120),
                    "strategy": sanitize_text(strategy, max_len=40),
                    "created_at": created_at,
                    "tenant_id": self._namespace["tenant_id"],
                    "team_id": self._namespace["team_id"],
                }
            else:
                query = """
                MERGE (s:Squad {id: $id, tenant_id: $tenant_id, team_id: $team_id})
                SET s.name = $name,
                    s.strategy = $strategy,
                    s.created_at = coalesce(s.created_at, $created_at)
                RETURN s
                """
                params = {
                    "id": squad_id,
                    "name": sanitize_text(name, max_len=120),
                    "strategy": sanitize_text(strategy, max_len=40),
                    "created_at": created_at,
                    "tenant_id": self._namespace["tenant_id"],
                    "team_id": self._namespace["team_id"],
                }
            self.query(query, params)
            return True
        except Exception as e:
            logger.error(f"Failed to create squad: {e}")
            return False

    def add_assignment(
        self,
        assignment_id: str,
        squad_id: str,
        role_id: str,
        profile_id: str,
        order: int = 0,
        weight: float = 1.0,
    ) -> bool:
        """Add an assignment and link to squad, role and profile."""
        if not self.connected:
            logger.error("Not connected to graph")
            return False
        try:
            query = """
            MERGE (s:Squad {id: $squad_id, tenant_id: $tenant_id, team_id: $team_id})
            MERGE (r:Role {id: $role_id, tenant_id: $tenant_id, team_id: $team_id})
            MERGE (p:Profile {id: $profile_id, tenant_id: $tenant_id, team_id: $team_id, project_id: $project_id})
            MERGE (a:Assignment {id: $id, tenant_id: $tenant_id, team_id: $team_id, project_id: $project_id})
            SET a.role_id = $role_id,
                a.profile_id = $profile_id,
                a.order = $order,
                a.weight = $weight
            MERGE (s)-[:ASSIGNS]->(a)
            MERGE (a)-[:PLAYS_ROLE]->(r)
            MERGE (a)-[:USES_PROFILE]->(p)
            RETURN a
            """
            self.query(
                query,
                {
                    "id": assignment_id,
                    "squad_id": squad_id,
                    "role_id": role_id,
                    "profile_id": profile_id,
                    "order": int(order),
                    "weight": float(weight),
                    "tenant_id": self._namespace["tenant_id"],
                    "team_id": self._namespace["team_id"],
                    "project_id": self._namespace["project_id"],
                },
            )
            return True
        except Exception as e:
            logger.error(f"Failed to add assignment: {e}")
            return False

    def list_squads(self, project_id: Optional[str] = None, limit: int = 20) -> List[Dict[str, Any]]:
        """List squads for a project or namespace."""
        query = """
        MATCH (s:Squad {tenant_id: $tenant_id, team_id: $team_id})
        WHERE ($project_id IS NULL OR s.project_id = $project_id)
        RETURN s
        ORDER BY s.created_at DESC
        LIMIT $limit
        """
        rows = self.query(
            query,
            {
                "tenant_id": self._namespace["tenant_id"],
                "team_id": self._namespace["team_id"],
                "project_id": project_id,
                "limit": int(limit),
            },
        )
        return [row[0] for row in rows]

    def list_assignments(self, squad_id: str) -> List[Dict[str, Any]]:
        """List assignments for a squad."""
        query = """
        MATCH (s:Squad {id: $squad_id, tenant_id: $tenant_id, team_id: $team_id})-[:ASSIGNS]->(a:Assignment)
        RETURN a
        ORDER BY a.order ASC
        """
        rows = self.query(
            query,
            {
                "squad_id": squad_id,
                "tenant_id": self._namespace["tenant_id"],
                "team_id": self._namespace["team_id"],
            },
        )
        return [row[0] for row in rows]

    def get_documents(
        self,
        doc_types: Optional[Iterable[str]] = None,
        file_paths: Optional[Iterable[str]] = None,
        doc_ids: Optional[Iterable[str]] = None,
        limit: int = 10,
    ) -> List[Dict[str, Any]]:
        """Fetch Document nodes by filters."""
        if not self.connected:
            logger.error("Not connected to graph")
            return []

        try:
            query = """
            MATCH (d:Document)
            WHERE ($doc_types IS NULL OR d.doc_type IN $doc_types)
              AND ($file_paths IS NULL OR d.file_path IN $file_paths)
              AND ($doc_ids IS NULL OR d.id IN $doc_ids)
              AND ($tenant_id IS NULL OR d.tenant_id = $tenant_id)
              AND ($team_id IS NULL OR d.team_id = $team_id)
              AND ($project_id IS NULL OR d.project_id = $project_id)
            RETURN d.id as id,
                   d.file_path as file_path,
                   d.doc_type as doc_type,
                   d.updated_at as updated_at,
                   d.content as content,
                   d.metadata as metadata
            ORDER BY d.updated_at DESC
            LIMIT $limit
            """
            params = {
                "doc_types": list(doc_types) if doc_types else None,
                "file_paths": list(file_paths) if file_paths else None,
                "doc_ids": list(doc_ids) if doc_ids else None,
                "limit": int(limit),
                "tenant_id": self._namespace["tenant_id"],
                "team_id": self._namespace["team_id"],
                "project_id": self._namespace["project_id"],
            }
            result = self.graph.query(query, params)
            return result or []
        except Exception as e:
            logger.error(f"Failed to fetch documents: {e}")
            return []

    def link_decision_docs(
        self,
        decision_id: str,
        doc_shot_id: Optional[str],
        docs: List[Dict[str, Any]],
        fetched_at: Optional[str] = None,
    ) -> bool:
        """Link a decision to documents for traceability."""
        if not self.connected:
            logger.error("Not connected to graph")
            return False

    def upsert_session_context(
        self,
        session_id: str,
        task: str,
        focus: Optional[str] = None,
        current_plan: Optional[str] = None,
        constraints: Optional[List[str]] = None,
        doc_shot_id: Optional[str] = None,
        ttl_days: int = 3,
    ) -> bool:
        """Upsert short-lived session context."""
        if not self.connected:
            logger.error("Not connected to graph")
            return False

        try:
            now_ts = int(__import__("time").time())
            expires_at = now_ts + int(ttl_days) * 86400 if ttl_days else None

            from membria.security import sanitize_text, sanitize_list

            payload = {
                "id": f"sc_{session_id}",
                "session_id": session_id,
                "task": sanitize_text(task, max_len=400),
                "focus": sanitize_text(focus or "", max_len=200) if focus else None,
                "current_plan": sanitize_text(current_plan or "", max_len=600) if current_plan else None,
                "constraints": sanitize_list(constraints or [], max_len=200),
                "doc_count": len(constraints or []),
                "doc_shot_id": sanitize_text(doc_shot_id or "", max_len=80) if doc_shot_id else None,
                "created_at": now_ts,
                "expires_at": expires_at,
                "is_active": True,
                "tenant_id": self._namespace["tenant_id"],
                "team_id": self._namespace["team_id"],
                "project_id": self._namespace["project_id"],
            }

            query = """
            MERGE (sc:SessionContext {id: $id})
            SET sc.session_id = $session_id,
                sc.task = $task,
                sc.focus = $focus,
                sc.current_plan = $current_plan,
                sc.constraints = $constraints,
                sc.doc_count = $doc_count,
                sc.doc_shot_id = $doc_shot_id,
                sc.tenant_id = $tenant_id,
                sc.team_id = $team_id,
                sc.project_id = $project_id,
                sc.created_at = COALESCE(sc.created_at, $created_at),
                sc.expires_at = $expires_at,
                sc.is_active = true
            RETURN sc
            """

            self.graph.query(query, payload)
            return True
        except Exception as e:
            logger.error(f"Failed to upsert session context: {e}")
            return False

    def get_session_context(self, session_id: str) -> Optional[Dict[str, Any]]:
        """Get active session context by session_id."""
        if not self.connected:
            logger.error("Not connected to graph")
            return None

        try:
            now_ts = int(__import__("time").time())
            query = """
            MATCH (sc:SessionContext {session_id: $session_id})
            WHERE (sc.is_active IS NULL OR sc.is_active = true)
              AND (sc.expires_at IS NULL OR sc.expires_at > $now)
              AND ($tenant_id IS NULL OR sc.tenant_id = $tenant_id)
              AND ($team_id IS NULL OR sc.team_id = $team_id)
              AND ($project_id IS NULL OR sc.project_id = $project_id)
            RETURN sc.id as id,
                   sc.session_id as session_id,
                   sc.task as task,
                   sc.focus as focus,
                   sc.current_plan as current_plan,
                   sc.constraints as constraints,
                   sc.doc_count as doc_count,
                   sc.doc_shot_id as doc_shot_id,
                   sc.created_at as created_at,
                   sc.expires_at as expires_at
            LIMIT 1
            """
            result = self.graph.query(query, {
                "session_id": session_id,
                "now": now_ts,
                "tenant_id": self._namespace["tenant_id"],
                "team_id": self._namespace["team_id"],
                "project_id": self._namespace["project_id"],
            })
            if result and len(result) > 0:
                row = result[0]
                return {
                    "id": row[0],
                    "session_id": row[1],
                    "task": row[2],
                    "focus": row[3],
                    "current_plan": row[4],
                    "constraints": row[5],
                    "doc_count": row[6],
                    "doc_shot_id": row[7],
                    "created_at": row[8],
                    "expires_at": row[9],
                }
            return None
        except Exception as e:
            logger.error(f"Failed to fetch session context: {e}")
            return None

    def list_session_contexts(
        self, limit: int = 10, active_only: bool = True
    ) -> List[Dict[str, Any]]:
        """List recent session contexts."""
        if not self.connected:
            logger.error("Not connected to graph")
            return []
        try:
            where = ""
            if active_only:
                where = "WHERE (sc.is_active IS NULL OR sc.is_active = true)"
            if where:
                where += "\n  AND ($tenant_id IS NULL OR sc.tenant_id = $tenant_id)\n" \
                         "  AND ($team_id IS NULL OR sc.team_id = $team_id)\n" \
                         "  AND ($project_id IS NULL OR sc.project_id = $project_id)"
            else:
                where = "WHERE ($tenant_id IS NULL OR sc.tenant_id = $tenant_id)\n" \
                        "  AND ($team_id IS NULL OR sc.team_id = $team_id)\n" \
                        "  AND ($project_id IS NULL OR sc.project_id = $project_id)"
            query = f"""
            MATCH (sc:SessionContext)
            {where}
            RETURN sc.session_id as session_id,
                   sc.task as task,
                   sc.focus as focus,
                   sc.current_plan as current_plan,
                   sc.constraints as constraints,
                   sc.doc_shot_id as doc_shot_id,
                   sc.created_at as created_at,
                   sc.expires_at as expires_at
            ORDER BY sc.created_at DESC
            LIMIT $limit
            """
            result = self.graph.query(query, {
                "limit": int(limit),
                "tenant_id": self._namespace["tenant_id"],
                "team_id": self._namespace["team_id"],
                "project_id": self._namespace["project_id"],
            })
            rows = result.result_set if hasattr(result, "result_set") else result
            items = []
            for row in rows or []:
                items.append(
                    {
                        "session_id": row[0],
                        "task": row[1],
                        "focus": row[2],
                        "current_plan": row[3],
                        "constraints": row[4],
                        "doc_shot_id": row[5],
                        "created_at": row[6],
                        "expires_at": row[7],
                    }
                )
            return items
        except Exception as e:
            logger.error(f"Failed to list session contexts: {e}")
            return []

    def deactivate_session_context(self, session_id: str) -> bool:
        """Deactivate a session context by session_id."""
        if not self.connected:
            logger.error("Not connected to graph")
            return False
        try:
            now_ts = int(__import__("time").time())
            query = """
            MATCH (sc:SessionContext {session_id: $session_id})
            SET sc.is_active = false,
                sc.expires_at = $now
            RETURN sc
            """
            self.graph.query(query, {"session_id": session_id, "now": now_ts})
            return True
        except Exception as e:
            logger.error(f"Failed to deactivate session context: {e}")
            return False

    def get_outcome(self, outcome_id: str) -> Optional[Dict[str, Any]]:
        """Get outcome by id from graph."""
        if not self.connected:
            logger.error("Not connected to graph")
            return None
        try:
            query = """
            MATCH (o:Outcome {id: $id})
            WHERE ($tenant_id IS NULL OR o.tenant_id = $tenant_id)
              AND ($team_id IS NULL OR o.team_id = $team_id)
              AND ($project_id IS NULL OR o.project_id = $project_id)
            RETURN o.id as id, o.status as status, o.evidence as evidence,
                   o.measured_at as measured_at, o.performance_impact as performance_impact,
                   o.reliability as reliability, o.maintenance_cost as maintenance_cost
            LIMIT 1
            """
            result = self.graph.query(query, {
                "id": outcome_id,
                "tenant_id": self._namespace["tenant_id"],
                "team_id": self._namespace["team_id"],
                "project_id": self._namespace["project_id"],
            })
            rows = result.result_set if hasattr(result, "result_set") else result
            if rows:
                row = rows[0]
                return {
                    "id": row[0],
                    "status": row[1],
                    "evidence": row[2],
                    "measured_at": row[3],
                    "performance_impact": row[4],
                    "reliability": row[5],
                    "maintenance_cost": row[6],
                }
            return None
        except Exception as e:
            logger.error(f"Failed to get outcome: {e}")
            return None

    def list_outcomes(self, limit: int = 10, status: Optional[str] = None) -> List[Dict[str, Any]]:
        """List outcomes with optional status filter."""
        if not self.connected:
            logger.error("Not connected to graph")
            return []
        try:
            where = "WHERE ($status IS NULL OR o.status = $status)\n" \
                    "  AND ($tenant_id IS NULL OR o.tenant_id = $tenant_id)\n" \
                    "  AND ($team_id IS NULL OR o.team_id = $team_id)\n" \
                    "  AND ($project_id IS NULL OR o.project_id = $project_id)"
            query = f"""
            MATCH (o:Outcome)
            {where}
            RETURN o.id as id, o.status as status, o.evidence as evidence,
                   o.measured_at as measured_at, o.performance_impact as performance_impact,
                   o.reliability as reliability, o.maintenance_cost as maintenance_cost
            ORDER BY o.measured_at DESC
            LIMIT $limit
            """
            result = self.graph.query(query, {
                "status": status,
                "limit": int(limit),
                "tenant_id": self._namespace["tenant_id"],
                "team_id": self._namespace["team_id"],
                "project_id": self._namespace["project_id"],
            })
            rows = result.result_set if hasattr(result, "result_set") else result
            items = []
            for row in rows or []:
                items.append(
                    {
                        "id": row[0],
                        "status": row[1],
                        "evidence": row[2],
                        "measured_at": row[3],
                        "performance_impact": row[4],
                        "reliability": row[5],
                        "maintenance_cost": row[6],
                    }
                )
            return items
        except Exception as e:
            logger.error(f"Failed to list outcomes: {e}")
            return []

    def get_antipattern(self, pattern_id: str) -> Optional[Dict[str, Any]]:
        """Get antipattern by id."""
        if not self.connected:
            logger.error("Not connected to graph")
            return None
        try:
            query = """
            MATCH (ap:AntiPattern {id: $id})
            WHERE ($tenant_id IS NULL OR ap.tenant_id = $tenant_id)
              AND ($team_id IS NULL OR ap.team_id = $team_id)
              AND ($project_id IS NULL OR ap.project_id = $project_id)
            RETURN ap.id as id, ap.name as name, ap.category as category,
                   ap.severity as severity, ap.removal_rate as removal_rate,
                   ap.avg_days_to_removal as avg_days_to_removal,
                   ap.recommendation as recommendation
            LIMIT 1
            """
            result = self.graph.query(query, {
                "id": pattern_id,
                "tenant_id": self._namespace["tenant_id"],
                "team_id": self._namespace["team_id"],
                "project_id": self._namespace["project_id"],
            })
            rows = result.result_set if hasattr(result, "result_set") else result
            if rows:
                row = rows[0]
                return {
                    "id": row[0],
                    "name": row[1],
                    "category": row[2],
                    "severity": row[3],
                    "removal_rate": row[4],
                    "avg_days_to_removal": row[5],
                    "recommendation": row[6],
                }
            return None
        except Exception as e:
            logger.error(f"Failed to get antipattern: {e}")
            return None

    def list_antipatterns(self, limit: int = 20, category: Optional[str] = None) -> List[Dict[str, Any]]:
        """List antipatterns with optional category filter."""
        if not self.connected:
            logger.error("Not connected to graph")
            return []
        try:
            query = """
            MATCH (ap:AntiPattern)
            WHERE ($category IS NULL OR ap.category = $category)
              AND ($tenant_id IS NULL OR ap.tenant_id = $tenant_id)
              AND ($team_id IS NULL OR ap.team_id = $team_id)
              AND ($project_id IS NULL OR ap.project_id = $project_id)
            RETURN ap.id as id, ap.name as name, ap.category as category,
                   ap.severity as severity, ap.removal_rate as removal_rate,
                   ap.avg_days_to_removal as avg_days_to_removal,
                   ap.recommendation as recommendation
            ORDER BY ap.removal_rate DESC
            LIMIT $limit
            """
            result = self.graph.query(query, {
                "category": category,
                "limit": int(limit),
                "tenant_id": self._namespace["tenant_id"],
                "team_id": self._namespace["team_id"],
                "project_id": self._namespace["project_id"],
            })
            rows = result.result_set if hasattr(result, "result_set") else result
            items = []
            for row in rows or []:
                items.append(
                    {
                        "id": row[0],
                        "name": row[1],
                        "category": row[2],
                        "severity": row[3],
                        "removal_rate": row[4],
                        "avg_days_to_removal": row[5],
                        "recommendation": row[6],
                    }
                )
            return items
        except Exception as e:
            logger.error(f"Failed to list antipatterns: {e}")
            return []

    def link_engram_session_context(self, session_id: str) -> bool:
        """Link Engram to SessionContext by session_id."""
        if not self.connected:
            logger.error("Not connected to graph")
            return False
        try:
            query = """
            MATCH (e:Engram {session_id: $session_id})
            MATCH (sc:SessionContext {session_id: $session_id})
            WHERE ($tenant_id IS NULL OR sc.tenant_id = $tenant_id)
              AND ($team_id IS NULL OR sc.team_id = $team_id)
              AND ($project_id IS NULL OR sc.project_id = $project_id)
            MERGE (e)-[:HAS_CONTEXT]->(sc)
            RETURN COUNT(sc) as count
            """
            self.graph.query(query, {
                "session_id": session_id,
                "tenant_id": self._namespace["tenant_id"],
                "team_id": self._namespace["team_id"],
                "project_id": self._namespace["project_id"],
            })
            return True
        except Exception as e:
            logger.error(f"Failed to link Engram to SessionContext: {e}")
            return False

    def deactivate_expired_session_context(self, now_ts: int) -> int:
        """Deactivate SessionContext records whose TTL has expired."""
        if not self.connected:
            logger.error("Not connected to graph")
            return 0
        try:
            query = """
            MATCH (sc:SessionContext)
            WHERE (sc.is_active IS NULL OR sc.is_active = true)
              AND sc.expires_at IS NOT NULL
              AND sc.expires_at < $now
            SET sc.is_active = false
            RETURN COUNT(sc) as count
            """
            result = self.graph.query(query, {"now": now_ts})
            if result and result[0].get("count") is not None:
                return int(result[0]["count"])
            return 0
        except Exception as e:
            logger.error(f"Failed to deactivate expired session contexts: {e}")
            return 0

        if not docs:
            return True

        try:
            query = """
            MATCH (d:Decision {id: $decision_id})
            MERGE (ds:DocShot {id: $doc_shot_id})
              ON CREATE SET ds.created_at = $created_at
            SET ds.doc_count = $doc_count
            WITH d, ds
            MERGE (d)-[r:USES_DOCSHOT]->(ds)
            SET r.fetched_at = $fetched_at,
                r.doc_count = $doc_count,
                r.doc_shot_id = $doc_shot_id
            WITH d, ds
            UNWIND $docs AS doc
            MATCH (docNode:Document {id: doc.id})
            MERGE (ds)-[:INCLUDES]->(docNode)
            MERGE (d)-[rel:DOCUMENTS {doc_shot_id: $doc_shot_id, doc_id: doc.id}]->(docNode)
            SET rel.doc_updated_at = doc.updated_at,
                rel.fetched_at = $fetched_at
            RETURN COUNT(docNode) as count
            """
            now_ts = int(__import__("time").time())
            params = {
                "decision_id": decision_id,
                "doc_shot_id": doc_shot_id or "docshot_unknown",
                "docs": docs,
                "doc_count": len(docs),
                "fetched_at": fetched_at,
                "created_at": now_ts,
            }
            self.graph.query(query, params)
            return True
        except Exception as e:
            logger.error(f"Failed to link decision docs: {e}")
            return False

    def deactivate_expired_decisions(self, now_ts: int) -> int:
        """Deactivate decisions whose TTL has expired."""
        if not self.connected:
            logger.error("Not connected to graph")
            return 0

        try:
            query = """
            MATCH (d:Decision)
            WHERE (d.is_active IS NULL OR d.is_active = true)
              AND d.ttl_days IS NOT NULL
              AND d.created_at IS NOT NULL
              AND (d.created_at + d.ttl_days * 86400) < $now
            SET d.is_active = false,
                d.deprecated_reason = "ttl_expired"
            RETURN COUNT(d) as count
            """
            result = self.graph.query(query, {"now": now_ts})
            if result and result[0].get("count") is not None:
                return int(result[0]["count"])
            return 0
        except Exception as e:
            logger.error(f"Failed to deactivate expired decisions: {e}")
            return 0

    def deactivate_expired_negative_knowledge(self, now_ts: int) -> int:
        """Deactivate negative knowledge whose TTL has expired."""
        if not self.connected:
            logger.error("Not connected to graph")
            return 0

        try:
            query = """
            MATCH (nk:NegativeKnowledge)
            WHERE (nk.is_active IS NULL OR nk.is_active = true)
              AND nk.ttl_days IS NOT NULL
              AND nk.last_verified_at IS NOT NULL
              AND (nk.last_verified_at + nk.ttl_days * 86400) < $now
            SET nk.is_active = false,
                nk.deprecated_reason = "ttl_expired"
            RETURN COUNT(nk) as count
            """
            result = self.graph.query(query, {"now": now_ts})
            if result and result.result_set and len(result.result_set) > 0:
                row = result.result_set[0]
                if row and len(row) > 0:
                    count = row[0]
                    if count is not None:
                        return int(count)
            return 0
        except Exception as e:
            logger.error(f"Failed to deactivate expired negative knowledge: {e}")
            return 0

    def deactivate_expired_outcomes(self, now_ts: int) -> int:
        """Deactivate outcomes whose TTL has expired."""
        if not self.connected:
            logger.error("Not connected to graph")
            return 0

        try:
            query = """
            MATCH (o:Outcome)
            WHERE (o.is_active IS NULL OR o.is_active = true)
              AND o.ttl_days IS NOT NULL
              AND o.measured_at IS NOT NULL
              AND (o.measured_at + o.ttl_days * 86400) < $now
            SET o.is_active = false,
                o.deprecated_reason = "ttl_expired"
            RETURN COUNT(o) as count
            """
            result = self.graph.query(query, {"now": now_ts})
            if result and result[0].get("count") is not None:
                return int(result[0]["count"])
            return 0
        except Exception as e:
            logger.error(f"Failed to deactivate expired outcomes: {e}")
            return 0

    def deactivate_expired_skills(self, now_ts: int) -> int:
        """Deactivate skills whose TTL has expired."""
        if not self.connected:
            logger.error("Not connected to graph")
            return 0

        try:
            query = """
            MATCH (s:Skill)
            WHERE (s.is_active IS NULL OR s.is_active = true)
              AND s.ttl_days IS NOT NULL
              AND s.last_updated IS NOT NULL
              AND (s.last_updated + s.ttl_days * 86400) < $now
            SET s.is_active = false
            RETURN COUNT(s) as count
            """
            result = self.graph.query(query, {"now": now_ts})
            if result and result[0].get("count") is not None:
                return int(result[0]["count"])
            return 0
        except Exception as e:
            logger.error(f"Failed to deactivate expired skills: {e}")
            return 0

        try:
            query = """
            MATCH (nk:NegativeKnowledge)
            WHERE (nk.is_active IS NULL OR nk.is_active = true)
              AND nk.ttl_days IS NOT NULL
              AND nk.discovered_at IS NOT NULL
              AND (nk.discovered_at + nk.ttl_days * 86400) < $now
            SET nk.is_active = false,
                nk.deprecated_reason = "ttl_expired"
            RETURN COUNT(nk) as count
            """
            result = self.graph.query(query, {"now": now_ts})
            if result and result[0].get("count") is not None:
                return int(result[0]["count"])
            return 0
        except Exception as e:
            logger.error(f"Failed to deactivate expired negative knowledge: {e}")
            return 0

    def create_relationship(
        self,
        from_node_id: str,
        from_label: str,
        to_node_id: str,
        to_label: str,
        rel_type: str,
        properties: Optional[Dict[str, Any]] = None,
    ) -> bool:
        """Create a relationship between two nodes."""
        if not self.connected:
            logger.error("Not connected to graph")
            return False

        try:
            properties = properties or {}
            
            query = f"""
            MATCH (from:{from_label} {{id: $from_id}}),
                  (to:{to_label} {{id: $to_id}})
            CREATE (from)-[r:{rel_type} $props]->(to)
            RETURN r
            """
            
            params = {
                "from_id": escape_string(from_node_id),
                "to_id": escape_string(to_node_id),
                "props": properties
            }
            
            self.graph.query(query, params)
            logger.info(f"Created {rel_type} relationship {from_node_id} -> {to_node_id}")
            return True
        except Exception as e:
            logger.error(f"Failed to create relationship: {e}")
            return False

    def query(self, cypher: str, params: Optional[Dict[str, Any]] = None) -> List[Dict[str, Any]]:
        """Execute a Cypher query."""
        if not self.connected:
            # Auto-connect if not connected
            if not self.connect():
                raise RuntimeError("Not connected to graph")

        try:
            result = self.graph.query(cypher, params or {})
            # FalkorDB returns results differently than Neo4j
            return result.result_set if hasattr(result, 'result_set') else []
        except Exception as e:
            logger.error(f"Query execution failed: {e}")
            raise

    # Analytics methods - success rates
    def success_rate_by_module(self) -> List[Dict[str, Any]]:
        """Get success rate of decisions by module."""
        from membria.graph_queries import GraphQueries
        return self.query(GraphQueries.success_rate_by_module())

    def success_rate_by_confidence_bucket(self) -> List[Dict[str, Any]]:
        """Get calibration data: confidence vs actual success rate."""
        from membria.graph_queries import GraphQueries
        return self.query(GraphQueries.success_rate_by_confidence_bucket())

    # Rework detection methods
    def decisions_by_rework_count(self) -> List[Dict[str, Any]]:
        """Get decisions with most reworks."""
        from membria.graph_queries import GraphQueries
        return self.query(GraphQueries.decisions_by_rework_count())

    def low_confidence_decisions_rework_rate(self) -> List[Dict[str, Any]]:
        """Get rework rate for low confidence decisions (0.6-0.7)."""
        from membria.graph_queries import GraphQueries
        return self.query(GraphQueries.low_confidence_decisions_rework_rate())

    # Negative knowledge methods
    def negative_knowledge_prevention_value(self) -> List[Dict[str, Any]]:
        """Get how many decisions were prevented by negative knowledge."""
        from membria.graph_queries import GraphQueries
        return self.query(GraphQueries.negative_knowledge_prevention_value())

    def learned_failures_by_domain(self) -> List[Dict[str, Any]]:
        """Get what we learned not to do, by domain."""
        from membria.graph_queries import GraphQueries
        return self.query(GraphQueries.learned_failures_by_domain())

    # Antipattern methods
    def antipatterns_by_removal_rate(self) -> List[Dict[str, Any]]:
        """Get most problematic antipatterns by removal rate."""
        from membria.graph_queries import GraphQueries
        return self.query(GraphQueries.antipatterns_by_removal_rate())

    def antipatterns_triggered_in_commits(self) -> List[Dict[str, Any]]:
        """Get antipatterns triggered most in commits."""
        from membria.graph_queries import GraphQueries
        return self.query(GraphQueries.antipatterns_triggered_in_commits())

    # Decision correlation methods
    def decision_to_outcome_flow(self) -> List[Dict[str, Any]]:
        """Trace decision → implementation → outcome."""
        from membria.graph_queries import GraphQueries
        return self.query(GraphQueries.decision_to_outcome_flow())

    def decision_rework_timeline(self) -> List[Dict[str, Any]]:
        """Get timeline of when decisions get reworked."""
        from membria.graph_queries import GraphQueries
        return self.query(GraphQueries.decision_rework_timeline())

    # Session methods
    def decisions_per_session(self) -> List[Dict[str, Any]]:
        """Get how many decisions extracted per session."""
        from membria.graph_queries import GraphQueries
        return self.query(GraphQueries.decisions_per_session())

    def high_risk_sessions(self) -> List[Dict[str, Any]]:
        """Get sessions where many decisions later failed."""
        from membria.graph_queries import GraphQueries
        return self.query(GraphQueries.high_risk_sessions())

    # Trend methods
    def success_rate_over_time(self) -> List[Dict[str, Any]]:
        """Get success rate trend over time (7 day windows)."""
        from membria.graph_queries import GraphQueries
        return self.query(GraphQueries.success_rate_over_time())

    def confidence_trend(self) -> List[Dict[str, Any]]:
        """Get average confidence trend over time."""
        from membria.graph_queries import GraphQueries
        return self.query(GraphQueries.confidence_trend())

    # Similarity methods
    def similar_decisions_with_outcomes(self) -> List[Dict[str, Any]]:
        """Find similar past decisions and their outcomes."""
        from membria.graph_queries import GraphQueries
        return self.query(GraphQueries.similar_decisions_with_outcomes())

    # Data quality methods
    def decisions_without_outcome(self) -> List[Dict[str, Any]]:
        """Get decisions still pending (no outcome recorded)."""
        from membria.graph_queries import GraphQueries
        return self.query(GraphQueries.decisions_without_outcome())

    def graph_statistics(self) -> List[Dict[str, Any]]:
        """Get overall graph statistics."""
        from membria.graph_queries import GraphQueries
        return self.query(GraphQueries.graph_statistics())

    def get_decisions(self, limit: int = 10, module: Optional[str] = None) -> List[Dict[str, Any]]:
        """Get recent decisions from graph."""
        if not self.connected:
            return []

        try:
            if module:
                query = "MATCH (d:Decision {module: $module}) RETURN d ORDER BY d.created_at DESC LIMIT $limit"
                params = {"module": module, "limit": limit}
            else:
                query = "MATCH (d:Decision) RETURN d ORDER BY d.created_at DESC LIMIT $limit"
                params = {"limit": limit}

            result = self.graph.query(query, params)
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
            query = """
            MATCH (d:Decision)
            WHERE d.statement CONTAINS $topic
            RETURN d
            ORDER BY d.created_at DESC
            LIMIT $limit
            """
            result = self.graph.query(query, {"topic": topic, "limit": limit})
            return result.result_set if hasattr(result, 'result_set') else []
        except Exception as e:
            logger.error(f"Failed to get similar decisions: {e}")
            return []
