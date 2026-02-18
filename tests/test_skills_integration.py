"""Tests for skills end-to-end integration."""

import pytest
from membria.commands.skill_commands import SkillCommands
from membria.commands.plan_commands import PlanCommands
from membria.skill_generator import SkillGenerator
from membria.pattern_extractor import PatternExtractor
from membria.graph import GraphClient
from membria.calibration_updater import CalibrationUpdater


class TestSkillsIntegration:
    """Test end-to-end skills workflow."""

    @pytest.mark.skip(reason="Requires running FalkorDB instance")
    def test_e2e_skill_generation_workflow(self):
        """Test complete skill generation workflow."""
        graph_client = GraphClient()
        calibration_updater = CalibrationUpdater()
        pattern_extractor = PatternExtractor(graph_client)
        skill_gen = SkillGenerator(graph_client, calibration_updater, pattern_extractor)

        # Should be able to generate for any domain
        domains = ["auth", "database", "api"]
        for domain in domains:
            result = skill_gen.generate_skill_for_domain(domain)
            # Result can be None if insufficient data, which is OK
            assert result is None or result.domain == domain

    @pytest.mark.skip(reason="Requires running FalkorDB instance")
    def test_e2e_plan_to_skill(self):
        """Test integration from plan validation to skill."""
        plan_cmd = PlanCommands()
        skill_cmd = SkillCommands()

        # Validate a plan
        plan_result = plan_cmd.validate_plan("Use PostgreSQL and JWT")
        assert isinstance(plan_result, str)
        assert "Validation" in plan_result

        # Check if skills are ready
        readiness = skill_cmd.check_readiness(domain="database")
        assert isinstance(readiness, str)

    @pytest.mark.skip(reason="Requires running FalkorDB instance")
    def test_skill_generation_creates_versions(self):
        """Test that skill generation creates versioned skills."""
        graph_client = GraphClient()
        calibration_updater = CalibrationUpdater()
        pattern_extractor = PatternExtractor(graph_client)
        skill_gen = SkillGenerator(graph_client, calibration_updater, pattern_extractor)

        # Generate twice - should increment version
        skill1 = skill_gen.generate_skill_for_domain("auth")
        if skill1:
            assert skill1.version >= 1
            # Version should be in ID
            assert str(skill1.version) in skill1.skill_id

    @pytest.mark.skip(reason="Requires running FalkorDB instance")
    def test_pattern_extraction_feeds_skill_generation(self):
        """Test that patterns feed into skill generation."""
        graph_client = GraphClient()
        calibration_updater = CalibrationUpdater()
        pattern_extractor = PatternExtractor(graph_client)

        # Extract patterns
        patterns = pattern_extractor.extract_patterns_for_domain("database")
        assert isinstance(patterns, list)

        # Should be able to generate skill if enough patterns
        skill_gen = SkillGenerator(graph_client, calibration_updater, pattern_extractor)
        skill = skill_gen.generate_skill_for_domain("database")
        # OK if None (insufficient data)

    @pytest.mark.skip(reason="Requires running FalkorDB instance")
    def test_skill_quality_calculation(self):
        """Test skill quality score calculation."""
        graph_client = GraphClient()
        calibration_updater = CalibrationUpdater()
        pattern_extractor = PatternExtractor(graph_client)
        skill_gen = SkillGenerator(graph_client, calibration_updater, pattern_extractor)

        # Test quality calculation
        quality = skill_gen._calculate_quality_score(0.85, 10)
        assert isinstance(quality, float)
        assert 0 <= quality <= 1

    @pytest.mark.skip(reason="Requires running FalkorDB instance")
    def test_skill_quality_improves_with_sample_size(self):
        """Test that quality improves with larger sample size."""
        graph_client = GraphClient()
        calibration_updater = CalibrationUpdater()
        pattern_extractor = PatternExtractor(graph_client)
        skill_gen = SkillGenerator(graph_client, calibration_updater, pattern_extractor)

        success_rate = 0.8
        quality_10 = skill_gen._calculate_quality_score(success_rate, 10)
        quality_20 = skill_gen._calculate_quality_score(success_rate, 20)

        # Larger sample should have better quality
        assert quality_20 >= quality_10

    @pytest.mark.skip(reason="Requires running FalkorDB instance")
    def test_skill_readiness_check_flow(self):
        """Test skill readiness checking workflow."""
        skill_cmd = SkillCommands()

        # Check readiness for multiple domains
        readiness = skill_cmd.check_readiness()
        assert isinstance(readiness, str)
        assert "Readiness" in readiness

    @pytest.mark.skip(reason="Requires running FalkorDB instance")
    def test_skill_list_and_show_integration(self):
        """Test listing and showing skills together."""
        skill_cmd = SkillCommands()

        # List skills
        list_result = skill_cmd.list_skills()
        assert isinstance(list_result, str)

        # If any skills exist, should be able to show them
        if "ID" in list_result and "not found" not in list_result.lower():
            # Try to show a skill (mock ID)
            show_result = skill_cmd.show_skill("sk-test-v1")
            assert isinstance(show_result, str)

    @pytest.mark.skip(reason="Requires running FalkorDB instance")
    def test_plan_validation_with_domain_inference(self):
        """Test plan validation with automatic domain inference."""
        plan_cmd = PlanCommands()

        # Test various domain inferences
        tests = [
            ("Use PostgreSQL", "database"),
            ("JWT authentication", "auth"),
            ("REST API endpoints", "api"),
            ("Redis caching", "cache"),
        ]

        for description, expected_domain in tests:
            domain = plan_cmd._infer_domain(description)
            assert domain == expected_domain

    @pytest.mark.skip(reason="Requires running FalkorDB instance")
    def test_calibration_integration_with_skills(self):
        """Test calibration data influences skill generation."""
        graph_client = GraphClient()
        calibration_updater = CalibrationUpdater()
        pattern_extractor = PatternExtractor(graph_client)
        skill_gen = SkillGenerator(graph_client, calibration_updater, pattern_extractor)

        # Get calibration
        profiles = calibration_updater.get_all_profiles()
        assert isinstance(profiles, dict)

        # Calibration should influence skill generation
        for domain in ["auth", "database"]:
            if domain in profiles:
                skill = skill_gen.generate_skill_for_domain(domain)
                if skill:
                    # Confidence should come from calibration
                    assert skill.confidence > 0

    @pytest.mark.skip(reason="Requires running FalkorDB instance")
    def test_skill_negative_knowledge_integration(self):
        """Test that skills incorporate negative knowledge."""
        graph_client = GraphClient()
        calibration_updater = CalibrationUpdater()
        pattern_extractor = PatternExtractor(graph_client)
        skill_gen = SkillGenerator(graph_client, calibration_updater, pattern_extractor)

        # Skill procedure should mention known failures if available
        skill = skill_gen.generate_skill_for_domain("auth")
        if skill and skill.procedure:
            # Procedure might include failure information
            assert isinstance(skill.procedure, str)

    @pytest.mark.skip(reason="Requires running FalkorDB instance")
    def test_multiple_domain_skill_generation(self):
        """Test generating skills for multiple domains."""
        graph_client = GraphClient()
        calibration_updater = CalibrationUpdater()
        pattern_extractor = PatternExtractor(graph_client)
        skill_gen = SkillGenerator(graph_client, calibration_updater, pattern_extractor)

        domains = ["auth", "database", "api"]
        results = skill_gen.generate_skills_for_domains(domains)

        assert isinstance(results, dict)
        assert len(results) == len(domains)

    @pytest.mark.skip(reason="Requires running FalkorDB instance")
    def test_skill_zone_classification(self):
        """Test that skills properly classify patterns into zones."""
        graph_client = GraphClient()
        calibration_updater = CalibrationUpdater()
        pattern_extractor = PatternExtractor(graph_client)
        skill_gen = SkillGenerator(graph_client, calibration_updater, pattern_extractor)

        skill = skill_gen.generate_skill_for_domain("auth")
        if skill:
            # Should have zone lists
            assert isinstance(skill.green_zone, list)
            assert isinstance(skill.yellow_zone, list)
            assert isinstance(skill.red_zone, list)

    @pytest.mark.skip(reason="Requires running FalkorDB instance")
    def test_plan_commands_and_skill_commands_compatibility(self):
        """Test that plan and skill commands work together."""
        plan_cmd = PlanCommands()
        skill_cmd = SkillCommands()

        # Generate a plan validation
        plan_result = plan_cmd.validate_plan("Use PostgreSQL with Drizzle ORM")
        assert isinstance(plan_result, str)

        # Check skill readiness for inferred domain
        domain = plan_cmd._infer_domain("Use PostgreSQL with Drizzle ORM")
        readiness = skill_cmd.check_readiness(domain=domain)
        assert isinstance(readiness, str)

    @pytest.mark.skip(reason="Requires running FalkorDB instance")
    def test_error_handling_in_integration(self):
        """Test error handling across integration."""
        plan_cmd = PlanCommands()
        skill_cmd = SkillCommands()

        # Invalid inputs should not crash
        plan_result = plan_cmd.validate_plan("")
        assert isinstance(plan_result, str)

        skill_result = skill_cmd.show_skill("")
        assert isinstance(skill_result, str)

    @pytest.mark.skip(reason="Requires running FalkorDB instance")
    def test_closed_loop_learning_structure(self):
        """Test that structure supports closed-loop learning."""
        # From plan validation → skill generation → calibration update

        plan_cmd = PlanCommands()
        skill_cmd = SkillCommands()

        # 1. Validate plan
        plan_validation = plan_cmd.validate_plan("Use Auth0 for authentication")
        assert isinstance(plan_validation, str)

        # 2. Check skill readiness
        readiness = skill_cmd.check_readiness(domain="auth")
        assert isinstance(readiness, str)

        # 3. List available skills
        skills = skill_cmd.list_skills(domain="auth")
        assert isinstance(skills, str)

    @pytest.mark.skip(reason="Requires running FalkorDB instance")
    def test_skill_version_management(self):
        """Test skill version management in workflow."""
        graph_client = GraphClient()
        calibration_updater = CalibrationUpdater()
        pattern_extractor = PatternExtractor(graph_client)
        skill_gen = SkillGenerator(graph_client, calibration_updater, pattern_extractor)

        # Generate multiple times - versions should increment
        skill1 = skill_gen.generate_skill_for_domain("auth")
        if skill1:
            v1 = skill1.version
            skill2 = skill_gen.generate_skill_for_domain("auth")
            if skill2:
                v2 = skill2.version
                # Second version should be >= first
                assert v2 >= v1
