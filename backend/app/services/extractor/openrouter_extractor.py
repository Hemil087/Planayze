import io
import base64
import logging

import PIL.Image
from json_repair import repair_json

from app.core.openrouter import get_openrouter_client
from app.core.config import get_settings

logger = logging.getLogger(__name__)
settings = get_settings()


def extract_floor_plan_raw(image_bytes: bytes, prompt: str) -> dict:
    client = get_openrouter_client()

    # Convert to RGB PNG — consistent format regardless of upload type
    pil_image = PIL.Image.open(io.BytesIO(image_bytes)).convert("RGB")
    buffer = io.BytesIO()
    pil_image.save(buffer, format="PNG")
    png_bytes = buffer.getvalue()

    # OpenAI-compatible vision format: base64 data URL in image_url content block
    b64_image = base64.b64encode(png_bytes).decode("utf-8")

    response = client.chat.completions.create(
        model=settings.OPENROUTER_MODEL,
        messages=[
            {
                "role": "user",
                "content": [
                    {
                        "type": "image_url",
                        "image_url": {
                            "url": f"data:image/png;base64,{b64_image}",
                        },
                    },
                    {
                        "type": "text",
                        "text": prompt,
                    },
                ],
            }
        ],
        response_format={"type": "json_object"},
        temperature=0.1,
        max_tokens=16384,
    )

    raw_text = response.choices[0].message.content
    logger.debug(f"Raw model response length: {len(raw_text)} chars")

    result = repair_json(raw_text, return_objects=True)

    if not isinstance(result, dict):
        raise ValueError(f"Expected JSON object from model, got {type(result)}")

    return result