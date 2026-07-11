"""
Report Route — Phase 8

GET /report/{plan_id}
    - Loads the Report row from DB
    - Returns the full ReportSummary JSON
"""

import logging
from uuid import UUID

from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from backend.app.core.database import get_db
from backend.app.models.report import Report as ReportModel

logger = logging.getLogger(__name__)

router = APIRouter()


@router.get("/{plan_id}", status_code=status.HTTP_200_OK)
async def get_report(
    plan_id: UUID,
    db: AsyncSession = Depends(get_db),
):
    """
    Fetch the structured findings report for a floor plan.

    Returns the full ReportSummary JSON including:
    - overall_score
    - pros (positive findings)
    - cons (negative findings, sorted by severity)
    - summary_text (plain-English summary)
    """
    result = await db.execute(
        select(ReportModel).where(ReportModel.plan_id == plan_id)
    )
    report_row = result.scalar_one_or_none()

    if report_row is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=(
                f"No report found for plan {plan_id}. "
                f"Run POST /analysis/{plan_id} first."
            ),
        )

    return report_row.report_json