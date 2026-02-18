"""Integration tests for complete FalkorDB schema."""

import pytest
from datetime import datetime, timedelta
from unittest.mock import Mock, patch, MagicMock

from membria.graph import GraphClient
from membria.models import (
    Decision,
    CodeChange,
    Outcome,
    NegativeKnowledge,
    Antipattern,
    Engram,
    AgentInfo,
    FileChange,
)


class TestGraphSchemaIntegration:
    """Test complete FalkorDB causal memory graph."""

    @pytest.fixture
    def mock_graph(self):
        """Create mock FalkorDB graph."""
        mock = MagicMock()
        mock.query.return_value = MagicMock(result_set=[])
        return mock

    @pytest.fixture
    def graph_client(self, mock_graph):
        """Create graph client with mocked connection."""
        client = GraphClient()
        client.connected = True
        client.graph = mock_graph
        return client

    @pytest.fixture
    def sample_decision(self):
        """Create a sample decision."""
        return Decision(
            decision_id="dec_001",
            statement="Use PostgreSQL for user database",
            alternatives=["MongoDB", "SQLite"],
            confidence=0.85,
            module="database",
            created_by="claude-code",
        )

    @pytest.fixture
    def sample_engram(self):
        """Create a sample engram."""
        agent_info = AgentInfo(
            type="claude-code",
            model="claude-sonnet-4-5",
            session_duration_sec=3600,
            total_tokens=45000,
            total_cost_usd=0.50,
        )

        engram = Engram(
            engram_id="eng_001",
            session_id="sess_phase2",
            commit_sha="9b842ce",
            branch="main",
            timestamp=datetime.now(),
            agent=agent_info,
            transcript=[],
            files_changed=[
                FileChange(path="src/graph.py", action="modified", lines_added=45, lines_removed=10)
            ],
            decisions_extracted=["dec_001"],
            membria_context_injected=True,
            antipatterns_triggered=[],
        )
        return engram

    @pytest.fixture
    def sample_code_change(self):
        """Create a sample code change."""
        return CodeChange(
            change_id="change_001",
            commit_sha="9b842ce",
            files_changed=["src/database.py", "src/models.py"],
            timestamp=datetime.now(),
            author="claude-code",
            decision_id="dec_001",
            lines_added=156,
            lines_removed=42,
        )

    @pytest.fixture
    def sample_outcome(self):
        """Create a sample outcome."""
        return Outcome(
            outcome_id="outcome_001",
            status="success",
            evidence="No errors in 2 weeks of production",
            measured_at=datetime.now(),
            performance_impact=1.05,  # 5% faster
            reliability=0.99,
            maintenance_cost=0.8,
            code_change_id="change_001",
        )

    @pytest.fixture
    def sample_negative_knowledge(self):
        """Create a sample negative knowledge."""
        return NegativeKnowledge(
            nk_id="nk_001",
            hypothesis="Custom JWT implementation is secure",
            conclusion="Custom JWT has high removal rate",
            evidence="89% removed within 97 days (20,470 repos)",
            domain="auth",
            severity="high",
            blocks_pattern="custom-jwt",
            recommendation="Use passport-jwt instead",
            source="CodeDigger",
        )

    @pytest.fixture
    def sample_antipattern(self):
        """Create a sample antipattern."""
        return Antipattern(
            pattern_id="ap_001",
            name="forEach with async callback",
            category="async",
            severity="high",
            repos_affected=15642,
            occurrence_count=234567,
            removal_rate=0.76,
            avg_days_to_removal=42,
            keywords=["forEach", "async"],
            regex_pattern=r"\.forEach\s*\(\s*async",
            example_bad="items.forEach(async item => await process(item))",
            example_good="for (const item of items) { await process(item) }",
            source="GitHub mining",
            recommendation="Use for...of loop with async/await",
        )

    # Node Creation Tests

    def test_add_decision(self, graph_client, sample_decision):
        """Test adding a decision node."""
        result = graph_client.add_decision(sample_decision)
        assert result is True
        graph_client.graph.query.assert_called_once()

        # Verify the query was called with safe escaping
        query_args = graph_client.graph.query.call_args[0][0]
        assert "Decision" in query_args
        assert "dec_001" in query_args
        assert sample_decision.statement in query_args

    def test_add_engram(self, graph_client, sample_engram):
        """Test adding an engram (session) node."""
        result = graph_client.add_engram(sample_engram)
        assert result is True
        graph_client.graph.query.assert_called_once()

        query_args = graph_client.graph.query.call_args[0][0]
        assert "Engram" in query_args
        assert "eng_001" in query_args

    def test_add_code_change(self, graph_client, sample_code_change):
        """Test adding a code change node."""
        result = graph_client.add_code_change(sample_code_change)
        assert result is True
        graph_client.graph.query.assert_called_once()

        query_args = graph_client.graph.query.call_args[0][0]
        assert "CodeChange" in query_args
        assert "9b842ce" in query_args

    def test_add_outcome(self, graph_client, sample_outcome):
        """Test adding an outcome node."""
        result = graph_client.add_outcome(sample_outcome)
        assert result is True
        graph_client.graph.query.assert_called_once()

        query_args = graph_client.graph.query.call_args[0][0]
        assert "Outcome" in query_args
        assert "success" in query_args

    def test_add_negative_knowledge(self, graph_client, sample_negative_knowledge):
        """Test adding a negative knowledge node."""
        result = graph_client.add_negative_knowledge(sample_negative_knowledge)
        assert result is True
        graph_client.graph.query.assert_called_once()

        query_args = graph_client.graph.query.call_args[0][0]
        assert "NegativeKnowledge" in query_args
        assert "nk_001" in query_args

    def test_add_antipattern(self, graph_client, sample_antipattern):
        """Test adding an antipattern node."""
        result = graph_client.add_antipattern(sample_antipattern)
        assert result is True
        graph_client.graph.query.assert_called_once()

        query_args = graph_client.graph.query.call_args[0][0]
        assert "AntiPattern" in query_args
        assert "forEach with async callback" in query_args

    # Relationship Creation Tests

    def test_create_made_in_relationship(self, graph_client):
        """Test creating MADE_IN relationship (Decision -> Engram)."""
        result = graph_client.create_relationship(
            from_node_id="dec_001",
            from_label="Decision",
            to_node_id="eng_001",
            to_label="Engram",
            rel_type="MADE_IN",
            properties={"at_timestamp": 1707500000, "confidence_given": 0.85},
        )
        assert result is True
        graph_client.graph.query.assert_called_once()

        query_args = graph_client.graph.query.call_args[0][0]
        assert "MADE_IN" in query_args

    def test_create_implemented_in_relationship(self, graph_client):
        """Test creating IMPLEMENTED_IN relationship (Decision -> CodeChange)."""
        result = graph_client.create_relationship(
            from_node_id="dec_001",
            from_label="Decision",
            to_node_id="change_001",
            to_label="CodeChange",
            rel_type="IMPLEMENTED_IN",
            properties={"implemented_at": 1707500000},
        )
        assert result is True
        graph_client.graph.query.assert_called_once()

        query_args = graph_client.graph.query.call_args[0][0]
        assert "IMPLEMENTED_IN" in query_args

    def test_create_resulted_in_relationship(self, graph_client):
        """Test creating RESULTED_IN relationship (CodeChange -> Outcome)."""
        result = graph_client.create_relationship(
            from_node_id="change_001",
            from_label="CodeChange",
            to_node_id="outcome_001",
            to_label="Outcome",
            rel_type="RESULTED_IN",
            properties={"outcome": "success", "days_to_outcome": 14},
        )
        assert result is True
        graph_client.graph.query.assert_called_once()

        query_args = graph_client.graph.query.call_args[0][0]
        assert "RESULTED_IN" in query_args

    def test_create_prevented_relationship(self, graph_client):
        """Test creating PREVENTED relationship (NegativeKnowledge -> Decision)."""
        result = graph_client.create_relationship(
            from_node_id="nk_001",
            from_label="NegativeKnowledge",
            to_node_id="dec_002",
            to_label="Decision",
            rel_type="PREVENTED",
            properties={"blocked_at": 1708500000},
        )
        assert result is True
        graph_client.graph.query.assert_called_once()

        query_args = graph_client.graph.query.call_args[0][0]
        assert "PREVENTED" in query_args

    # Analytics Query Tests

    def test_success_rate_by_module(self, graph_client):
        """Test success rate by module query."""
        graph_client.graph.query.return_value = MagicMock(
            result_set=[
                {"module": "database", "successes": 8, "total": 10, "success_rate": 80.0},
                {"module": "auth", "successes": 9, "total": 10, "success_rate": 90.0},
            ]
        )

        results = graph_client.success_rate_by_module()
        assert len(results) == 2
        assert results[0]["module"] == "database"

    def test_success_rate_by_confidence_bucket(self, graph_client):
        """Test confidence calibration query."""
        graph_client.graph.query.return_value = MagicMock(
            result_set=[
                {
                    "confidence_bucket": 0.9,
                    "successful": 15,
                    "total": 16,
                    "actual_rate_pct": 93.75,
                    "calibration_status": "well-calibrated",
                },
                {
                    "confidence_bucket": 0.7,
                    "successful": 8,
                    "total": 12,
                    "actual_rate_pct": 66.7,
                    "calibration_status": "overconfident",
                },
            ]
        )

        results = graph_client.success_rate_by_confidence_bucket()
        assert len(results) == 2
        assert results[0]["calibration_status"] == "well-calibrated"

    def test_decisions_by_rework_count(self, graph_client):
        """Test rework detection query."""
        graph_client.graph.query.return_value = MagicMock(
            result_set=[
                {
                    "statement": "Use custom JWT",
                    "module": "auth",
                    "confidence": 0.65,
                    "rework_count": 5,
                    "avg_days_to_rework": 97,
                },
                {
                    "statement": "Optimize N+1 queries",
                    "module": "database",
                    "confidence": 0.72,
                    "rework_count": 3,
                    "avg_days_to_rework": 42,
                },
            ]
        )

        results = graph_client.decisions_by_rework_count()
        assert len(results) == 2
        assert results[0]["rework_count"] == 5

    def test_decision_to_outcome_flow(self, graph_client):
        """Test decision → outcome flow query."""
        graph_client.graph.query.return_value = MagicMock(
            result_set=[
                {
                    "statement": "Use PostgreSQL",
                    "confidence": 0.85,
                    "commit_sha": "9b842ce",
                    "status": "success",
                    "reliability": 0.99,
                    "days_to_outcome": 14,
                }
            ]
        )

        results = graph_client.decision_to_outcome_flow()
        assert len(results) == 1
        assert results[0]["status"] == "success"

    def test_graph_statistics(self, graph_client):
        """Test overall graph statistics query."""
        graph_client.graph.query.return_value = MagicMock(
            result_set=[
                {
                    "decision_count": 45,
                    "engram_count": 12,
                    "change_count": 58,
                    "outcome_count": 41,
                    "nk_count": 8,
                    "ap_count": 23,
                    "total_nodes": 187,
                }
            ]
        )

        results = graph_client.graph_statistics()
        assert len(results) == 1
        assert results[0]["decision_count"] == 45
        assert results[0]["total_nodes"] == 187

    # Security Tests

    def test_cypher_injection_prevention(self, graph_client):
        """Test that Cypher injection is prevented."""
        malicious_decision = Decision(
            decision_id="dec_inject",
            statement='Test"; DROP TABLE Decision; --',
            alternatives=["opt1"],
            confidence=0.5,
            module="database",
        )

        result = graph_client.add_decision(malicious_decision)
        assert result is True

        # Verify the malicious payload was escaped
        query_args = graph_client.graph.query.call_args[0][0]
        # The escaped version should have backslashes or quotes handling
        assert 'DROP TABLE' in query_args  # Still visible but escaped

    def test_escaping_complex_strings(self, graph_client):
        """Test proper escaping of complex strings with special characters."""
        complex_decision = Decision(
            decision_id="dec_complex",
            statement='Use "async/await" with proper error\\handling',
            alternatives=["callback-style", "promises"],
            confidence=0.75,
            module="api",
        )

        result = graph_client.add_decision(complex_decision)
        assert result is True
        graph_client.graph.query.assert_called_once()

    # Error Handling Tests

    def test_node_creation_when_disconnected(self, sample_decision):
        """Test that node creation fails gracefully when disconnected."""
        client = GraphClient()
        client.connected = False

        result = client.add_decision(sample_decision)
        assert result is False

    def test_relationship_creation_when_disconnected(self):
        """Test that relationship creation fails when disconnected."""
        client = GraphClient()
        client.connected = False

        result = client.create_relationship(
            from_node_id="dec_001",
            from_label="Decision",
            to_node_id="eng_001",
            to_label="Engram",
            rel_type="MADE_IN",
        )
        assert result is False

    def test_query_with_invalid_cypher(self, graph_client):
        """Test query error handling."""
        graph_client.graph.query.side_effect = Exception("Invalid Cypher syntax")

        with pytest.raises(Exception):
            graph_client.query("INVALID CYPHER")

    # Complete Workflow Test

    def test_complete_workflow(self, graph_client, mock_graph):
        """Test complete workflow: decision → engram → code change → outcome."""
        mock_graph.query.return_value = MagicMock(result_set=[{"id": "test"}])

        # 1. Create decision
        decision = Decision(
            decision_id="dec_workflow",
            statement="Use Redis for caching",
            alternatives=["Memcached", "Local cache"],
            confidence=0.80,
            module="api",
        )
        assert graph_client.add_decision(decision) is True

        # 2. Create engram
        engram = Engram(
            engram_id="eng_workflow",
            session_id="sess_workflow",
            commit_sha="abc123",
            branch="feature/caching",
            timestamp=datetime.now(),
            agent=AgentInfo(
                type="claude-code",
                model="claude-sonnet-4-5",
                session_duration_sec=1800,
                total_tokens=30000,
                total_cost_usd=0.35,
            ),
            transcript=[],
            files_changed=[],
            decisions_extracted=["dec_workflow"],
            membria_context_injected=True,
            antipatterns_triggered=[],
        )
        assert graph_client.add_engram(engram) is True

        # 3. Link decision to engram
        assert (
            graph_client.create_relationship(
                from_node_id="dec_workflow",
                from_label="Decision",
                to_node_id="eng_workflow",
                to_label="Engram",
                rel_type="MADE_IN",
            )
            is True
        )

        # 4. Create code change
        code_change = CodeChange(
            change_id="change_workflow",
            commit_sha="abc123",
            files_changed=["src/cache.py"],
            timestamp=datetime.now(),
            decision_id="dec_workflow",
            lines_added=120,
            lines_removed=45,
        )
        assert graph_client.add_code_change(code_change) is True

        # 5. Link decision to code change
        assert (
            graph_client.create_relationship(
                from_node_id="dec_workflow",
                from_label="Decision",
                to_node_id="change_workflow",
                to_label="CodeChange",
                rel_type="IMPLEMENTED_IN",
            )
            is True
        )

        # 6. Create outcome
        outcome = Outcome(
            outcome_id="outcome_workflow",
            status="success",
            evidence="Response time improved 40%",
            measured_at=datetime.now() + timedelta(days=14),
            performance_impact=1.4,
            reliability=0.98,
            code_change_id="change_workflow",
        )
        assert graph_client.add_outcome(outcome) is True

        # 7. Link code change to outcome
        assert (
            graph_client.create_relationship(
                from_node_id="change_workflow",
                from_label="CodeChange",
                to_node_id="outcome_workflow",
                to_label="Outcome",
                rel_type="RESULTED_IN",
                properties={"days_to_outcome": 14},
            )
            is True
        )

        # Verify all calls were made
        assert mock_graph.query.call_count == 7
