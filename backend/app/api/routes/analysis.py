"""
Analysis Route — Async Background Task

POST /analysis/{plan_id}
    - Validates the plan exists and isn't already processed
    - Kicks off analysis as a background task
    - Returns immediately with { plan_id, status: "PROCESSING" }

GET /analysis/{plan_id}/status
    - Polls the current status of the analysis
    - Returns { plan_id, status } (and overall_score if COMPLETED)
"""

import asyncio
import logging
from uuid import UUID

from fastapi import APIRouter, Depends, HTTPException, Request, status
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.database import get_db, AsyncSessionLocal
from app.core.rate_limit import check_rate_limit
from app.core.storage import read_image
from app.core.exceptions import ExtractionFailedError
from app.core.config import get_settings

from app.models.floor_plan import FloorPlan, PlanStatus
from app.models.analysis import Analysis
from app.models.report import Report as ReportModel

from app.services.extractor.retry import run_extraction_with_retry
from app.services.engine.consistency_filter import run_consistency_filter
from app.services.engine.rule_runner import run_rules
from app.services.report.report_builder import build_report
from app.services.report.summary_writer import write_summary

logger = logging.getLogger(__name__)
settings = get_settings()

router = APIRouter()


# ── Background pipeline ─────────────────────────────────────────

async def _run_pipeline(plan_id: UUID, image_path: str) -> None:
    """
    Run the full analysis pipeline in the background.
    Opens its own DB session since the request session is closed.
    """
    async with AsyncSessionLocal() as db:
        try:
            # Load image
            image_bytes = read_image(image_path)

            # Gemini extraction + retry
            logger.info(f"[bg] Starting extraction for plan {plan_id}")
            extraction = run_extraction_with_retry(image_bytes)

            # Raw findings (single pass)
            raw_findings = run_rules(extraction)

            # Consistency filter
            logger.info(f"[bg] Running consistency filter for plan {plan_id}")
            hardened_findings = run_consistency_filter(extraction)

            # Build report
            plan_id_str = str(plan_id)
            report = build_report(plan_id_str, hardened_findings)

            # Generate summary
            logger.info(f"[bg] Generating summary for plan {plan_id}")
            summary = await write_summary(report)
            report.summary_text = summary

            # Persist Analysis row
            analysis_row = Analysis(
                plan_id=plan_id,
                extraction_json=extraction.model_dump(mode="json"),
                raw_findings_json=[f.model_dump(mode="json") for f in raw_findings],
                hardened_findings_json=[f.model_dump(mode="json") for f in hardened_findings],
                consistency_runs=settings.CONSISTENCY_RUNS,
            )
            db.add(analysis_row)

            # Persist Report row
            report_row = ReportModel(
                plan_id=plan_id,
                overall_score=report.overall_score,
                report_json=report.model_dump(mode="json"),
                summary_text=report.summary_text,
            )
            db.add(report_row)

            # Mark completed
            result = await db.execute(
                select(FloorPlan).where(FloorPlan.id == plan_id)
            )
            floor_plan = result.scalar_one()
            floor_plan.status = PlanStatus.COMPLETED

            await db.commit()

            logger.info(
                f"[bg] Analysis complete for plan {plan_id}: "
                f"score={report.overall_score}, "
                f"{len(report.pros)} pros, {len(report.cons)} cons"
            )

        except Exception as e:
            logger.error(f"[bg] Analysis failed for plan {plan_id}: {e}", exc_info=True)
            try:
                result = await db.execute(
                    select(FloorPlan).where(FloorPlan.id == plan_id)
                )
                floor_plan = result.scalar_one()
                floor_plan.status = PlanStatus.FAILED
                await db.commit()
            except Exception:
                await db.rollback()


# ── Routes ───────────────────────────────────────────────────────

@router.post("/{plan_id}", status_code=status.HTTP_202_ACCEPTED)
async def start_analysis(
    plan_id: UUID,
    request: Request,
    db: AsyncSession = Depends(get_db),
):
    """
    Start analysis as a background task.
    Returns immediately with status PROCESSING.
    Poll GET /analysis/{plan_id}/status to check progress.
    """
    check_rate_limit(request, "analysis")
    result = await db.execute(
        select(FloorPlan).where(FloorPlan.id == plan_id)
    )
    floor_plan = result.scalar_one_or_none()

    if floor_plan is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Floor plan not found: {plan_id}",
        )

    if floor_plan.status == PlanStatus.COMPLETED:
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail="Analysis already completed. Use GET /report/{plan_id} to retrieve it.",
        )

    if floor_plan.status == PlanStatus.PROCESSING:
        return {
            "plan_id": str(plan_id),
            "status": PlanStatus.PROCESSING.value,
            "message": "Analysis already in progress.",
        }

    # Mark as processing
    floor_plan.status = PlanStatus.PROCESSING
    await db.flush()

    # Fire background task
    asyncio.create_task(_run_pipeline(plan_id, floor_plan.image_path))

    return {
        "plan_id": str(plan_id),
        "status": PlanStatus.PROCESSING.value,
    }


@router.get("/{plan_id}/status", status_code=status.HTTP_200_OK)
async def get_analysis_status(
    plan_id: UUID,
    db: AsyncSession = Depends(get_db),
):
    """
    Poll the status of a running analysis.
    Returns overall_score when COMPLETED.
    """
    result = await db.execute(
        select(FloorPlan).where(FloorPlan.id == plan_id)
    )
    floor_plan = result.scalar_one_or_none()

    if floor_plan is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Floor plan not found: {plan_id}",
        )

    response = {
        "plan_id": str(plan_id),
        "status": floor_plan.status.value,
    }

    # If completed, include the score
    if floor_plan.status == PlanStatus.COMPLETED:
        report_result = await db.execute(
            select(ReportModel).where(ReportModel.plan_id == plan_id)
        )
        report_row = report_result.scalar_one_or_none()
        if report_row:
            response["overall_score"] = report_row.overall_score

    return response