from typing import List, Dict, Any, Optional, Annotated
from pydantic import BaseModel, Field
import operator

class InvestigationFinding(BaseModel):
    source_agent: str
    component: str
    severity: str
    evidence: str
    recommended_action: Optional[str] = None

class RemediationPlan(BaseModel):
    action_type: str
    target_resource: str
    parameters: Dict[str, Any]
    risk_level: str  # LOW, MEDIUM, HIGH, CRITICAL
    requires_approval: bool = True
    approved_by: Optional[str] = None
    execution_status: str = "PENDING"  # PENDING, APPROVED, REJECTED, EXECUTED, FAILED

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
