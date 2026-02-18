"""Registry of specialized agent experts for the Membria Council."""

from typing import Dict, Any, List

class ExpertRegistry:
    """Central store for expert personas and system prompts."""
    
    EXPERTS: Dict[str, Dict[str, Any]] = {
        "architect": {
            "name": "System Architect",
            "prompt": "You are a world-class System Architect. Focus on scalability, modularity, and high-level design patterns.",
            "traits": ["Scalability", "Design Patterns", "Efficiency"]
        },
        "implementer": {
            "name": "Senior Software Engineer",
            "prompt": "You are an expert Implementation Engineer. Focus on clean, readable, and maintainable code following KISS and DRY principles.",
            "traits": ["Clean Code", "Maintainability", "Speed"]
        },
        "reviewer": {
            "name": "QA & Review Specialist",
            "prompt": "You are a meticulous Code Reviewer. Audit code for bugs, edge cases, and performance bottlenecks.",
            "traits": ["Meticulous", "Bug Hunting", "Performance"]
        },
        "security_auditor": {
            "name": "Cybersecurity Expert",
            "prompt": "You are a Security Auditor. Focus on vulnerability detection (OWASP Top 10), data protection, and secure communication.",
            "traits": ["Secure Coding", "Threat Modeling", "Compliance"]
        },
        "sre": {
            "name": "Site Reliability Engineer",
            "prompt": "You are an SRE. Focus on observability, fault tolerance, resource limits, and infrastructure as code.",
            "traits": ["Reliability", "Observability", "Infra"]
        },
        "ux_designer": {
            "name": "UI/UX Strategist",
            "prompt": "You are a UX Designer. Focus on accessibility, intuitive interfaces, and user psychology.",
            "traits": ["Accessibility", "UX", "Visuals"]
        },
        "database_pro": {
            "name": "DBA Specialist",
            "prompt": "You are a Database Architect. Focus on schema normalization, query optimization, and data integrity.",
            "traits": ["SQL/NoSQL", "Indexing", "Integrity"]
        },
        "analyst": {
            "name": "Business & Knowledge Analyst",
            "prompt": "You are a Strategic Analyst. Focus on market research, requirement extraction, and impact analysis.",
            "traits": ["Strategy", "Market", "Requirements"]
        },
        "copywriter": {
            "name": "Technical Writer",
            "prompt": "You are a Technical Copywriter. Focus on clarity, documentation standards, and user-facing communication.",
            "traits": ["Clarity", "Documentation", "Consistency"]
        }
    }

    @classmethod
    def _get_custom_experts(cls) -> Dict[str, Any]:
        """Load custom expert definitions from configuration."""
        try:
            from membria.config import ConfigManager
            config = ConfigManager().config
            return config.team.get("agents", {})
        except Exception:
            return {}

    @classmethod
    def get_expert(cls, role: str) -> Dict[str, Any]:
        """Retrieve expert config for a given role, merging defaults with custom config and graph."""
        role = role.lower()
        default = cls.EXPERTS.get(role, cls.EXPERTS["implementer"])
        custom = cls._get_custom_experts().get(role, {})

        # Merge: Custom overrides model, provider, and name/prompt if provided
        merged = {
            **default,
            **custom
        }

        # If role not in EXPERTS, try to fetch from graph (Squad roles)
        if role not in cls.EXPERTS:
            graph_role = cls._get_graph_role(role)
            if graph_role:
                # Enhance with graph data: name, prompt from prompt_path
                merged["name"] = graph_role.get("name", merged.get("name", role))
                merged["description"] = graph_role.get("description", "")
                if graph_role.get("prompt_path"):
                    merged["prompt"] = cls._load_prompt_from_path(graph_role["prompt_path"])

        return merged

    @classmethod
    def _get_graph_role(cls, role: str) -> Dict[str, Any]:
        """Attempt to fetch role from FalkorDB graph."""
        try:
            from membria.graph import GraphClient
            graph = GraphClient()
            if not graph.connect():
                return {}
            return graph.get_role(role) or {}
        except Exception:
            return {}

    @classmethod
    def _load_prompt_from_path(cls, path: str) -> str:
        """Load system prompt from markdown file path."""
        try:
            from pathlib import Path
            p = Path(path).expanduser()
            if p.exists():
                return p.read_text(encoding="utf-8", errors="ignore").strip()
        except Exception:
            pass
        return ""

    @classmethod
    def list_roles(cls) -> List[str]:
        """List all available expert roles (defaults + any custom roles defined in config)."""
        roles = set(cls.EXPERTS.keys())
        roles.update(cls._get_custom_experts().keys())
        return sorted(list(roles))
