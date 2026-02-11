"""Git hook integration for automatic engram capture on commits."""

import json
import logging
import subprocess
from pathlib import Path
from datetime import datetime
from typing import Optional, Dict, Any

from membria.storage import EngramStorage
from membria.models import Engram

logger = logging.getLogger(__name__)


class EngramCapturer:
    """Capture engrams from git commits."""

    def __init__(self):
        """Initialize engram capturer."""
        self.storage = EngramStorage()

    def capture_from_commit(self, commit_sha: Optional[str] = None) -> Optional[str]:
        """
        Capture an engram from current git commit.

        Called by post-commit hook. Captures:
        - Branch name
        - Commit SHA and message
        - Files changed
        - Timestamp
        - Session context (if available)

        Args:
            commit_sha: Git commit SHA (if None, uses HEAD)

        Returns:
            Engram ID if successful, None otherwise
        """
        try:
            # Get git context
            if not commit_sha:
                commit_sha = self._get_current_commit()

            if not commit_sha:
                logger.warning("Could not get commit SHA")
                return None

            branch = self._get_current_branch()
            commit_msg = self._get_commit_message(commit_sha)
            files_changed = self._get_files_changed(commit_sha)

            # Create engram with required fields
            from membria.models import AgentInfo, FileChange

            file_changes = [
                FileChange(path=f, action="modified", lines_added=0, lines_removed=0)
                for f in files_changed
            ]

            engram = Engram(
                engram_id=f"eng_{datetime.now().strftime('%Y%m%d%H%M%S')}_{commit_sha[:8]}",
                session_id=f"session_{commit_sha[:12]}",
                commit_sha=commit_sha,
                branch=branch,
                timestamp=datetime.now(),
                # Required fields
                agent=AgentInfo(
                    type="git-hook",
                    model="git-commit",
                    session_duration_sec=0,
                    total_tokens=0,
                    total_cost_usd=0.0,
                ),
                transcript=[],
                files_changed=file_changes,
                decisions_extracted=[],
                membria_context_injected=False,
                antipatterns_triggered=[],
                # Optional fields
                summary=None,
                monty_state=None,
                reasoning_trail=[],
                context_window_snapshot=None,
                tool_call_graph=[],
                confidence_trajectory=[],
                energy_cost=None,
            )

            # Save engram
            if self.storage.save_engram(engram):
                logger.info(f"Engram captured: {engram.engram_id}")
                return engram.engram_id
            else:
                logger.error("Failed to save engram")
                return None

        except Exception as e:
            logger.error(f"Failed to capture engram: {e}")
            return None

    def _get_current_commit(self) -> Optional[str]:
        """Get current HEAD commit SHA."""
        try:
            result = subprocess.run(
                ["git", "rev-parse", "HEAD"],
                capture_output=True,
                text=True,
                check=True,
            )
            return result.stdout.strip()
        except Exception as e:
            logger.error(f"Failed to get commit SHA: {e}")
            return None

    def _get_current_branch(self) -> str:
        """Get current git branch name."""
        try:
            result = subprocess.run(
                ["git", "rev-parse", "--abbrev-ref", "HEAD"],
                capture_output=True,
                text=True,
                check=True,
            )
            return result.stdout.strip()
        except Exception:
            return "unknown"

    def _get_commit_message(self, commit_sha: str) -> str:
        """Get commit message."""
        try:
            result = subprocess.run(
                ["git", "log", "-1", "--pretty=%B", commit_sha],
                capture_output=True,
                text=True,
                check=True,
            )
            return result.stdout.strip()
        except Exception:
            return "unknown"

    def _get_files_changed(self, commit_sha: str) -> list:
        """Get list of files changed in commit."""
        try:
            result = subprocess.run(
                ["git", "show", "--name-only", "--pretty=format:", commit_sha],
                capture_output=True,
                text=True,
                check=True,
            )
            return result.stdout.strip().split("\n") if result.stdout.strip() else []
        except Exception:
            return []

    def ensure_engram_branch(self) -> bool:
        """Ensure membria/engrams/v1 branch exists."""
        try:
            # Check if branch exists
            result = subprocess.run(
                ["git", "rev-parse", "--verify", "membria/engrams/v1"],
                capture_output=True,
                check=False,
            )

            if result.returncode == 0:
                # Branch exists
                return True

            # Create branch from current HEAD
            subprocess.run(
                ["git", "branch", "membria/engrams/v1"],
                check=True,
                capture_output=True,
            )
            logger.info("Created membria/engrams/v1 branch")
            return True

        except Exception as e:
            logger.error(f"Failed to ensure engram branch: {e}")
            return False
