"""Tests for MCP server Plan Mode integration."""

import pytest
import json
from membria.mcp_server import MembriaMCPServer, MCPResponse, MembriaToolHandler


class TestMCPPlanModeTools:
    """Test MCP server Plan Mode tools."""

    def test_handler_initialization(self):
        """Test handler has Plan Mode tools."""
        handler = MembriaToolHandler()
        assert hasattr(handler, 'get_plan_context')
        assert hasattr(handler, 'validate_plan')
        assert hasattr(handler, 'record_plan')

    def test_get_plan_context_requires_domain(self):
        """Test get_plan_context requires domain."""
        handler = MembriaToolHandler()
        result = handler.get_plan_context({})
        assert "error" in result
        assert result["error"]["code"] == -32602

    def test_get_plan_context_with_domain(self):
        """Test get_plan_context with domain."""
        handler = MembriaToolHandler()
        result = handler.get_plan_context({"domain": "database"})
        assert "error" not in result
        assert "domain" in result
        assert result["domain"] == "database"

    def test_get_plan_context_with_scope(self):
        """Test get_plan_context with optional scope."""
        handler = MembriaToolHandler()
        result = handler.get_plan_context({
            "domain": "auth",
            "scope": "JWT implementation"
        })
        assert "error" not in result
        assert "domain" in result

    def test_get_plan_context_structure(self):
        """Test get_plan_context response structure."""
        handler = MembriaToolHandler()
        result = handler.get_plan_context({"domain": "api"})

        expected_keys = [
            "domain", "formatted", "total_tokens",
            "past_plans", "failed_approaches", "successful_patterns",
            "calibration", "constraints", "recommendations"
        ]

        for key in expected_keys:
            assert key in result

    def test_validate_plan_requires_steps(self):
        """Test validate_plan requires steps."""
        handler = MembriaToolHandler()
        result = handler.validate_plan({})
        assert "error" in result
        assert result["error"]["code"] == -32602

    def test_validate_plan_steps_must_be_list(self):
        """Test validate_plan steps must be list."""
        handler = MembriaToolHandler()
        result = handler.validate_plan({"steps": "not a list"})
        assert "error" in result

    def test_validate_plan_with_steps(self):
        """Test validate_plan with steps."""
        handler = MembriaToolHandler()
        result = handler.validate_plan({
            "steps": ["Step 1", "Step 2"]
        })
        assert "error" not in result
        assert "total_steps" in result
        assert result["total_steps"] == 2

    def test_validate_plan_with_domain(self):
        """Test validate_plan with domain context."""
        handler = MembriaToolHandler()
        result = handler.validate_plan({
            "steps": ["Use PostgreSQL", "Set up ORM"],
            "domain": "database"
        })
        assert "error" not in result
        assert "warnings_count" in result

    def test_validate_plan_structure(self):
        """Test validate_plan response structure."""
        handler = MembriaToolHandler()
        result = handler.validate_plan({
            "steps": ["Plan step"]
        })

        expected_keys = [
            "total_steps", "warnings_count",
            "high_severity", "medium_severity", "low_severity",
            "can_proceed", "warnings", "timestamp"
        ]

        for key in expected_keys:
            assert key in result

    def test_validate_plan_can_proceed_flag(self):
        """Test validate_plan can_proceed flag."""
        handler = MembriaToolHandler()
        result = handler.validate_plan({
            "steps": ["Simple step"]
        })

        assert "can_proceed" in result
        assert isinstance(result["can_proceed"], bool)
        # If no high severity warnings, should be able to proceed
        if result["high_severity"] == 0:
            assert result["can_proceed"] is True

    def test_record_plan_requires_plan_steps(self):
        """Test record_plan requires plan_steps."""
        handler = MembriaToolHandler()
        result = handler.record_plan({})
        assert "error" in result

    def test_record_plan_requires_domain(self):
        """Test record_plan requires domain."""
        handler = MembriaToolHandler()
        result = handler.record_plan({"plan_steps": []})
        assert "error" in result

    def test_record_plan_steps_must_be_list(self):
        """Test record_plan steps must be list."""
        handler = MembriaToolHandler()
        result = handler.record_plan({
            "plan_steps": "not a list",
            "domain": "database"
        })
        assert "error" in result

    def test_record_plan_basic(self):
        """Test record_plan with basic parameters."""
        handler = MembriaToolHandler()
        result = handler.record_plan({
            "plan_steps": ["Step 1", "Step 2"],
            "domain": "auth"
        })
        assert "error" not in result
        assert "engram_id" in result
        assert "decisions_recorded" in result

    def test_record_plan_with_confidence(self):
        """Test record_plan with confidence."""
        handler = MembriaToolHandler()
        result = handler.record_plan({
            "plan_steps": ["Create API"],
            "domain": "api",
            "plan_confidence": 0.85
        })
        assert "error" not in result
        assert result["plan_confidence"] == 0.85

    def test_record_plan_with_duration(self):
        """Test record_plan with duration estimate."""
        handler = MembriaToolHandler()
        result = handler.record_plan({
            "plan_steps": ["Setup"],
            "domain": "database",
            "duration_estimate": "4 hours"
        })
        assert "error" not in result
        assert result["duration_estimate"] == "4 hours"

    def test_record_plan_with_warnings(self):
        """Test record_plan with warnings impact."""
        handler = MembriaToolHandler()
        result = handler.record_plan({
            "plan_steps": ["Step 1"],
            "domain": "auth",
            "warnings_shown": 2,
            "warnings_heeded": 1
        })
        assert "error" not in result
        assert result["warnings_impact"]["shown"] == 2
        assert result["warnings_impact"]["heeded"] == 1

    def test_record_plan_structure(self):
        """Test record_plan response structure."""
        handler = MembriaToolHandler()
        result = handler.record_plan({
            "plan_steps": ["Step 1", "Step 2"],
            "domain": "database"
        })

        expected_keys = [
            "engram_id", "domain", "plan_steps",
            "plan_confidence", "duration_estimate",
            "warnings_impact", "decisions_recorded",
            "status", "message"
        ]

        for key in expected_keys:
            assert key in result

    def test_record_plan_generates_decision_ids(self):
        """Test record_plan generates decision IDs."""
        handler = MembriaToolHandler()
        result = handler.record_plan({
            "plan_steps": ["Step 1", "Step 2", "Step 3"],
            "domain": "api"
        })

        decisions = result["decisions_recorded"]
        assert len(decisions) == 3

        # Each decision should have required fields
        for i, decision in enumerate(decisions):
            assert decision["step"] == i + 1
            assert "decision_id" in decision
            assert decision["decision_id"].startswith("dec_")


class TestMCPServerIntegration:
    """Test MCP server integration with Plan Mode."""

    def test_server_initialization(self):
        """Test server has Plan Mode tools registered."""
        server = MembriaMCPServer()
        assert "membria.get_plan_context" in server.tools
        assert "membria.validate_plan" in server.tools
        assert "membria.record_plan" in server.tools

    def test_handle_get_plan_context_request(self):
        """Test handling get_plan_context MCP request."""
        server = MembriaMCPServer()
        request = {
            "id": "1",
            "method": "tools/call",
            "params": {
                "name": "membria.get_plan_context",
                "arguments": {"domain": "database"}
            }
        }

        response = server.handle_request(request)
        assert response.id == "1"
        assert response.error is None
        assert response.result is not None

    def test_handle_validate_plan_request(self):
        """Test handling validate_plan MCP request."""
        server = MembriaMCPServer()
        request = {
            "id": "2",
            "method": "tools/call",
            "params": {
                "name": "membria.validate_plan",
                "arguments": {"steps": ["Step 1", "Step 2"]}
            }
        }

        response = server.handle_request(request)
        assert response.id == "2"
        assert response.error is None
        assert response.result is not None

    def test_handle_record_plan_request(self):
        """Test handling record_plan MCP request."""
        server = MembriaMCPServer()
        request = {
            "id": "3",
            "method": "tools/call",
            "params": {
                "name": "membria.record_plan",
                "arguments": {
                    "plan_steps": ["Step 1"],
                    "domain": "auth"
                }
            }
        }

        response = server.handle_request(request)
        assert response.id == "3"
        assert response.error is None
        assert response.result is not None

    def test_mcp_response_to_json(self):
        """Test MCPResponse JSON serialization."""
        response = MCPResponse(
            request_id="123",
            result={"data": "test"}
        )
        json_str = response.to_json()
        data = json.loads(json_str)

        assert data["jsonrpc"] == "2.0"
        assert data["id"] == "123"
        assert "result" in data

    def test_existing_tools_still_work(self):
        """Test that existing tools still work."""
        server = MembriaMCPServer()
        assert "membria.capture_decision" in server.tools
        assert "membria.record_outcome" in server.tools
        assert "membria.get_calibration" in server.tools
        assert "membria.get_decision_context" in server.tools
