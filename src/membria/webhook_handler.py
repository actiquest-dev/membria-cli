"""Webhook handler: Process GitHub and CI events to update outcomes."""

import logging
import json
import hashlib
import hmac
from typing import Optional, Dict, Any
from datetime import datetime

from membria.outcome_tracker import OutcomeTracker
from membria.outcome_models import SignalType, SignalValence

logger = logging.getLogger(__name__)


class WebhookHandler:
    """Handles webhooks from GitHub and CI systems."""

    def __init__(self, tracker: Optional[OutcomeTracker] = None):
        """Initialize webhook handler.

        Args:
            tracker: OutcomeTracker instance (creates new if not provided)
        """
        self.tracker = tracker or OutcomeTracker()
        self.github_secret = None  # Would be loaded from config

    def set_github_secret(self, secret: str) -> None:
        """Set GitHub webhook secret for signature verification.

        Args:
            secret: GitHub webhook secret
        """
        self.github_secret = secret

    def verify_github_signature(self, payload: bytes, signature: str) -> bool:
        """Verify GitHub webhook signature.

        Args:
            payload: Raw webhook payload
            signature: X-Hub-Signature-256 header value

        Returns:
            True if signature is valid
        """
        if not self.github_secret:
            logger.warning("GitHub secret not configured, skipping signature verification")
            return True

        try:
            # Extract hash from signature header (format: sha256=hash)
            if not signature.startswith("sha256="):
                return False

            provided_hash = signature[7:]

            # Compute expected hash
            expected_hash = hmac.new(
                self.github_secret.encode(),
                payload,
                hashlib.sha256,
            ).hexdigest()

            return hmac.compare_digest(provided_hash, expected_hash)

        except Exception as e:
            logger.error(f"Error verifying GitHub signature: {e}")
            return False

    def handle_github_push(self, payload: Dict[str, Any]) -> Optional[str]:
        """Handle GitHub push event.

        Args:
            payload: GitHub webhook payload

        Returns:
            Outcome ID if decision ID was found, else None
        """
        try:
            ref = payload.get("ref", "")
            commits = payload.get("commits", [])

            if not commits:
                logger.debug("Push event with no commits")
                return None

            # Get commit info
            commit = commits[0]
            commit_sha = commit.get("id", "")
            message = commit.get("message", "")

            # Extract decision ID from commit message
            decision_id = self._extract_decision_id(message)

            if not decision_id:
                logger.debug(f"No decision ID found in commit {commit_sha}")
                return None

            # Create or find outcome
            outcome = self.tracker.create_outcome(decision_id)

            # Record the commit
            self.tracker.record_commit(outcome.outcome_id, commit_sha, message, decision_id)

            logger.info(f"Recorded commit {commit_sha} for decision {decision_id}")
            return outcome.outcome_id

        except Exception as e:
            logger.error(f"Error handling GitHub push: {e}")
            return None

    def handle_github_pull_request(self, payload: Dict[str, Any]) -> Optional[str]:
        """Handle GitHub pull request event.

        Args:
            payload: GitHub webhook payload

        Returns:
            Outcome ID if decision ID was found, else None
        """
        try:
            action = payload.get("action", "")
            pr = payload.get("pull_request", {})

            pr_number = pr.get("number")
            pr_url = pr.get("html_url")
            pr_title = pr.get("title", "")
            pr_body = pr.get("body", "")
            pr_state = pr.get("state")

            # Extract decision ID from PR title or body
            decision_id = self._extract_decision_id(f"{pr_title} {pr_body}")

            if not decision_id:
                logger.debug(f"No decision ID found in PR #{pr_number}")
                return None

            # Create or find outcome
            outcome = self.tracker.create_outcome(decision_id)

            if action == "opened":
                # Record PR creation
                head_ref = pr.get("head", {}).get("ref", "HEAD")
                self.tracker.record_pr_created(
                    outcome.outcome_id,
                    pr_number,
                    pr_url,
                    head_ref,
                    decision_id,
                )
                logger.info(f"Recorded PR #{pr_number} for decision {decision_id}")

            elif action == "closed" and pr_state == "merged":
                # Record PR merge
                self.tracker.record_pr_merged(outcome.outcome_id, pr_number)
                logger.info(f"Recorded PR merge #{pr_number} for decision {decision_id}")

            return outcome.outcome_id

        except Exception as e:
            logger.error(f"Error handling GitHub PR: {e}")
            return None

    def handle_github_workflow_run(self, payload: Dict[str, Any]) -> Optional[str]:
        """Handle GitHub Actions workflow_run event.

        Args:
            payload: GitHub webhook payload

        Returns:
            Outcome ID if decision ID was found, else None
        """
        try:
            workflow_run = payload.get("workflow_run", {})
            conclusion = workflow_run.get("conclusion", "")
            status = workflow_run.get("status", "")
            pr_numbers = workflow_run.get("pull_requests", [])

            if not pr_numbers:
                logger.debug("Workflow run with no associated PR")
                return None

            # Get first PR number
            pr_number = pr_numbers[0].get("number") if pr_numbers else None

            if not pr_number:
                return None

            # Try to find outcome from PR
            # In a real implementation, would query DB for outcome by PR number
            # For now, we'll need the decision ID passed in via commit
            pr_title = payload.get("workflow_run", {}).get("head_commit", {}).get("message", "")
            decision_id = self._extract_decision_id(pr_title)

            if not decision_id:
                logger.debug(f"No decision ID found for PR #{pr_number}")
                return None

            # Create outcome if needed
            outcome = self.tracker.create_outcome(decision_id)

            # Record CI result
            if status == "completed":
                passed = conclusion == "success"
                details = f"CI workflow: {conclusion}"

                self.tracker.record_ci_result(
                    outcome.outcome_id,
                    passed,
                    details,
                )

                logger.info(
                    f"Recorded CI result ({conclusion}) for decision {decision_id}"
                )

            return outcome.outcome_id

        except Exception as e:
            logger.error(f"Error handling GitHub workflow: {e}")
            return None

    def handle_check_run(self, payload: Dict[str, Any]) -> Optional[str]:
        """Handle GitHub check_run event (for workflow steps).

        Args:
            payload: GitHub webhook payload

        Returns:
            Outcome ID if decision ID was found, else None
        """
        try:
            check_run = payload.get("check_run", {})
            conclusion = check_run.get("conclusion", "")
            status = check_run.get("status", "")
            pr_numbers = check_run.get("pull_requests", [])

            if not pr_numbers or status != "completed":
                return None

            # Extract decision ID from check run output/title
            title = check_run.get("name", "")
            output = check_run.get("output", {})
            summary = output.get("summary", "")

            decision_id = self._extract_decision_id(f"{title} {summary}")

            if not decision_id:
                return None

            outcome = self.tracker.create_outcome(decision_id)

            passed = conclusion == "success"
            details = f"Check run '{title}': {conclusion}"

            self.tracker.record_ci_result(outcome.outcome_id, passed, details)

            logger.info(f"Recorded check run result for decision {decision_id}")
            return outcome.outcome_id

        except Exception as e:
            logger.error(f"Error handling check run: {e}")
            return None

    def handle_ci_json(self, payload: Dict[str, Any]) -> Optional[str]:
        """Handle generic CI system event (JSON format).

        Expected format:
        {
            "decision_id": "dec_123",
            "outcome_id": "outcome_...",  # optional
            "event_type": "ci_complete",
            "passed": true,
            "details": "All tests passed",
            "metrics": {...}
        }

        Args:
            payload: CI webhook payload

        Returns:
            Outcome ID if processed, else None
        """
        try:
            decision_id = payload.get("decision_id")
            outcome_id = payload.get("outcome_id")
            event_type = payload.get("event_type", "")
            passed = payload.get("passed")
            details = payload.get("details", "")
            metrics = payload.get("metrics", {})

            if not decision_id and not outcome_id:
                logger.debug("CI event with no decision or outcome ID")
                return None

            # Create outcome if needed
            if not outcome_id:
                outcome = self.tracker.create_outcome(decision_id)
                outcome_id = outcome.outcome_id
            else:
                outcome = self.tracker.get_outcome(outcome_id)
                if not outcome:
                    logger.warning(f"Outcome {outcome_id} not found")
                    return None

            # Handle different event types
            if event_type == "ci_complete" and passed is not None:
                self.tracker.record_ci_result(outcome_id, passed, details)

            elif event_type == "test_result":
                # Record test as signal
                valence = SignalValence.POSITIVE if passed else SignalValence.NEGATIVE
                signal_type = SignalType.CI_PASSED if passed else SignalType.CI_FAILED

                outcome.add_signal(
                    signal_type,
                    valence,
                    description=details,
                    metrics=metrics,
                )

            elif event_type == "performance":
                self.tracker.record_performance(outcome_id, metrics)

            elif event_type == "incident":
                severity = payload.get("severity", "medium")
                self.tracker.record_incident(outcome_id, severity, details)

            logger.info(f"Handled CI event '{event_type}' for outcome {outcome_id}")
            return outcome_id

        except Exception as e:
            logger.error(f"Error handling CI JSON event: {e}")
            return None

    def _extract_decision_id(self, text: str) -> Optional[str]:
        """Extract decision ID from text.

        Looks for patterns like:
        - Membria Decision: dec_123
        - Decision: dec_123
        - [dec_123]
        - dec_123_feature_name

        Args:
            text: Text to search

        Returns:
            Decision ID or None
        """
        import re

        patterns = [
            r"Membria Decision:\s*(dec_[a-zA-Z0-9_]+)",
            r"Decision:\s*(dec_[a-zA-Z0-9_]+)",
            r"\[dec_[a-zA-Z0-9_]+\]",
            r"(dec_[a-zA-Z0-9_]+)",
        ]

        for pattern in patterns:
            match = re.search(pattern, text, re.IGNORECASE)
            if match:
                # Return captured group if exists, else full match
                return match.group(1) if match.groups() else match.group(0)

        return None

    def process_webhook(
        self,
        event_type: str,
        payload: Dict[str, Any],
        signature: Optional[str] = None,
        raw_body: Optional[bytes] = None,
    ) -> Dict[str, Any]:
        """Process incoming webhook.

        Args:
            event_type: Type of webhook event (e.g., 'push', 'pull_request')
            payload: Webhook payload
            signature: Optional signature for verification

        Returns:
            Result dict with status and outcome_id
        """
        try:
            # Verify signature if provided
            if signature:
                payload_bytes = raw_body if raw_body is not None else json.dumps(payload).encode()
                if not self.verify_github_signature(payload_bytes, signature):
                    logger.error("Invalid webhook signature")
                    return {"status": "error", "message": "Invalid signature"}

            # Route to appropriate handler
            outcome_id = None

            if event_type == "push":
                outcome_id = self.handle_github_push(payload)

            elif event_type == "pull_request":
                outcome_id = self.handle_github_pull_request(payload)

            elif event_type == "workflow_run":
                outcome_id = self.handle_github_workflow_run(payload)

            elif event_type == "check_run":
                outcome_id = self.handle_check_run(payload)

            elif event_type in ("ci_event", "ci_json"):
                outcome_id = self.handle_ci_json(payload)

            else:
                logger.warning(f"Unknown webhook event type: {event_type}")
                return {
                    "status": "ignored",
                    "message": f"Unknown event type: {event_type}",
                }

            return {
                "status": "success" if outcome_id else "no_decision_found",
                "outcome_id": outcome_id,
            }

        except Exception as e:
            logger.error(f"Error processing webhook: {e}")
            return {"status": "error", "message": str(e)}
