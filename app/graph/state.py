from typing import List, Dict, Any, Optional, Annotated, Literal
from pydantic import BaseModel, Field, field_validator
import operator



# Strict domain literals
SeverityLevel = Literal["SEV1", "SEV2", "SEV3", "SEV4"]
RiskLevel = Literal["LOW", "MEDIUM", "HIGH", "CRITICAL"]
PhaseState = Literal["TRIAGE", "INVESTIGATING", "PLANNING", "AWAITING_APPROVAL", "REMEDIATING", "CLOSED"]
ExecutionStatus = Literal["PENDING", "APPROVED", "REJECTED", "EXECUTED", "FAILED"]

class IncidentDiagnosis(BaseModel):
    """Structured LLM extraction model for incident triage."""
    incident_id: str = Field(description="Incident ID format: INC-XXXX")
    service_name: str = Field(min_length = 2, description="Target microservice or cloud resource")
    severity: SeverityLevel = Field(description="Normalized severity from SEV1 (critical) to SEV4 (minor)")
    suspected_root_cause: str = Field(min_length=10, description="Concise hypothesis of the root cause")
    impacted_components: List[str] = Field(min_length=1, description="List of downstream services impacted")
    confidence_score: float = Field(ge=0.0, le=1.0, description="Calibrated confidence between 0.0 and 1.0")

    @field_validator("incident_id")
    @classmethod
    def validate_incident_id_prefix(cls, v:str)-> str:
        if not v.startswith("INC-"):
            raise ValueError(f"Incident ID must start with 'INC-', received: '{v}'")
        return v

class InvestigationFinding(BaseModel):
    """Evidence finding recorded by a specialist agent."""
    source_agent: str = Field(description="Specialist agent that discovered the finding")
    component: str = Field(description="Target resource identifier")
    severity: SeverityLevel
    evidence: str = Field(description="Telemetry trace, log snippet, or metric observation")
    recommended_action: Optional[str] = None

class RemediationPlan(BaseModel):
    """Proposed remediation intervention requiring policy or human approval."""
    action_type: str = Field(description="e.g., RESTART_POD, DB_FAILOVER, SCALE_REPLICAS")
    target_resource: str
    parameters: Dict[str, Any] = Field(default_factory=dict)
    risk_level: RiskLevel
    requires_approval: bool = True
    approved_by: Optional[str] = None
    execution_status: ExecutionStatus = "PENDING"

class IncidentState(BaseModel):
    incident_id: str
    title: str
    service_impacted: str
    raw_alert: Dict[str, Any]
    current_phase: str = "TRIAGE"  # TRIAGE, INVESTIGATING, PLANNING, AWAITING_APPROVAL, REMEDIATING, CLOSED
    findings: Annotated[List[InvestigationFinding], operator.add] = []
    blast_radius: List[str] = []
    active_hypotheses: List[str] = []
    remediation_plan: Optional[RemediationPlan] = None
    investigation_log: Annotated[List[str], operator.add] = []
    human_approved: Optional[bool] = None
    error: Optional[str] = None
