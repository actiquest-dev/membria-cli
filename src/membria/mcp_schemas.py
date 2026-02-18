"""MCP tool schema validation for inputs and outputs."""

from typing import Any, Dict, List, Optional
from pydantic import BaseModel, Field, ConfigDict


class CaptureDecisionParams(BaseModel):
    model_config = ConfigDict(extra="forbid")
    statement: str = Field(..., min_length=1)
    alternatives: List[str] = Field(..., min_length=1)
    confidence: float = Field(0.5, ge=0.0, le=1.0)
    context: Optional[Dict[str, Any]] = None


class RecordOutcomeParams(BaseModel):
    model_config = ConfigDict(extra="forbid")
    decision_id: str = Field(..., min_length=1)
    final_status: str = Field(..., min_length=1)
    final_score: float = Field(0.5, ge=0.0, le=1.0)
    decision_domain: str = Field("general", min_length=1)


class GetCalibrationParams(BaseModel):
    model_config = ConfigDict(extra="forbid")
    domain: Optional[str] = None


class GetDecisionContextParams(BaseModel):
    model_config = ConfigDict(extra="forbid")
    statement: str = Field(..., min_length=1)
    module: Optional[str] = None
    confidence: float = Field(0.5, ge=0.0, le=1.0)
    max_tokens: Optional[int] = Field(2000, ge=256, le=8000)


class GetContextParams(BaseModel):
    model_config = ConfigDict(extra="forbid")
    request: str = Field(..., min_length=1)
    module: Optional[str] = None
    confidence: float = Field(0.5, ge=0.0, le=1.0)
    max_tokens: Optional[int] = Field(2000, ge=256, le=8000)
    session_id: Optional[str] = None


class GetPlanContextParams(BaseModel):
    model_config = ConfigDict(extra="forbid")
    domain: str = Field(..., min_length=1)
    scope: Optional[str] = None
    max_tokens: Optional[int] = Field(1500, ge=256, le=8000)


class FetchDocsParams(BaseModel):
    model_config = ConfigDict(extra="forbid")
    doc_types: Optional[List[str]] = None
    file_paths: Optional[List[str]] = None
    doc_ids: Optional[List[str]] = None
    limit: int = Field(10, ge=1, le=200)


class MDXtractParams(BaseModel):
    model_config = ConfigDict(extra="forbid")
    input: str = Field(..., min_length=1)
    input_type: Optional[str] = None  # "path" | "url"
    max_chars: Optional[int] = Field(0, ge=0, le=200000)
    ocr: Optional[bool] = False


class MemoryStoreParams(BaseModel):
    model_config = ConfigDict(extra="forbid")
    memory_type: str = Field(..., min_length=1)  # decision | negative_knowledge
    payload: Dict[str, Any]
    ttl_days: Optional[int] = Field(None, ge=1, le=3650)


class MemoryRetrieveParams(BaseModel):
    model_config = ConfigDict(extra="forbid")
    memory_type: str = Field(..., min_length=1)
    domain: Optional[str] = None
    limit: int = Field(5, ge=1, le=50)


class MemoryDeleteParams(BaseModel):
    model_config = ConfigDict(extra="forbid")
    memory_type: str = Field(..., min_length=1)
    item_id: str = Field(..., min_length=1)
    reason: str = Field("manual_delete", min_length=1)


class MemoryListParams(BaseModel):
    model_config = ConfigDict(extra="forbid")
    memory_type: str = Field(..., min_length=1)
    domain: Optional[str] = None
    limit: int = Field(10, ge=1, le=100)


class SessionContextStoreParams(BaseModel):
    model_config = ConfigDict(extra="forbid")
    session_id: str = Field(..., min_length=1)
    task: str = Field(..., min_length=1)
    focus: Optional[str] = None
    current_plan: Optional[str] = None
    constraints: Optional[List[str]] = None
    doc_shot_id: Optional[str] = None
    ttl_days: int = Field(3, ge=1, le=30)


class SessionContextRetrieveParams(BaseModel):
    model_config = ConfigDict(extra="forbid")
    session_id: Optional[str] = None
    limit: int = Field(5, ge=1, le=50)


class SessionContextDeleteParams(BaseModel):
    model_config = ConfigDict(extra="forbid")
    session_id: str = Field(..., min_length=1)


class DocsAddParams(BaseModel):
    model_config = ConfigDict(extra="forbid")
    file_path: str = Field(..., min_length=1)
    content: str = Field(..., min_length=1)
    doc_type: str = Field("kb", min_length=1)
    metadata: Optional[Dict[str, Any]] = None


class DocsGetParams(BaseModel):
    model_config = ConfigDict(extra="forbid")
    doc_ids: Optional[List[str]] = None
    file_paths: Optional[List[str]] = None
    doc_types: Optional[List[str]] = None
    limit: int = Field(10, ge=1, le=200)


class DocShotLinkParams(BaseModel):
    model_config = ConfigDict(extra="forbid")
    decision_id: str = Field(..., min_length=1)
    doc_shot_id: str = Field(..., min_length=1)
    docs: List[Dict[str, Any]] = Field(default_factory=list)
    fetched_at: Optional[str] = None


class OutcomeGetParams(BaseModel):
    model_config = ConfigDict(extra="forbid")
    outcome_id: str = Field(..., min_length=1)


class OutcomeListParams(BaseModel):
    model_config = ConfigDict(extra="forbid")
    status: Optional[str] = None
    limit: int = Field(10, ge=1, le=100)


class SkillListParams(BaseModel):
    model_config = ConfigDict(extra="forbid")
    domain: Optional[str] = None
    min_quality: float = Field(0.5, ge=0.0, le=1.0)
    limit: int = Field(20, ge=1, le=100)


class SkillGetParams(BaseModel):
    model_config = ConfigDict(extra="forbid")
    domain: str = Field(..., min_length=1)
    name: str = Field(..., min_length=1)


class AntipatternListParams(BaseModel):
    model_config = ConfigDict(extra="forbid")
    category: Optional[str] = None
    limit: int = Field(20, ge=1, le=200)


class AntipatternGetParams(BaseModel):
    model_config = ConfigDict(extra="forbid")
    pattern_id: str = Field(..., min_length=1)


class HealthParams(BaseModel):
    model_config = ConfigDict(extra="forbid")


class MigrationsStatusParams(BaseModel):
    model_config = ConfigDict(extra="forbid")


class LogsTailParams(BaseModel):
    model_config = ConfigDict(extra="forbid")
    lines: int = Field(50, ge=1, le=500)


class FetchDocsResult(ToolResultBase):
    status: str
    count: int
    doc_shot_id: Optional[str] = None
    docs: List[Dict[str, Any]]


class MDXtractResult(ToolResultBase):
    status: str
    markdown: str
    metadata: Dict[str, Any]


class SquadCreateParams(BaseModel):
    model_config = ConfigDict(extra="forbid")
    name: str = Field(..., min_length=1)
    project_id: str = Field(..., min_length=1)
    strategy: str = Field(..., min_length=1)
    roles: List[str] = Field(..., min_length=1)
    profiles: List[str] = Field(..., min_length=1)
    profile_paths: Optional[List[str]] = None


class AssignmentAddParams(BaseModel):
    model_config = ConfigDict(extra="forbid")
    squad_id: str = Field(..., min_length=1)
    role: str = Field(..., min_length=1)
    profile: str = Field(..., min_length=1)
    profile_path: Optional[str] = None
    order: int = Field(0, ge=0, le=1000)
    weight: float = Field(1.0, ge=0.0, le=10.0)


class SquadListParams(BaseModel):
    model_config = ConfigDict(extra="forbid")
    project_id: Optional[str] = None
    limit: int = Field(20, ge=1, le=100)


class SquadAssignmentsParams(BaseModel):
    model_config = ConfigDict(extra="forbid")
    squad_id: str = Field(..., min_length=1)


class SquadCreateResult(ToolResultBase):
    status: str
    squad_id: str
    assignments: List[Dict[str, Any]]


class SquadListResult(ToolResultBase):
    status: str
    items: List[Dict[str, Any]]


class SquadAssignmentsResult(ToolResultBase):
    status: str
    items: List[Dict[str, Any]]


class AssignmentAddResult(ToolResultBase):
    status: str
    assignment_id: str


class RoleUpsertParams(BaseModel):
    model_config = ConfigDict(extra="forbid")
    name: str = Field(..., min_length=1)
    description: Optional[str] = None
    prompt_path: Optional[str] = None
    context_policy: Optional[Dict[str, Any]] = None
    docshot_ids: Optional[List[str]] = None
    skill_ids: Optional[List[str]] = None
    nk_ids: Optional[List[str]] = None


class RoleGetParams(BaseModel):
    model_config = ConfigDict(extra="forbid")
    name: str = Field(..., min_length=1)


class RoleUpsertResult(ToolResultBase):
    status: str
    role_id: str


class RoleGetResult(ToolResultBase):
    status: str
    item: Optional[Dict[str, Any]] = None


class RoleLinkParams(BaseModel):
    model_config = ConfigDict(extra="forbid")
    name: str = Field(..., min_length=1)
    docshot_ids: Optional[List[str]] = None
    skill_ids: Optional[List[str]] = None
    nk_ids: Optional[List[str]] = None


class RoleUnlinkParams(BaseModel):
    model_config = ConfigDict(extra="forbid")
    name: str = Field(..., min_length=1)
    docshot_ids: Optional[List[str]] = None
    skill_ids: Optional[List[str]] = None
    nk_ids: Optional[List[str]] = None


class RoleLinkResult(ToolResultBase):
    status: str


class ValidatePlanParams(BaseModel):
    model_config = ConfigDict(extra="forbid")
    steps: List[str] = Field(..., min_length=1)
    domain: Optional[str] = None


class RecordPlanParams(BaseModel):
    model_config = ConfigDict(extra="forbid")
    plan_steps: List[str] = Field(..., min_length=1)
    domain: str = Field(..., min_length=1)
    plan_confidence: float = Field(0.5, ge=0.0, le=1.0)
    duration_estimate: Optional[str] = None
    warnings_shown: int = 0
    warnings_heeded: int = 0


class ToolResultBase(BaseModel):
    model_config = ConfigDict(extra="allow")


class CaptureDecisionResult(ToolResultBase):
    decision_id: str
    statement: str
    confidence: float
    module: str
    status: str


class RecordOutcomeResult(ToolResultBase):
    outcome_id: str
    decision_id: str
    final_status: str
    final_score: float


class GetDecisionContextResult(ToolResultBase):
    decision_statement: str
    module: str
    your_confidence: float
    compact_context: Optional[str] = None
    total_tokens: Optional[int] = None
    truncated: Optional[bool] = None
    sections_included: Optional[List[Dict[str, Any]]] = None


class GetPlanContextResult(ToolResultBase):
    domain: str
    formatted: Optional[str] = None
    total_tokens: Optional[int] = None
    compact_context: Optional[str] = None
    compact_tokens: Optional[int] = None
    compact_truncated: Optional[bool] = None
    sections_included: Optional[List[Dict[str, Any]]] = None


class ValidatePlanResult(ToolResultBase):
    total_steps: int
    warnings_count: int
    can_proceed: bool


class RecordPlanResult(ToolResultBase):
    engram_id: str
    domain: str
    plan_steps: int
    status: str


class RecordDecisionDaemonResult(ToolResultBase):
    status: str
    decision_id: str


class GetContextDaemonResult(ToolResultBase):
    pending_signals: int
    similar_decisions: list
    recent_patterns: list
    context_ready: bool
    compact_context: Optional[str] = None
    total_tokens: Optional[int] = None
    truncated: Optional[bool] = None
    sections_included: Optional[List[Dict[str, Any]]] = None
    doc_shot_id: Optional[str] = None


class MemoryStoreResult(ToolResultBase):
    status: str
    item_id: str


class MemoryRetrieveResult(ToolResultBase):
    status: str
    items: List[Dict[str, Any]]


class MemoryDeleteResult(ToolResultBase):
    status: str
    item_id: str


class MemoryListResult(ToolResultBase):
    status: str
    items: List[Dict[str, Any]]


class SessionContextResult(ToolResultBase):
    status: str
    items: List[Dict[str, Any]]


class DocsResult(ToolResultBase):
    status: str
    items: List[Dict[str, Any]]


class DocShotLinkResult(ToolResultBase):
    status: str
    decision_id: str
    doc_shot_id: str


class OutcomeResult(ToolResultBase):
    status: str
    item: Optional[Dict[str, Any]] = None
    items: Optional[List[Dict[str, Any]]] = None


class SkillResult(ToolResultBase):
    status: str
    items: List[Dict[str, Any]]


class AntipatternResult(ToolResultBase):
    status: str
    items: List[Dict[str, Any]]


class HealthResult(ToolResultBase):
    status: str
    health: Dict[str, Any]


class MigrationsStatusResult(ToolResultBase):
    status: str
    current_version: str
    pending: int


class LogsTailResult(ToolResultBase):
    status: str
    logs: str


class GetCalibrationDaemonResult(ToolResultBase):
    calibrated: bool
    overconfidence_gap: float
    sample_size: int


INPUT_SCHEMAS = {
    "membria.capture_decision": CaptureDecisionParams,
    "membria.record_outcome": RecordOutcomeParams,
    "membria.get_calibration": GetCalibrationParams,
    "membria.get_decision_context": GetDecisionContextParams,
    "membria.get_plan_context": GetPlanContextParams,
    "membria.fetch_docs": FetchDocsParams,
    "membria.md_xtract": MDXtractParams,
    "membria.squad_create": SquadCreateParams,
    "membria.assignment_add": AssignmentAddParams,
    "membria.squad_list": SquadListParams,
    "membria.squad_assignments": SquadAssignmentsParams,
    "membria.role_upsert": RoleUpsertParams,
    "membria.role_get": RoleGetParams,
    "membria.role_link": RoleLinkParams,
    "membria.role_unlink": RoleUnlinkParams,
    "membria.memory_store": MemoryStoreParams,
    "membria.memory_retrieve": MemoryRetrieveParams,
    "membria.memory_delete": MemoryDeleteParams,
    "membria.memory_list": MemoryListParams,
    "membria.session_context_store": SessionContextStoreParams,
    "membria.session_context_retrieve": SessionContextRetrieveParams,
    "membria.session_context_delete": SessionContextDeleteParams,
    "membria.docs_add": DocsAddParams,
    "membria.docs_get": DocsGetParams,
    "membria.docs_list": DocsGetParams,
    "membria.docshot_link": DocShotLinkParams,
    "membria.outcome_get": OutcomeGetParams,
    "membria.outcome_list": OutcomeListParams,
    "membria.skills_list": SkillListParams,
    "membria.skills_get": SkillGetParams,
    "membria.antipatterns_list": AntipatternListParams,
    "membria.antipatterns_get": AntipatternGetParams,
    "membria.health": HealthParams,
    "membria.migrations_status": MigrationsStatusParams,
    "membria.logs_tail": LogsTailParams,
    "membria.validate_plan": ValidatePlanParams,
    "membria.record_plan": RecordPlanParams,
    "membria_record_decision": CaptureDecisionParams,
    "membria_get_context": GetContextParams,
    "membria_get_calibration": GetCalibrationParams,
}


OUTPUT_SCHEMAS = {
    "membria.capture_decision": CaptureDecisionResult,
    "membria.record_outcome": RecordOutcomeResult,
    "membria.get_decision_context": GetDecisionContextResult,
    "membria.get_plan_context": GetPlanContextResult,
    "membria.fetch_docs": FetchDocsResult,
    "membria.md_xtract": MDXtractResult,
    "membria.squad_create": SquadCreateResult,
    "membria.assignment_add": AssignmentAddResult,
    "membria.squad_list": SquadListResult,
    "membria.squad_assignments": SquadAssignmentsResult,
    "membria.role_upsert": RoleUpsertResult,
    "membria.role_get": RoleGetResult,
    "membria.role_link": RoleLinkResult,
    "membria.role_unlink": RoleLinkResult,
    "membria.memory_store": MemoryStoreResult,
    "membria.memory_retrieve": MemoryRetrieveResult,
    "membria.memory_delete": MemoryDeleteResult,
    "membria.memory_list": MemoryListResult,
    "membria.session_context_store": SessionContextResult,
    "membria.session_context_retrieve": SessionContextResult,
    "membria.session_context_delete": SessionContextResult,
    "membria.docs_add": DocsResult,
    "membria.docs_get": DocsResult,
    "membria.docs_list": DocsResult,
    "membria.docshot_link": DocShotLinkResult,
    "membria.outcome_get": OutcomeResult,
    "membria.outcome_list": OutcomeResult,
    "membria.skills_list": SkillResult,
    "membria.skills_get": SkillResult,
    "membria.antipatterns_list": AntipatternResult,
    "membria.antipatterns_get": AntipatternResult,
    "membria.health": HealthResult,
    "membria.migrations_status": MigrationsStatusResult,
    "membria.logs_tail": LogsTailResult,
    "membria.validate_plan": ValidatePlanResult,
    "membria.record_plan": RecordPlanResult,
    "membria_record_decision": RecordDecisionDaemonResult,
    "membria_get_context": GetContextDaemonResult,
    "membria_get_calibration": GetCalibrationDaemonResult,
}


def validate_tool_params(tool_name: str, params: Dict[str, Any]) -> Optional[str]:
    schema = INPUT_SCHEMAS.get(tool_name)
    if not schema:
        return None
    try:
        schema(**params)
        return None
    except Exception as exc:
        return str(exc)


def validate_tool_result(tool_name: str, result: Dict[str, Any]) -> Optional[str]:
    schema = OUTPUT_SCHEMAS.get(tool_name)
    if not schema:
        return None
    try:
        schema(**result)
        return None
    except Exception as exc:
        return str(exc)
