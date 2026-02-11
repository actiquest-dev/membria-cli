"""Configuration management for Membria."""

import os
import json
from pathlib import Path
from typing import Any, Optional, Dict
from dataclasses import dataclass, field, asdict
import toml


@dataclass
class FalkorDBConfig:
    """FalkorDB connection configuration."""
    host: str = "localhost"
    port: int = 6379
    password: Optional[str] = None
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
    ui_color: str = "auto"
    ui_compact: bool = False


class ConfigManager:
    """Manages Membria configuration."""

    def __init__(self, config_dir: Optional[str] = None):
        self.config_dir = Path(config_dir or Path.home() / ".membria")
        self.config_dir.mkdir(parents=True, exist_ok=True)
        self.config_file = self.config_dir / "config.toml"
        self.config: MembriaConfig = self._load_config()

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
            if not hasattr(obj, part):
                setattr(obj, part, {})
            obj = getattr(obj, part)
        setattr(obj, parts[-1], value)
        self.save()

    def to_dict(self) -> dict:
        """Convert config to dictionary."""
        return asdict(self.config)
