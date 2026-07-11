import enum
from datetime import datetime, timezone
from uuid import uuid4

from sqlalchemy import Column, String, DateTime, Enum as SAEnum
from sqlalchemy.dialects.postgresql import UUID

from backend.app.core.database import Base


class PlanStatus(str, enum.Enum):
    UPLOADED   = "UPLOADED"    # image saved, not yet analysed
    PROCESSING = "PROCESSING"  # analysis in progress
    COMPLETED  = "COMPLETED"   # report ready
    FAILED     = "FAILED"      # extraction or rule engine error


class FloorPlan(Base):
    __tablename__ = "floor_plans"

    id = Column(
        UUID(as_uuid=True),
        primary_key=True,
        default=uuid4,
        nullable=False,
    )
    filename = Column(String, nullable=False)
    image_path = Column(String, nullable=False)       # path inside /storage/plans/
    uploaded_at = Column(
        DateTime(timezone=True),
        default=lambda: datetime.now(timezone.utc),
        nullable=False,
    )
    status = Column(
        SAEnum(PlanStatus, name="plan_status"),
        default=PlanStatus.UPLOADED,
        nullable=False,
    )