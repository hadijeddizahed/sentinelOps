from fastapi import APIRouter, HTTPException, Depends
from pydantic import BaseModel
from typing import Dict, Any, Optional
from app.graph.state import IncidentState

router = APIRouter(prefix="/incidents", tags=["incidents"])

class IncidentTriggerRequest(BaseModel):
    incident_id: str
    title: str
    service_impacted: str
    raw_alert: Dict[str, Any]

class IncidentApprovalRequest(BaseModel):
    approved: bool
    operator_id: str
    notes: Optional[str] = None

@router.post("/trigger", response_model=Dict[str, Any])
async def trigger_incident_investigation(payload: IncidentTriggerRequest):
    """Ingest a monitoring alert and initiate multi-agent investigation workflow."""
    return {
        "status": "QUEUED",
        "incident_id": payload.incident_id,
        "message": f"Investigation launched for {payload.service_impacted}"
    }

@router.get("/{incident_id}/status")
async def get_incident_status(incident_id: str):
    """Query current state, active findings, and pending approvals."""
    return {
        "incident_id": incident_id,
        "status": "INVESTIGATING",
        "findings_count": 0
    }

@router.post("/{incident_id}/approve")
async def submit_human_approval(incident_id: str, approval: IncidentApprovalRequest):
    """Resume an interrupted incident workflow with human operator authorization."""
    return {
        "incident_id": incident_id,
        "approved": approval.approved,
        "operator": approval.operator_id,
        "status": "RESUMED" if approval.approved else "ABORTED"
    }
