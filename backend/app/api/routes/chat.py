"""
Chat Route — Phase 10

POST /chat/{plan_id}
    Accepts ChatRequest (conversation history), loads the
    FloorPlanExtraction from the Analysis row, and runs
    the chat agent with geometry tools.
"""

import logging
from uuid import UUID

from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.database import get_db
from app.models.analysis import Analysis
from app.schemas.extraction import FloorPlanExtraction
from app.schemas.chat import ChatRequest, ChatResponse
from app.services.chat.chat_agent import run_chat_agent

logger = logging.getLogger(__name__)

router = APIRouter()


@router.post("/{plan_id}", response_model=ChatResponse, status_code=status.HTTP_200_OK)
async def chat_with_plan(
    plan_id: UUID,
    request: ChatRequest,
    db: AsyncSession = Depends(get_db),
):
    """
    Chat with a floor plan using geometry tools.

    Requires that POST /analysis/{plan_id} has been run first —
    the chat agent uses the stored extraction data.
    """
    # Load the analysis row to get extraction JSON
    result = await db.execute(
        select(Analysis).where(Analysis.plan_id == plan_id)
    )
    analysis = result.scalar_one_or_none()

    if analysis is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=(
                f"No analysis found for plan {plan_id}. "
                f"Run POST /analysis/{plan_id} first."
            ),
        )

    # Deserialise the stored extraction JSON
    try:
        extraction = FloorPlanExtraction(**analysis.extraction_json)
    except Exception as e:
        logger.error(f"Failed to load extraction for plan {plan_id}: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to load floor plan data. The analysis may be corrupted.",
        )

    # Run the chat agent
    response = await run_chat_agent(
        extraction=extraction,
        messages=request.messages,
    )

    logger.info(
        f"Chat for plan {plan_id}: "
        f"tools={response.tool_calls_made}, "
        f"reply_len={len(response.reply)}"
    )

    return response