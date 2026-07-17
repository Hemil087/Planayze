import json
import time
import logging

from openai import RateLimitError, APIStatusError

from app.core.exceptions import ExtractionFailedError
from app.schemas.extraction import FloorPlanExtraction
from app.services.extractor.openrouter_extractor import extract_floor_plan_raw  # renamed
from app.services.extractor.schema_validator import validate_extraction
from app.services.extractor.prompts import build_extraction_prompt
from app.services.extractor.post_processor import fill_missing_fields, coerce_room_types

logger = logging.getLogger(__name__)

MAX_ATTEMPTS = 3

# Fixed backoff for per-minute rate limits on the free tier (20 RPM).
# No retry_delay header to parse on OpenRouter — just wait and retry.
RATE_LIMIT_WAIT = 60


def _is_daily_quota_exceeded(error: RateLimitError) -> bool:
    """
    Distinguish per-minute throttle (retry-able) from daily cap (fatal).
    OpenRouter free tier: 200 requests/day. Hitting that returns a 429
    whose message mentions the daily limit rather than per-minute.
    """
    msg = str(error).lower()
    return "per day" in msg or "daily" in msg or (
        "limit exceeded" in msg and "minute" not in msg
    )


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

        except RateLimitError as e:
            last_error = f"OpenRouter rate limit: {str(e)}"
            if _is_daily_quota_exceeded(e):
                logger.error("Daily request quota exceeded (200 RPD on free tier) — aborting")
                raise ExtractionFailedError(attempts=attempt, last_error=last_error)
            logger.warning(
                f"Attempt {attempt} — per-minute rate limit hit, "
                f"waiting {RATE_LIMIT_WAIT}s before retry..."
            )
            time.sleep(RATE_LIMIT_WAIT)
            continue

        except APIStatusError as e:
            # Non-429 HTTP errors from OpenRouter (502, 503, model overloaded, etc.)
            last_error = f"OpenRouter API error {e.status_code}: {e.message}"
            logger.warning(f"Attempt {attempt} — {last_error}")
            continue

        except Exception as e:
            last_error = f"Unexpected error: {str(e)}"
            logger.warning(f"Attempt {attempt} — {last_error}")
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