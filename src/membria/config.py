"""Configuration management for Membria."""

import os
import json
from pathlib import Path
from typing import Any, Optional, Dict, List
from dataclasses import dataclass, field, asdict
import toml


@dataclass
class FalkorDBConfig:
    """FalkorDB connection configuration."""
    host: str = field(default_factory=lambda: os.environ.get("FALKORDB_HOST", "localhost"))
    port: int = field(default_factory=lambda: int(os.environ.get("FALKORDB_PORT", "6379")))
    password: Optional[str] = field(default_factory=lambda: os.environ.get("FALKORDB_PASSWORD"))
    db: int = 0
    mode: str = "local"  # "local" or "remote"


@dataclass
class DaemonConfig:
    """Daemon configuration."""
    port: int = 3117
    auto_start: bool = True
    log_level: str = "info"


@dataclass
class CacheConfig:
    """Cache layer configuration."""
    enabled: bool = True
    max_age: str = "24h"
    max_size_mb: int = 100
    sync_interval: str = "5m"


@dataclass
class DetectionConfig:
    """Detection sensitivity configuration."""
    sensitivity: str = "medium"
    custom_keywords: list = field(default_factory=list)


@dataclass
class SafetyConfig:
    """Safety and cognitive interventions."""
    resonance_threshold: float = 0.6
    max_friction_per_session: int = 2
    enabled_interventions: list = field(default_factory=lambda: [
        "anchoring_decomposition",
        "confirmation_devils_advocate",
        "overconfidence_premortem",
        "sunk_cost_fresh_start"
    ])


@dataclass
class EngramsConfig:
    """Engrams (checkpoints) configuration."""
    enabled: bool = True
    strategy: str = "auto-commit"  # "auto-commit" or "manual"
    branch: str = "membria/engrams/v1"
    auto_push: bool = True
    auto_pull: bool = True


@dataclass
class MemoryToolsConfig:
    """Memory tools auto-registration."""
    enabled: bool = False


@dataclass
class MCPDiscoveryConfig:
    """MCP external tool discovery."""
    enabled: bool = False
    allowlist_path: str = field(default_factory=lambda: str(Path.home() / ".membria" / "mcp_allowlist.json"))
    timeout_sec: int = 8
    refresh_sec: int = 600


@dataclass
class MembriaConfig:
    """Main Membria configuration."""
    mode: str = "solo"  # "solo", "team", "enterprise"
    language: str = "en"
    graph_backend: str = "falkordb"
    falkordb: FalkorDBConfig = field(default_factory=FalkorDBConfig)
    daemon: DaemonConfig = field(default_factory=DaemonConfig)
    cache: CacheConfig = field(default_factory=CacheConfig)
    detection: DetectionConfig = field(default_factory=DetectionConfig)
    safety: SafetyConfig = field(default_factory=SafetyConfig)
    engrams: EngramsConfig = field(default_factory=EngramsConfig)
    memory_tools: MemoryToolsConfig = field(default_factory=MemoryToolsConfig)
    mcp_discovery: MCPDiscoveryConfig = field(default_factory=MCPDiscoveryConfig)
    tenant_id: str = "default"
    team_id: str = "default"
    project_id: str = "default"
    context_plugins: List[str] = field(default_factory=lambda: [
        "docshot",
        "session_context",
        "calibration",
        "negative_knowledge",
        "similar_decisions",
        "behavior_chains",
    ])
    ui_color: str = "auto"
    ui_compact: bool = False
    
    # Default AI Settings
    default_model: str = "claude-3-5-sonnet-latest"
    default_provider: str = "anthropic"
    
    # Interactive Mode Configs (dict storage for Pydantic models)
    providers: Dict[str, Any] = field(default_factory=lambda: {
        "anthropic": {
            "type": "anthropic",
            "model": "claude-3-5-sonnet-latest",
            "api_key": "",
            "endpoint": "https://api.anthropic.com/v1",
            "enabled": True
        },
        "openai": {
            "type": "openai",
            "model": "gpt-4-turbo",
            "api_key": "",
            "endpoint": "https://api.openai.com/v1",
            "enabled": True
        },
        "kilo": {
            "type": "kilo",
            "model": "kilo-code",
            "api_key": "",
            "endpoint": "http://kilo.ai",
            "enabled": False,
            "available_models": [
                "kilo-code",
                "kilo-chat",
                "kilo-instruct",
                "kilo-vision",
                "kilo-embeddings",
                "kilo-reasoning",
                "kilo-translation",
                "kilo-summarization",
                "kilo-qa",
                "kilo-classification",
                "kilo-sentiment",
                "kilo-ner",
                "kilo-semantic-search",
                "kilo-generation",
                "kilo-dialogue",
                "kilo-explanation",
                "kilo-analysis",
                "kilo-optimization",
                "kilo-detection",
                "kilo-forecasting"
            ]
        },
        "openrouter": {
            "type": "openrouter",
            "model": "kilo-code",
            "api_key": "",
            "endpoint": "https://openrouter.ai/api/v1",
            "enabled": False,
            "available_models": [
                "kilo-code"
            ]
        }
    })
    team: Dict[str, Any] = field(default_factory=dict)
    orchestration: Dict[str, Any] = field(default_factory=dict)


class ConfigManager:
    """Manages Membria configuration loading and saving."""

    def __init__(self, config_dir: Optional[str] = None):
        self.config_dir = Path(config_dir or Path.home() / ".membria")
        self.config_dir.mkdir(parents=True, exist_ok=True)
        self.config_file = self.config_dir / "config.toml"
        self.config: MembriaConfig = self._load_config()

    def is_first_run(self) -> bool:
        """Check if this is the first run (no providers configured)."""
        return not self.config.providers

    def _load_config(self) -> MembriaConfig:
        """Load configuration from file or create default."""
        if self.config_file.exists():
            with open(self.config_file) as f:
                data = toml.load(f)

            falkordb_data = data.pop("falkordb", {})
            falkordb_cfg = FalkorDBConfig(**falkordb_data)
            return MembriaConfig(falkordb=falkordb_cfg, **data)

        return MembriaConfig()

    def save(self) -> None:
        """Save configuration to file."""
        config_dict = asdict(self.config)
        with open(self.config_file, "w") as f:
            toml.dump(config_dict, f)

    def set_falkordb_remote(self, host: str, port: int, password: Optional[str] = None) -> None:
        """Configure remote FalkorDB connection."""
        self.config.falkordb = FalkorDBConfig(
            host=host,
            port=port,
            password=password,
            mode="remote"
        )
        self.save()

    def get_falkordb_config(self) -> FalkorDBConfig:
        """Get FalkorDB configuration."""
        return self.config.falkordb

    def get(self, key: str) -> Any:
        """Get configuration value by dot-notation key."""
        parts = key.split(".")
        value = self.config
        for part in parts:
            if hasattr(value, part):
                value = getattr(value, part)
            elif isinstance(value, dict):
                value = value.get(part)
            else:
                return None
        return value

    def set(self, key: str, value: Any) -> None:
        """Set configuration value by dot-notation key."""
        parts = key.split(".")
        obj = self.config
        for part in parts[:-1]:
            if isinstance(obj, dict):
                if part not in obj or not isinstance(obj[part], (dict,)):
                    obj[part] = {}
                obj = obj[part]
                continue
            if not hasattr(obj, part):
                setattr(obj, part, {})
            obj = getattr(obj, part)
        if isinstance(obj, dict):
            obj[parts[-1]] = value
        else:
            setattr(obj, parts[-1], value)
        self.save()

    def to_dict(self) -> dict:
        """Convert config to dictionary."""
        return asdict(self.config)
