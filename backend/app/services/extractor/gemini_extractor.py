import io
import PIL.Image
from json_repair import repair_json

from app.core.gemini import get_gemini_model


def extract_floor_plan_raw(
    image_bytes: bytes,
    prompt: str,
) -> dict:
    model = get_gemini_model()
    image = PIL.Image.open(io.BytesIO(image_bytes))

    response = model.generate_content(
        [image, prompt],
        generation_config={
            "temperature": 0.1,
            "max_output_tokens": 8192,
            "response_mime_type": "application/json",
        },
    )

    # repair_json fixes trailing commas, missing quotes,
    # missing commas, truncated output — and returns a valid dict directly
    result = repair_json(response.text, return_objects=True)

    if not isinstance(result, dict):
        raise ValueError(f"Expected JSON object, got {type(result)}")

    return result
