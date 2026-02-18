"""Calibration updater - orchestrates updates from outcomes."""

import logging
from typing import Optional, Dict, Any

from membria.calibration_models import TeamCalibration
from membria.outcome_models import Outcome

logger = logging.getLogger(__name__)


class CalibrationUpdater:
    """Updates team calibration from finalized outcomes."""

    def __init__(self, team_calibration: Optional[TeamCalibration] = None):
        """Initialize calibration updater.

        Args:
            team_calibration: Shared TeamCalibration instance (optional)
        """
        self.team_calibration = team_calibration or TeamCalibration()

    def update_from_finalized_outcome(
        self, outcome: Outcome, decision_domain: str
    ) -> bool:
        """Update calibration from a finalized outcome.

        Args:
            outcome: Finalized Outcome object
            decision_domain: Domain of the decision

        Returns:
            True if update successful, False otherwise
        """
        try:
            if not outcome.final_status:
                logger.warning(f"Outcome {outcome.outcome_id} not finalized, skipping calibration update")
                return False

            # Determine success/failure from outcome
            success = outcome.final_status == "success"

            # Update calibration
            self.team_calibration.update_from_outcome(
                domain=decision_domain,
                success=success,
                score=outcome.final_score or (1.0 if success else 0.0),
            )

            logger.info(
                f"Updated calibration for {decision_domain}: "
                f"{'success' if success else 'failure'} "
                f"(score: {outcome.final_score})"
            )
            return True

        except Exception as e:
            logger.error(f"Error updating calibration from outcome {outcome.outcome_id}: {e}")
            return False

    def batch_update_pending_outcomes(
        self, outcomes: list, domain_map: Dict[str, str]
    ) -> Dict[str, int]:
        """Batch update from multiple outcomes.

        Args:
            outcomes: List of Outcome objects
            domain_map: Mapping of decision_id -> domain

        Returns:
            Summary: {updated: int, failed: int, skipped: int}
        """
        stats = {"updated": 0, "failed": 0, "skipped": 0}

        for outcome in outcomes:
            # Find decision ID from outcome (assuming it has decision_id)
            decision_id = getattr(outcome, "decision_id", None)
            if not decision_id:
                stats["skipped"] += 1
                continue

            # Get domain from mapping
            domain = domain_map.get(decision_id, "general")

            # Update
            if self.update_from_finalized_outcome(outcome, domain):
                stats["updated"] += 1
            else:
                stats["failed"] += 1

        return stats

    def get_confidence_guidance(
        self,
        domain: str,
        decision_confidence: Optional[float] = None,
    ) -> Dict[str, Any]:
        """Get confidence adjustment guidance for a domain.

        Args:
            domain: Decision domain
            decision_confidence: User's estimated confidence (0-1)

        Returns:
            Guidance dict with recommendation and metrics
        """
        if domain not in self.team_calibration.calibrations:
            return {
                "domain": domain,
                "status": "no_data",
                "message": "No calibration data available yet",
                "adjustment": 0.0,
                "recommendation": None,
            }

        dist = self.team_calibration.calibrations[domain]
        profile = self.team_calibration.analyze_domain(domain)

        # Calculate calibration gap
        actual_success_rate = dist.mean
        confidence_gap = (decision_confidence or 0.5) - actual_success_rate if decision_confidence else 0.0

        adjustment = profile.get_adjustment()

        # Generate recommendation if there's any gap and we have sufficient data
        recommendation = None
        if dist.sample_size >= 3 and abs(confidence_gap) > 0.05:
            if confidence_gap > 0:  # Overconfident
                pct = max(5, int(abs(confidence_gap) * 100))
                recommendation = f"Team is {pct}% overconfident in {domain}. Consider reducing new decision confidence by {pct}%."
            else:  # Underconfident
                pct = max(5, int(abs(confidence_gap) * 100))
                recommendation = f"Team is {pct}% underconfident in {domain}. Consider increasing new decision confidence by {pct}%."

        return {
            "domain": domain,
            "status": "data_available",
            "sample_size": dist.sample_size,
            "actual_success_rate": actual_success_rate,
            "estimated_confidence": decision_confidence or "unknown",
            "confidence_gap": confidence_gap,
            "adjustment": adjustment,
            "trend": profile.trend,
            "recommendation": recommendation,
            "credible_interval_95": dist.confidence_interval(0.95),
        }

    def get_all_profiles(self) -> Dict[str, Dict[str, Any]]:
        """Get calibration profiles for all domains."""
        result = {}
        for domain in self.team_calibration.calibrations:
            profile = self.team_calibration.analyze_domain(domain)
            result[domain] = profile.to_dict()
        return result
