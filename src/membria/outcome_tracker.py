"""Outcome tracker: Links decisions to code, PRs, and CI results."""

import logging
import uuid
from typing import Optional, List, Dict, Any
from datetime import datetime
from dataclasses import asdict

from membria.outcome_models import Outcome, OutcomeStatus, Signal, SignalType, SignalValence
from membria.github_client import GitHubClient
from membria.graph import GraphClient
from membria.calibration_updater import CalibrationUpdater

logger = logging.getLogger(__name__)


class OutcomeTracker:
    """Tracks decision outcomes through code → PR → CI → merged lifecycle."""

    def __init__(self, db_client: Optional[GraphClient] = None, calibration_updater: Optional[CalibrationUpdater] = None):
        """Initialize outcome tracker.

        Args:
            db_client: GraphClient for persistence (optional for now)
            calibration_updater: CalibrationUpdater for tracking team calibration (optional)
        """
        self.db_client = db_client
        self.github_client = GitHubClient()
        self.calibration_updater = calibration_updater or CalibrationUpdater()
        self._outcomes: Dict[str, Outcome] = {}  # In-memory store for now

    def create_outcome(self, decision_id: str, outcome_id: Optional[str] = None) -> Outcome:
        """Create new outcome tracking record.

        Args:
            decision_id: ID of decision being tracked
            outcome_id: Optional specific outcome ID (auto-generated if not provided)

        Returns:
            Created Outcome object
        """
        if not outcome_id:
            # Use UUID for uniqueness, include decision_id for readability
            short_uuid = str(uuid.uuid4())[:8]
            outcome_id = f"outcome_{decision_id}_{short_uuid}"

        outcome = Outcome(
            outcome_id=outcome_id,
            decision_id=decision_id,
            status=OutcomeStatus.PENDING,
        )

        self._outcomes[outcome_id] = outcome
        logger.info(f"Created outcome {outcome_id} for decision {decision_id}")
        return outcome

    def record_commit(
        self,
        outcome_id: str,
        commit_sha: str,
        message: str,
        decision_id: Optional[str] = None,
    ) -> Outcome:
        """Record that decision was implemented as a commit.

        Args:
            outcome_id: Outcome ID to update
            commit_sha: Git commit SHA
            message: Commit message
            decision_id: Optional decision ID to link

        Returns:
            Updated Outcome
        """
        if outcome_id not in self._outcomes:
            raise ValueError(f"Outcome {outcome_id} not found")

        outcome = self._outcomes[outcome_id]
        outcome.commit_sha = commit_sha[:8]  # Store short SHA

        # Add signal
        outcome.add_signal(
            SignalType.PR_CREATED,  # Reuse for commit signal initially
            SignalValence.NEUTRAL,
            description=f"Commit {commit_sha[:8]}: {message[:100]}",
        )

        logger.info(f"Recorded commit {commit_sha} for outcome {outcome_id}")
        return outcome

    def record_pr_created(
        self,
        outcome_id: str,
        pr_number: int,
        pr_url: str,
        branch: str,
        decision_id: Optional[str] = None,
    ) -> Outcome:
        """Record PR creation for decision implementation.

        Args:
            outcome_id: Outcome ID to update
            pr_number: PR number
            pr_url: Full PR URL
            branch: Branch name
            decision_id: Optional decision ID

        Returns:
            Updated Outcome
        """
        if outcome_id not in self._outcomes:
            raise ValueError(f"Outcome {outcome_id} not found")

        outcome = self._outcomes[outcome_id]
        outcome.status = OutcomeStatus.SUBMITTED
        outcome.submitted_at = datetime.now().isoformat()
        outcome.pr_number = pr_number
        outcome.pr_url = pr_url

        # Add signal
        outcome.add_signal(
            SignalType.PR_CREATED,
            SignalValence.POSITIVE,
            description=f"PR #{pr_number} created: {pr_url}",
        )

        logger.info(f"Recorded PR {pr_number} for outcome {outcome_id}")
        return outcome

    def record_pr_merged(
        self,
        outcome_id: str,
        pr_number: int,
    ) -> Outcome:
        """Record PR merge event.

        Args:
            outcome_id: Outcome ID to update
            pr_number: PR number that merged

        Returns:
            Updated Outcome
        """
        if outcome_id not in self._outcomes:
            raise ValueError(f"Outcome {outcome_id} not found")

        outcome = self._outcomes[outcome_id]
        outcome.status = OutcomeStatus.MERGED
        outcome.merged_at = datetime.now().isoformat()

        # Add signal
        outcome.add_signal(
            SignalType.PR_MERGED,
            SignalValence.POSITIVE,
            description=f"PR #{pr_number} merged to main",
        )

        logger.info(f"Recorded PR merge for outcome {outcome_id}")
        return outcome

    def record_ci_result(
        self,
        outcome_id: str,
        passed: bool,
        details: Optional[str] = None,
    ) -> Outcome:
        """Record CI test result.

        Args:
            outcome_id: Outcome ID to update
            passed: Whether tests passed
            details: Optional test details/failures

        Returns:
            Updated Outcome
        """
        if outcome_id not in self._outcomes:
            raise ValueError(f"Outcome {outcome_id} not found")

        outcome = self._outcomes[outcome_id]

        signal_type = SignalType.CI_PASSED if passed else SignalType.CI_FAILED
        valence = SignalValence.POSITIVE if passed else SignalValence.NEGATIVE

        outcome.add_signal(
            signal_type,
            valence,
            description=f"CI {'passed' if passed else 'failed'}: {details or 'All checks complete'}",
        )

        logger.info(f"Recorded CI result ({signal_type}) for outcome {outcome_id}")
        return outcome

    def record_incident(
        self,
        outcome_id: str,
        severity: str = "medium",
        description: str = "",
    ) -> Outcome:
        """Record incident/bug found in production.

        Args:
            outcome_id: Outcome ID to update
            severity: Severity level (low, medium, high, critical)
            description: Incident description

        Returns:
            Updated Outcome
        """
        if outcome_id not in self._outcomes:
            raise ValueError(f"Outcome {outcome_id} not found")

        outcome = self._outcomes[outcome_id]

        outcome.add_signal(
            SignalType.INCIDENT,
            SignalValence.NEGATIVE,
            description=description or "Incident detected",
            severity=severity,
        )

        logger.warning(f"Recorded incident for outcome {outcome_id}: {description}")
        return outcome

    def record_performance(
        self,
        outcome_id: str,
        metrics: Dict[str, Any],
    ) -> Outcome:
        """Record performance metrics (latency, throughput, etc).

        Args:
            outcome_id: Outcome ID to update
            metrics: Performance metrics dict

        Returns:
            Updated Outcome
        """
        if outcome_id not in self._outcomes:
            raise ValueError(f"Outcome {outcome_id} not found")

        outcome = self._outcomes[outcome_id]

        # Determine valence based on metrics
        # If latency is high or throughput is low, it's negative
        latency = metrics.get("avg_latency_ms", 0)
        throughput = metrics.get("throughput_rps", float("inf"))

        is_good = latency < 100 and throughput > 1000  # Heuristic thresholds
        valence = SignalValence.POSITIVE if is_good else SignalValence.NEGATIVE

        outcome.add_signal(
            SignalType.PERFORMANCE_OK if is_good else SignalType.PERFORMANCE_POOR,
            valence,
            description=f"Performance: {latency}ms latency, {throughput} rps throughput",
            metrics=metrics,
        )

        logger.info(f"Recorded performance metrics for outcome {outcome_id}")
        return outcome

    def check_success_criteria(self, outcome_id: str) -> Dict[str, Any]:
        """Check if decision's success criteria are being met.

        Args:
            outcome_id: Outcome ID to check

        Returns:
            Dict with success assessment
        """
        if outcome_id not in self._outcomes:
            raise ValueError(f"Outcome {outcome_id} not found")

        outcome = self._outcomes[outcome_id]

        # Count signal valences
        positive_count = outcome.positive_signal_count()
        negative_count = outcome.negative_signal_count()

        # Simple heuristic
        success_score = outcome.estimate_success()

        return {
            "outcome_id": outcome_id,
            "status": outcome.status.value,
            "positive_signals": positive_count,
            "negative_signals": negative_count,
            "estimated_success": success_score,
            "needs_attention": negative_count > 0 or success_score < 0.5,
        }

    def finalize_outcome(
        self,
        outcome_id: str,
        final_status: str = "success",
        final_score: float = 0.5,
        lessons_learned: Optional[List[str]] = None,
        decision_domain: Optional[str] = None,
    ) -> Outcome:
        """Mark outcome as complete after 30-day period.

        Args:
            outcome_id: Outcome ID to finalize
            final_status: Final result (success, partial, failure)
            final_score: Final success score (0.0-1.0)
            lessons_learned: Key learnings from outcome
            decision_domain: Domain of the decision (e.g., "database", "auth")

        Returns:
            Finalized Outcome
        """
        if outcome_id not in self._outcomes:
            raise ValueError(f"Outcome {outcome_id} not found")

        outcome = self._outcomes[outcome_id]
        outcome.status = OutcomeStatus.COMPLETED
        outcome.completed_at = datetime.now().isoformat()
        outcome.final_status = final_status
        outcome.final_score = final_score
        outcome.lessons_learned = lessons_learned or []

        logger.info(
            f"Finalized outcome {outcome_id}: {final_status} (score: {final_score})"
        )

        # Update team calibration if domain provided
        if decision_domain and self.calibration_updater:
            try:
                self.calibration_updater.update_from_finalized_outcome(outcome, decision_domain)
                logger.info(f"Updated calibration for domain '{decision_domain}' from outcome {outcome_id}")
            except Exception as e:
                logger.warning(f"Failed to update calibration: {e}")

        return outcome

    def get_outcome(self, outcome_id: str) -> Optional[Outcome]:
        """Get outcome by ID.

        Args:
            outcome_id: Outcome ID to retrieve

        Returns:
            Outcome object or None
        """
        return self._outcomes.get(outcome_id)

    def list_outcomes(
        self,
        decision_id: Optional[str] = None,
        status: Optional[OutcomeStatus] = None,
    ) -> List[Outcome]:
        """List outcomes with optional filtering.

        Args:
            decision_id: Filter by decision ID
            status: Filter by status

        Returns:
            List of matching outcomes
        """
        results = []

        for outcome in self._outcomes.values():
            if decision_id and outcome.decision_id != decision_id:
                continue
            if status and outcome.status != status:
                continue
            results.append(outcome)

        return results

    def export_outcome(self, outcome_id: str) -> Dict[str, Any]:
        """Export outcome as dict (for serialization).

        Args:
            outcome_id: Outcome ID to export

        Returns:
            Dict representation of outcome
        """
        if outcome_id not in self._outcomes:
            raise ValueError(f"Outcome {outcome_id} not found")

        outcome = self._outcomes[outcome_id]
        data = asdict(outcome)

        # Convert enums to strings
        data["status"] = outcome.status.value
        data["signals"] = [
            {
                "signal_type": s.signal_type.value,
                "valence": s.valence.value,
                "timestamp": s.timestamp,
                "description": s.description,
                "severity": s.severity,
                "metrics": s.metrics,
            }
            for s in outcome.signals
        ]

        return data
