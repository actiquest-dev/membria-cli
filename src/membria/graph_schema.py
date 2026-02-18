"""FalkorDB Graph Schema - Node and Relationship Definitions

This module defines the complete causal memory graph structure.
All nodes and relationships are defined here for easy reference and maintenance.
"""

from dataclasses import dataclass, field
import json
from typing import Dict, List, Optional, Any, Tuple
from enum import Enum


class NodeType(str, Enum):
    """All node types in the graph"""
    DECISION = "Decision"
    ENGRAM = "Engram"
    CODE_CHANGE = "CodeChange"
    OUTCOME = "Outcome"
    NEGATIVE_KNOWLEDGE = "NegativeKnowledge"
    ANTIPATTERN = "AntiPattern"
    SCHEMA_VERSION = "SchemaVersion"
    MIGRATION = "Migration"
    DOCUMENT = "Document"
    DOCSHOT = "DocShot"
    CALIBRATION_PROFILE = "CalibrationProfile"
    SKILL = "Skill"
    SESSION_CONTEXT = "SessionContext"
    WORKSPACE = "Workspace"
    PROJECT = "Project"
    PROFILE = "Profile"
    ROLE = "Role"
    SQUAD = "Squad"
    ASSIGNMENT = "Assignment"


class RelationType(str, Enum):
    """All relationship types in the graph"""
    MADE_IN = "MADE_IN"  # Decision --[MADE_IN]--> Engram
    IMPLEMENTED_IN = "IMPLEMENTED_IN"  # Decision --[IMPLEMENTED_IN]--> CodeChange
    RESULTED_IN = "RESULTED_IN"  # CodeChange --[RESULTED_IN]--> Outcome
    TRIGGERED = "TRIGGERED"  # CodeChange --[TRIGGERED]--> AntiPattern
    CAUSED = "CAUSED"  # Outcome --[CAUSED]--> NegativeKnowledge
    PREVENTED = "PREVENTED"  # NegativeKnowledge --[PREVENTED]--> Decision
    REWORKED_BY = "REWORKED_BY"  # Decision --[REWORKED_BY]--> CodeChange
    SIMILAR_TO = "SIMILAR_TO"  # Decision --[SIMILAR_TO]--> Decision
    REFERENCES = "REFERENCES"  # Document --[REFERENCES]--> Decision
    DOCUMENTS = "DOCUMENTS"  # Decision --[DOCUMENTS]--> Document
    USES_DOCSHOT = "USES_DOCSHOT"  # Decision --[USES_DOCSHOT]--> DocShot
    INCLUDES = "INCLUDES"  # DocShot --[INCLUDES]--> Document
    HAS_CONTEXT = "HAS_CONTEXT"  # Engram --[HAS_CONTEXT]--> SessionContext
    MEASURED_BY = "MEASURED_BY"  # Decision --[MEASURED_BY]--> CalibrationProfile
    TRACKS = "TRACKS"  # CalibrationProfile --[TRACKS]--> Domain (implicit via domain field)
    GENERATED_FROM = "GENERATED_FROM"  # Skill --[GENERATED_FROM]--> Decision
    BASED_ON = "BASED_ON"  # Skill --[BASED_ON]--> CalibrationProfile
    WARNS_AGAINST = "WARNS_AGAINST"  # Skill --[WARNS_AGAINST]--> AntiPattern
    VERSION_OF = "VERSION_OF"  # Skill --[VERSION_OF]--> Skill (previous version)
    HAS_PROJECT = "HAS_PROJECT"  # Workspace --[HAS_PROJECT]--> Project
    USES_SQUAD = "USES_SQUAD"  # Project --[USES_SQUAD]--> Squad
    ASSIGNS = "ASSIGNS"  # Squad --[ASSIGNS]--> Assignment
    USES_PROFILE = "USES_PROFILE"  # Assignment --[USES_PROFILE]--> Profile
    PLAYS_ROLE = "PLAYS_ROLE"  # Assignment --[PLAYS_ROLE]--> Role
    ROLE_USES_DOCSHOT = "ROLE_USES_DOCSHOT"  # Role --[ROLE_USES_DOCSHOT]--> DocShot
    ROLE_USES_SKILL = "ROLE_USES_SKILL"  # Role --[ROLE_USES_SKILL]--> Skill
    ROLE_USES_NK = "ROLE_USES_NK"  # Role --[ROLE_USES_NK]--> NegativeKnowledge


# ============================================================================
# NODE SCHEMAS
# ============================================================================


@dataclass
class DecisionNodeSchema:
    """Decision Node - A choice made by developer or AI"""

    # Identity
    id: str  # Unique ID (dec_abc123)

    # What was decided
    statement: str  # "Use PostgreSQL for persistence"
    alternatives: List[str]  # ["MongoDB", "SQLite"]
    confidence: float  # 0-1 scale

    # Context
    module: str  # auth, database, api, frontend, backend, infra
    created_at: int  # Unix timestamp
    created_by: str  # "claude-code", "human"

    # Outcome tracking
    outcome: Optional[str] = None  # success, failure, pending, reworked
    resolved_at: Optional[int] = None  # When outcome known
    actual_success_rate: Optional[float] = None  # 0-1, how often succeeded

    # Reference
    engram_id: Optional[str] = None  # eng_xyz
    commit_sha: Optional[str] = None  # abc123def456

    # Vector embedding (FalkorDB native: stored as array property)
    embedding: Optional[List[float]] = None  # 1536-dim or smaller for semantic search

    def to_cypher_create(self) -> Tuple[str, Dict]:
        """Generate CREATE statement for this node with parameterized query"""
        query = """
        CREATE (d:Decision {
            id: $id,
            statement: $statement,
            alternatives: $alternatives,
            confidence: $confidence,
            module: $module,
            created_at: $created_at,
            created_by: $created_by,
            role_id: $role_id,
            assignment_id: $assignment_id,
            outcome: $outcome,
            resolved_at: $resolved_at,
            actual_success_rate: $actual_success_rate,
            engram_id: $engram_id,
            commit_sha: $commit_sha,
            embedding: $embedding
        })
        RETURN d
        """
        params = {
            "id": self.id,
            "statement": self.statement,
            "alternatives": str(self.alternatives),
            "confidence": self.confidence,
            "module": self.module,
            "created_at": self.created_at,
            "created_by": self.created_by,
            "role_id": getattr(self, "role_id", None),
            "assignment_id": getattr(self, "assignment_id", None),
            "outcome": self.outcome,
            "resolved_at": self.resolved_at,
            "actual_success_rate": self.actual_success_rate,
            "engram_id": self.engram_id,
            "commit_sha": self.commit_sha,
            "embedding": self.embedding
        }
        return query, params

    @staticmethod
    def _escape_string(s: str) -> str:
        """Escape string for Cypher"""
        return f'"{s.replace(chr(34), chr(92) + chr(34))}"'


@dataclass
class EngramNodeSchema:
    """Engram Node - Session checkpoint (Claude Code session)"""

    # Identity
    id: str  # eng_abc123
    session_id: str  # sess_phase2_work

    # Git context
    commit_sha: str  # What was committed
    commit_message: str  # Commit message
    branch: str  # Branch name (main, feature/X)

    # Timing
    created_at: int  # Unix timestamp when session ended
    session_duration_sec: int  # Total duration

    # AI context
    agent_type: str  # "claude-code"
    agent_model: str  # "claude-sonnet-4-5-20250514"

    # Summary
    decisions_extracted: int = 0
    files_changed: int = 0
    lines_added: int = 0
    lines_removed: int = 0

    def to_cypher_create(self) -> Tuple[str, Dict]:
        """Generate CREATE statement for this node with parameterized query"""
        query = """
        CREATE (e:Engram {
            id: $id,
            session_id: $session_id,
            commit_sha: $commit_sha,
            commit_message: $commit_message,
            branch: $branch,
            created_at: $created_at,
            session_duration_sec: $session_duration_sec,
            agent_type: $agent_type,
            agent_model: $agent_model,
            decisions_extracted: $decisions_extracted,
            files_changed: $files_changed,
            lines_added: $lines_added,
            lines_removed: $lines_removed
        })
        RETURN e
        """
        params = {
            "id": self.id,
            "session_id": self.session_id,
            "commit_sha": self.commit_sha,
            "commit_message": self.commit_message,
            "branch": self.branch,
            "created_at": self.created_at,
            "session_duration_sec": self.session_duration_sec,
            "agent_type": self.agent_type,
            "agent_model": self.agent_model,
            "decisions_extracted": self.decisions_extracted,
            "files_changed": self.files_changed,
            "lines_added": self.lines_added,
            "lines_removed": self.lines_removed
        }
        return query, params


@dataclass
class CodeChangeNodeSchema:
    """CodeChange Node - A git commit that implemented a decision"""

    # Identity
    id: str  # change_123

    # What changed
    commit_sha: str  # abc123def456
    files_changed: List[str]  # ["src/graph.py", "src/models.py"]
    diff_stat_added: int  # Lines added
    diff_stat_removed: int  # Lines removed
    diff_stat_modified: int  # Files modified count

    # When
    timestamp: int  # Unix timestamp
    author: str  # "claude-code", "developer"

    # Why (linked to decision)
    decision_id: Optional[str] = None  # dec_abc123

    # Did it work?
    outcome: Optional[str] = None  # success, failure, reverted
    reverted_by: Optional[str] = None  # change_456 (if reverted)
    days_to_revert: Optional[int] = None  # How many days until reverted

    def to_cypher_create(self) -> Tuple[str, Dict]:
        """Generate CREATE statement for this node with parameterized query"""
        query = """
        CREATE (c:CodeChange {
            id: $id,
            commit_sha: $commit_sha,
            files_changed: $files_changed,
            diff_stat_added: $diff_stat_added,
            diff_stat_removed: $diff_stat_removed,
            diff_stat_modified: $diff_stat_modified,
            timestamp: $timestamp,
            author: $author,
            decision_id: $decision_id,
            outcome: $outcome,
            reverted_by: $reverted_by,
            days_to_revert: $days_to_revert
        })
        RETURN c
        """
        params = {
            "id": self.id,
            "commit_sha": self.commit_sha,
            "files_changed": str(self.files_changed),
            "diff_stat_added": self.diff_stat_added,
            "diff_stat_removed": self.diff_stat_removed,
            "diff_stat_modified": self.diff_stat_modified,
            "timestamp": self.timestamp,
            "author": self.author,
            "decision_id": self.decision_id,
            "outcome": self.outcome,
            "reverted_by": self.reverted_by,
            "days_to_revert": self.days_to_revert
        }
        return query, params


@dataclass
class OutcomeNodeSchema:
    """Outcome Node - Result of a code change"""

    # Identity
    id: str  # outcome_123

    # Result
    status: str  # success, failure, partial
    evidence: str  # "Graph performs well, no errors in 2 weeks"
    measured_at: int  # Unix timestamp

    # Metrics (0-1 scale where applicable)
    performance_impact: float = 1.0  # 1.0 = no impact, <1 = slower, >1 = faster
    reliability: float = 1.0  # Uptime/error rate (0-1)
    maintenance_cost: float = 0.5  # Developer effort (0-1, lower = easier)

    # Link
    code_change_id: Optional[str] = None
    ttl_days: Optional[int] = None
    is_active: bool = True
    deprecated_reason: Optional[str] = None

    def to_cypher_create(self) -> Tuple[str, Dict]:
        """Generate CREATE statement for this node with parameterized query"""
        query = """
        CREATE (o:Outcome {
            id: $id,
            status: $status,
            evidence: $evidence,
            measured_at: $measured_at,
            performance_impact: $performance_impact,
            reliability: $reliability,
            maintenance_cost: $maintenance_cost,
            code_change_id: $code_change_id,
            ttl_days: $ttl_days,
            is_active: $is_active,
            deprecated_reason: $deprecated_reason
        })
        RETURN o
        """
        params = {
            "id": self.id,
            "status": self.status,
            "evidence": self.evidence,
            "measured_at": self.measured_at,
            "performance_impact": self.performance_impact,
            "reliability": self.reliability,
            "maintenance_cost": self.maintenance_cost,
            "code_change_id": self.code_change_id,
            "ttl_days": self.ttl_days,
            "is_active": self.is_active,
            "deprecated_reason": self.deprecated_reason
        }
        return query, params


@dataclass
class NegativeKnowledgeNodeSchema:
    """NegativeKnowledge Node - What we learned NOT to do"""

    # Identity
    id: str  # nk_custom_jwt_fail

    # What failed
    hypothesis: str  # "Custom JWT implementation is safe"
    conclusion: str  # "Custom JWT has 89% removal rate"

    # Evidence
    evidence: str  # "20,470 repos, removed within 97 days avg"
    source: str  # "CodeDigger analysis", "personal experience"

    # Context
    domain: str  # auth, database, performance, etc.
    severity: str  # high, medium, low

    # Timing
    discovered_at: int  # Unix timestamp
    expires_at: Optional[int] = None  # Can expire (None = never)

    # Prevention
    blocks_pattern: str = ""  # Pattern ID to block (if from CodeDigger)
    recommendation: str = ""  # What to do instead

    # Vector embedding (FalkorDB native: for semantic search)
    embedding: Optional[List[float]] = None  # 1536-dim for similarity search

    def to_cypher_create(self) -> Tuple[str, Dict]:
        """Generate CREATE statement for this node with parameterized query"""
        query = """
        CREATE (nk:NegativeKnowledge {
            id: $id,
            hypothesis: $hypothesis,
            conclusion: $conclusion,
            evidence: $evidence,
            source: $source,
            domain: $domain,
            severity: $severity,
            discovered_at: $discovered_at,
            expires_at: $expires_at,
            blocks_pattern: $blocks_pattern,
            recommendation: $recommendation,
            embedding: $embedding
        })
        RETURN nk
        """
        params = {
            "id": self.id,
            "hypothesis": self.hypothesis,
            "conclusion": self.conclusion,
            "evidence": self.evidence,
            "source": self.source,
            "domain": self.domain,
            "severity": self.severity,
            "discovered_at": self.discovered_at,
            "expires_at": self.expires_at,
            "blocks_pattern": self.blocks_pattern,
            "recommendation": self.recommendation,
            "embedding": self.embedding
        }
        return query, params


@dataclass
class DocumentNodeSchema:
    """Document Node - Markdown documentation and specification files"""

    # Identity
    id: str  # doc_design_graph
    file_path: str  # "docs/design/graph.md"

    # Content
    content: str  # Full markdown content
    doc_type: str  # "design", "spec", "readme", "guide", "tutorial"

    # Timing
    created_at: int  # Unix timestamp
    updated_at: int  # Unix timestamp

    # Vector embedding (FalkorDB native: for semantic search)
    embedding: Optional[List[float]] = None  # 1536-dim for semantic matching

    # Metadata
    metadata: Dict[str, Any] = field(default_factory=dict)
    tenant_id: str = "default"
    team_id: str = "default"
    project_id: str = "default"

    def to_cypher_create(self) -> Tuple[str, Dict]:
        """Generate CREATE statement for this node with parameterized query"""
        from membria.security import safe_json_dumps, escape_cypher_string
        
        metadata_str = escape_cypher_string(safe_json_dumps(self.metadata))
        
        query = """
        CREATE (doc:Document {
            id: $id,
            file_path: $file_path,
            content: $content,
            doc_type: $doc_type,
            created_at: $created_at,
            updated_at: $updated_at,
            embedding: $embedding,
            metadata: $metadata,
            tenant_id: $tenant_id,
            team_id: $team_id,
            project_id: $project_id
        })
        RETURN doc
        """
        params = {
            "id": self.id,
            "file_path": self.file_path,
            "content": self.content,
            "doc_type": self.doc_type,
            "created_at": self.created_at,
            "updated_at": self.updated_at,
            "embedding": self.embedding,
            "metadata": metadata_str,
            "tenant_id": self.tenant_id,
            "team_id": self.team_id,
            "project_id": self.project_id
        }
        return query, params


@dataclass
class SessionContextNodeSchema:
    """SessionContext Node - short-lived working memory."""

    id: str  # sc_<session_id>
    session_id: str
    task: str
    focus: Optional[str] = None
    current_plan: Optional[str] = None
    constraints: List[str] = field(default_factory=list)
    doc_count: int = 0
    doc_shot_id: Optional[str] = None
    created_at: int = 0
    expires_at: Optional[int] = None
    is_active: bool = True

    def to_cypher_create(self) -> Tuple[str, Dict]:
        """Generate CREATE statement for this node with parameterized query"""
        from membria.security import sanitize_text, sanitize_list

        task = sanitize_text(self.task, max_len=400)
        focus = sanitize_text(self.focus or "", max_len=200) if self.focus else ""
        current_plan = sanitize_text(self.current_plan or "", max_len=600) if self.current_plan else ""
        constraints = sanitize_list(self.constraints, max_len=200)
        doc_shot = sanitize_text(self.doc_shot_id or "", max_len=80) if self.doc_shot_id else ""

        query = """
        CREATE (sc:SessionContext {
            id: $id,
            session_id: $session_id,
            task: $task,
            focus: $focus,
            current_plan: $current_plan,
            constraints: $constraints,
            doc_count: $doc_count,
            doc_shot_id: $doc_shot_id,
            created_at: $created_at,
            expires_at: $expires_at,
            is_active: $is_active
        })
        RETURN sc
        """
        params = {
            "id": self.id,
            "session_id": self.session_id,
            "task": task,
            "focus": focus if focus else None,
            "current_plan": current_plan if current_plan else None,
            "constraints": json.dumps(constraints),
            "doc_count": int(self.doc_count),
            "doc_shot_id": doc_shot if doc_shot else None,
            "created_at": self.created_at,
            "expires_at": self.expires_at,
            "is_active": self.is_active
        }
        return query, params


@dataclass
class WorkspaceNodeSchema:
    """Workspace Node - Top-level container for projects and teams."""
    id: str
    name: str
    created_at: int
    description: Optional[str] = None
    tenant_id: str = "default"
    team_id: str = "default"


@dataclass
class ProjectNodeSchema:
    """Project Node - Task/initiative inside a workspace."""
    id: str
    name: str
    workspace_id: str
    created_at: int
    description: Optional[str] = None


@dataclass
class ProfileNodeSchema:
    """Profile Node - LLM model/personality profile."""
    id: str
    model: str  # claude-opus-4-6, gpt-4, etc.
    temperature: float = 0.7
    top_p: float = 1.0
    max_tokens: int = 4096


@dataclass
class RoleNodeSchema:
    """Role Node - Squad role template."""
    id: str  # investigator, skeptic, arbiter, etc.
    name: str
    system_prompt: str
    description: str = ""


@dataclass
class SquadNodeSchema:
    """Squad Node - Team of AI roles."""
    id: str
    name: str
    roles: List[str] = field(default_factory=list)  # Role IDs
    created_at: int = 0


@dataclass
class AssignmentNodeSchema:
    """Assignment Node - Role assignment to a project."""
    id: str
    squad_id: str
    project_id: str
    profile_id: str
    role_id: str
    assigned_at: int


@dataclass
class AntiPatternNodeSchema:
    """AntiPattern Node - Code patterns to avoid (from CodeDigger)"""

    id: str  # ap_custom_jwt_auth
    name: str  # "Custom JWT Auth"
    category: str  # "security", "performance", "reliability"

    # Stats
    repos_affected: int  # Number of repos with this pattern
    occurrence_count: int  # Total occurrences
    removal_rate: float  # % of repos that remove it
    avg_days_to_removal: float  # Average time to removal

    # Content
    keywords: List[str] = field(default_factory=list)
    regex_pattern: str = ""
    example_bad: str = ""
    example_good: str = ""

    # Origin
    first_seen: int = 0  # Unix timestamp
    found_by: str = "CodeDigger"  # Source
    source: str = ""  # Reference

    def to_cypher_create(self) -> Tuple[str, Dict]:
        """Generate CREATE statement for this node with parameterized query"""
        query = """
        CREATE (ap:AntiPattern {
            id: $id,
            name: $name,
            category: $category,
            repos_affected: $repos_affected,
            occurrence_count: $occurrence_count,
            removal_rate: $removal_rate,
            avg_days_to_removal: $avg_days_to_removal,
            keywords: $keywords,
            regex_pattern: $regex_pattern,
            example_bad: $example_bad,
            example_good: $example_good,
            first_seen: $first_seen,
            found_by: $found_by,
            source: $source
        })
        RETURN ap
        """
        params = {
            "id": self.id,
            "name": self.name,
            "category": self.category,
            "repos_affected": self.repos_affected,
            "occurrence_count": self.occurrence_count,
            "removal_rate": self.removal_rate,
            "avg_days_to_removal": self.avg_days_to_removal,
            "keywords": str(self.keywords),
            "regex_pattern": self.regex_pattern,
            "example_bad": self.example_bad,
            "example_good": self.example_good,
            "first_seen": self.first_seen,
            "found_by": self.found_by,
            "source": self.source
        }
        return query, params


@dataclass
class CalibrationProfileNodeSchema:
    """CalibrationProfile Node - Team calibration metrics for a domain"""

    # Identity
    id: str  # cal_database, cal_auth, cal_api
    domain: str  # database, auth, api, frontend, backend

    # Beta distribution parameters (Bayesian calibration)
    alpha: float  # Successes + prior (default 1)
    beta: float  # Failures + prior (default 1)
    sample_size: int  # Number of decisions tracked (α+β-2)

    # Calibration metrics
    mean_success_rate: float  # α/(α+β)
    variance: float  # Variance of distribution
    confidence_gap: float  # Expected confidence - actual success rate
    trend: str  # improving, stable, declining

    # Metadata
    created_at: int  # Unix timestamp when profile created
    last_updated: int  # Unix timestamp of last update
    last_evaluation: Optional[int] = None  # When last analyzed

    # Recommendations
    recommendations: List[str] = field(default_factory=list)

    def to_cypher_create(self) -> Tuple[str, Dict]:
        """Generate CREATE statement for this node with parameterized query"""
        query = """
        CREATE (cp:CalibrationProfile {
            id: $id,
            domain: $domain,
            alpha: $alpha,
            beta: $beta,
            sample_size: $sample_size,
            mean_success_rate: $mean_success_rate,
            variance: $variance,
            confidence_gap: $confidence_gap,
            trend: $trend,
            created_at: $created_at,
            last_updated: $last_updated,
            last_evaluation: $last_evaluation,
            recommendations: $recommendations
        })
        RETURN cp
        """
        params = {
            "id": self.id,
            "domain": self.domain,
            "alpha": self.alpha,
            "beta": self.beta,
            "sample_size": self.sample_size,
            "mean_success_rate": self.mean_success_rate,
            "variance": self.variance,
            "confidence_gap": self.confidence_gap,
            "trend": self.trend,
            "created_at": self.created_at,
            "last_updated": self.last_updated,
            "last_evaluation": self.last_evaluation,
            "recommendations": str(self.recommendations)
        }
        return query, params


@dataclass
class SkillNodeSchema:
    """Skill Node - Procedural knowledge generated from outcomes"""

    # Identity
    id: str  # sk-database_strategy-v2
    domain: str  # database, auth, api, etc.
    name: str  # "database_strategy_recommendation"
    version: int  # 2

    # Evidence
    success_rate: float  # 0.89
    confidence: float  # From Beta distribution
    sample_size: int  # Number of decisions observed

    # Content
    procedure: str  # Markdown with decision procedure

    # Applicability zones
    green_zone: List[str] = field(default_factory=list)  # Use confidently (>75% success)
    yellow_zone: List[str] = field(default_factory=list)  # Review carefully (50-75%)
    red_zone: List[str] = field(default_factory=list)  # Avoid (<50% success)

    # Metadata
    created_at: int = 0  # Unix timestamp
    last_updated: int = 0  # Unix timestamp
    next_review: int = 0  # When to regenerate
    ttl_days: Optional[int] = None  # When to deprecate if no updates

    # Quality
    quality_score: float = 0.5  # 0-1 (success_rate * (1 - 1/sqrt(sample_size)))
    confidence_interval_lower: float = 0.0
    confidence_interval_upper: float = 1.0

    # Links
    generated_from_decisions: List[str] = field(default_factory=list)  # Decision IDs
    conflicts_with: List[str] = field(default_factory=list)  # Skill IDs
    related_skills: List[str] = field(default_factory=list)

    # Status
    is_active: bool = True

    def to_cypher_create(self) -> Tuple[str, Dict]:
        """Generate CREATE statement for this node with parameterized query"""
        from membria.security import escape_cypher_string, safe_json_dumps

        green = escape_cypher_string(safe_json_dumps(self.green_zone))
        yellow = escape_cypher_string(safe_json_dumps(self.yellow_zone))
        red = escape_cypher_string(safe_json_dumps(self.red_zone))
        from_decs = escape_cypher_string(safe_json_dumps(self.generated_from_decisions))
        conflicts = escape_cypher_string(safe_json_dumps(self.conflicts_with))
        related = escape_cypher_string(safe_json_dumps(self.related_skills))

        query = """
        CREATE (sk:Skill {
            id: $id,
            domain: $domain,
            name: $name,
            version: $version,
            success_rate: $success_rate,
            confidence: $confidence,
            sample_size: $sample_size,
            procedure: $procedure,
            green_zone: $green_zone,
            yellow_zone: $yellow_zone,
            red_zone: $red_zone,
            created_at: $created_at,
            last_updated: $last_updated,
            next_review: $next_review,
            ttl_days: $ttl_days,
            quality_score: $quality_score,
            confidence_interval_lower: $confidence_interval_lower,
            confidence_interval_upper: $confidence_interval_upper,
            generated_from_decisions: $generated_from_decisions,
            conflicts_with: $conflicts_with,
            related_skills: $related_skills,
            is_active: $is_active
        })
        RETURN sk
        """
        params = {
            "id": self.id,
            "domain": self.domain,
            "name": self.name,
            "version": self.version,
            "success_rate": self.success_rate,
            "confidence": self.confidence,
            "sample_size": self.sample_size,
            "procedure": self.procedure,
            "green_zone": green,
            "yellow_zone": yellow,
            "red_zone": red,
            "created_at": self.created_at,
            "last_updated": self.last_updated,
            "next_review": self.next_review,
            "ttl_days": self.ttl_days,
            "quality_score": self.quality_score,
            "confidence_interval_lower": self.confidence_interval_lower,
            "confidence_interval_upper": self.confidence_interval_upper,
            "generated_from_decisions": from_decs,
            "conflicts_with": conflicts,
            "related_skills": related,
            "is_active": self.is_active
        }
        return query, params


# ============================================================================
# RELATIONSHIP SCHEMAS
# ============================================================================


@dataclass
class RelationshipSchema:
    """Generic relationship schema"""

    from_node_id: str
    from_node_type: NodeType
    to_node_id: str
    to_node_type: NodeType
    relation_type: RelationType
    properties: Dict[str, Any]

    def to_cypher_create(self) -> Tuple[str, Dict]:
        """Generate CREATE relationship statement with parameterized query"""
        # Build the properties clause with parameter placeholders
        prop_clauses = []
        prop_params = {}
        for i, (k, v) in enumerate(self.properties.items()):
            param_name = f"prop_{k}"
            prop_clauses.append(f"{k}: ${param_name}")
            prop_params[param_name] = v

        props_str = f" {{{', '.join(prop_clauses)}}}" if prop_clauses else ""

        query = f"""
        MATCH (from:{self.from_node_type.value} {{id: $from_id}}),
              (to:{self.to_node_type.value} {{id: $to_id}})
        CREATE (from)-[r:{self.relation_type.value}{props_str}]->(to)
        RETURN r
        """

        params = {
            "from_id": self.from_node_id,
            "to_id": self.to_node_id,
            **prop_params
        }

        return query, params


def make_made_in(decision_id: str, engram_id: str, timestamp: int) -> RelationshipSchema:
    """Decision --[MADE_IN]--> Engram"""
    return RelationshipSchema(
        from_node_id=decision_id,
        from_node_type=NodeType.DECISION,
        to_node_id=engram_id,
        to_node_type=NodeType.ENGRAM,
        relation_type=RelationType.MADE_IN,
        properties={"timestamp": timestamp}
    )


def make_implemented_in(decision_id: str, change_id: str, timestamp: int) -> RelationshipSchema:
    """Decision --[IMPLEMENTED_IN]--> CodeChange"""
    return RelationshipSchema(
        from_node_id=decision_id,
        from_node_type=NodeType.DECISION,
        to_node_id=change_id,
        to_node_type=NodeType.CODE_CHANGE,
        relation_type=RelationType.IMPLEMENTED_IN,
        properties={"timestamp": timestamp}
    )


def make_resulted_in(change_id: str, outcome_id: str, days_to_outcome: int) -> RelationshipSchema:
    """CodeChange --[RESULTED_IN]--> Outcome"""
    return RelationshipSchema(
        from_node_id=change_id,
        from_node_type=NodeType.CODE_CHANGE,
        to_node_id=outcome_id,
        to_node_type=NodeType.OUTCOME,
        relation_type=RelationType.RESULTED_IN,
        properties={"days_to_outcome": days_to_outcome}
    )


def make_triggered(change_id: str, pattern_id: str, severity: str) -> RelationshipSchema:
    """CodeChange --[TRIGGERED]--> AntiPattern"""
    return RelationshipSchema(
        from_node_id=change_id,
        from_node_type=NodeType.CODE_CHANGE,
        to_node_id=pattern_id,
        to_node_type=NodeType.ANTIPATTERN,
        relation_type=RelationType.TRIGGERED,
        properties={"severity": severity}
    )


def make_caused(outcome_id: str, nk_id: str) -> RelationshipSchema:
    """Outcome --[CAUSED]--> NegativeKnowledge"""
    return RelationshipSchema(
        from_node_id=outcome_id,
        from_node_type=NodeType.OUTCOME,
        to_node_id=nk_id,
        to_node_type=NodeType.NEGATIVE_KNOWLEDGE,
        relation_type=RelationType.CAUSED,
        properties={}
    )


def make_prevented(nk_id: str, decision_id: str) -> RelationshipSchema:
    """NegativeKnowledge --[PREVENTED]--> Decision"""
    return RelationshipSchema(
        from_node_id=nk_id,
        from_node_type=NodeType.NEGATIVE_KNOWLEDGE,
        to_node_id=decision_id,
        to_node_type=NodeType.DECISION,
        relation_type=RelationType.PREVENTED,
        properties={}
    )


def make_reworked_by(decision_id: str, change_id: str, reason: str) -> RelationshipSchema:
    """Decision --[REWORKED_BY]--> CodeChange"""
    return RelationshipSchema(
        from_node_id=decision_id,
        from_node_type=NodeType.DECISION,
        to_node_id=change_id,
        to_node_type=NodeType.CODE_CHANGE,
        relation_type=RelationType.REWORKED_BY,
        properties={"reason": reason}
    )


def make_similar_to(decision_id_1: str, decision_id_2: str, similarity: float) -> RelationshipSchema:
    """Decision --[SIMILAR_TO]--> Decision"""
    return RelationshipSchema(
        from_node_id=decision_id_1,
        from_node_type=NodeType.DECISION,
        to_node_id=decision_id_2,
        to_node_type=NodeType.DECISION,
        relation_type=RelationType.SIMILAR_TO,
        properties={"similarity_score": similarity}
    )


def make_references(doc_id: str, decision_id: str) -> RelationshipSchema:
    """Document --[REFERENCES]--> Decision"""
    return RelationshipSchema(
        from_node_id=doc_id,
        from_node_type=NodeType.DOCUMENT,
        to_node_id=decision_id,
        to_node_type=NodeType.DECISION,
        relation_type=RelationType.REFERENCES,
        properties={}
    )


def make_documents(decision_id: str, doc_id: str) -> RelationshipSchema:
    """Decision --[DOCUMENTS]--> Document"""
    return RelationshipSchema(
        from_node_id=decision_id,
        from_node_type=NodeType.DECISION,
        to_node_id=doc_id,
        to_node_type=NodeType.DOCUMENT,
        relation_type=RelationType.DOCUMENTS,
        properties={}
    )


def make_generated_from(skill_id: str, decision_id: str) -> RelationshipSchema:
    """Skill --[GENERATED_FROM]--> Decision"""
    return RelationshipSchema(
        from_node_id=skill_id,
        from_node_type=NodeType.SKILL,
        to_node_id=decision_id,
        to_node_type=NodeType.DECISION,
        relation_type=RelationType.GENERATED_FROM,
        properties={}
    )


def make_based_on(skill_id: str, calibration_id: str) -> RelationshipSchema:
    """Skill --[BASED_ON]--> CalibrationProfile"""
    return RelationshipSchema(
        from_node_id=skill_id,
        from_node_type=NodeType.SKILL,
        to_node_id=calibration_id,
        to_node_type=NodeType.CALIBRATION_PROFILE,
        relation_type=RelationType.BASED_ON,
        properties={}
    )


def make_warns_against(skill_id: str, antipattern_id: str) -> RelationshipSchema:
    """Skill --[WARNS_AGAINST]--> AntiPattern"""
    return RelationshipSchema(
        from_node_id=skill_id,
        from_node_type=NodeType.SKILL,
        to_node_id=antipattern_id,
        to_node_type=NodeType.ANTIPATTERN,
        relation_type=RelationType.WARNS_AGAINST,
        properties={}
    )


def make_version_of(skill_v2_id: str, skill_v1_id: str) -> RelationshipSchema:
    """Skill v2 --[VERSION_OF]--> Skill v1 (previous version)"""
    return RelationshipSchema(
        from_node_id=skill_v2_id,
        from_node_type=NodeType.SKILL,
        to_node_id=skill_v1_id,
        to_node_type=NodeType.SKILL,
        relation_type=RelationType.VERSION_OF,
        properties={}
    )


# ============================================================================
# INDICES & CONSTRAINTS
# ============================================================================


INDICES = [
    # Decision indices
    "CREATE INDEX ON :Decision(id)",
    "CREATE INDEX ON :Decision(module)",
    "CREATE INDEX ON :Decision(created_at)",
    "CREATE INDEX ON :Decision(outcome)",

    # Engram indices
    "CREATE INDEX ON :Engram(id)",
    "CREATE INDEX ON :Engram(session_id)",
    "CREATE INDEX ON :Engram(commit_sha)",

    # CodeChange indices
    "CREATE INDEX ON :CodeChange(id)",
    "CREATE INDEX ON :CodeChange(commit_sha)",
    "CREATE INDEX ON :CodeChange(decision_id)",

    # Outcome indices
    "CREATE INDEX ON :Outcome(id)",
    "CREATE INDEX ON :Outcome(status)",

    # NegativeKnowledge indices
    "CREATE INDEX ON :NegativeKnowledge(id)",
    "CREATE INDEX ON :NegativeKnowledge(domain)",

    # AntiPattern indices
    "CREATE INDEX ON :AntiPattern(id)",
    "CREATE INDEX ON :AntiPattern(category)",

    # Document indices
    "CREATE INDEX ON :Document(id)",
    "CREATE INDEX ON :Document(doc_type)",

    # DocShot indices
    "CREATE INDEX ON :DocShot(id)",
    "CREATE INDEX ON :DocShot(created_at)",

    # Skill indices
    "CREATE INDEX ON :Skill(id)",
    "CREATE INDEX ON :Skill(domain)",
    "CREATE INDEX ON :Skill(version)",
    "CREATE INDEX ON :Skill(quality_score)",

    # SessionContext indices
    "CREATE INDEX ON :SessionContext(session_id)",
    "CREATE INDEX ON :SessionContext(expires_at)",

    # Vector indices (FalkorDB HNSW for similarity search)
    # Note: Execute these separately after creating nodes with embeddings
    # "CALL db.idx.vector.createNodeIndex('Decision', 'embedding', 1536, 'cosine')",
    # "CALL db.idx.vector.createNodeIndex('NegativeKnowledge', 'embedding', 1536, 'cosine')",
    # "CALL db.idx.vector.createNodeIndex('Document', 'embedding', 1536, 'cosine')",
]

CONSTRAINTS = [
    # Unique constraints
    "CREATE CONSTRAINT FOR (d:Decision) REQUIRE d.id IS UNIQUE",
    "CREATE CONSTRAINT FOR (e:Engram) REQUIRE e.id IS UNIQUE",
    "CREATE CONSTRAINT FOR (c:CodeChange) REQUIRE c.id IS UNIQUE",
    "CREATE CONSTRAINT FOR (o:Outcome) REQUIRE o.id IS UNIQUE",
    "CREATE CONSTRAINT FOR (nk:NegativeKnowledge) REQUIRE nk.id IS UNIQUE",
    "CREATE CONSTRAINT FOR (ap:AntiPattern) REQUIRE ap.id IS UNIQUE",
    "CREATE CONSTRAINT FOR (doc:Document) REQUIRE doc.id IS UNIQUE",
    "CREATE CONSTRAINT FOR (sk:Skill) REQUIRE sk.id IS UNIQUE",
]
