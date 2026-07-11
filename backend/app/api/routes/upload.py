from uuid import uuid4

from fastapi import APIRouter, Depends, HTTPException, UploadFile, File, Request, status
from sqlalchemy.ext.asyncio import AsyncSession

from backend.app.core.database import get_db
from backend.app.core.rate_limit import check_rate_limit
from backend.app.core.storage import (
    save_image,
    get_extension,
    ALLOWED_CONTENT_TYPES,
    MAX_FILE_SIZE_BYTES,
)
from backend.app.models.floor_plan import FloorPlan, PlanStatus

router = APIRouter()


@router.post("", status_code=status.HTTP_201_CREATED)
async def upload_floor_plan(
    request: Request,
    file: UploadFile = File(...),
    db: AsyncSession = Depends(get_db),
):
    """
    Upload a floor plan image.

    - Validates file type (JPEG, PNG, PDF)
    - Validates file size (max 20 MB)
    - Saves image to /storage/plans/{plan_id}.{ext}
    - Creates a FloorPlan row with status UPLOADED
    - Returns plan_id to use in subsequent API calls
    """

    # ── 0. Rate limit ───────────────────────────────────────────
    check_rate_limit(request, "upload")

    # ── 1. Validate content type ────────────────────────────────
    if file.content_type not in ALLOWED_CONTENT_TYPES:
        raise HTTPException(
            status_code=status.HTTP_415_UNSUPPORTED_MEDIA_TYPE,
            detail=(
                f"Unsupported file type '{file.content_type}'. "
                f"Allowed: JPEG, PNG, PDF."
            ),
        )

    # ── 2. Read file and validate size ──────────────────────────
    data = await file.read()
    if len(data) > MAX_FILE_SIZE_BYTES:
        raise HTTPException(
            status_code=status.HTTP_413_REQUEST_ENTITY_TOO_LARGE,
            detail="File exceeds the 20 MB size limit.",
        )

    # ── 3. Validate extension ───────────────────────────────────
    try:
        ext = get_extension(file.filename)
    except ValueError as e:
        raise HTTPException(
            status_code=status.HTTP_415_UNSUPPORTED_MEDIA_TYPE,
            detail=str(e),
        )

    # ── 4. Save to disk ─────────────────────────────────────────
    plan_id = uuid4()
    image_path = save_image(data, plan_id, ext)

    # ── 5. Persist to DB ────────────────────────────────────────
    floor_plan = FloorPlan(
        id=plan_id,
        filename=file.filename,
        image_path=image_path,
        status=PlanStatus.UPLOADED,
    )
    db.add(floor_plan)
    await db.flush()

    return {
        "plan_id": str(plan_id),
        "filename": file.filename,
        "status": PlanStatus.UPLOADED.value,
    }