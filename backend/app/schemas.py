from typing import Literal
from pydantic import BaseModel, Field

Category = Literal[
    "plumbing", "electrical", "hvac", "it_equipment",
    "furniture", "structural", "cleaning", "other",
]
Severity = Literal["critical", "high", "medium", "low"]


class AnalysisResult(BaseModel):
    is_valid_fault: bool
    category: Category
    problem_summary: str
    severity: Severity
    severity_reason: str
    confidence: float = Field(ge=0, le=1)
    safety_risk: bool
    repair_steps: list[str]
    tools_required: list[str]
    estimated_effort: str