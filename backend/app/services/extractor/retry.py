import re
import json
import time
import logging

from backend.app.core.exceptions import ExtractionFailedError
from backend.app.schemas.extraction import FloorPlanExtraction
from backend.app.services.extractor.gemini_extractor import extract_floor_plan_raw
from backend.app.services.extractor.schema_validator import validate_extraction
from backend.app.services.extractor.prompts import build_extraction_prompt
from backend.app.services.extractor.post_processor import fill_missing_fields,coerce_room_types

logger = logging.getLogger(__name__)

MAX_ATTEMPTS = 3
RATE_LIMIT_BUFFER = 15


def parse_retry_delay(error_str: str) -> int:
    match = re.search(r"retry_delay\s*\{\s*seconds:\s*(\d+)", error_str)
    suggested = int(match.group(1)) if match else 60
    return suggested + RATE_LIMIT_BUFFER


def is_daily_quota(error_str: str) -> bool:
    return "PerDay" in error_str or "per_day" in error_str.lower()


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
            error_str = str(e)
            last_error = f"Gemini API error: {error_str}"

            if "429" in error_str:
                if is_daily_quota(error_str):
                    logger.error("Daily quota exceeded — retry tomorrow or enable billing")
                    raise ExtractionFailedError(attempts=attempt, last_error=last_error)
                wait = parse_retry_delay(error_str)
                logger.warning(f"Attempt {attempt} — rate limited, waiting {wait}s...")
                time.sleep(wait)
            else:
                logger.warning(f"Attempt {attempt} — Gemini error: {last_error}")
            continue

        raw = fill_missing_fields(raw)
        raw = coerce_room_types(raw)
        result = validate_extraction(raw)

        if result.success:
            logger.info(f"Extraction succeeded on attempt {attempt}")
            return result.data

        last_error = result.error_summary
        logger.warning(f"Attempt {attempt} — schema validation failed:\n{last_error}")

    raise ExtractionFailedError(attempts=MAX_ATTEMPTS, last_error=last_error)
