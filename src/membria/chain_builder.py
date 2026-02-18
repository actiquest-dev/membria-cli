"""Chain Builder - Orchestrates behavior chains for context injection

The BehaviorChainOrchestrator runs all 4 chains in sequence,
aggregates their outputs, and formats for Claude injection.
"""

import logging
from typing import Dict, List, Optional
from datetime import datetime

from membria.behavior_chains import (
    PositivePrecedentChain,
    NegativeEvidenceChain,
    CalibrationWarningChain,
    AntiPatternGuardChain,
    ChainExecutionResult,
)

logger = logging.getLogger(__name__)


class BehaviorChainOrchestrator:
    """Orchestrates all 4 behavior chains for context injection.

    Execution order prioritizes debiasing (calibration warning first)
    then negative knowledge (what to avoid) before positive precedents.

    Token budget aware - limits output to ~2000 tokens total.
    """

    def __init__(self, graph_client, calibration_updater):
        """Initialize orchestrator with dependencies.

        Args:
            graph_client: GraphClient instance
            calibration_updater: CalibrationUpdater instance
        """
        self.graph_client = graph_client
        self.calibration_updater = calibration_updater

        # Initialize chains (order matters for prioritization)
        self.chains = [
            ("calibration_warning", CalibrationWarningChain(calibration_updater)),
            ("negative_evidence", NegativeEvidenceChain(graph_client)),
            ("antipattern_guard", AntiPatternGuardChain(graph_client)),
            ("positive_precedent", PositivePrecedentChain(graph_client)),
        ]

    def build_context(
        self,
        domain: str,
        statement: str,
        confidence: float,
        max_tokens: int = 2000
    ) -> Dict[str, any]:
        """Build complete behavior chain context for a decision.

        Runs all chains, aggregates outputs, respects token budget.

        Args:
            domain: Domain name (database, auth, api, etc.)
            statement: Decision statement
            confidence: Developer's stated confidence (0-1)
            max_tokens: Maximum tokens for output (~4 chars per token)

        Returns:
            Dict with:
            - full_context: Markdown formatted complete context
            - chains_executed: List of ChainExecutionResult
            - total_tokens: Estimated token count
            - truncated: Whether output was truncated
        """
        logger.info(f"Building context for: {domain} @ {confidence:.0%} confidence")

        results = []
        full_output = f"# Decision Context: {domain}\n\n"
        full_output += f"**Your Confidence:** {confidence:.0%}\n\n"

        # Run chains in priority order
        for chain_name, chain in self.chains:
            try:
                if chain_name == "calibration_warning":
                    output = chain.build(domain, confidence)
                elif chain_name == "negative_evidence":
                    output = chain.build(domain)
                elif chain_name == "antipattern_guard":
                    output = chain.build(domain, statement)
                elif chain_name == "positive_precedent":
                    output = chain.build(domain, statement)
                else:
                    output = ""

                result = ChainExecutionResult(chain_name, output)
                results.append(result)

                if output:
                    full_output += output + "\n"

            except Exception as e:
                logger.error(f"Error executing {chain_name} chain: {e}")
                result = ChainExecutionResult(chain_name, error=str(e))
                results.append(result)

        # Check token budget
        estimated_tokens = len(full_output) // 4
        truncated = False

        if estimated_tokens > max_tokens:
            # Truncate least important chains (positive_precedent first)
            logger.warning(
                f"Context exceeds token budget: {estimated_tokens} > {max_tokens}"
            )
            full_output = self._truncate_context(results, max_tokens)
            truncated = True

        return {
            "domain": domain,
            "statement": statement,
            "confidence": confidence,
            "full_context": full_output,
            "chains_executed": [
                {
                    "name": r.chain_name,
                    "triggered": r.triggered,
                    "tokens": len(r.content) // 4 if r.content else 0,
                    "error": r.error,
                }
                for r in results
            ],
            "total_tokens": estimated_tokens,
            "truncated": truncated,
            "timestamp": datetime.now().isoformat(),
        }

    def _truncate_context(self, results: List[ChainExecutionResult], max_tokens: int) -> str:
        """Truncate context to fit token budget.

        Priority order (from most important):
        1. Calibration Warning (debiasing - most critical)
        2. Negative Evidence (failures - important)
        3. AntiPattern Guard (pattern detection)
        4. Positive Precedent (examples - can be truncated)

        Args:
            results: List of chain execution results
            max_tokens: Maximum tokens to include

        Returns:
            Truncated markdown context
        """
        priority_order = [
            "calibration_warning",
            "negative_evidence",
            "antipattern_guard",
            "positive_precedent",
        ]

        output = f"# Decision Context (Truncated)\n\n"
        tokens_used = len(output) // 4

        # Add chains in priority order
        for chain_name in priority_order:
            for result in results:
                if result.chain_name == chain_name and result.content:
                    chain_tokens = len(result.content) // 4

                    if tokens_used + chain_tokens <= max_tokens:
                        output += result.content + "\n"
                        tokens_used += chain_tokens
                    else:
                        # Add truncation note
                        output += f"\n*[Additional {chain_name} content truncated due to token limit]*\n"
                        return output

        return output

    def test_chains(self, domain: str, statement: str, confidence: float = 0.75) -> Dict:
        """Test all chains without returning full context (for debugging).

        Args:
            domain: Domain name
            statement: Decision statement
            confidence: Test confidence level

        Returns:
            Dict with chain execution details
        """
        logger.info(f"Testing chains for: {domain}")

        test_results = {
            "domain": domain,
            "statement": statement,
            "confidence": confidence,
            "chains": {},
        }

        for chain_name, chain in self.chains:
            try:
                if chain_name == "calibration_warning":
                    output = chain.build(domain, confidence)
                elif chain_name == "negative_evidence":
                    output = chain.build(domain)
                elif chain_name == "antipattern_guard":
                    output = chain.build(domain, statement)
                elif chain_name == "positive_precedent":
                    output = chain.build(domain, statement)
                else:
                    output = ""

                triggered = bool(output and output.strip())
                test_results["chains"][chain_name] = {
                    "triggered": triggered,
                    "output_length": len(output),
                    "token_estimate": len(output) // 4,
                    "first_line": output.split("\n")[0] if output else "",
                }

            except Exception as e:
                logger.error(f"Error testing {chain_name}: {e}")
                test_results["chains"][chain_name] = {
                    "error": str(e),
                    "triggered": False,
                }

        return test_results

    def get_chain_stats(self) -> Dict[str, any]:
        """Get statistics about chain implementations.

        Returns:
            Dict with chain statistics
        """
        return {
            "total_chains": len(self.chains),
            "chains": [
                {
                    "name": chain_name,
                    "class": chain.__class__.__name__,
                }
                for chain_name, chain in self.chains
            ],
            "execution_order": [name for name, _ in self.chains],
            "priority_order": [
                "calibration_warning",
                "negative_evidence",
                "antipattern_guard",
                "positive_precedent",
            ],
        }
