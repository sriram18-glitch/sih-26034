from pydantic import BaseModel, Field
from typing import Optional, Dict, Any, List

class InspectionCreate(BaseModel):
    officer_email: str = "officer@gov.in"
    product_name: str = ""
    is_demo: bool = False
    demo_hint: str = ""

class ReviewRequest(BaseModel):
    actor: str = "officer@gov.in"
    corrections: Dict[str, str] = Field(default_factory=dict)
    confirm_violation: Optional[bool] = None
    mark_false_positive: Optional[bool] = None
    notes: str = ""
    resolve_findings: List[str] = Field(default_factory=list)
    finding_decision: Optional[str] = None  # VERIFIED or FALSE_POSITIVE

class AuditOut(BaseModel):
    id: str
    event: str
    actor: str
    inspection_id: str
    reason: str = ""
