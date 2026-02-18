"""Real MCP daemon with stdio protocol and background processing."""

import asyncio
import json
import hashlib
import logging
import sys
from pathlib import Path
from typing import Any, Dict, Optional
from datetime import datetime
import signal
import threading
import time

from membria.config import ConfigManager
from membria.graph import GraphClient
from membria.signal_detector import SignalDetector
from membria.haiku_extractor import HaikuExtractor
from membria.session_capturer import capture_mcp_session, get_capturer
from membria.security import sanitize_text

logger = logging.getLogger(__name__)


class MCPDaemonServer:
    """Real MCP server with background processing."""

    def __init__(self):
        """Initialize MCP daemon."""
        self.config = ConfigManager()
        self.graph = GraphClient(self.config.get_falkordb_config())
        self.signal_detector = SignalDetector()
        self.haiku_extractor = HaikuExtractor()
        self.capturer = get_capturer()
        try:
            from membria.memory_manager import MemoryManager
            self.memory_manager = MemoryManager(self.graph)
        except Exception:
            self.memory_manager = None
        try:
            from membria.calibration_updater import CalibrationUpdater
            self.calibration_updater = CalibrationUpdater(self.graph)
        except Exception:
            self.calibration_updater = None
        self.memory_tools_enabled = bool(
            getattr(self.config.config, "memory_tools", None)
            and self.config.config.memory_tools.enabled
        )

        self.running = False
        self.last_extraction = datetime.now()
        self.extraction_interval = 3600  # Extract every hour
        self.last_forget = datetime.now()
        self.forget_interval = 3600  # Forget sweep every hour

        # Background threads
        self.batch_thread: Optional[threading.Thread] = None
        self.health_thread: Optional[threading.Thread] = None

        self.session_docs: Dict[str, Dict[str, Any]] = {}

    def start(self) -> None:
        """Start MCP daemon."""
        logger.info("Starting MCP daemon...")

        # Connect to graph
        if not self.graph.connect():
            logger.error("Failed to connect to graph")
            return

        self.running = True

        # Start background threads
        self._start_batch_processor()
        self._start_health_monitor()

        # Listen for MCP calls on stdio
        logger.info("MCP daemon ready, listening on stdio")
        self._run_mcp_loop()

    def stop(self) -> None:
        """Stop MCP daemon gracefully."""
        logger.info("Stopping MCP daemon...")
        self.running = False

        # Wait for threads
        if self.batch_thread:
            self.batch_thread.join(timeout=5)
        if self.health_thread:
            self.health_thread.join(timeout=5)

        self.graph.disconnect()
        logger.info("MCP daemon stopped")

    def _run_mcp_loop(self) -> None:
        """Main MCP message loop (stdio)."""
        try:
            while self.running:
                try:
                    line = sys.stdin.readline()
                    if not line:
                        break

                    message = json.loads(line)
                    response = self._handle_mcp_message(message)

                    if response:
                        print(json.dumps(response))
                        sys.stdout.flush()

                except json.JSONDecodeError:
                    logger.error("Invalid JSON received")
                except Exception as e:
                    logger.error(f"Error handling MCP message: {e}")

        except KeyboardInterrupt:
            logger.info("Received interrupt")
        finally:
            self.stop()

    def _handle_mcp_message(self, message: Dict[str, Any]) -> Optional[Dict[str, Any]]:
        """Handle incoming MCP message."""
        message_type = message.get("type")
        request_id = message.get("id")

        if message_type == "initialize":
            return self._handle_initialize(request_id)

        elif message_type == "call_tool":
            tool_name = message.get("tool")
            params = message.get("params", {})
            session_id = message.get("session_id")
            return self._handle_tool_call(request_id, tool_name, params, session_id)

        elif message_type == "capture_session":
            prompt = message.get("prompt", "")
            response = message.get("response", "")
            return self._handle_capture_session(request_id, prompt, response)

        else:
            return {
                "type": "error",
                "id": request_id,
                "error": f"Unknown message type: {message_type}",
            }

    def _handle_initialize(self, request_id: Optional[str]) -> Dict[str, Any]:
        """Handle initialize message."""
        return {
            "type": "initialized",
            "id": request_id,
            "name": "membria",
            "version": "0.2.0",
            "tools": self._get_tool_definitions(),
            "capabilities": {
                "context_injection": True,
                "decision_capture": True,
                "signal_detection": True,
                "batch_extraction": True,
                "background_processing": True,
            },
        }

    def _get_tool_definitions(self) -> list:
        """Get MCP tool definitions."""
        tools = [
            {
                "name": "membria.fetch_docs",
                "description": "Fetch documentation from the graph (doc-first)",
                "inputSchema": {
                    "type": "object",
                    "properties": {
                        "doc_types": {"type": "array", "items": {"type": "string"}},
                        "file_paths": {"type": "array", "items": {"type": "string"}},
                        "doc_ids": {"type": "array", "items": {"type": "string"}},
                        "limit": {"type": "integer"},
                    },
                },
            },
            {
                "name": "membria.md_xtract",
                "description": "MD xtract: universal file/URL to clean markdown",
                "inputSchema": {
                    "type": "object",
                    "properties": {
                        "input": {"type": "string"},
                        "input_type": {"type": "string"},
                        "max_chars": {"type": "integer"},
                        "ocr": {"type": "boolean"},
                    },
                    "required": ["input"],
                },
            },
            {
                "name": "membria.squad_create",
                "description": "Create a squad with roles/profiles",
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
                    "required": ["name", "project_id", "strategy", "roles", "profiles"],
                },
            },
            {
                "name": "membria.assignment_add",
                "description": "Add an assignment to a squad",
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
                    "required": ["squad_id", "role", "profile"],
                },
            },
            {
                "name": "membria.squad_list",
                "description": "List squads",
                "inputSchema": {
                    "type": "object",
                    "properties": {
                        "project_id": {"type": "string"},
                        "limit": {"type": "integer"},
                    },
                },
            },
            {
                "name": "membria.squad_assignments",
                "description": "List squad assignments",
                "inputSchema": {
                    "type": "object",
                    "properties": {"squad_id": {"type": "string"}},
                    "required": ["squad_id"],
                },
            },
            {
                "name": "membria.role_upsert",
                "description": "Create or update a role with prompt path and context policy",
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
                    "required": ["name"],
                },
            },
            {
                "name": "membria.role_get",
                "description": "Get role configuration",
                "inputSchema": {
                    "type": "object",
                    "properties": {"name": {"type": "string"}},
                    "required": ["name"],
                },
            },
            {
                "name": "membria.role_link",
                "description": "Link role to DocShot/Skill/NegativeKnowledge",
                "inputSchema": {
                    "type": "object",
                    "properties": {
                        "name": {"type": "string"},
                        "docshot_ids": {"type": "array", "items": {"type": "string"}},
                        "skill_ids": {"type": "array", "items": {"type": "string"}},
                        "nk_ids": {"type": "array", "items": {"type": "string"}}
                    },
                    "required": ["name"],
                },
            },
            {
                "name": "membria.role_unlink",
                "description": "Unlink role from DocShot/Skill/NegativeKnowledge",
                "inputSchema": {
                    "type": "object",
                    "properties": {
                        "name": {"type": "string"},
                        "docshot_ids": {"type": "array", "items": {"type": "string"}},
                        "skill_ids": {"type": "array", "items": {"type": "string"}},
                        "nk_ids": {"type": "array", "items": {"type": "string"}}
                    },
                    "required": ["name"],
                },
            },
            {
                "name": "membria_record_decision",
                "description": "Record a decision to the reasoning graph",
                "inputSchema": {
                    "type": "object",
                    "properties": {
                        "statement": {"type": "string"},
                        "alternatives": {"type": "array", "items": {"type": "string"}},
                        "confidence": {"type": "number"},
                        "module": {"type": "string"},
                    },
                    "required": ["statement", "alternatives", "confidence"],
                },
            },
            {
                "name": "membria_get_context",
                "description": "Get decision context for current request",
                "inputSchema": {
                    "type": "object",
                    "properties": {
                        "request": {"type": "string"},
                        "module": {"type": "string"},
                        "confidence": {"type": "number"},
                        "max_tokens": {"type": "integer"},
                    },
                    "required": ["request"],
                },
            },
            {
                "name": "membria_get_calibration",
                "description": "Get team calibration metrics",
                "inputSchema": {
                    "type": "object",
                    "properties": {
                        "domain": {"type": "string"},
                    },
                },
            },
        ]
        if self.memory_tools_enabled:
            tools.extend(
                [
                    {
                        "name": "membria.memory_store",
                        "description": "Store memory item (decision or negative knowledge)",
                        "inputSchema": {
                            "type": "object",
                            "properties": {
                                "memory_type": {"type": "string"},
                                "payload": {"type": "object"},
                                "ttl_days": {"type": "integer"},
                            },
                            "required": ["memory_type", "payload"],
                        },
                    },
                    {
                        "name": "membria.memory_retrieve",
                        "description": "Retrieve memory items by type",
                        "inputSchema": {
                            "type": "object",
                            "properties": {
                                "memory_type": {"type": "string"},
                                "domain": {"type": "string"},
                                "limit": {"type": "integer"},
                            },
                            "required": ["memory_type"],
                        },
                    },
                    {
                        "name": "membria.memory_delete",
                        "description": "Forget memory item by id",
                        "inputSchema": {
                            "type": "object",
                            "properties": {
                                "memory_type": {"type": "string"},
                                "item_id": {"type": "string"},
                                "reason": {"type": "string"},
                            },
                            "required": ["memory_type", "item_id"],
                        },
                    },
                    {
                        "name": "membria.memory_list",
                        "description": "List memory items by type",
                        "inputSchema": {
                            "type": "object",
                            "properties": {
                                "memory_type": {"type": "string"},
                                "domain": {"type": "string"},
                                "limit": {"type": "integer"},
                            },
                            "required": ["memory_type"],
                        },
                    },
                ]
            )
        tools.extend(
            [
                {
                    "name": "membria.session_context_store",
                    "description": "Store or update session context",
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
                    "description": "Retrieve session context",
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
                    "description": "Deactivate session context",
                    "inputSchema": {
                        "type": "object",
                        "properties": {"session_id": {"type": "string"}},
                        "required": ["session_id"],
                    },
                },
                {
                    "name": "membria.docs_add",
                    "description": "Add document to graph",
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
                    "description": "Get documents",
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
                    "description": "List documents",
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
                    "description": "Link decision to DocShot and documents",
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
                    "description": "Get outcome by id",
                    "inputSchema": {
                        "type": "object",
                        "properties": {"outcome_id": {"type": "string"}},
                        "required": ["outcome_id"],
                    },
                },
                {
                    "name": "membria.outcome_list",
                    "description": "List outcomes",
                    "inputSchema": {
                        "type": "object",
                        "properties": {"status": {"type": "string"}, "limit": {"type": "integer"}},
                    },
                },
                {
                    "name": "membria.skills_list",
                    "description": "List skills",
                    "inputSchema": {
                        "type": "object",
                        "properties": {"domain": {"type": "string"}, "min_quality": {"type": "number"}, "limit": {"type": "integer"}},
                    },
                },
                {
                    "name": "membria.skills_get",
                    "description": "Get latest skill",
                    "inputSchema": {
                        "type": "object",
                        "properties": {"domain": {"type": "string"}, "name": {"type": "string"}},
                        "required": ["domain", "name"],
                    },
                },
                {
                    "name": "membria.antipatterns_list",
                    "description": "List antipatterns",
                    "inputSchema": {
                        "type": "object",
                        "properties": {"category": {"type": "string"}, "limit": {"type": "integer"}},
                    },
                },
                {
                    "name": "membria.antipatterns_get",
                    "description": "Get antipattern by id",
                    "inputSchema": {
                        "type": "object",
                        "properties": {"pattern_id": {"type": "string"}},
                        "required": ["pattern_id"],
                    },
                },
                {
                    "name": "membria.health",
                    "description": "Get graph health status",
                    "inputSchema": {"type": "object", "properties": {}},
                },
                {
                    "name": "membria.migrations_status",
                    "description": "Get migrations status",
                    "inputSchema": {"type": "object", "properties": {}},
                },
                {
                    "name": "membria.logs_tail",
                    "description": "Tail daemon logs",
                    "inputSchema": {"type": "object", "properties": {"lines": {"type": "integer"}}},
                },
            ]
        )
        return tools

    def _handle_tool_call(
        self,
        request_id: Optional[str],
        tool_name: str,
        params: Dict[str, Any],
        session_id: Optional[str],
    ) -> Dict[str, Any]:
        """Handle tool call from Claude Code."""
        try:
            from membria.mcp_schemas import validate_tool_params, validate_tool_result

            validation_error = validate_tool_params(tool_name, params)
            if validation_error:
                return {
                    "type": "error",
                    "id": request_id,
                    "error": f"Invalid params: {validation_error}",
                }

            if tool_name == "membria.fetch_docs":
                response = self._tool_fetch_docs(request_id, params, session_id)
            elif tool_name == "membria.md_xtract":
                response = self._tool_md_xtract(request_id, params)
            elif tool_name == "membria.squad_create":
                response = self._tool_squad_create(request_id, params)
            elif tool_name == "membria.assignment_add":
                response = self._tool_assignment_add(request_id, params)
            elif tool_name == "membria.squad_list":
                response = self._tool_squad_list(request_id, params)
            elif tool_name == "membria.squad_assignments":
                response = self._tool_squad_assignments(request_id, params)
            elif tool_name == "membria.role_upsert":
                response = self._tool_role_upsert(request_id, params)
            elif tool_name == "membria.role_get":
                response = self._tool_role_get(request_id, params)
            elif tool_name == "membria.role_link":
                response = self._tool_role_link(request_id, params)
            elif tool_name == "membria.role_unlink":
                response = self._tool_role_unlink(request_id, params)
            elif tool_name == "membria_record_decision":
                if session_id and session_id not in self.session_docs:
                    logger.warning(
                        "Doc-first guard: membria_record_decision called without fetch_docs (session_id=%s)",
                        session_id,
                    )
                if session_id:
                    params = dict(params)
                    params["session_id"] = session_id
                response = self._tool_record_decision(request_id, params)
            elif tool_name == "membria_get_context":
                if session_id and session_id not in self.session_docs:
                    logger.warning(
                        "Doc-first guard: membria_get_context called without fetch_docs (session_id=%s)",
                        session_id,
                    )
                if session_id:
                    params = dict(params)
                    params["session_id"] = session_id
                response = self._tool_get_context(request_id, params)
            elif tool_name == "membria_get_calibration":
                if session_id and session_id not in self.session_docs:
                    logger.warning(
                        "Doc-first guard: membria_get_calibration called without fetch_docs (session_id=%s)",
                        session_id,
                    )
                response = self._tool_get_calibration(request_id, params)
            elif tool_name == "membria.memory_store":
                response = self._tool_memory_store(request_id, params)
            elif tool_name == "membria.memory_retrieve":
                response = self._tool_memory_retrieve(request_id, params)
            elif tool_name == "membria.memory_delete":
                response = self._tool_memory_delete(request_id, params)
            elif tool_name == "membria.memory_list":
                response = self._tool_memory_list(request_id, params)
            elif tool_name == "membria.session_context_store":
                response = self._tool_session_context_store(request_id, params)
            elif tool_name == "membria.session_context_retrieve":
                response = self._tool_session_context_retrieve(request_id, params)
            elif tool_name == "membria.session_context_delete":
                response = self._tool_session_context_delete(request_id, params)
            elif tool_name == "membria.docs_add":
                response = self._tool_docs_add(request_id, params)
            elif tool_name == "membria.docs_get":
                response = self._tool_docs_get(request_id, params)
            elif tool_name == "membria.docs_list":
                response = self._tool_docs_list(request_id, params)
            elif tool_name == "membria.docshot_link":
                response = self._tool_docshot_link(request_id, params)
            elif tool_name == "membria.outcome_get":
                response = self._tool_outcome_get(request_id, params)
            elif tool_name == "membria.outcome_list":
                response = self._tool_outcome_list(request_id, params)
            elif tool_name == "membria.skills_list":
                response = self._tool_skills_list(request_id, params)
            elif tool_name == "membria.skills_get":
                response = self._tool_skills_get(request_id, params)
            elif tool_name == "membria.antipatterns_list":
                response = self._tool_antipatterns_list(request_id, params)
            elif tool_name == "membria.antipatterns_get":
                response = self._tool_antipatterns_get(request_id, params)
            elif tool_name == "membria.health":
                response = self._tool_health(request_id)
            elif tool_name == "membria.migrations_status":
                response = self._tool_migrations_status(request_id)
            elif tool_name == "membria.logs_tail":
                response = self._tool_logs_tail(request_id, params)
            else:
                return {
                    "type": "error",
                    "id": request_id,
                    "error": f"Unknown tool: {tool_name}",
                }
            if response.get("type") == "tool_result":
                result_error = validate_tool_result(tool_name, response.get("result", {}))
                if result_error:
                    return {
                        "type": "error",
                        "id": request_id,
                        "error": f"Invalid result schema: {result_error}",
                    }

            return response
        except Exception as e:
            logger.error(f"Tool execution failed: {e}")
            return {
                "type": "error",
                "id": request_id,
                "error": str(e),
            }

    def _tool_fetch_docs(
        self,
        request_id: Optional[str],
        params: Dict[str, Any],
        session_id: Optional[str],
    ) -> Dict[str, Any]:
        """Tool: Fetch docs from graph (doc-first workflow)."""
        if not session_id:
            return {
                "type": "error",
                "id": request_id,
                "error": "session_id is required for membria.fetch_docs",
            }

        docs = self.graph.get_documents(
            doc_types=params.get("doc_types"),
            file_paths=params.get("file_paths"),
            doc_ids=params.get("doc_ids"),
            limit=int(params.get("limit") or 10),
        )

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
        self.session_docs[session_id] = {
            "fetched_at": datetime.utcnow().isoformat(),
            "doc_count": len(result_docs),
            "doc_types": params.get("doc_types"),
            "file_paths": params.get("file_paths"),
            "doc_ids": params.get("doc_ids"),
            "doc_shot_id": doc_shot_id,
            "docs": [
                {"id": d.get("id"), "updated_at": d.get("updated_at")}
                for d in result_docs
            ],
        }

        # Persist session context for multi-agent access
        try:
            self.graph.upsert_session_context(
                session_id=session_id,
                task="doc_first_fetch",
                focus=None,
                current_plan=None,
                constraints=[],
                doc_shot_id=doc_shot_id,
                ttl_days=3,
            )
            self.graph.link_engram_session_context(session_id)
        except Exception as exc:
            logger.warning(f"SessionContext upsert failed: {exc}")

        return {
            "type": "tool_result",
            "id": request_id,
            "result": {
                "status": "success",
                "count": len(result_docs),
                "doc_shot_id": doc_shot_id,
                "docs": result_docs,
            },
        }

    def _tool_md_xtract(
        self,
        request_id: Optional[str],
        params: Dict[str, Any],
    ) -> Dict[str, Any]:
        """Tool: MD xtract (file/URL to clean markdown)."""
        try:
            from membria.md_xtract import xtract_to_markdown

            markdown, metadata = xtract_to_markdown(
                params.get("input"),
                input_type=params.get("input_type"),
                max_chars=int(params.get("max_chars") or 0),
                ocr=bool(params.get("ocr") or False),
            )
            return {
                "type": "tool_result",
                "id": request_id,
                "result": {"status": "success", "markdown": markdown, "metadata": metadata},
            }
        except Exception as e:
            return {
                "type": "tool_result",
                "id": request_id,
                "result": {"status": "error", "error": str(e)},
            }

    def _tool_squad_create(self, request_id: Optional[str], params: Dict[str, Any]) -> Dict[str, Any]:
        """Tool: Create squad."""
        try:
            roles = params.get("roles") or []
            profiles = params.get("profiles") or []
            if len(roles) != len(profiles):
                return {
                    "type": "error",
                    "id": request_id,
                    "error": "roles and profiles length mismatch",
                }
            import uuid
            from membria.config import ConfigManager

            self.graph.upsert_project(params.get("project_id"), params.get("project_id"))
            squad_id = f"sqd_{uuid.uuid4().hex[:10]}"
            ok = self.graph.create_squad(
                squad_id,
                name=params.get("name"),
                strategy=params.get("strategy"),
                project_id=params.get("project_id"),
            )
            if not ok:
                return {
                    "type": "error",
                    "id": request_id,
                    "error": "failed to create squad",
                }
            cfg = ConfigManager()
            default_path = str(cfg.config_file)
            profile_paths = params.get("profile_paths") or []
            assignments = []
            for idx, (role, profile) in enumerate(zip(roles, profiles), start=1):
                role_id = f"role_{role}"
                profile_id = f"profile_{profile}"
                path = default_path
                if profile_paths:
                    path = profile_paths[0] if len(profile_paths) == 1 else profile_paths[idx - 1]
                self.graph.upsert_role(role_id, role)
                self.graph.upsert_profile(profile_id, profile, config_path=path)
                assignment_id = f"asn_{uuid.uuid4().hex[:10]}"
                self.graph.add_assignment(
                    assignment_id=assignment_id,
                    squad_id=squad_id,
                    role_id=role_id,
                    profile_id=profile_id,
                    order=idx,
                )
                assignments.append({"assignment_id": assignment_id, "role_id": role_id, "profile_id": profile_id})
            return {
                "type": "tool_result",
                "id": request_id,
                "result": {"status": "success", "squad_id": squad_id, "assignments": assignments},
            }
        except Exception as e:
            return {
                "type": "error",
                "id": request_id,
                "error": str(e),
            }

    def _tool_assignment_add(self, request_id: Optional[str], params: Dict[str, Any]) -> Dict[str, Any]:
        """Tool: Add assignment."""
        try:
            import uuid
            from membria.config import ConfigManager

            role = params.get("role")
            profile = params.get("profile")
            role_id = f"role_{role}"
            profile_id = f"profile_{profile}"
            cfg = ConfigManager()
            default_path = str(cfg.config_file)
            profile_path = params.get("profile_path") or default_path
            self.graph.upsert_role(role_id, role)
            self.graph.upsert_profile(profile_id, profile, config_path=profile_path)
            assignment_id = f"asn_{uuid.uuid4().hex[:10]}"
            ok = self.graph.add_assignment(
                assignment_id=assignment_id,
                squad_id=params.get("squad_id"),
                role_id=role_id,
                profile_id=profile_id,
                order=int(params.get("order") or 0),
                weight=float(params.get("weight") or 1.0),
            )
            if not ok:
                return {
                    "type": "error",
                    "id": request_id,
                    "error": "failed to add assignment",
                }
            return {
                "type": "tool_result",
                "id": request_id,
                "result": {"status": "success", "assignment_id": assignment_id},
            }
        except Exception as e:
            return {
                "type": "error",
                "id": request_id,
                "error": str(e),
            }

    def _tool_squad_list(self, request_id: Optional[str], params: Dict[str, Any]) -> Dict[str, Any]:
        """Tool: List squads."""
        try:
            items = self.graph.list_squads(
                project_id=params.get("project_id"),
                limit=int(params.get("limit") or 20),
            )
            return {
                "type": "tool_result",
                "id": request_id,
                "result": {"status": "success", "items": items},
            }
        except Exception as e:
            return {
                "type": "error",
                "id": request_id,
                "error": str(e),
            }

    def _tool_squad_assignments(self, request_id: Optional[str], params: Dict[str, Any]) -> Dict[str, Any]:
        """Tool: List squad assignments."""
        try:
            items = self.graph.list_assignments(params.get("squad_id"))
            return {
                "type": "tool_result",
                "id": request_id,
                "result": {"status": "success", "items": items},
            }
        except Exception as e:
            return {
                "type": "error",
                "id": request_id,
                "error": str(e),
            }

    def _tool_role_upsert(self, request_id: Optional[str], params: Dict[str, Any]) -> Dict[str, Any]:
        """Tool: Create or update role."""
        try:
            name = params.get("name")
            role_id = f"role_{name}"
            ok = self.graph.upsert_role(
                role_id=role_id,
                name=name,
                description=params.get("description"),
                prompt_path=params.get("prompt_path"),
                context_policy=params.get("context_policy"),
            )
            if not ok:
                return {"type": "error", "id": request_id, "error": "failed to upsert role"}
            for ds in params.get("docshot_ids") or []:
                self.graph.link_role_docshot(name, ds)
            for sk in params.get("skill_ids") or []:
                self.graph.link_role_skill(name, sk)
            for nk in params.get("nk_ids") or []:
                self.graph.link_role_nk(name, nk)
            return {
                "type": "tool_result",
                "id": request_id,
                "result": {"status": "success", "role_id": role_id},
            }
        except Exception as e:
            return {"type": "error", "id": request_id, "error": str(e)}

    def _tool_role_get(self, request_id: Optional[str], params: Dict[str, Any]) -> Dict[str, Any]:
        """Tool: Get role."""
        try:
            item = self.graph.get_role(params.get("name"))
            return {
                "type": "tool_result",
                "id": request_id,
                "result": {"status": "success", "item": item},
            }
        except Exception as e:
            return {"type": "error", "id": request_id, "error": str(e)}

    def _tool_role_link(self, request_id: Optional[str], params: Dict[str, Any]) -> Dict[str, Any]:
        """Tool: Link role to DocShot/Skill/NegativeKnowledge."""
        try:
            name = params.get("name")
            for ds in params.get("docshot_ids") or []:
                self.graph.link_role_docshot(name, ds)
            for sk in params.get("skill_ids") or []:
                self.graph.link_role_skill(name, sk)
            for nk in params.get("nk_ids") or []:
                self.graph.link_role_nk(name, nk)
            return {"type": "tool_result", "id": request_id, "result": {"status": "success"}}
        except Exception as e:
            return {"type": "error", "id": request_id, "error": str(e)}

    def _tool_role_unlink(self, request_id: Optional[str], params: Dict[str, Any]) -> Dict[str, Any]:
        """Tool: Unlink role from DocShot/Skill/NegativeKnowledge."""
        try:
            name = params.get("name")
            for ds in params.get("docshot_ids") or []:
                self.graph.unlink_role_docshot(name, ds)
            for sk in params.get("skill_ids") or []:
                self.graph.unlink_role_skill(name, sk)
            for nk in params.get("nk_ids") or []:
                self.graph.unlink_role_nk(name, nk)
            return {"type": "tool_result", "id": request_id, "result": {"status": "success"}}
        except Exception as e:
            return {"type": "error", "id": request_id, "error": str(e)}

    def _compute_doc_shot_id(self, docs: list) -> str:
        entries = []
        for doc in docs:
            doc_id = doc.get("id") or ""
            updated_at = doc.get("updated_at") or ""
            entries.append(f"{doc_id}:{updated_at}")
        entries.sort()
        payload = "|".join(entries).encode("utf-8")
        return f"docshot_{hashlib.sha1(payload).hexdigest()[:12]}"

    def _tool_record_decision(
        self, request_id: Optional[str], params: Dict[str, Any]
    ) -> Dict[str, Any]:
        """Tool: Record decision."""
        from membria.models import Decision
        import uuid

        try:
            decision = Decision(
                decision_id=f"dec_{uuid.uuid4().hex[:12]}",
                statement=params.get("statement", ""),
                alternatives=params.get("alternatives", []),
                confidence=float(params.get("confidence", 0.5)),
                module=params.get("module", "general"),
            )
            if params.get("role_id"):
                decision.role_id = params.get("role_id")
            if params.get("assignment_id"):
                decision.assignment_id = params.get("assignment_id")

            if self.graph.add_decision(decision):
                session_id = params.get("session_id")
                if session_id and session_id in self.session_docs:
                    doc_ctx = self.session_docs[session_id]
                    try:
                        self.graph.link_decision_docs(
                            decision_id=decision.decision_id,
                            doc_shot_id=doc_ctx.get("doc_shot_id"),
                            docs=doc_ctx.get("docs") or [],
                            fetched_at=doc_ctx.get("fetched_at"),
                        )
                        try:
                            self.graph.update_decision_memory(
                                decision.decision_id,
                                {"factcheck_status": "pending"},
                            )
                        except Exception as e:
                            logger.warning(f"Factcheck status update failed: {e}")
                    except Exception as e:
                        logger.warning(f"Doc traceability failed: {e}")
                logger.info(f"Decision recorded: {decision.decision_id}")
                return {
                    "type": "tool_result",
                    "id": request_id,
                    "result": {
                        "status": "success",
                        "decision_id": decision.decision_id,
                    },
                }
            else:
                return {
                    "type": "error",
                    "id": request_id,
                    "error": "Failed to save decision",
                }
        except Exception as e:
            logger.error(f"Failed to record decision: {e}")
            return {
                "type": "error",
                "id": request_id,
                "error": str(e),
            }

    def _tool_get_context(
        self, request_id: Optional[str], params: Dict[str, Any]
    ) -> Dict[str, Any]:
        """Tool: Get decision context."""
        request = params.get("request", "")
        module = params.get("module", "general")
        confidence = float(params.get("confidence", 0.5))
        max_tokens = int(params.get("max_tokens", 2000))
        session_id = params.get("session_id")
        pending_signals = self.signal_detector.get_pending_signals()

        compact_context = ""
        sections_included = []
        truncated = False
        total_tokens = 0

        try:
            from membria.context_manager import ContextManager
            from membria.calibration_updater import CalibrationUpdater

            calibration = CalibrationUpdater()
            ctx_manager = ContextManager(self.graph, calibration)
            doc_shot = None
            session_ctx = None
            if session_id:
                session_ctx = self.graph.get_session_context(session_id)
                if session_ctx:
                    doc_shot = {
                        "doc_shot_id": session_ctx.get("doc_shot_id"),
                        "count": int(session_ctx.get("doc_count") or 0),
                    }
            ctx = ctx_manager.build_decision_context(
                statement=request,
                module=module,
                confidence=confidence,
                max_tokens=max_tokens,
                include_chains=False,
                doc_shot=doc_shot,
                session_context=session_ctx,
            )
            compact_context = ctx.get("compact_context", "")
            sections_included = ctx.get("sections_included", [])
            truncated = bool(ctx.get("truncated"))
            total_tokens = int(ctx.get("total_tokens") or 0)
        except Exception as exc:
            logger.warning(f"ContextManager unavailable in daemon: {exc}")

        return {
            "type": "tool_result",
            "id": request_id,
            "result": {
                "pending_signals": len(pending_signals),
                "similar_decisions": [],
                "recent_patterns": [],
                "context_ready": True,
                "compact_context": compact_context,
                "total_tokens": total_tokens,
                "truncated": truncated,
                "sections_included": sections_included,
                "doc_shot_id": doc_shot.get("doc_shot_id") if doc_shot else None,
            },
        }

    def _tool_get_calibration(
        self, request_id: Optional[str], params: Dict[str, Any]
    ) -> Dict[str, Any]:
        """Tool: Get calibration metrics."""
        try:
            if not self.calibration_updater:
                return {
                    "type": "tool_result",
                    "id": request_id,
                    "result": {
                        "error": "Calibration updater not available",
                        "calibrated": False,
                    },
                }

            # Fetch team calibration from graph
            domain = params.get("domain", "general")
            team_cal = self.calibration_updater.get_team_calibration(domain)

            if not team_cal:
                return {
                    "type": "tool_result",
                    "id": request_id,
                    "result": {
                        "calibrated": False,
                        "message": f"No calibration data for domain: {domain}",
                    },
                }

            return {
                "type": "tool_result",
                "id": request_id,
                "result": {
                    "calibrated": True,
                    "domain": domain,
                    "success_rate": team_cal.get("success_rate", 0.0),
                    "confidence_avg": team_cal.get("confidence_avg", 0.0),
                    "overconfidence_gap": team_cal.get("overconfidence", 0.0),
                    "sample_size": team_cal.get("sample_size", 0),
                    "trend": team_cal.get("trend", "unknown"),
                },
            }
        except Exception as e:
            logger.error(f"Failed to get calibration: {e}")
            return {
                "type": "error",
                "id": request_id,
                "error": f"Calibration error: {str(e)}",
            }

    def _tool_memory_store(
        self, request_id: Optional[str], params: Dict[str, Any]
    ) -> Dict[str, Any]:
        """Tool: memory_store."""
        try:
            if not self.memory_tools_enabled or not self.memory_manager:
                return {"type": "error", "id": request_id, "error": "Memory tools disabled"}

            mem_type = params.get("memory_type")
            payload = params.get("payload") or {}
            ttl_days = params.get("ttl_days")

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
                ok = self.memory_manager.store_decision(decision, ttl_days=ttl_days)
                if not ok:
                    return {"type": "error", "id": request_id, "error": "Failed to store decision"}
                return {"type": "tool_result", "id": request_id, "result": {"status": "success", "item_id": decision.decision_id}}

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
                    return {"type": "error", "id": request_id, "error": "Failed to store negative knowledge"}
                return {"type": "tool_result", "id": request_id, "result": {"status": "success", "item_id": nk.nk_id}}

            return {"type": "error", "id": request_id, "error": "Unknown memory_type"}
        except Exception as e:
            return {"type": "error", "id": request_id, "error": str(e)}

    def _tool_memory_retrieve(
        self, request_id: Optional[str], params: Dict[str, Any]
    ) -> Dict[str, Any]:
        """Tool: memory_retrieve."""
        try:
            if not self.memory_tools_enabled or not self.memory_manager:
                return {"type": "error", "id": request_id, "error": "Memory tools disabled"}

            mem_type = params.get("memory_type")
            domain = params.get("domain")
            limit = int(params.get("limit", 5))

            if mem_type == "decision":
                if not domain:
                    return {"type": "error", "id": request_id, "error": "domain required for decision"}
                items = self.memory_manager.retrieve_decisions(domain=domain, limit=limit)
                return {"type": "tool_result", "id": request_id, "result": {"status": "success", "items": [i.__dict__ for i in items]}}

            if mem_type == "negative_knowledge":
                items = self.memory_manager.retrieve_negative_knowledge(domain=domain, limit=limit)
                return {"type": "tool_result", "id": request_id, "result": {"status": "success", "items": items}}

            return {"type": "error", "id": request_id, "error": "Unknown memory_type"}
        except Exception as e:
            return {"type": "error", "id": request_id, "error": str(e)}

    def _tool_memory_delete(
        self, request_id: Optional[str], params: Dict[str, Any]
    ) -> Dict[str, Any]:
        """Tool: memory_delete."""
        try:
            if not self.memory_tools_enabled or not self.memory_manager:
                return {"type": "error", "id": request_id, "error": "Memory tools disabled"}

            mem_type = params.get("memory_type")
            item_id = params.get("item_id")
            reason = params.get("reason", "manual_delete")

            if mem_type == "decision":
                ok = self.memory_manager.forget_decision(item_id, reason)
                return {"type": "tool_result", "id": request_id, "result": {"status": "success" if ok else "failed", "item_id": item_id}}

            if mem_type == "negative_knowledge":
                ok = self.memory_manager.forget_negative_knowledge(item_id, reason)
                return {"type": "tool_result", "id": request_id, "result": {"status": "success" if ok else "failed", "item_id": item_id}}

            return {"type": "error", "id": request_id, "error": "Unknown memory_type"}
        except Exception as e:
            return {"type": "error", "id": request_id, "error": str(e)}

    def _tool_memory_list(
        self, request_id: Optional[str], params: Dict[str, Any]
    ) -> Dict[str, Any]:
        """Tool: memory_list."""
        return self._tool_memory_retrieve(request_id, params)

    def _tool_session_context_store(
        self, request_id: Optional[str], params: Dict[str, Any]
    ) -> Dict[str, Any]:
        try:
            ok = self.graph.upsert_session_context(
                session_id=params.get("session_id"),
                task=params.get("task"),
                focus=params.get("focus"),
                current_plan=params.get("current_plan"),
                constraints=params.get("constraints") or [],
                doc_shot_id=params.get("doc_shot_id"),
                ttl_days=int(params.get("ttl_days", 3)),
            )
            return {"type": "tool_result", "id": request_id, "result": {"status": "success" if ok else "failed", "items": []}}
        except Exception as e:
            return {"type": "error", "id": request_id, "error": str(e)}

    def _tool_session_context_retrieve(
        self, request_id: Optional[str], params: Dict[str, Any]
    ) -> Dict[str, Any]:
        try:
            session_id = params.get("session_id")
            if session_id:
                item = self.graph.get_session_context(session_id)
                items = [item] if item else []
            else:
                items = self.graph.list_session_contexts(limit=int(params.get("limit", 5)))
            return {"type": "tool_result", "id": request_id, "result": {"status": "success", "items": items}}
        except Exception as e:
            return {"type": "error", "id": request_id, "error": str(e)}

    def _tool_session_context_delete(
        self, request_id: Optional[str], params: Dict[str, Any]
    ) -> Dict[str, Any]:
        try:
            ok = self.graph.deactivate_session_context(params.get("session_id"))
            return {"type": "tool_result", "id": request_id, "result": {"status": "success" if ok else "failed", "items": []}}
        except Exception as e:
            return {"type": "error", "id": request_id, "error": str(e)}

    def _tool_docs_add(
        self, request_id: Optional[str], params: Dict[str, Any]
    ) -> Dict[str, Any]:
        try:
            from membria.graph_schema import DocumentNodeSchema
            now_ts = int(__import__("time").time())
            cfg = ConfigManager().config
            doc = DocumentNodeSchema(
                id=f"doc_{__import__('hashlib').sha1(params['file_path'].encode()).hexdigest()[:10]}_{now_ts}",
                file_path=params.get("file_path"),
                content=params.get("content"),
                doc_type=params.get("doc_type", "kb"),
                created_at=now_ts,
                updated_at=now_ts,
                metadata=params.get("metadata") or {},
                tenant_id=getattr(cfg, "tenant_id", "default"),
                team_id=getattr(cfg, "team_id", "default"),
                project_id=getattr(cfg, "project_id", "default"),
            )
            ok = self.graph.add_document(doc)
            return {"type": "tool_result", "id": request_id, "result": {"status": "success" if ok else "failed", "items": [{"id": doc.id}]}}
        except Exception as e:
            return {"type": "error", "id": request_id, "error": str(e)}

    def _tool_docs_get(
        self, request_id: Optional[str], params: Dict[str, Any]
    ) -> Dict[str, Any]:
        try:
            docs = self.graph.get_documents(
                doc_types=params.get("doc_types"),
                file_paths=params.get("file_paths"),
                doc_ids=params.get("doc_ids"),
                limit=int(params.get("limit", 10)),
            )
            return {"type": "tool_result", "id": request_id, "result": {"status": "success", "items": docs}}
        except Exception as e:
            return {"type": "error", "id": request_id, "error": str(e)}

    def _tool_docs_list(
        self, request_id: Optional[str], params: Dict[str, Any]
    ) -> Dict[str, Any]:
        return self._tool_docs_get(request_id, params)

    def _tool_docshot_link(
        self, request_id: Optional[str], params: Dict[str, Any]
    ) -> Dict[str, Any]:
        try:
            ok = self.graph.link_decision_docs(
                decision_id=params.get("decision_id"),
                doc_shot_id=params.get("doc_shot_id"),
                docs=params.get("docs") or [],
                fetched_at=params.get("fetched_at"),
            )
            return {"type": "tool_result", "id": request_id, "result": {"status": "success" if ok else "failed", "decision_id": params.get("decision_id"), "doc_shot_id": params.get("doc_shot_id")}}
        except Exception as e:
            return {"type": "error", "id": request_id, "error": str(e)}

    def _tool_outcome_get(
        self, request_id: Optional[str], params: Dict[str, Any]
    ) -> Dict[str, Any]:
        try:
            item = self.graph.get_outcome(params.get("outcome_id"))
            return {"type": "tool_result", "id": request_id, "result": {"status": "success", "item": item}}
        except Exception as e:
            return {"type": "error", "id": request_id, "error": str(e)}

    def _tool_outcome_list(
        self, request_id: Optional[str], params: Dict[str, Any]
    ) -> Dict[str, Any]:
        try:
            items = self.graph.list_outcomes(limit=int(params.get("limit", 10)), status=params.get("status"))
            return {"type": "tool_result", "id": request_id, "result": {"status": "success", "items": items}}
        except Exception as e:
            return {"type": "error", "id": request_id, "error": str(e)}

    def _tool_skills_list(
        self, request_id: Optional[str], params: Dict[str, Any]
    ) -> Dict[str, Any]:
        try:
            from membria.graph_queries import SkillQueries
            domain = params.get("domain")
            min_quality = float(params.get("min_quality", 0.5))
            if domain:
                query, query_params = SkillQueries.get_skills_for_domain(domain, min_quality=min_quality)
            else:
                query, query_params = SkillQueries.get_skills_by_quality(min_quality=min_quality)
            rows = self.graph.query(query, query_params) or []
            return {"type": "tool_result", "id": request_id, "result": {"status": "success", "items": rows[: int(params.get("limit", 20))]}}
        except Exception as e:
            return {"type": "error", "id": request_id, "error": str(e)}

    def _tool_skills_get(
        self, request_id: Optional[str], params: Dict[str, Any]
    ) -> Dict[str, Any]:
        try:
            from membria.graph_queries import SkillQueries
            query, query_params = SkillQueries.get_latest_skill_version(params.get("domain"), params.get("name"))
            rows = self.graph.query(query, query_params) or []
            return {"type": "tool_result", "id": request_id, "result": {"status": "success", "items": rows[:1]}}
        except Exception as e:
            return {"type": "error", "id": request_id, "error": str(e)}

    def _tool_antipatterns_list(
        self, request_id: Optional[str], params: Dict[str, Any]
    ) -> Dict[str, Any]:
        try:
            items = self.graph.list_antipatterns(limit=int(params.get("limit", 20)), category=params.get("category"))
            return {"type": "tool_result", "id": request_id, "result": {"status": "success", "items": items}}
        except Exception as e:
            return {"type": "error", "id": request_id, "error": str(e)}

    def _tool_antipatterns_get(
        self, request_id: Optional[str], params: Dict[str, Any]
    ) -> Dict[str, Any]:
        try:
            item = self.graph.get_antipattern(params.get("pattern_id"))
            return {"type": "tool_result", "id": request_id, "result": {"status": "success", "items": [item] if item else []}}
        except Exception as e:
            return {"type": "error", "id": request_id, "error": str(e)}

    def _tool_health(self, request_id: Optional[str]) -> Dict[str, Any]:
        try:
            return {"type": "tool_result", "id": request_id, "result": {"status": "success", "health": self.graph.health_check()}}
        except Exception as e:
            return {"type": "error", "id": request_id, "error": str(e)}

    def _tool_migrations_status(self, request_id: Optional[str]) -> Dict[str, Any]:
        try:
            from membria.migrations.migrator import Migrator
            migrator = Migrator(self.graph.db_instance)
            current = migrator.get_current_version()
            pending = len(migrator.get_pending_migrations())
            return {"type": "tool_result", "id": request_id, "result": {"status": "success", "current_version": current, "pending": pending}}
        except Exception as e:
            return {"type": "error", "id": request_id, "error": str(e)}

    def _tool_logs_tail(self, request_id: Optional[str], params: Dict[str, Any]) -> Dict[str, Any]:
        try:
            from membria.process_manager import ProcessManager
            lines = int(params.get("lines", 50))
            logs = ProcessManager().get_logs(lines=lines)
            return {"type": "tool_result", "id": request_id, "result": {"status": "success", "logs": logs}}
        except Exception as e:
            return {"type": "error", "id": request_id, "error": str(e)}

    def _handle_capture_session(
        self, request_id: Optional[str], prompt: str, response: str
    ) -> Dict[str, Any]:
        """Handle session capture (auto-detection)."""
        result = capture_mcp_session(prompt, response)

        return {
            "type": "session_captured",
            "id": request_id,
            "signals_detected": result["signals_detected"],
            "signals": result["signals"],
        }

    def _start_batch_processor(self) -> None:
        """Start background batch processing thread."""
        def processor():
            logger.info("Batch processor started")
            while self.running:
                try:
                    # Check if it's time to extract (every hour)
                    now = datetime.now()
                    if (now - self.last_extraction).total_seconds() >= self.extraction_interval:
                        self._process_pending_signals()
                        self.last_extraction = now

                    if (now - self.last_forget).total_seconds() >= self.forget_interval:
                        self._forget_expired_memory()
                        self.last_forget = now

                    # Sleep 5 seconds before checking again
                    time.sleep(5)

                except Exception as e:
                    logger.error(f"Batch processor error: {e}")

        self.batch_thread = threading.Thread(target=processor, daemon=True)
        self.batch_thread.start()

    def _start_health_monitor(self) -> None:
        """Start background health monitoring."""
        def monitor():
            logger.info("Health monitor started")
            while self.running:
                try:
                    # Check graph health
                    health = self.graph.health_check()
                    if health["status"] != "healthy":
                        logger.warning(f"Graph unhealthy: {health['status']}")

                    # Check pending signals
                    pending = self.signal_detector.get_pending_signals()
                    if pending:
                        logger.debug(f"Pending signals: {len(pending)}")

                    time.sleep(30)

                except Exception as e:
                    logger.error(f"Health monitor error: {e}")

        self.health_thread = threading.Thread(target=monitor, daemon=True)
        self.health_thread.start()

    def _process_pending_signals(self) -> None:
        """Process pending signals with Haiku extraction."""
        try:
            pending = self.signal_detector.get_pending_signals()
            if not pending:
                return

            logger.info(f"Processing {len(pending)} pending signals...")

            # Use Haiku for batch extraction
            extracted = self.haiku_extractor.batch_extract(pending)
            logger.info(f"Extracted {len(extracted)} decisions")

            # Save to graph
            from membria.models import Decision
            import uuid

            for ext in extracted:
                try:
                    decision = Decision(
                        decision_id=f"dec_{uuid.uuid4().hex[:12]}",
                        statement=ext.get("decision_statement", ""),
                        alternatives=ext.get("alternatives", []),
                        confidence=float(ext.get("confidence", 0.5)),
                        module=ext.get("module", "general"),
                    )

                    if self.graph.add_decision(decision):
                        self.signal_detector.mark_extracted(
                            ext["signal_id"], decision.decision_id
                        )
                        logger.debug(f"Saved decision: {decision.decision_id}")

                except Exception as e:
                    logger.error(f"Failed to save extracted decision: {e}")

        except Exception as e:
            logger.error(f"Pending signal processing failed: {e}")

    def _forget_expired_memory(self) -> None:
        """Deactivate memory records whose TTL has expired."""
        try:
            now_ts = int(datetime.utcnow().timestamp())
            dec_count = self.graph.deactivate_expired_decisions(now_ts)
            nk_count = self.graph.deactivate_expired_negative_knowledge(now_ts)
            out_count = self.graph.deactivate_expired_outcomes(now_ts)
            sk_count = self.graph.deactivate_expired_skills(now_ts)
            sc_count = self.graph.deactivate_expired_session_context(now_ts)
            if dec_count or nk_count or out_count or sk_count or sc_count:
                logger.info(
                    "Memory TTL sweep: decisions=%s, negative_knowledge=%s, outcomes=%s, skills=%s, session_context=%s",
                    dec_count,
                    nk_count,
                    out_count,
                    sk_count,
                    sc_count,
                )
        except Exception as e:
            logger.error(f"Memory TTL sweep failed: {e}")


def main():
    """Run MCP daemon."""
    # Setup logging
    log_dir = Path.home() / ".membria" / "logs"
    log_dir.mkdir(parents=True, exist_ok=True)

    logging.basicConfig(
        level=logging.INFO,
        format="%(asctime)s - %(name)s - %(levelname)s - %(message)s",
        handlers=[
            logging.FileHandler(log_dir / "daemon.log"),
            logging.StreamHandler(sys.stderr),
        ],
    )

    logger.info("MCP Daemon starting...")

    # Create and start daemon
    daemon = MCPDaemonServer()

    # Handle graceful shutdown
    def signal_handler(signum, frame):
        logger.info(f"Received signal {signum}")
        daemon.stop()
        sys.exit(0)

    signal.signal(signal.SIGTERM, signal_handler)
    signal.signal(signal.SIGINT, signal_handler)

    try:
        daemon.start()
    except Exception as e:
        logger.error(f"Daemon error: {e}", exc_info=True)
        sys.exit(1)


if __name__ == "__main__":
    main()
