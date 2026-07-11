from datetime import datetime, timezone
from uuid import uuid4

from sqlalchemy import Column, DateTime, Integer, Text, ForeignKey
from sqlalchemy.dialects.postgresql import UUID, JSONB

from app.core.database import Base


class Report(Base):
    __tablename__ = "reports"

    id = Column(
        UUID(as_uuid=True),
        primary_key=True,
        default=uuid4,
        nullable=False,
    )
    plan_id = Column(
        UUID(as_uuid=True),
        ForeignKey("floor_plans.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
        unique=True,    # one report per floor plan
    )

    overall_score = Column(Integer, nullable=False)

    # Full ReportSummary as JSON (pros, cons, findings list)
    report_json = Column(JSONB, nullable=False)

    # Plain-English summary written by Gemini from findings only
    summary_text = Column(Text, nullable=False, default="")

    created_at = Column(
        DateTime(timezone=True),
        default=lambda: datetime.now(timezone.utc),
        nullable=False,
    )