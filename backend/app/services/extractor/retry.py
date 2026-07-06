import json
import logging

from app.core.exceptions import ExtractionFailedError
from app.schemas.extraction import FloorPlanExtraction
from app.services.extractor.gemini_extractor import extract_floor_plan_raw
from app.services.extractor.schema_validator import validate_extraction
from app.services.extractor.prompts import build_extraction_prompt
from app.services.extractor.post_processor import fill_missing_fields

logger = logging.getLogger(__name__)

MAX_ATTEMPTS = 3


def run_extraction_with_retry(image_bytes: bytes) -> FloorPlanExtraction:
    last_error: str | None = None

    for attempt in range(1, MAX_ATTEMPTS + 1):
        logger.info(f"Extraction attempt {attempt}/{MAX_ATTEMPTS}")

        prompt = build_extraction_prompt(validation_error=last_error)

        try:
            raw = extract_floor_plan_raw(image_bytes, prompt)
        except json.JSONDecodeError as e:
            last_error = f"Response was not valid JSON: {str(e)}"
            logger.warning(f"Attempt {attempt} — JSON parse failed: {last_error}")
            continue
        except Exception as e:
            last_error = f"Gemini API error: {str(e)}"
            logger.warning(f"Attempt {attempt} — Gemini error: {last_error}")
            continue

        # Fill predictably missing fields before validation
        raw = fill_missing_fields(raw)

        result = validate_extraction(raw)

        if result.success:
            logger.info(f"Extraction succeeded on attempt {attempt}")
            return result.data

        last_error = result.error_summary
        logger.warning(
            f"Attempt {attempt} — schema validation failed:\n{last_error}"
        )

    raise ExtractionFailedError(attempts=MAX_ATTEMPTS, last_error=last_error)
