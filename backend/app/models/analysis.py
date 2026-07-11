from datetime import datetime, timezone
from uuid import uuid4

from sqlalchemy import Column, DateTime, Integer, ForeignKey
from sqlalchemy.dialects.postgresql import UUID, JSONB

from backend.app.core.database import Base


class Analysis(Base):
    __tablename__ = "analyses"

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
    )

    # Gemini extraction result — validated FloorPlanExtraction as JSON
    extraction_json = Column(JSONB, nullable=True)

    # Rule engine output before consistency filter
    raw_findings_json = Column(JSONB, nullable=True)

    # Rule engine output after consistency filter (what the report is built from)
    hardened_findings_json = Column(JSONB, nullable=True)

    # How many consistency runs were performed
    consistency_runs = Column(Integer, default=0, nullable=False)

    created_at = Column(
        DateTime(timezone=True),
        default=lambda: datetime.now(timezone.utc),
        nullable=False,
    )