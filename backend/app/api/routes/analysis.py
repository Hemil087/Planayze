"""
Analysis Route — Phase 8

POST /analysis/{plan_id}
    - Loads the uploaded image from storage
    - Runs Gemini extraction with retry
    - Runs consistency filter (N runs of rule engine)
    - Builds report + generates summary
    - Persists Analysis + Report rows to DB
    - Updates FloorPlan.status to COMPLETED (or FAILED)
    - Returns { plan_id, status, overall_score }
"""

import logging
from uuid import UUID

from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.database import get_db
from app.core.storage import read_image
from app.core.exceptions import ExtractionFailedError, PlanNotFoundError
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


@router.post("/{plan_id}", status_code=status.HTTP_200_OK)
async def run_analysis(
    plan_id: UUID,
    db: AsyncSession = Depends(get_db),
):
    """
    Run the full analysis pipeline on an uploaded floor plan.

    Steps:
        1. Load floor plan row and image from storage
        2. Gemini extraction with schema validation + retry
        3. Consistency filter (N runs of deterministic rule engine)
        4. Build scored report from hardened findings
        5. Generate plain-English summary via Gemini
        6. Persist Analysis + Report rows
        7. Update FloorPlan.status → COMPLETED
    """

    # ── 1. Load floor plan ────────────────────────────────────────
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
            detail="Analysis already completed for this floor plan. Use GET /report/{plan_id} to retrieve it.",
        )

    # Mark as processing
    floor_plan.status = PlanStatus.PROCESSING
    await db.flush()

    try:
        # ── 2. Read image from storage ────────────────────────────
        image_bytes = read_image(floor_plan.image_path)

        # ── 3. Gemini extraction + retry ──────────────────────────
        logger.info(f"Starting extraction for plan {plan_id}")
        extraction = run_extraction_with_retry(image_bytes)

        # ── 4. Run rule engine once for raw findings ──────────────
        raw_findings = run_rules(extraction)

        # ── 5. Consistency filter — hardened findings ─────────────
        logger.info(f"Running consistency filter for plan {plan_id}")
        hardened_findings = run_consistency_filter(extraction)

        # ── 6. Build report ───────────────────────────────────────
        plan_id_str = str(plan_id)
        report = build_report(plan_id_str, hardened_findings)

        # ── 7. Generate summary ───────────────────────────────────
        logger.info(f"Generating summary for plan {plan_id}")
        summary = await write_summary(report)
        report.summary_text = summary

        # ── 8. Persist Analysis row ───────────────────────────────
        analysis_row = Analysis(
            plan_id=plan_id,
            extraction_json=extraction.model_dump(mode="json"),
            raw_findings_json=[f.model_dump(mode="json") for f in raw_findings],
            hardened_findings_json=[f.model_dump(mode="json") for f in hardened_findings],
            consistency_runs=settings.CONSISTENCY_RUNS,
        )
        db.add(analysis_row)

        # ── 9. Persist Report row ─────────────────────────────────
        report_row = ReportModel(
            plan_id=plan_id,
            overall_score=report.overall_score,
            report_json=report.model_dump(mode="json"),
            summary_text=report.summary_text,
        )
        db.add(report_row)

        # ── 10. Mark as completed ─────────────────────────────────
        floor_plan.status = PlanStatus.COMPLETED
        await db.flush()

        logger.info(
            f"Analysis complete for plan {plan_id}: "
            f"score={report.overall_score}, "
            f"{len(report.pros)} pros, {len(report.cons)} cons"
        )

        return {
            "plan_id": plan_id_str,
            "status": PlanStatus.COMPLETED.value,
            "overall_score": report.overall_score,
        }

    except ExtractionFailedError as e:
        floor_plan.status = PlanStatus.FAILED
        await db.flush()
        logger.error(f"Extraction failed for plan {plan_id}: {e}")
        raise HTTPException(
            status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
            detail=f"Floor plan extraction failed after {e.attempts} attempts. {e.last_error}",
        )

    except FileNotFoundError as e:
        floor_plan.status = PlanStatus.FAILED
        await db.flush()
        logger.error(f"Image not found for plan {plan_id}: {e}")
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Floor plan image file not found on disk: {e}",
        )

    except Exception as e:
        floor_plan.status = PlanStatus.FAILED
        await db.flush()
        logger.error(f"Analysis failed for plan {plan_id}: {e}", exc_info=True)
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Analysis failed: {str(e)}",
        )