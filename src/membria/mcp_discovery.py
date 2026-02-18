"""External MCP tool discovery (HTTP JSON-RPC)."""

from __future__ import annotations

import json
import time
from dataclasses import dataclass
from pathlib import Path
from typing import Any, Dict, List, Optional, Tuple

import httpx


@dataclass
class ExternalServer:
    server_id: str
    base_url: str
    auth_header: Optional[str] = None


class ExternalToolRegistry:
    """Fetch and proxy tools from external MCP servers (HTTP)."""

    def __init__(self, allowlist_path: str, timeout_sec: int = 8, refresh_sec: int = 600):
        self.allowlist_path = Path(allowlist_path).expanduser().resolve()
        self.timeout_sec = timeout_sec
        self.refresh_sec = refresh_sec
        self._servers: List[ExternalServer] = []
        self._tools: Dict[str, Dict[str, Any]] = {}
        self._tool_to_server: Dict[str, ExternalServer] = {}
        self._last_refresh = 0.0

    def load_allowlist(self) -> List[ExternalServer]:
        if not self.allowlist_path.exists():
            self._servers = []
            return self._servers
        with open(self.allowlist_path, "r") as f:
            data = json.load(f)
        servers = data.get("servers") if isinstance(data, dict) else data
        parsed: List[ExternalServer] = []
        for item in servers or []:
            server_id = (item or {}).get("id")
            base_url = (item or {}).get("base_url")
            if not server_id or not base_url:
                continue
            parsed.append(ExternalServer(server_id=server_id, base_url=base_url, auth_header=item.get("auth_header")))
        self._servers = parsed
        return parsed

    def _should_refresh(self) -> bool:
        return (time.time() - self._last_refresh) > self.refresh_sec

    def refresh(self) -> None:
        if self._last_refresh and not self._should_refresh():
            return
        self.load_allowlist()
        self._tools = {}
        self._tool_to_server = {}
        for server in self._servers:
            try:
                tools = self._fetch_tools(server)
            except Exception:
                continue
            for tool in tools:
                name = tool.get("name")
                if not name:
                    continue
                ext_name = f"ext.{server.server_id}.{name}"
                tool_def = dict(tool)
                tool_def["name"] = ext_name
                self._tools[ext_name] = tool_def
                self._tool_to_server[ext_name] = server
        self._last_refresh = time.time()

    def list_tools(self) -> List[Dict[str, Any]]:
        self.refresh()
        return list(self._tools.values())

    def call_tool(self, tool_name: str, arguments: Dict[str, Any]) -> Dict[str, Any]:
        self.refresh()
        server = self._tool_to_server.get(tool_name)
        if not server:
            return {"error": {"code": -32601, "message": f"Unknown external tool: {tool_name}"}}
        raw_name = tool_name.split(".", 2)[2]
        req = {"jsonrpc": "2.0", "id": "ext-call", "method": "tools/call", "params": {"name": raw_name, "arguments": arguments}}
        return self._post(server, req)

    def _fetch_tools(self, server: ExternalServer) -> List[Dict[str, Any]]:
        req = {"jsonrpc": "2.0", "id": "ext-tools", "method": "tools/list", "params": {}}
        resp = self._post(server, req)
        tools = (resp.get("result") or {}).get("tools") or []
        return tools

    def _post(self, server: ExternalServer, payload: Dict[str, Any]) -> Dict[str, Any]:
        headers = {"Content-Type": "application/json"}
        if server.auth_header:
            headers["Authorization"] = server.auth_header
        with httpx.Client(timeout=self.timeout_sec, follow_redirects=True) as client:
            resp = client.post(server.base_url, headers=headers, json=payload)
            resp.raise_for_status()
            return resp.json()
