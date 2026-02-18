"""GitHub integration for PR/commit linking."""

import logging
import asyncio
from typing import Optional, List, Dict, Any
from dataclasses import dataclass
import subprocess

logger = logging.getLogger(__name__)


@dataclass
class GitHubPR:
    """GitHub Pull Request."""

    number: int
    url: str
    title: str
    state: str  # "open", "closed", "merged"
    created_at: str
    merged_at: Optional[str] = None
    author: Optional[str] = None
    branch: Optional[str] = None
    body: Optional[str] = None


@dataclass
class GitHubCommit:
    """GitHub Commit."""

    sha: str
    message: str
    author: str
    committed_at: str
    url: str


class GitHubClient:
    """GitHub client for PR/commit linking.

    Uses GitHub CLI (gh) for authentication and API access.
    """

    def __init__(self, repo: Optional[str] = None):
        """Initialize GitHub client.

        Args:
            repo: Repository in format "owner/repo". If None, auto-detect.
        """
        self.repo = repo or self._detect_repo()

    def _detect_repo(self) -> str:
        """Auto-detect GitHub repo from git remote.

        Returns:
            Repo in "owner/repo" format
        """
        try:
            # Get origin remote URL
            output = subprocess.check_output(
                ["git", "config", "--get", "remote.origin.url"],
                text=True,
            ).strip()

            # Parse: https://github.com/owner/repo.git → owner/repo
            if "github.com" in output:
                parts = output.split("/")
                owner = parts[-2]
                repo = parts[-1].replace(".git", "")
                detected = f"{owner}/{repo}"
                logger.info(f"Auto-detected repo: {detected}")
                return detected

            return "unknown/unknown"

        except Exception as e:
            logger.warning(f"Could not detect repo: {str(e)}")
            return "unknown/unknown"

    def get_current_branch(self) -> str:
        """Get current git branch.

        Returns:
            Branch name
        """
        try:
            output = subprocess.check_output(
                ["git", "rev-parse", "--abbrev-ref", "HEAD"],
                text=True,
            ).strip()
            return output
        except Exception:
            return "unknown"

    def get_current_commit(self) -> str:
        """Get current commit SHA.

        Returns:
            Commit SHA (short)
        """
        try:
            output = subprocess.check_output(
                ["git", "rev-parse", "--short", "HEAD"],
                text=True,
            ).strip()
            return output
        except Exception:
            return "unknown"

    def find_pr_for_branch(self, branch: str) -> Optional[GitHubPR]:
        """Find PR associated with a branch.

        Args:
            branch: Branch name

        Returns:
            GitHubPR or None
        """
        try:
            # Use gh CLI to find PR
            output = subprocess.check_output(
                ["gh", "pr", "list", "--head", branch, "--json", "number,url,title,state,createdAt,mergedAt,author"],
                text=True,
            ).strip()

            if not output:
                return None

            # Parse JSON output
            import json

            data = json.loads(output)
            if not data:
                return None

            pr_data = data[0]
            return GitHubPR(
                number=pr_data.get("number"),
                url=pr_data.get("url"),
                title=pr_data.get("title"),
                state=pr_data.get("state"),
                created_at=pr_data.get("createdAt"),
                merged_at=pr_data.get("mergedAt"),
                author=pr_data.get("author", {}).get("login") if pr_data.get("author") else None,
                branch=branch,
            )

        except Exception as e:
            logger.warning(f"Could not find PR for branch {branch}: {str(e)}")
            return None

    def find_pr_by_commit(self, commit_sha: str) -> Optional[GitHubPR]:
        """Find PR that contains a commit.

        Args:
            commit_sha: Commit SHA

        Returns:
            GitHubPR or None
        """
        try:
            # Get PR associated with commit
            output = subprocess.check_output(
                [
                    "gh",
                    "pr",
                    "list",
                    "--search",
                    commit_sha,
                    "--json",
                    "number,url,title,state",
                ],
                text=True,
            ).strip()

            if not output:
                return None

            import json

            data = json.loads(output)
            if not data:
                return None

            pr_data = data[0]
            return GitHubPR(
                number=pr_data.get("number"),
                url=pr_data.get("url"),
                title=pr_data.get("title"),
                state=pr_data.get("state"),
                created_at="",
            )

        except Exception as e:
            logger.warning(f"Could not find PR for commit {commit_sha}: {str(e)}")
            return None

    def create_pr_with_decision_link(
        self,
        title: str,
        body: str,
        decision_id: str,
        branch: str = "HEAD",
    ) -> Optional[GitHubPR]:
        """Create a PR with decision link in body.

        Args:
            title: PR title
            body: PR body (description)
            decision_id: Link to decision ID
            branch: Branch to create PR from

        Returns:
            Created GitHubPR or None
        """
        try:
            # Add decision link to body
            decision_link = f"\n\n---\n🧠 **Membria Decision:** `{decision_id}`"
            full_body = body + decision_link

            # Create PR
            output = subprocess.check_output(
                [
                    "gh",
                    "pr",
                    "create",
                    "--title",
                    title,
                    "--body",
                    full_body,
                    "--head",
                    branch,
                ],
                text=True,
            ).strip()

            logger.info(f"Created PR: {output}")
            # Parse PR URL and extract PR number
            pr_number = int(output.split("/")[-1])

            return GitHubPR(
                number=pr_number,
                url=output,
                title=title,
                state="open",
                created_at="",
            )

        except Exception as e:
            logger.error(f"Could not create PR: {str(e)}")
            return None

    def get_pr_status(self, pr_number: int) -> Dict[str, Any]:
        """Get PR status and checks.

        Args:
            pr_number: PR number

        Returns:
            Status dict with state, checks, reviews
        """
        try:
            # Get PR status
            output = subprocess.check_output(
                [
                    "gh",
                    "pr",
                    "view",
                    str(pr_number),
                    "--json",
                    "state,statusCheckRollup,reviews,mergedAt",
                ],
                text=True,
            ).strip()

            import json

            data = json.loads(output)
            return {
                "state": data.get("state"),
                "checks": data.get("statusCheckRollup", []),
                "reviews": data.get("reviews", []),
                "merged_at": data.get("mergedAt"),
            }

        except Exception as e:
            logger.warning(f"Could not get PR status: {str(e)}")
            return {}

    def get_recent_commits(self, limit: int = 10) -> List[GitHubCommit]:
        """Get recent commits on current branch.

        Args:
            limit: Number of commits to fetch

        Returns:
            List of GitHubCommit objects
        """
        try:
            output = subprocess.check_output(
                [
                    "git",
                    "log",
                    "--pretty=format:%H|%s|%an|%ai",
                    f"-n{limit}",
                ],
                text=True,
            ).strip()

            commits = []
            for line in output.split("\n"):
                if not line:
                    continue

                parts = line.split("|")
                if len(parts) >= 4:
                    commits.append(
                        GitHubCommit(
                            sha=parts[0][:8],  # Short SHA
                            message=parts[1],
                            author=parts[2],
                            committed_at=parts[3],
                            url=f"{self.repo}/commit/{parts[0]}",
                        )
                    )

            return commits

        except Exception as e:
            logger.warning(f"Could not get commits: {str(e)}")
            return []

    def is_pr_merged(self, pr_number: int) -> bool:
        """Check if PR is merged.

        Args:
            pr_number: PR number

        Returns:
            True if merged
        """
        try:
            status = self.get_pr_status(pr_number)
            return status.get("state") == "MERGED"
        except Exception:
            return False

    def link_decision_to_commit_message(
        self,
        decision_id: str,
        message: str,
    ) -> str:
        """Prepare commit message with decision link.

        Args:
            decision_id: Decision ID
            message: Original commit message

        Returns:
            Message with decision link
        """
        # Append decision link to message
        decision_link = f"\n\nMembria Decision: {decision_id}"
        return message + decision_link
