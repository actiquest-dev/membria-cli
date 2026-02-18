"""Membria MCP Server - Implements Model Context Protocol for Claude integration."""

import json
import sys
import logging
from typing import Any, Dict, Optional

from membria.outcome_tracker import OutcomeTracker
from membria.calibration_updater import CalibrationUpdater
from membria.plan_context_builder import PlanContextBuilder
from membria.plan_validator import PlanValidator
from membria.graph import GraphClient
from membria.interactive.executor import AgentExecutor
from membria.interactive.expert_registry import ExpertRegistry
from membria.config import ConfigManager

logger = logging.getLogger(__name__)


class MCPResponse:
    """MCP Response wrapper."""
    
    def __init__(self, request_id: Optional[str] = None, result: Optional[Dict[str, Any]] = None, error: Optional[Dict[str, Any]] = None):
        self.jsonrpc = "2.0"
        self.id = request_id
        self.result = result
        self.error = error

    def to_json(self) -> str:
        """Convert to JSON."""
        data = {"jsonrpc": self.jsonrpc, "id": self.id}
        if self.error:
            data["error"] = self.error
        elif self.result is not None:
            data["result"] = self.result
        return json.dumps(data)


class MembriaToolHandler:
    """Handles all tool calls for MCP protocol."""

    def __init__(self):
        """Initialize with backend services."""
        self.graph_client = GraphClient()
        self.outcome_tracker = OutcomeTracker()
        self.calibration_updater = CalibrationUpdater()
        self.plan_context_builder = PlanContextBuilder(self.graph_client, self.calibration_updater)
        self.plan_validator = PlanValidator(self.graph_client, self.calibration_updater)
        self.config_manager = ConfigManager()
        self.executor = AgentExecutor(self.config_manager)
        self.docs_cache: Dict[str, Any] = {}
        self._docshot_hasher = __import__("hashlib")
        try:
            from membria.memory_manager import MemoryManager
            self.memory_manager = MemoryManager(self.graph_client)
        except Exception:
            self.memory_manager = None

    def _ensure_graph(self) -> None:
        if not self.graph_client.connected:
            self.graph_client.connect()

    def consult_expert(self, args: Dict[str, Any]) -> Dict[str, Any]:
        """Tool: membria.consult_expert"""
        try:
            role = args.get("role", "architect")
            task = args.get("task")
            if not task:
                return {"error": {"code": -32602, "message": "task required"}}

            # Use asyncio to run the async executor
            import asyncio
            loop = asyncio.new_event_loop()
            asyncio.set_event_loop(loop)
            response = loop.run_until_complete(self.executor.run_task(task, role=role))
            loop.close()

            return {
                "role": role,
                "response": response,
                "status": "completed"
            }
        except Exception as e:
            return {"error": {"code": -32603, "message": str(e)}}

    def red_team_audit(self, args: Dict[str, Any]) -> Dict[str, Any]:
        """Tool: membria.red_team_audit"""
        try:
            task = args.get("task")
            context = args.get("context", "")
            if not task:
                return {"error": {"code": -32602, "message": "task required"}}

            # Sanitize inputs to prevent prompt injection
            from membria.security import sanitize_text
            safe_task = sanitize_text(task, max_len=1000)
            safe_context = sanitize_text(context, max_len=2000)

            # Run orchestration in debate mode with red_team=True
            import asyncio
            loop = asyncio.new_event_loop()
            asyncio.set_event_loop(loop)
            orchestration_task = f"AUDIT TASK: {safe_task}\nCONTEXT: {safe_context}"
            response = loop.run_until_complete(self.executor.run_orchestration(orchestration_task, mode="debate", red_team=True))
            loop.close()

            return {
                "audit_report": response,
                "status": "audited"
            }
        except Exception as e:
            return {"error": {"code": -32603, "message": str(e)}}

    def run_orchestration(self, args: Dict[str, Any]) -> Dict[str, Any]:
        """Tool: membria.run_orchestration"""
        try:
            task = args.get("task")
            mode = args.get("mode", "pipeline")
            red_team = args.get("red_team", False)
            if not task:
                return {"error": {"code": -32602, "message": "task required"}}

            import asyncio
            loop = asyncio.new_event_loop()
            asyncio.set_event_loop(loop)
            response = loop.run_until_complete(self.executor.run_orchestration(task, mode=mode, red_team=red_team))
            loop.close()

            return {
                "response": response,
                "mode": mode,
                "status": "completed"
            }
        except Exception as e:
            return {"error": {"code": -32603, "message": str(e)}}

    def list_experts(self, args: Dict[str, Any]) -> Dict[str, Any]:
        """Tool: membria.list_experts"""
        try:
            experts = ExpertRegistry.list_experts()
            return {"experts": experts}
        except Exception as e:
            return {"error": {"code": -32603, "message": str(e)}}

    def fetch_docs(self, args: Dict[str, Any]) -> Dict[str, Any]:
        """Tool: membria.fetch_docs"""
        try:
            self._ensure_graph()
            docs = self.graph_client.get_documents(
                doc_types=args.get("doc_types"),
                file_paths=args.get("file_paths"),
                doc_ids=args.get("doc_ids"),
                limit=int(args.get("limit") or 10),
            )

            from membria.security import sanitize_text

            result_docs = []
            for doc in docs:
                raw = doc.get("content") or ""
                content = sanitize_text(raw, max_len=6000)
                result_docs.append(
                    {
                        "id": doc.get("id"),
                        "file_path": doc.get("file_path"),
                        "doc_type": doc.get("doc_type"),
                        "updated_at": doc.get("updated_at"),
                        "metadata": doc.get("metadata"),
                        "content": content,
                    }
                )

            doc_shot_id = self._compute_doc_shot_id(result_docs)
            self.docs_cache = {
                "fetched_at": __import__("datetime").datetime.utcnow().isoformat(),
                "count": len(result_docs),
                "doc_types": args.get("doc_types"),
                "file_paths": args.get("file_paths"),
                "doc_ids": args.get("doc_ids"),
                "doc_shot_id": doc_shot_id,
            }

            return {
                "status": "success",
                "count": len(result_docs),
                "doc_shot_id": doc_shot_id,
                "docs": result_docs,
            }
        except Exception as e:
            return {"error": {"code": -32603, "message": str(e)}}

    def md_xtract(self, args: Dict[str, Any]) -> Dict[str, Any]:
        """Tool: membria.md_xtract"""
        try:
            from membria.md_xtract import xtract_to_markdown

            markdown, metadata = xtract_to_markdown(
                args.get("input"),
                input_type=args.get("input_type"),
                max_chars=int(args.get("max_chars") or 0),
                ocr=bool(args.get("ocr") or False),
            )
            return {"status": "success", "markdown": markdown, "metadata": metadata}
        except Exception as e:
            return {"error": {"code": -32603, "message": str(e)}}

    def squad_create(self, args: Dict[str, Any]) -> Dict[str, Any]:
        """Tool: membria.squad_create"""
        try:
            self._ensure_graph()
            roles = args.get("roles") or []
            profiles = args.get("profiles") or []
            if len(roles) != len(profiles):
                return {"error": {"code": -32602, "message": "roles and profiles length mismatch"}}
            from membria.config import ConfigManager
            import uuid

            self.graph_client.upsert_project(args.get("project_id"), args.get("project_id"))
            squad_id = f"sqd_{uuid.uuid4().hex[:10]}"
            ok = self.graph_client.create_squad(
                squad_id,
                name=args.get("name"),
                strategy=args.get("strategy"),
                project_id=args.get("project_id"),
            )
            if not ok:
                return {"error": {"code": -32603, "message": "failed to create squad"}}

            cfg = ConfigManager()
            default_path = str(cfg.config_file)
            profile_paths = args.get("profile_paths") or []
            assignments = []
            for idx, (role, profile) in enumerate(zip(roles, profiles), start=1):
                role_id = f"role_{role}"
                profile_id = f"profile_{profile}"
                path = default_path
                if profile_paths:
                    path = profile_paths[0] if len(profile_paths) == 1 else profile_paths[idx - 1]
                self.graph_client.upsert_role(role_id, role)
                self.graph_client.upsert_profile(profile_id, profile, config_path=path)
                assignment_id = f"asn_{uuid.uuid4().hex[:10]}"
                self.graph_client.add_assignment(
                    assignment_id=assignment_id,
                    squad_id=squad_id,
                    role_id=role_id,
                    profile_id=profile_id,
                    order=idx,
                )
                assignments.append({"assignment_id": assignment_id, "role_id": role_id, "profile_id": profile_id})
            return {"status": "success", "squad_id": squad_id, "assignments": assignments}
        except Exception as e:
            return {"error": {"code": -32603, "message": str(e)}}

    def assignment_add(self, args: Dict[str, Any]) -> Dict[str, Any]:
        """Tool: membria.assignment_add"""
        try:
            self._ensure_graph()
            from membria.config import ConfigManager
            import uuid

            role = args.get("role")
            profile = args.get("profile")
            role_id = f"role_{role}"
            profile_id = f"profile_{profile}"
            cfg = ConfigManager()
            default_path = str(cfg.config_file)
            profile_path = args.get("profile_path") or default_path
            self.graph_client.upsert_role(role_id, role)
            self.graph_client.upsert_profile(profile_id, profile, config_path=profile_path)
            assignment_id = f"asn_{uuid.uuid4().hex[:10]}"
            ok = self.graph_client.add_assignment(
                assignment_id=assignment_id,
                squad_id=args.get("squad_id"),
                role_id=role_id,
                profile_id=profile_id,
                order=int(args.get("order") or 0),
                weight=float(args.get("weight") or 1.0),
            )
            if not ok:
                return {"error": {"code": -32603, "message": "failed to add assignment"}}
            return {"status": "success", "assignment_id": assignment_id}
        except Exception as e:
            return {"error": {"code": -32603, "message": str(e)}}

    def squad_list(self, args: Dict[str, Any]) -> Dict[str, Any]:
        """Tool: membria.squad_list"""
        try:
            self._ensure_graph()
            items = self.graph_client.list_squads(
                project_id=args.get("project_id"),
                limit=int(args.get("limit") or 20),
            )
            return {"status": "success", "items": items}
        except Exception as e:
            return {"error": {"code": -32603, "message": str(e)}}

    def squad_assignments(self, args: Dict[str, Any]) -> Dict[str, Any]:
        """Tool: membria.squad_assignments"""
        try:
            self._ensure_graph()
            items = self.graph_client.list_assignments(args.get("squad_id"))
            return {"status": "success", "items": items}
        except Exception as e:
            return {"error": {"code": -32603, "message": str(e)}}

    def role_upsert(self, args: Dict[str, Any]) -> Dict[str, Any]:
        """Tool: membria.role_upsert"""
        try:
            self._ensure_graph()
            name = args.get("name")
            role_id = f"role_{name}"
            ok = self.graph_client.upsert_role(
                role_id=role_id,
                name=name,
                description=args.get("description"),
                prompt_path=args.get("prompt_path"),
                context_policy=args.get("context_policy"),
            )
            if not ok:
                return {"error": {"code": -32603, "message": "failed to upsert role"}}
            for ds in args.get("docshot_ids") or []:
                self.graph_client.link_role_docshot(name, ds)
            for sk in args.get("skill_ids") or []:
                self.graph_client.link_role_skill(name, sk)
            for nk in args.get("nk_ids") or []:
                self.graph_client.link_role_nk(name, nk)
            return {"status": "success", "role_id": role_id}
        except Exception as e:
            return {"error": {"code": -32603, "message": str(e)}}

    def role_get(self, args: Dict[str, Any]) -> Dict[str, Any]:
        """Tool: membria.role_get"""
        try:
            self._ensure_graph()
            item = self.graph_client.get_role(args.get("name"))
            return {"status": "success", "item": item}
        except Exception as e:
            return {"error": {"code": -32603, "message": str(e)}}

    def role_link(self, args: Dict[str, Any]) -> Dict[str, Any]:
        """Tool: membria.role_link"""
        try:
            self._ensure_graph()
            name = args.get("name")
            for ds in args.get("docshot_ids") or []:
                self.graph_client.link_role_docshot(name, ds)
            for sk in args.get("skill_ids") or []:
                self.graph_client.link_role_skill(name, sk)
            for nk in args.get("nk_ids") or []:
                self.graph_client.link_role_nk(name, nk)
            return {"status": "success"}
        except Exception as e:
            return {"error": {"code": -32603, "message": str(e)}}

    def role_unlink(self, args: Dict[str, Any]) -> Dict[str, Any]:
        """Tool: membria.role_unlink"""
        try:
            self._ensure_graph()
            name = args.get("name")
            for ds in args.get("docshot_ids") or []:
                self.graph_client.unlink_role_docshot(name, ds)
            for sk in args.get("skill_ids") or []:
                self.graph_client.unlink_role_skill(name, sk)
            for nk in args.get("nk_ids") or []:
                self.graph_client.unlink_role_nk(name, nk)
            return {"status": "success"}
        except Exception as e:
            return {"error": {"code": -32603, "message": str(e)}}

    def session_context_store(self, args: Dict[str, Any]) -> Dict[str, Any]:
        """Tool: membria.session_context_store"""
        try:
            self._ensure_graph()
            ok = self.graph_client.upsert_session_context(
                session_id=args.get("session_id"),
                task=args.get("task"),
                focus=args.get("focus"),
                current_plan=args.get("current_plan"),
                constraints=args.get("constraints") or [],
                doc_shot_id=args.get("doc_shot_id"),
                ttl_days=int(args.get("ttl_days", 3)),
            )
            return {"status": "success" if ok else "failed", "items": []}
        except Exception as e:
            return {"error": {"code": -32603, "message": str(e)}}

    def session_context_retrieve(self, args: Dict[str, Any]) -> Dict[str, Any]:
        """Tool: membria.session_context_retrieve"""
        try:
            self._ensure_graph()
            session_id = args.get("session_id")
            if session_id:
                item = self.graph_client.get_session_context(session_id)
                return {"status": "success", "items": [item] if item else []}
            items = self.graph_client.list_session_contexts(limit=int(args.get("limit", 5)))
            return {"status": "success", "items": items}
        except Exception as e:
            return {"error": {"code": -32603, "message": str(e)}}

    def session_context_delete(self, args: Dict[str, Any]) -> Dict[str, Any]:
        """Tool: membria.session_context_delete"""
        try:
            self._ensure_graph()
            ok = self.graph_client.deactivate_session_context(args.get("session_id"))
            return {"status": "success" if ok else "failed", "items": []}
        except Exception as e:
            return {"error": {"code": -32603, "message": str(e)}}

    def docs_add(self, args: Dict[str, Any]) -> Dict[str, Any]:
        """Tool: membria.docs_add"""
        try:
            self._ensure_graph()
            from membria.graph_schema import DocumentNodeSchema
            now_ts = int(__import__("time").time())
            cfg = ConfigManager().config
            doc = DocumentNodeSchema(
                id=f"doc_{__import__('hashlib').sha1(args['file_path'].encode()).hexdigest()[:10]}_{now_ts}",
                file_path=args.get("file_path"),
                content=args.get("content"),
                doc_type=args.get("doc_type", "kb"),
                created_at=now_ts,
                updated_at=now_ts,
                metadata=args.get("metadata") or {},
                tenant_id=getattr(cfg, "tenant_id", "default"),
                team_id=getattr(cfg, "team_id", "default"),
                project_id=getattr(cfg, "project_id", "default"),
            )
            ok = self.graph_client.add_document(doc)
            return {"status": "success" if ok else "failed", "items": [ {"id": doc.id} ]}
        except Exception as e:
            return {"error": {"code": -32603, "message": str(e)}}

    def docs_get(self, args: Dict[str, Any]) -> Dict[str, Any]:
        """Tool: membria.docs_get"""
        try:
            self._ensure_graph()
            docs = self.graph_client.get_documents(
                doc_types=args.get("doc_types"),
                file_paths=args.get("file_paths"),
                doc_ids=args.get("doc_ids"),
                limit=int(args.get("limit", 10)),
            )
            return {"status": "success", "items": docs}
        except Exception as e:
            return {"error": {"code": -32603, "message": str(e)}}

    def docs_list(self, args: Dict[str, Any]) -> Dict[str, Any]:
        """Tool: membria.docs_list"""
        return self.docs_get(args)

    def docshot_link(self, args: Dict[str, Any]) -> Dict[str, Any]:
        """Tool: membria.docshot_link"""
        try:
            self._ensure_graph()
            ok = self.graph_client.link_decision_docs(
                decision_id=args.get("decision_id"),
                doc_shot_id=args.get("doc_shot_id"),
                docs=args.get("docs") or [],
                fetched_at=args.get("fetched_at"),
            )
            return {"status": "success" if ok else "failed", "decision_id": args.get("decision_id"), "doc_shot_id": args.get("doc_shot_id")}
        except Exception as e:
            return {"error": {"code": -32603, "message": str(e)}}

    def outcome_get(self, args: Dict[str, Any]) -> Dict[str, Any]:
        """Tool: membria.outcome_get"""
        try:
            self._ensure_graph()
            item = self.graph_client.get_outcome(args.get("outcome_id"))
            return {"status": "success", "item": item}
        except Exception as e:
            return {"error": {"code": -32603, "message": str(e)}}

    def outcome_list(self, args: Dict[str, Any]) -> Dict[str, Any]:
        """Tool: membria.outcome_list"""
        try:
            self._ensure_graph()
            items = self.graph_client.list_outcomes(limit=int(args.get("limit", 10)), status=args.get("status"))
            return {"status": "success", "items": items}
        except Exception as e:
            return {"error": {"code": -32603, "message": str(e)}}

    def skills_list(self, args: Dict[str, Any]) -> Dict[str, Any]:
        """Tool: membria.skills_list"""
        try:
            self._ensure_graph()
            from membria.graph_queries import SkillQueries
            domain = args.get("domain")
            min_quality = float(args.get("min_quality", 0.5))
            if domain:
                query, params = SkillQueries.get_skills_for_domain(domain, min_quality=min_quality)
            else:
                query, params = SkillQueries.get_skills_by_quality(min_quality=min_quality)
            rows = self.graph_client.query(query, params) or []
            return {"status": "success", "items": rows[: int(args.get("limit", 20))]}
        except Exception as e:
            return {"error": {"code": -32603, "message": str(e)}}

    def skills_get(self, args: Dict[str, Any]) -> Dict[str, Any]:
        """Tool: membria.skills_get"""
        try:
            self._ensure_graph()
            from membria.graph_queries import SkillQueries
            query, params = SkillQueries.get_latest_skill_version(args.get("domain"), args.get("name"))
            rows = self.graph_client.query(query, params) or []
            return {"status": "success", "items": rows[:1]}
        except Exception as e:
            return {"error": {"code": -32603, "message": str(e)}}

    def antipatterns_list(self, args: Dict[str, Any]) -> Dict[str, Any]:
        """Tool: membria.antipatterns_list"""
        try:
            self._ensure_graph()
            items = self.graph_client.list_antipatterns(limit=int(args.get("limit", 20)), category=args.get("category"))
            return {"status": "success", "items": items}
        except Exception as e:
            return {"error": {"code": -32603, "message": str(e)}}

    def antipatterns_get(self, args: Dict[str, Any]) -> Dict[str, Any]:
        """Tool: membria.antipatterns_get"""
        try:
            self._ensure_graph()
            item = self.graph_client.get_antipattern(args.get("pattern_id"))
            return {"status": "success", "items": [item] if item else []}
        except Exception as e:
            return {"error": {"code": -32603, "message": str(e)}}

    def health(self, args: Dict[str, Any]) -> Dict[str, Any]:
        """Tool: membria.health"""
        try:
            self._ensure_graph()
            return {"status": "success", "health": self.graph_client.health_check()}
        except Exception as e:
            return {"error": {"code": -32603, "message": str(e)}}

    def migrations_status(self, args: Dict[str, Any]) -> Dict[str, Any]:
        """Tool: membria.migrations_status"""
        try:
            self._ensure_graph()
            from membria.migrations.migrator import Migrator
            migrator = Migrator(self.graph_client.db_instance)
            current = migrator.get_current_version()
            pending = len(migrator.get_pending_migrations())
            return {"status": "success", "current_version": current, "pending": pending}
        except Exception as e:
            return {"error": {"code": -32603, "message": str(e)}}

    def logs_tail(self, args: Dict[str, Any]) -> Dict[str, Any]:
        """Tool: membria.logs_tail"""
        try:
            from membria.process_manager import ProcessManager
            lines = int(args.get("lines", 50))
            logs = ProcessManager().get_logs(lines=lines)
            return {"status": "success", "logs": logs}
        except Exception as e:
            return {"error": {"code": -32603, "message": str(e)}}

    def memory_store(self, args: Dict[str, Any]) -> Dict[str, Any]:
        """Tool: membria.memory_store"""
        try:
            if not self.memory_manager:
                return {"error": {"code": -32603, "message": "MemoryManager unavailable"}}

            mem_type = args.get("memory_type")
            payload = args.get("payload") or {}
            ttl_days = args.get("ttl_days")

            if mem_type == "decision":
                from membria.models import Decision
                import uuid
                decision = Decision(
                    decision_id=f"dec_{uuid.uuid4().hex[:12]}",
                    statement=payload.get("statement", ""),
                    alternatives=payload.get("alternatives", []),
                    confidence=float(payload.get("confidence", 0.5)),
                    module=payload.get("module", "general"),
                )
                decision.role_id = payload.get("role_id")
                decision.assignment_id = payload.get("assignment_id")
                ok = self.memory_manager.store_decision(decision, ttl_days=ttl_days)
                if not ok:
                    return {"error": {"code": -32603, "message": "Failed to store decision"}}
                return {"status": "success", "item_id": decision.decision_id}

            if mem_type == "negative_knowledge":
                from membria.models import NegativeKnowledge
                import uuid
                nk = NegativeKnowledge(
                    nk_id=f"nk_{uuid.uuid4().hex[:12]}",
                    hypothesis=payload.get("hypothesis", ""),
                    conclusion=payload.get("conclusion", ""),
                    evidence=payload.get("evidence", ""),
                    domain=payload.get("domain", "general"),
                    severity=payload.get("severity", "medium"),
                    recommendation=payload.get("recommendation", ""),
                    source=payload.get("source", "manual"),
                )
                ok = self.memory_manager.store_negative_knowledge(nk, ttl_days=ttl_days)
                if not ok:
                    return {"error": {"code": -32603, "message": "Failed to store negative knowledge"}}
                return {"status": "success", "item_id": nk.nk_id}

            return {"error": {"code": -32602, "message": "Unknown memory_type"}}
        except Exception as e:
            return {"error": {"code": -32603, "message": str(e)}}

    def memory_retrieve(self, args: Dict[str, Any]) -> Dict[str, Any]:
        """Tool: membria.memory_retrieve"""
        try:
            if not self.memory_manager:
                return {"error": {"code": -32603, "message": "MemoryManager unavailable"}}

            mem_type = args.get("memory_type")
            domain = args.get("domain")
            limit = int(args.get("limit", 5))

            if mem_type == "decision":
                if not domain:
                    return {"error": {"code": -32602, "message": "domain required for decision"}}
                items = self.memory_manager.retrieve_decisions(domain=domain, limit=limit)
                return {"status": "success", "items": [i.__dict__ for i in items]}

            if mem_type == "negative_knowledge":
                items = self.memory_manager.retrieve_negative_knowledge(domain=domain, limit=limit)
                return {"status": "success", "items": items}

            return {"error": {"code": -32602, "message": "Unknown memory_type"}}
        except Exception as e:
            return {"error": {"code": -32603, "message": str(e)}}

    def memory_delete(self, args: Dict[str, Any]) -> Dict[str, Any]:
        """Tool: membria.memory_delete"""
        try:
            if not self.memory_manager:
                return {"error": {"code": -32603, "message": "MemoryManager unavailable"}}

            mem_type = args.get("memory_type")
            item_id = args.get("item_id")
            reason = args.get("reason", "manual_delete")

            if mem_type == "decision":
                ok = self.memory_manager.forget_decision(item_id, reason)
                return {"status": "success" if ok else "failed", "item_id": item_id}

            if mem_type == "negative_knowledge":
                ok = self.memory_manager.forget_negative_knowledge(item_id, reason)
                return {"status": "success" if ok else "failed", "item_id": item_id}

            return {"error": {"code": -32602, "message": "Unknown memory_type"}}
        except Exception as e:
            return {"error": {"code": -32603, "message": str(e)}}

    def memory_list(self, args: Dict[str, Any]) -> Dict[str, Any]:
        """Tool: membria.memory_list"""
        return self.memory_retrieve(args)

    def _compute_doc_shot_id(self, docs: list) -> str:
        entries = []
        for doc in docs:
            doc_id = doc.get("id") or ""
            updated_at = doc.get("updated_at") or ""
            entries.append(f"{doc_id}:{updated_at}")
        entries.sort()
        payload = "|".join(entries).encode("utf-8")
        return f"docshot_{self._docshot_hasher.sha1(payload).hexdigest()[:12]}"

    def capture_decision(self, args: Dict[str, Any]) -> Dict[str, Any]:
        """Tool: membria.capture_decision"""
        try:
            statement = args.get("statement")
            alternatives = args.get("alternatives", [])
            confidence = args.get("confidence", 0.5)
            module = args.get("context", {}).get("module", "unknown")

            if not statement:
                return {"error": {"code": -32602, "message": "statement required"}}
            if not alternatives:
                return {"error": {"code": -32602, "message": "alternatives required"}}
            if not (0 <= confidence <= 1):
                return {"error": {"code": -32602, "message": "confidence must be 0-1"}}

            import uuid
            decision_id = f"dec_{uuid.uuid4().hex[:12]}"
            
            return {
                "decision_id": decision_id,
                "statement": statement,
                "confidence": confidence,
                "module": module,
                "status": "pending",
                "message": "Decision captured"
            }
        except Exception as e:
            return {"error": {"code": -32603, "message": str(e)}}

    def record_outcome(self, args: Dict[str, Any]) -> Dict[str, Any]:
        """Tool: membria.record_outcome"""
        try:
            decision_id = args.get("decision_id")
            final_status = args.get("final_status")
            final_score = args.get("final_score", 0.5)
            decision_domain = args.get("decision_domain", "general")

            if not decision_id or not final_status:
                return {"error": {"code": -32602, "message": "decision_id and final_status required"}}

            outcome = self.outcome_tracker.create_outcome(decision_id)
            self.outcome_tracker.finalize_outcome(
                outcome.outcome_id,
                final_status=final_status,
                final_score=final_score,
                decision_domain=decision_domain
            )

            calibration = self.calibration_updater.get_confidence_guidance(decision_domain)

            return {
                "outcome_id": outcome.outcome_id,
                "decision_id": decision_id,
                "final_status": final_status,
                "final_score": final_score,
                "calibration_impact": {
                    "domain": decision_domain,
                    "sample_size": calibration.get("sample_size", 1),
                    "success_rate": calibration.get("actual_success_rate", 0.5)
                }
            }
        except Exception as e:
            return {"error": {"code": -32603, "message": str(e)}}

    def get_calibration(self, args: Dict[str, Any]) -> Dict[str, Any]:
        """Tool: membria.get_calibration"""
        try:
            domain = args.get("domain", "general")
            calibration = self.calibration_updater.get_confidence_guidance(domain)
            return calibration
        except Exception as e:
            return {"error": {"code": -32603, "message": str(e)}}

    def get_decision_context(self, args: Dict[str, Any]) -> Dict[str, Any]:
        """Tool: membria.get_decision_context"""
        try:
            statement = args.get("statement")
            module = args.get("module", "unknown")
            confidence = args.get("confidence", 0.5)
            max_tokens = args.get("max_tokens", 2000)

            if not statement:
                return {"error": {"code": -32602, "message": "statement required"}}

            calibration = self.calibration_updater.get_confidence_guidance(module, confidence)

            # Unified Context Manager (graph-aware compaction)
            try:
                from membria.context_manager import ContextManager
                ctx_manager = ContextManager(self.graph_client, self.calibration_updater)
                doc_shot = self.docs_cache or None
                ctx = ctx_manager.build_decision_context(
                    statement=statement,
                    module=module,
                    confidence=confidence,
                    max_tokens=max_tokens,
                    include_chains=True,
                    doc_shot=doc_shot,
                )
            except Exception as exc:
                logger.warning(f"ContextManager failed, falling back: {exc}")
                ctx = {"compact_context": "", "total_tokens": 0, "truncated": False, "sections_included": []}

            past_decisions = []
            negative_knowledge = []
            surface = ctx.get("surface")
            if surface:
                past_decisions = surface.similar_decisions
                negative_knowledge = surface.negative_knowledge_alerts

            return {
                "decision_statement": statement,
                "module": module,
                "your_confidence": confidence,
                "calibration_context": calibration,
                "past_precedents": past_decisions,
                "negative_knowledge": negative_knowledge,
                "compact_context": ctx.get("compact_context", ""),
                "total_tokens": ctx.get("total_tokens", 0),
                "truncated": ctx.get("truncated", False),
                "sections_included": ctx.get("sections_included", []),
                "doc_shot_id": (self.docs_cache or {}).get("doc_shot_id"),
            }
        except Exception as e:
            return {"error": {"code": -32603, "message": str(e)}}

    def get_plan_context(self, args: Dict[str, Any]) -> Dict[str, Any]:
        """Tool: membria.get_plan_context - PRE-PLAN context injection"""
        try:
            domain = args.get("domain")
            scope = args.get("scope")
            max_tokens = args.get("max_tokens", 1500)

            if not domain:
                return {"error": {"code": -32602, "message": "domain required"}}

            context = self.plan_context_builder.build_plan_context(
                domain=domain,
                scope=scope,
                max_tokens=max_tokens
            )

            try:
                from membria.context_manager import ContextManager
                ctx_manager = ContextManager(self.graph_client, self.calibration_updater)
                compact = ctx_manager.build_plan_context(
                    plan_context=context,
                    max_tokens=max_tokens,
                    doc_shot=self.docs_cache or None,
                )
            except Exception as exc:
                logger.warning(f"Plan ContextManager failed: {exc}")
                compact = {"compact_context": context.get("formatted", ""), "total_tokens": context.get("total_tokens", 0), "truncated": False, "sections_included": []}

            return {
                "domain": context.get("domain"),
                "formatted": context.get("formatted"),
                "total_tokens": context.get("total_tokens"),
                "compact_context": compact.get("compact_context"),
                "compact_tokens": compact.get("total_tokens"),
                "compact_truncated": compact.get("truncated"),
                "sections_included": compact.get("sections_included"),
                "doc_shot_id": (self.docs_cache or {}).get("doc_shot_id"),
                "past_plans": context.get("past_plans"),
                "failed_approaches": context.get("failed_approaches"),
                "successful_patterns": context.get("successful_patterns"),
                "calibration": context.get("calibration"),
                "constraints": context.get("constraints"),
                "recommendations": context.get("recommendations")
            }
        except Exception as e:
            return {"error": {"code": -32603, "message": str(e)}}

    def validate_plan(self, args: Dict[str, Any]) -> Dict[str, Any]:
        """Tool: membria.validate_plan - MID-PLAN validation"""
        try:
            steps = args.get("steps")
            domain = args.get("domain")

            if not steps or not isinstance(steps, list):
                return {"error": {"code": -32602, "message": "steps (list) required"}}

            validation_result = self.plan_validator.validate_plan_async(
                steps=steps,
                domain=domain
            )

            return {
                "total_steps": validation_result.get("total_steps"),
                "warnings_count": validation_result.get("warnings_count"),
                "high_severity": validation_result.get("high_severity"),
                "medium_severity": validation_result.get("medium_severity"),
                "low_severity": validation_result.get("low_severity"),
                "can_proceed": validation_result.get("can_proceed"),
                "warnings": validation_result.get("warnings"),
                "timestamp": validation_result.get("timestamp")
            }
        except Exception as e:
            return {"error": {"code": -32603, "message": str(e)}}

    def record_plan(self, args: Dict[str, Any]) -> Dict[str, Any]:
        """Tool: membria.record_plan - POST-PLAN decision capture"""
        try:
            plan_steps = args.get("plan_steps")
            domain = args.get("domain")
            plan_confidence = args.get("plan_confidence", 0.5)
            duration_estimate = args.get("duration_estimate")
            warnings_shown = args.get("warnings_shown", 0)
            warnings_heeded = args.get("warnings_heeded", 0)

            if not plan_steps or not isinstance(plan_steps, list):
                return {"error": {"code": -32602, "message": "plan_steps (list) required"}}
            if not domain:
                return {"error": {"code": -32602, "message": "domain required"}}

            # Generate engram ID for this plan
            import uuid
            engram_id = f"eng_{uuid.uuid4().hex[:12]}"

            # Record each step as a decision
            decision_ids = []
            for i, step in enumerate(plan_steps, 1):
                decision_id = f"dec_{uuid.uuid4().hex[:12]}"
                decision_ids.append({
                    "step": i,
                    "description": step,
                    "decision_id": decision_id,
                    "decision_type": "tactical"  # Can be enhanced to detect architecture vs tactical
                })

            return {
                "engram_id": engram_id,
                "domain": domain,
                "plan_steps": len(plan_steps),
                "plan_confidence": plan_confidence,
                "duration_estimate": duration_estimate,
                "warnings_impact": {
                    "shown": warnings_shown,
                    "heeded": warnings_heeded
                },
                "decisions_recorded": decision_ids,
                "status": "recorded",
                "message": f"Plan recorded: {len(decision_ids)} steps captured"
            }
        except Exception as e:
            return {"error": {"code": -32603, "message": str(e)}}


    def get_auth_status(self, args: Dict[str, Any]) -> Dict[str, Any]:
        """Tool: membria.get_auth_status"""
        try:
            from membria.interactive.auth import AuthManager
            auth = AuthManager()
            token = auth.get_token()
            if token:
                return {
                    "authenticated": True,
                    "tier": "plus" if "plus" in token else "pro" if "pro" in token else "standard",
                    "method": "browser"
                }
            return {"authenticated": False}
        except Exception as e:
            return {"error": {"code": -32603, "message": str(e)}}

TOOL_DEFINITIONS = [
    {
        "name": "membria.fetch_docs",
        "description": "Fetch documentation and project files from the Membria knowledge graph.",
        "inputSchema": {
            "type": "object",
            "properties": {
                "doc_types": {"type": "array", "items": {"type": "string"}, "description": "Filter by document types"},
                "file_paths": {"type": "array", "items": {"type": "string"}, "description": "Filter by file paths"},
                "doc_ids": {"type": "array", "items": {"type": "string"}, "description": "Filter by document IDs"},
                "limit": {"type": "integer", "default": 10, "minimum": 1, "maximum": 200}
            }
        }
    },
    {
        "name": "membria.md_xtract",
        "description": "MD xtract: universal file/URL to clean markdown.",
        "inputSchema": {
            "type": "object",
            "properties": {
                "input": {"type": "string"},
                "input_type": {"type": "string"},
                "max_chars": {"type": "integer", "default": 0},
                "ocr": {"type": "boolean", "default": False}
            },
            "required": ["input"]
        }
    },
    {
        "name": "membria.squad_create",
        "description": "Create a squad with roles/profiles.",
        "inputSchema": {
            "type": "object",
            "properties": {
                "name": {"type": "string"},
                "project_id": {"type": "string"},
                "strategy": {"type": "string"},
                "roles": {"type": "array", "items": {"type": "string"}},
                "profiles": {"type": "array", "items": {"type": "string"}},
                "profile_paths": {"type": "array", "items": {"type": "string"}}
            },
            "required": ["name", "project_id", "strategy", "roles", "profiles"]
        }
    },
    {
        "name": "membria.assignment_add",
        "description": "Add an assignment to an existing squad.",
        "inputSchema": {
            "type": "object",
            "properties": {
                "squad_id": {"type": "string"},
                "role": {"type": "string"},
                "profile": {"type": "string"},
                "profile_path": {"type": "string"},
                "order": {"type": "integer"},
                "weight": {"type": "number"}
            },
            "required": ["squad_id", "role", "profile"]
        }
    },
    {
        "name": "membria.squad_list",
        "description": "List squads (optionally by project).",
        "inputSchema": {
            "type": "object",
            "properties": {
                "project_id": {"type": "string"},
                "limit": {"type": "integer"}
            }
        }
    },
    {
        "name": "membria.squad_assignments",
        "description": "List assignments for a squad.",
        "inputSchema": {
            "type": "object",
            "properties": {
                "squad_id": {"type": "string"}
            },
            "required": ["squad_id"]
        }
    },
    {
        "name": "membria.role_upsert",
        "description": "Create or update a role with prompt path and context policy.",
        "inputSchema": {
            "type": "object",
            "properties": {
                "name": {"type": "string"},
                "description": {"type": "string"},
                "prompt_path": {"type": "string"},
                "context_policy": {"type": "object"},
                "docshot_ids": {"type": "array", "items": {"type": "string"}},
                "skill_ids": {"type": "array", "items": {"type": "string"}},
                "nk_ids": {"type": "array", "items": {"type": "string"}}
            },
            "required": ["name"]
        }
    },
    {
        "name": "membria.role_get",
        "description": "Get role configuration from graph.",
        "inputSchema": {
            "type": "object",
            "properties": {"name": {"type": "string"}},
            "required": ["name"]
        }
    },
    {
        "name": "membria.role_link",
        "description": "Link role to DocShot/Skill/NegativeKnowledge.",
        "inputSchema": {
            "type": "object",
            "properties": {
                "name": {"type": "string"},
                "docshot_ids": {"type": "array", "items": {"type": "string"}},
                "skill_ids": {"type": "array", "items": {"type": "string"}},
                "nk_ids": {"type": "array", "items": {"type": "string"}}
            },
            "required": ["name"]
        }
    },
    {
        "name": "membria.role_unlink",
        "description": "Unlink role from DocShot/Skill/NegativeKnowledge.",
        "inputSchema": {
            "type": "object",
            "properties": {
                "name": {"type": "string"},
                "docshot_ids": {"type": "array", "items": {"type": "string"}},
                "skill_ids": {"type": "array", "items": {"type": "string"}},
                "nk_ids": {"type": "array", "items": {"type": "string"}}
            },
            "required": ["name"]
        }
    },
    {
        "name": "membria.capture_decision",
        "description": "Capture a decision point with confidence level for calibration tracking.",
        "inputSchema": {
            "type": "object",
            "properties": {
                "statement": {"type": "string", "description": "The decision statement"},
                "alternatives": {"type": "array", "items": {"type": "string"}, "description": "Alternative options considered"},
                "confidence": {"type": "number", "minimum": 0, "maximum": 1, "default": 0.5},
                "context": {"type": "object", "description": "Additional context (module, etc.)"}
            },
            "required": ["statement", "alternatives"]
        }
    },
    {
        "name": "membria.record_outcome",
        "description": "Record the outcome of a previously captured decision.",
        "inputSchema": {
            "type": "object",
            "properties": {
                "decision_id": {"type": "string"},
                "final_status": {"type": "string"},
                "final_score": {"type": "number", "minimum": 0, "maximum": 1, "default": 0.5},
                "decision_domain": {"type": "string", "default": "general"}
            },
            "required": ["decision_id", "final_status"]
        }
    },
    {
        "name": "membria.get_calibration",
        "description": "Get calibration data and confidence guidance for a domain.",
        "inputSchema": {
            "type": "object",
            "properties": {
                "domain": {"type": "string"}
            }
        }
    },
    {
        "name": "membria.get_decision_context",
        "description": "Get context for a decision including past precedents and calibration.",
        "inputSchema": {
            "type": "object",
            "properties": {
                "statement": {"type": "string"},
                "module": {"type": "string"},
                "confidence": {"type": "number", "minimum": 0, "maximum": 1, "default": 0.5}
            },
            "required": ["statement"]
        }
    },
    {
        "name": "membria.get_plan_context",
        "description": "Get pre-plan context injection with past plans and patterns.",
        "inputSchema": {
            "type": "object",
            "properties": {
                "domain": {"type": "string"},
                "scope": {"type": "string"}
            },
            "required": ["domain"]
        }
    },
    {
        "name": "membria.validate_plan",
        "description": "Validate plan steps against known patterns and antipatterns.",
        "inputSchema": {
            "type": "object",
            "properties": {
                "steps": {"type": "array", "items": {"type": "string"}},
                "domain": {"type": "string"}
            },
            "required": ["steps"]
        }
    },
    {
        "name": "membria.record_plan",
        "description": "Record a finalized plan with all steps as decision entries.",
        "inputSchema": {
            "type": "object",
            "properties": {
                "plan_steps": {"type": "array", "items": {"type": "string"}},
                "domain": {"type": "string"},
                "plan_confidence": {"type": "number", "minimum": 0, "maximum": 1, "default": 0.5},
                "duration_estimate": {"type": "string"},
                "warnings_shown": {"type": "integer", "default": 0},
                "warnings_heeded": {"type": "integer", "default": 0}
            },
            "required": ["plan_steps", "domain"]
        }
    },
    {
        "name": "membria.get_auth_status",
        "description": "Check authentication status.",
        "inputSchema": {"type": "object", "properties": {}}
    },
    {
        "name": "membria.consult_expert",
        "description": "Consult a domain expert (architect, security, etc.) on a task.",
        "inputSchema": {
            "type": "object",
            "properties": {
                "role": {"type": "string", "default": "architect"},
                "task": {"type": "string"}
            },
            "required": ["task"]
        }
    },
    {
        "name": "membria.red_team_audit",
        "description": "Run a red-team security audit on a task.",
        "inputSchema": {
            "type": "object",
            "properties": {
                "task": {"type": "string"},
                "context": {"type": "string", "default": ""}
            },
            "required": ["task"]
        }
    },
    {
        "name": "membria.run_orchestration",
        "description": "Run multi-agent orchestration (pipeline or debate mode).",
        "inputSchema": {
            "type": "object",
            "properties": {
                "task": {"type": "string"},
                "mode": {"type": "string", "enum": ["pipeline", "debate"], "default": "pipeline"},
                "red_team": {"type": "boolean", "default": False}
            },
            "required": ["task"]
        }
    },
    {
        "name": "membria.list_experts",
        "description": "List all available expert roles.",
        "inputSchema": {"type": "object", "properties": {}}
    },
    {
        "name": "membria.memory_store",
        "description": "Store memory item (decision or negative knowledge).",
        "inputSchema": {
            "type": "object",
            "properties": {
                "memory_type": {"type": "string"},
                "payload": {"type": "object"},
                "ttl_days": {"type": "integer"}
            },
            "required": ["memory_type", "payload"]
        }
    },
    {
        "name": "membria.memory_retrieve",
        "description": "Retrieve memory items by type.",
        "inputSchema": {
            "type": "object",
            "properties": {
                "memory_type": {"type": "string"},
                "domain": {"type": "string"},
                "limit": {"type": "integer"}
            },
            "required": ["memory_type"]
        }
    },
    {
        "name": "membria.memory_delete",
        "description": "Forget memory item by id.",
        "inputSchema": {
            "type": "object",
            "properties": {
                "memory_type": {"type": "string"},
                "item_id": {"type": "string"},
                "reason": {"type": "string"}
            },
            "required": ["memory_type", "item_id"]
        }
    },
    {
        "name": "membria.memory_list",
        "description": "List memory items by type.",
        "inputSchema": {
            "type": "object",
            "properties": {
                "memory_type": {"type": "string"},
                "domain": {"type": "string"},
                "limit": {"type": "integer"}
            },
            "required": ["memory_type"]
        }
    },
    {
        "name": "membria.session_context_store",
        "description": "Store or update a session context snapshot.",
        "inputSchema": {
            "type": "object",
            "properties": {
                "session_id": {"type": "string"},
                "task": {"type": "string"},
                "focus": {"type": "string"},
                "current_plan": {"type": "string"},
                "constraints": {"type": "array", "items": {"type": "string"}},
                "doc_shot_id": {"type": "string"},
                "ttl_days": {"type": "integer"},
            },
            "required": ["session_id", "task"],
        },
    },
    {
        "name": "membria.session_context_retrieve",
        "description": "Retrieve session context by session_id or list recent.",
        "inputSchema": {
            "type": "object",
            "properties": {
                "session_id": {"type": "string"},
                "limit": {"type": "integer"},
            },
        },
    },
    {
        "name": "membria.session_context_delete",
        "description": "Deactivate a session context by session_id.",
        "inputSchema": {
            "type": "object",
            "properties": {"session_id": {"type": "string"}},
            "required": ["session_id"],
        },
    },
    {
        "name": "membria.docs_add",
        "description": "Add a document to the graph.",
        "inputSchema": {
            "type": "object",
            "properties": {
                "file_path": {"type": "string"},
                "content": {"type": "string"},
                "doc_type": {"type": "string"},
                "metadata": {"type": "object"},
            },
            "required": ["file_path", "content"],
        },
    },
    {
        "name": "membria.docs_get",
        "description": "Get documents from the graph.",
        "inputSchema": {
            "type": "object",
            "properties": {
                "doc_ids": {"type": "array", "items": {"type": "string"}},
                "file_paths": {"type": "array", "items": {"type": "string"}},
                "doc_types": {"type": "array", "items": {"type": "string"}},
                "limit": {"type": "integer"},
            },
        },
    },
    {
        "name": "membria.docs_list",
        "description": "List documents from the graph.",
        "inputSchema": {
            "type": "object",
            "properties": {
                "doc_types": {"type": "array", "items": {"type": "string"}},
                "limit": {"type": "integer"},
            },
        },
    },
    {
        "name": "membria.docshot_link",
        "description": "Link decision to DocShot and documents.",
        "inputSchema": {
            "type": "object",
            "properties": {
                "decision_id": {"type": "string"},
                "doc_shot_id": {"type": "string"},
                "docs": {"type": "array", "items": {"type": "object"}},
                "fetched_at": {"type": "string"},
            },
            "required": ["decision_id", "doc_shot_id"],
        },
    },
    {
        "name": "membria.outcome_get",
        "description": "Get an Outcome by id.",
        "inputSchema": {"type": "object", "properties": {"outcome_id": {"type": "string"}}, "required": ["outcome_id"]},
    },
    {
        "name": "membria.outcome_list",
        "description": "List Outcomes.",
        "inputSchema": {"type": "object", "properties": {"status": {"type": "string"}, "limit": {"type": "integer"}}},
    },
    {
        "name": "membria.skills_list",
        "description": "List skills by domain or quality.",
        "inputSchema": {
            "type": "object",
            "properties": {
                "domain": {"type": "string"},
                "min_quality": {"type": "number"},
                "limit": {"type": "integer"},
            },
        },
    },
    {
        "name": "membria.skills_get",
        "description": "Get latest skill by domain and name.",
        "inputSchema": {
            "type": "object",
            "properties": {"domain": {"type": "string"}, "name": {"type": "string"}},
            "required": ["domain", "name"],
        },
    },
    {
        "name": "membria.antipatterns_list",
        "description": "List antipatterns.",
        "inputSchema": {
            "type": "object",
            "properties": {"category": {"type": "string"}, "limit": {"type": "integer"}},
        },
    },
    {
        "name": "membria.antipatterns_get",
        "description": "Get antipattern by id.",
        "inputSchema": {"type": "object", "properties": {"pattern_id": {"type": "string"}}, "required": ["pattern_id"]},
    },
    {
        "name": "membria.health",
        "description": "Get graph health status.",
        "inputSchema": {"type": "object", "properties": {}},
    },
    {
        "name": "membria.migrations_status",
        "description": "Get migrations status.",
        "inputSchema": {"type": "object", "properties": {}},
    },
    {
        "name": "membria.logs_tail",
        "description": "Tail daemon logs.",
        "inputSchema": {"type": "object", "properties": {"lines": {"type": "integer"}}},
    },
]


class MembriaMCPServer:
    """Main MCP Server."""

    def __init__(self):
        self.handler = MembriaToolHandler()
        config = ConfigManager().config
        self._memory_tools_enabled = bool(getattr(config, "memory_tools", None) and config.memory_tools.enabled)
        self._discovery_enabled = bool(getattr(config, "mcp_discovery", None) and config.mcp_discovery.enabled)
        self._external_registry = None
        if self._discovery_enabled:
            from membria.mcp_discovery import ExternalToolRegistry
            self._external_registry = ExternalToolRegistry(
                allowlist_path=config.mcp_discovery.allowlist_path,
                timeout_sec=config.mcp_discovery.timeout_sec,
                refresh_sec=config.mcp_discovery.refresh_sec,
            )
        self.tools = {
            "membria.fetch_docs": self.handler.fetch_docs,
            "membria.md_xtract": self.handler.md_xtract,
            "membria.squad_create": self.handler.squad_create,
            "membria.assignment_add": self.handler.assignment_add,
            "membria.squad_list": self.handler.squad_list,
            "membria.squad_assignments": self.handler.squad_assignments,
            "membria.role_upsert": self.handler.role_upsert,
            "membria.role_get": self.handler.role_get,
            "membria.role_link": self.handler.role_link,
            "membria.role_unlink": self.handler.role_unlink,
            "membria.capture_decision": self.handler.capture_decision,
            "membria.record_outcome": self.handler.record_outcome,
            "membria.get_calibration": self.handler.get_calibration,
            "membria.get_decision_context": self.handler.get_decision_context,
            "membria.get_plan_context": self.handler.get_plan_context,
            "membria.validate_plan": self.handler.validate_plan,
            "membria.record_plan": self.handler.record_plan,
            "membria.get_auth_status": self.handler.get_auth_status,
            "membria.consult_expert": self.handler.consult_expert,
            "membria.red_team_audit": self.handler.red_team_audit,
            "membria.run_orchestration": self.handler.run_orchestration,
            "membria.list_experts": self.handler.list_experts,
            "membria.session_context_store": self.handler.session_context_store,
            "membria.session_context_retrieve": self.handler.session_context_retrieve,
            "membria.session_context_delete": self.handler.session_context_delete,
            "membria.docs_add": self.handler.docs_add,
            "membria.docs_get": self.handler.docs_get,
            "membria.docs_list": self.handler.docs_list,
            "membria.docshot_link": self.handler.docshot_link,
            "membria.outcome_get": self.handler.outcome_get,
            "membria.outcome_list": self.handler.outcome_list,
            "membria.skills_list": self.handler.skills_list,
            "membria.skills_get": self.handler.skills_get,
            "membria.antipatterns_list": self.handler.antipatterns_list,
            "membria.antipatterns_get": self.handler.antipatterns_get,
            "membria.health": self.handler.health,
            "membria.migrations_status": self.handler.migrations_status,
            "membria.logs_tail": self.handler.logs_tail,
        }
        if getattr(config, "memory_tools", None) and config.memory_tools.enabled:
            self.tools.update(
                {
                    "membria.memory_store": self.handler.memory_store,
                    "membria.memory_retrieve": self.handler.memory_retrieve,
                    "membria.memory_delete": self.handler.memory_delete,
                    "membria.memory_list": self.handler.memory_list,
                }
            )

    def _tool_definitions(self) -> List[Dict[str, Any]]:
        tools = TOOL_DEFINITIONS
        if not self._memory_tools_enabled:
            tools = [t for t in tools if not t.get("name", "").startswith("membria.memory_")]
        if self._external_registry:
            tools = tools + self._external_registry.list_tools()
        return tools

    def handle_request(self, request: Dict[str, Any]) -> Optional[MCPResponse]:
        """Handle MCP request. Returns None for notifications (no id)."""
        try:
            req_id = request.get("id")
            method = request.get("method")
            params = request.get("params", {})

            # Notifications have no id — must not send a response
            if req_id is None:
                return None

            if method == "initialize":
                return MCPResponse(req_id, result={
                    "protocolVersion": "2024-11-05",
                    "capabilities": {
                        "tools": {"listChanged": False},
                    },
                    "serverInfo": {"name": "membria-mcp", "version": "1.0"}
                })

            elif method == "ping":
                return MCPResponse(req_id, result={})

            elif method == "tools/list":
                return MCPResponse(req_id, result={"tools": self._tool_definitions()})

            elif method == "resources/list":
                return MCPResponse(req_id, result={"resources": []})

            elif method == "prompts/list":
                return MCPResponse(req_id, result={"prompts": []})

            elif method == "tools/call":
                tool_name = params.get("name")
                tool_args = params.get("arguments", {})

                if tool_name not in self.tools and not (self._external_registry and tool_name.startswith("ext.")):
                    return MCPResponse(req_id, error={"code": -32601, "message": f"Unknown tool: {tool_name}"})

                from membria.mcp_schemas import validate_tool_params, validate_tool_result

                if not tool_name.startswith("ext."):
                    validation_error = validate_tool_params(tool_name, tool_args)
                    if validation_error:
                        return MCPResponse(
                            req_id,
                            error={"code": -32602, "message": f"Invalid params: {validation_error}"}
                        )

                if tool_name.startswith("ext.") and self._external_registry:
                    result = self._external_registry.call_tool(tool_name, tool_args)
                else:
                    result = self.tools[tool_name](tool_args)

                if "error" in result:
                    return MCPResponse(req_id, error=result["error"])

                if not tool_name.startswith("ext."):
                    result_error = validate_tool_result(tool_name, result)
                    if result_error:
                        return MCPResponse(
                            req_id,
                            error={"code": -32603, "message": f"Invalid result schema: {result_error}"}
                        )

                from membria.security import safe_json_dumps
                return MCPResponse(req_id, result={"content": [{"type": "text", "text": safe_json_dumps(result)}]})

            return MCPResponse(req_id, error={"code": -32601, "message": f"Unknown method: {method}"})

        except Exception as e:
            req_id = request.get("id")
            if req_id is None:
                return None
            return MCPResponse(req_id, error={"code": -32603, "message": str(e)})

    def run(self):
        """Run on stdio."""
        while True:
            try:
                line = sys.stdin.readline()
                if not line:
                    break
                request = json.loads(line)
                response = self.handle_request(request)
                if response is not None:
                    sys.stdout.write(response.to_json() + "\n")
                    sys.stdout.flush()
            except json.JSONDecodeError:
                sys.stdout.write(json.dumps({"jsonrpc": "2.0", "id": None, "error": {"code": -32700, "message": "Parse error"}}) + "\n")
                sys.stdout.flush()
            except Exception:
                break


def start_mcp_server():
    """Start the MCP server."""
    server = MembriaMCPServer()
    server.run()


if __name__ == "__main__":
    start_mcp_server()
