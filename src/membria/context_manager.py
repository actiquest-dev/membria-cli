"""Unified Context Manager with compaction across sources."""

import logging
from dataclasses import dataclass
from typing import Any, Dict, List, Optional

from membria.decision_surface import DecisionSurface
from membria.chain_builder import BehaviorChainOrchestrator
from membria.security import sanitize_text

logger = logging.getLogger(__name__)


@dataclass
class ContextSection:
    name: str
    content: str
    priority: int  # lower = higher priority

    @property
    def tokens(self) -> int:
        return len(self.content) // 4 if self.content else 0


class ContextManager:
    """Builds a single compact context bundle from multiple sources."""

    def __init__(self, graph_client, calibration_updater):
        # Accept GraphClient or raw FalkorDB graph instance.
        self.graph_client = graph_client
        self.calibration_updater = calibration_updater
        surface_client = graph_client
        self.surface_available = True
        if hasattr(graph_client, "query") and not hasattr(graph_client, "graph"):
            # DecisionSurface expects GraphClient; raw graph has no .graph attribute.
            surface_client = None
            self.surface_available = False
        self.decision_surface = DecisionSurface(surface_client)
        self.chain_orchestrator = BehaviorChainOrchestrator(graph_client, calibration_updater)
        try:
            from membria.config import ConfigManager
            self.plugin_order = ConfigManager().config.context_plugins
        except Exception:
            self.plugin_order = [
                "docshot",
                "session_context",
                "calibration",
                "negative_knowledge",
                "role_negative_knowledge",
                "similar_decisions",
                "role_skills",
                "behavior_chains",
            ]
        # Ensure role-specific plugins are present
        if "role_negative_knowledge" not in self.plugin_order:
            self.plugin_order.append("role_negative_knowledge")
        if "role_skills" not in self.plugin_order:
            self.plugin_order.append("role_skills")

    def build_decision_context(
        self,
        statement: str,
        module: str,
        confidence: float,
        max_tokens: int = 2000,
        include_chains: bool = True,
        doc_shot: Optional[Dict[str, Any]] = None,
        session_context: Optional[Dict[str, Any]] = None,
        role_skills: Optional[List[Dict[str, Any]]] = None,
        role_negative_knowledge: Optional[List[Dict[str, Any]]] = None,
    ) -> Dict[str, Any]:
        """Build a compact decision context with a single token budget."""
        surface = None
        if self.surface_available:
            surface = self.decision_surface.generate_context(statement, module=module)

        sections: List[ContextSection] = []

        plugin_map = {
            "docshot": lambda: _docshot_section(doc_shot),
            "session_context": lambda: _session_section(session_context),
            "calibration": lambda: _calibration_section(surface),
            "negative_knowledge": lambda: _nk_section(surface),
            "role_negative_knowledge": lambda: _role_nk_section(role_negative_knowledge),
            "similar_decisions": lambda: _similar_section(surface),
            "role_skills": lambda: _role_skills_section(role_skills),
            "behavior_chains": lambda: _chains_section(include_chains, self.chain_orchestrator, module, statement, confidence, max_tokens),
        }

        for name in self.plugin_order:
            builder = plugin_map.get(name)
            if not builder:
                continue
            section = builder()
            if section:
                sections.append(section)

        compact = self._compact_sections(sections, max_tokens=max_tokens)
        return {
            "compact_context": compact["text"],
            "total_tokens": compact["tokens"],
            "truncated": compact["truncated"],
            "sections_included": compact["sections"],
            "surface": surface,
        }

    def _compact_sections(self, sections: List[ContextSection], max_tokens: int) -> Dict[str, Any]:
        """Compacts context sections within token budget."""
        if not sections:
            return {"text": "", "tokens": 0, "truncated": False, "sections": []}

        sections_sorted = sorted(sections, key=lambda s: s.priority)
        output_lines: List[str] = ["# Decision Context (Unified)\n"]
        tokens_used = len(output_lines[0]) // 4
        included: List[Dict[str, Any]] = []
        truncated = False

        for section in sections_sorted:
            if not section.content:
                continue
            section_tokens = section.tokens
            if tokens_used + section_tokens <= max_tokens:
                output_lines.append(section.content.strip() + "\n")
                tokens_used += section_tokens
                included.append({"name": section.name, "tokens": section_tokens})
            else:
                # Try partial fit
                remaining = max_tokens - tokens_used
                if remaining > 20:
                    chars = remaining * 4
                    snippet = section.content[:chars].rstrip()
                    output_lines.append(snippet + "\n")
                    tokens_used += len(snippet) // 4
                    included.append({"name": section.name, "tokens": len(snippet) // 4})
                truncated = True
                break

        if truncated:
            output_lines.append("*[Context truncated to fit token budget]*\n")

        return {
            "text": "\n".join(output_lines).strip() + "\n",
            "tokens": tokens_used,
            "truncated": truncated,
            "sections": included,
        }


def _docshot_section(doc_shot: Optional[Dict[str, Any]]) -> Optional[ContextSection]:
    if not doc_shot:
        return None
    doc_shot_id = doc_shot.get("doc_shot_id") or "docshot_unknown"
    doc_count = doc_shot.get("count", 0)
    content = (
        "## DocShot (Provenance)\n"
        f"- DocShot ID: {sanitize_text(str(doc_shot_id), max_len=80)}\n"
        f"- Documents: {doc_count}\n"
    )
    return ContextSection("docshot", content, priority=0)


def _session_section(session_context: Optional[Dict[str, Any]]) -> Optional[ContextSection]:
    if not session_context:
        return None
    lines = ["## Session Context"]
    task = session_context.get("task")
    focus = session_context.get("focus")
    current_plan = session_context.get("current_plan")
    constraints = session_context.get("constraints") or []
    if task:
        lines.append(f"- Task: {sanitize_text(task, max_len=200)}")
    if focus:
        lines.append(f"- Focus: {sanitize_text(focus, max_len=200)}")
    if current_plan:
        lines.append(f"- Plan: {sanitize_text(current_plan, max_len=280)}")
    if constraints:
        for c in constraints[:5]:
            lines.append(f"- Constraint: {sanitize_text(str(c), max_len=160)}")
    return ContextSection("session_context", "\n".join(lines) + "\n", priority=1)


def _calibration_section(surface) -> Optional[ContextSection]:
    if not surface or not surface.team_calibration:
        return None
    cal = surface.team_calibration
    content = (
        "## Team Calibration\n"
        f"- Success rate: {cal.get('actual_success', cal.get('success_rate', 0)):.0%}\n"
        f"- Confidence gap: {cal.get('overconfidence', cal.get('confidence_gap', 0)):+.0%}\n"
        f"- Sample size: {cal.get('sample_size', 0)}\n"
    )
    return ContextSection("calibration", content, priority=2)


def _nk_section(surface) -> Optional[ContextSection]:
    if not surface or not surface.negative_knowledge_alerts:
        return None
    lines = ["## Negative Knowledge (Avoid)"]
    for alert in surface.negative_knowledge_alerts[:5]:
        pattern = sanitize_text(alert.get("pattern", ""), max_len=120)
        rec = sanitize_text(alert.get("recommendation", ""), max_len=160)
        lines.append(f"- {pattern}: {rec}")
    return ContextSection("negative_knowledge", "\n".join(lines) + "\n", priority=3)


def _role_nk_section(items: Optional[List[Dict[str, Any]]]) -> Optional[ContextSection]:
    if not items:
        return None
    lines = ["## Role Negative Knowledge (Avoid)"]
    for item in items[:5]:
        pattern = sanitize_text(item.get("hypothesis", "") or item.get("pattern", ""), max_len=120)
        rec = sanitize_text(item.get("recommendation", "") or item.get("conclusion", ""), max_len=160)
        if pattern:
            lines.append(f"- {pattern}: {rec}")
    return ContextSection("role_negative_knowledge", "\n".join(lines) + "\n", priority=3)


def _similar_section(surface) -> Optional[ContextSection]:
    if not surface or not surface.similar_decisions:
        return None
    lines = ["## Similar Decisions"]
    for item in surface.similar_decisions[:5]:
        stmt = sanitize_text(item.get("statement", ""), max_len=160)
        outcome = item.get("outcome", "unknown")
        lines.append(f"- {stmt} ({outcome})")
    return ContextSection("similar_decisions", "\n".join(lines) + "\n", priority=4)


def _role_skills_section(items: Optional[List[Dict[str, Any]]]) -> Optional[ContextSection]:
    if not items:
        return None
    lines = ["## Role Skills (Use)"]
    for item in items[:5]:
        name = sanitize_text(item.get("name", ""), max_len=80)
        statement = sanitize_text(item.get("statement", ""), max_len=160)
        if name or statement:
            lines.append(f"- {name}: {statement}".strip(": "))
    return ContextSection("role_skills", "\n".join(lines) + "\n", priority=4)


def _chains_section(include_chains: bool, orchestrator, module: str, statement: str, confidence: float, max_tokens: int) -> Optional[ContextSection]:
    if not include_chains:
        return None
    try:
        chain_ctx = orchestrator.build_context(
            domain=module,
            statement=statement,
            confidence=confidence,
            max_tokens=max_tokens,
        )
        if chain_ctx.get("full_context"):
            return ContextSection("behavior_chains", chain_ctx["full_context"], priority=5)
    except Exception as exc:
        logger.warning(f"Context chains failed: {exc}")
    return None
