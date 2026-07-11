import io
import PIL.Image
from json_repair import repair_json

from vertexai.generative_models import GenerationConfig, Part, Image as VertexImage
from app.core.gemini import get_gemini_model


def extract_floor_plan_raw(
    image_bytes: bytes,
    prompt: str,
) -> dict:
    model = get_gemini_model()

    # Convert to RGB PNG bytes — Vertex AI needs a supported format
    pil_image = PIL.Image.open(io.BytesIO(image_bytes)).convert("RGB")
    buffer = io.BytesIO()
    pil_image.save(buffer, format="PNG")
    png_bytes = buffer.getvalue()

    # Wrap as Vertex AI Part
    image_part = Part.from_data(data=png_bytes, mime_type="image/png")

    response = model.generate_content(
        [image_part, prompt],
        generation_config=GenerationConfig(
            temperature=0.1,
            max_output_tokens=16384,
            response_mime_type="application/json",
        ),
    )

    result = repair_json(response.text, return_objects=True)

    if not isinstance(result, dict):
        raise ValueError(f"Expected JSON object, got {type(result)}")

    return result
