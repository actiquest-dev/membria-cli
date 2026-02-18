"""Test ExpertRegistry graph fallback mechanism."""

import unittest
from unittest.mock import patch, MagicMock
from membria.interactive.expert_registry import ExpertRegistry


class TestExpertRegistryGraphFallback(unittest.TestCase):
    """Test that ExpertRegistry correctly falls back to graph for custom roles."""

    def test_get_expert_hardcoded_role(self):
        """Hardcoded roles should return immediately."""
        expert = ExpertRegistry.get_expert("architect")
        assert expert["name"] == "System Architect"
        assert "scalability" in expert["prompt"].lower()

    def test_get_expert_unknown_role_no_graph(self):
        """Unknown role with no graph should fallback to implementer."""
        with patch.object(ExpertRegistry, '_get_graph_role', return_value={}):
            expert = ExpertRegistry.get_expert("unknown_role")
            # Should fallback to implementer
            assert expert["name"] == "Senior Software Engineer"

    def test_get_expert_from_graph(self):
        """Unknown role found in graph should use graph data."""
        mock_graph_role = {
            "id": "role_investigator",
            "name": "Incident Investigator",
            "description": "Traces root causes",
            "prompt_path": "/path/to/prompt.md"
        }

        with patch.object(ExpertRegistry, '_get_graph_role', return_value=mock_graph_role):
            with patch.object(ExpertRegistry, '_load_prompt_from_path', return_value="Custom prompt from file"):
                expert = ExpertRegistry.get_expert("investigator")
                assert expert["name"] == "Incident Investigator"
                assert expert["description"] == "Traces root causes"
                assert expert["prompt"] == "Custom prompt from file"

    def test_get_expert_custom_config_overrides(self):
        """Custom config should override defaults."""
        mock_config_agents = {
            "architect": {
                "model": "claude-opus-4.6",
                "provider": "anthropic"
            }
        }

        with patch.object(ExpertRegistry, '_get_custom_experts', return_value=mock_config_agents):
            expert = ExpertRegistry.get_expert("architect")
            assert expert.get("model") == "claude-opus-4.6"
            assert expert.get("provider") == "anthropic"

    def test_graph_fallback_tries_connection(self):
        """Graph fallback should attempt connection even if it fails gracefully."""
        with patch('membria.interactive.expert_registry.GraphClient') as mock_graph_class:
            mock_graph = MagicMock()
            mock_graph.connect.return_value = False
            mock_graph_class.return_value = mock_graph

            # Should not raise, should return empty dict
            result = ExpertRegistry._get_graph_role("investigator")
            assert result == {}
            mock_graph.connect.assert_called_once()

    def test_load_prompt_from_path_missing_file(self):
        """Loading prompt from non-existent path should return empty string."""
        result = ExpertRegistry._load_prompt_from_path("/nonexistent/path/prompt.md")
        assert result == ""

    def test_load_prompt_from_path_valid_file(self):
        """Loading prompt from valid file should return content."""
        import tempfile
        with tempfile.NamedTemporaryFile(mode='w', suffix='.md', delete=False) as f:
            f.write("Test prompt content")
            f.flush()

            result = ExpertRegistry._load_prompt_from_path(f.name)
            assert result == "Test prompt content"

            import os
            os.unlink(f.name)

    def test_list_roles_includes_hardcoded_and_custom(self):
        """list_roles should return hardcoded + custom roles."""
        mock_config_agents = {"custom_role": {}}

        with patch.object(ExpertRegistry, '_get_custom_experts', return_value=mock_config_agents):
            roles = ExpertRegistry.list_roles()
            assert "architect" in roles  # hardcoded
            assert "custom_role" in roles  # custom


if __name__ == "__main__":
    unittest.main()
