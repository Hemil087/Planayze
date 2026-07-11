from enum import Enum
from datetime import datetime, timezone
from uuid import uuid4
from pydantic import BaseModel, Field


# -------------------------------------------------------------------
# Enums
# -------------------------------------------------------------------

class Severity(str, Enum):
    """
    How serious a finding is.
    Drives score deduction and UI colour coding.
    """
    VIOLATION   = "VIOLATION"    # Breaches NBC / RERA standard   → -10 pts
    TRADEOFF    = "TRADEOFF"     # Suboptimal but not a breach     → -4 pts
    OBSERVATION = "OBSERVATION"  # Neutral or positive note        → -1 pt


class Category(str, Enum):
    """Which rule category produced this finding."""
    SPACE_EFFICIENCY = "SPACE_EFFICIENCY"
    VENTILATION      = "VENTILATION"
    PRIVACY          = "PRIVACY"
    CIRCULATION      = "CIRCULATION"
    ADJACENCY        = "ADJACENCY"
    SIZE_ADEQUACY    = "SIZE_ADEQUACY"


# -------------------------------------------------------------------
# Finding
# -------------------------------------------------------------------

class Finding(BaseModel):
    """
    A single traceable finding produced by the rule engine.
    Every finding cites the room(s) and rule that triggered it.
    """
    id: str = Field(
        default_factory=lambda: str(uuid4()),
        description="Unique finding ID",
    )
    severity: Severity = Field(..., description="VIOLATION / TRADEOFF / OBSERVATION")
    category: Category = Field(..., description="Rule category that produced this finding")

    # Human-readable content
    title: str  = Field(..., description="Short one-line summary, e.g. 'No natural ventilation'")
    detail: str = Field(..., description="Full explanation with standard citation if applicable")

    # Traceability
    room_names: list[str] = Field(
        ...,
        min_length=1,
        description="Room(s) this finding applies to — ties UI overlay to the finding",
    )
    rule_id: str = Field(
        ...,
        description="Unique rule identifier, e.g. 'VENT_001' — used by evals for precision scoring",
    )
    score_impact: int = Field(
        ...,
        description="Points deducted from overall score (negative int, or 0 for a pro finding)",
    )


# -------------------------------------------------------------------
# ReportSummary
# -------------------------------------------------------------------

class ReportSummary(BaseModel):
    """
    Complete report for a single floor plan.
    Produced by the report builder from hardened findings.
    """
    plan_id: str = Field(..., description="UUID of the FloorPlan row this report belongs to")

    overall_score: int = Field(
        ...,
        ge=0, le=100,
        description=(
            "Aggregate score (starts at 100, deductions per finding). "
            "VIOLATION=-10, TRADEOFF=-4, OBSERVATION=-1, floored at 0."
        ),
    )

    pros: list[Finding] = Field(
        default_factory=list,
        description="Positive findings (score_impact == 0)",
    )
    cons: list[Finding] = Field(
        default_factory=list,
        description="Negative findings (score_impact < 0), sorted by severity",
    )

    summary_text: str = Field(
        default="",
        description="3-4 sentence plain-English summary written by Gemini from findings only",
    )

    created_at: datetime = Field(
        default_factory=lambda: datetime.now(timezone.utc),
        description="UTC timestamp when this report was generated",
    )