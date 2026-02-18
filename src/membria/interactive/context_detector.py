"""Automatically detect repository type and work context."""

import os
from pathlib import Path
from enum import Enum
from typing import List

class ContextMode(Enum):
    DEVELOPMENT = "DEVELOPMENT"
    KNOWLEDGE = "KNOWLEDGE"
    GENERAL = "GENERAL"

class ContextDetector:
    """Detects Dev vs Knowledge mode based on file signatures."""
    
    DEV_SIGNATURES = [
        "package.json", "pyproject.toml", "go.mod", "Cargo.toml",
        ".git", "Makefile", "docker-compose.yml", "tsconfig.json"
    ]
    
    KNOWLEDGE_SIGNATURES = [
        "PRD", "STRATEGY", "MARKET", "BUSINESS", "REPORT",
        "doc/", "docs/", "wiki/", "whitepaper"
    ]

    def detect(self, path: str = ".") -> ContextMode:
        """Analyze the directory and return the most likely mode."""
        p = Path(path).resolve()
        
        # Check for development signatures
        for sig in self.DEV_SIGNATURES:
            if (p / sig).exists():
                return ContextMode.DEVELOPMENT
        
        # Check for common dev folders
        if (p / "src").is_dir() or (p / "lib").is_dir() or (p / "node_modules").is_dir():
            return ContextMode.DEVELOPMENT
            
        # Check for knowledge signatures (case-insensitive in filename)
        file_names = [f.name.upper() for f in p.glob("*") if f.is_file()]
        for sig in self.KNOWLEDGE_SIGNATURES:
            if any(sig in name for name in file_names):
                return ContextMode.KNOWLEDGE
                
        # If many markdown files, likely Knowledge
        md_count = len(list(p.glob("*.md")))
        if md_count > 5:
            return ContextMode.KNOWLEDGE
            
        return ContextMode.GENERAL

    def get_expert_roles(self, mode: ContextMode) -> List[str]:
        """Get recommended agent roles for the detected mode."""
        if mode == ContextMode.DEVELOPMENT:
            return ["architect", "implementer", "reviewer", "security_auditor"]
        elif mode == ContextMode.KNOWLEDGE:
            return ["strategist", "researcher", "analyst", "copywriter"]
        return ["architect", "implementer", "reviewer"]
