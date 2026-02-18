"""Tests for MCP Server."""

import pytest
import json
from membria.mcp_server import MembriaMCPServer, MCPResponse


class TestMCPServer:
    """Test MCP Server implementation."""

    def test_mcp_initialize(self):
        """Test server initialization."""
        server = MembriaMCPServer()
        request = {
            "jsonrpc": "2.0",
            "id": "init-1",
            "method": "initialize",
            "params": {}
        }
        response = server.handle_request(request)
        
        assert response.id == "init-1"
        assert response.result is not None
        assert response.result["protocolVersion"] == "2024-11-25"
        assert response.result["capabilities"]["tools"] is True

    def test_capture_decision(self):
        """Test capturing a decision."""
        server = MembriaMCPServer()
        request = {
            "jsonrpc": "2.0",
            "id": "cap-1",
            "method": "tools/call",
            "params": {
                "name": "membria.capture_decision",
                "arguments": {
                    "statement": "Use PostgreSQL for user database",
                    "alternatives": ["MongoDB", "SQLite"],
                    "confidence": 0.82,
                    "context": {"module": "database"}
                }
            }
        }
        response = server.handle_request(request)
        
        assert response.id == "cap-1"
        assert response.error is None
        assert "content" in response.result
        content = json.loads(response.result["content"][0]["text"])
        assert "decision_id" in content
        assert content["status"] == "pending"

    def test_capture_decision_missing_statement(self):
        """Test capture without statement."""
        server = MembriaMCPServer()
        request = {
            "jsonrpc": "2.0",
            "id": "cap-2",
            "method": "tools/call",
            "params": {
                "name": "membria.capture_decision",
                "arguments": {
                    "alternatives": ["Alt1"],
                    "confidence": 0.75
                }
            }
        }
        response = server.handle_request(request)
        
        assert response.error is not None
        assert response.error["code"] == -32602

    def test_record_outcome(self):
        """Test recording outcome."""
        server = MembriaMCPServer()
        request = {
            "jsonrpc": "2.0",
            "id": "out-1",
            "method": "tools/call",
            "params": {
                "name": "membria.record_outcome",
                "arguments": {
                    "decision_id": "dec_test_001",
                    "final_status": "success",
                    "final_score": 0.87,
                    "decision_domain": "database"
                }
            }
        }
        response = server.handle_request(request)
        
        assert response.id == "out-1"
        assert response.error is None
        content = json.loads(response.result["content"][0]["text"])
        assert content["final_status"] == "success"

    def test_get_calibration(self):
        """Test getting calibration."""
        server = MembriaMCPServer()
        request = {
            "jsonrpc": "2.0",
            "id": "cal-1",
            "method": "tools/call",
            "params": {
                "name": "membria.get_calibration",
                "arguments": {"domain": "database"}
            }
        }
        response = server.handle_request(request)
        
        assert response.error is None
        content = json.loads(response.result["content"][0]["text"])
        assert "domain" in content

    def test_get_decision_context(self):
        """Test getting decision context."""
        server = MembriaMCPServer()
        request = {
            "jsonrpc": "2.0",
            "id": "ctx-1",
            "method": "tools/call",
            "params": {
                "name": "membria.get_decision_context",
                "arguments": {
                    "statement": "Use PostgreSQL",
                    "module": "database",
                    "confidence": 0.75
                }
            }
        }
        response = server.handle_request(request)
        
        assert response.error is None
        content = json.loads(response.result["content"][0]["text"])
        assert content["decision_statement"] == "Use PostgreSQL"

    def test_unknown_tool(self):
        """Test calling unknown tool."""
        server = MembriaMCPServer()
        request = {
            "jsonrpc": "2.0",
            "id": "unk-1",
            "method": "tools/call",
            "params": {
                "name": "membria.unknown_tool",
                "arguments": {}
            }
        }
        response = server.handle_request(request)
        
        assert response.error is not None
        assert response.error["code"] == -32601

    def test_mcp_response_formatting(self):
        """Test MCP response JSON formatting."""
        response = MCPResponse(request_id="test-1", result={"key": "value"})
        json_str = response.to_json()
        
        data = json.loads(json_str)
        assert data["jsonrpc"] == "2.0"
        assert data["id"] == "test-1"
        assert data["result"] == {"key": "value"}

    def test_mcp_error_response_formatting(self):
        """Test MCP error response formatting."""
        response = MCPResponse(
            request_id="err-1",
            error={"code": -32602, "message": "Invalid params"}
        )
        json_str = response.to_json()
        
        data = json.loads(json_str)
        assert data["error"]["code"] == -32602
        assert "result" not in data
