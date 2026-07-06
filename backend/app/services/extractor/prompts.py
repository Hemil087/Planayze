BASE_EXTRACTION_PROMPT = """
You are a floor plan geometry extractor. Your only job is to extract spatial data from the floor plan image.

RULES:
- Return ONLY a valid JSON object. No explanation, no markdown, no code fences.
- Do NOT make any judgments about the design quality.
- All dimensions must be in metres and square metres.
- If you cannot determine an exact value, provide your best estimate.
- Every room MUST have at least one door.

Return a JSON object matching this exact structure:

{
  "rooms": [
    {
      "name": "Master Bedroom",
      "type": "MASTER_BEDROOM",
      "area_sqm": 14.5,
      "length_m": 4.5,
      "width_m": 3.2,
      "external_walls": ["N", "E"],
      "windows": [
        { "wall": "N", "width_m": 1.5 }
      ],
      "doors": [
        { "connects_to": "CORRIDOR", "width_m": 0.9 }
      ]
    }
  ],
  "total_built_up_sqm": 95.0,
  "total_carpet_sqm": 78.0,
  "orientation_north": 0.0,
  "floor": 0,
  "confidence_score": 0.85
}

FIELD RULES:
- "type" must be one of: BEDROOM, MASTER_BEDROOM, LIVING, KITCHEN, BATHROOM, TOILET, BALCONY, CORRIDOR, UTILITY, UNKNOWN
- "external_walls" lists which walls face the building exterior — use N, S, E, W. Empty list for internal rooms.
- "windows[].wall" must be one of: N, S, E, W
- "doors[].connects_to" is the name of the adjacent room exactly as you name it, or "ENTRANCE" (building entrance) or "EXTERIOR"
- "orientation_north" is the compass bearing (0-359) that corresponds to UP on the plan. 0 = up is North.
- "confidence_score" is your confidence in the extraction between 0.0 and 1.0
- "total_carpet_sqm" must be less than "total_built_up_sqm"

Now extract the floor plan:
""".strip()


def build_extraction_prompt(validation_error: str | None = None) -> str:
    """
    Build the extraction prompt.
    If a validation_error is provided, append it so Gemini
    knows exactly what to fix on the retry.
    """
    if not validation_error:
        return BASE_EXTRACTION_PROMPT

    return (
        BASE_EXTRACTION_PROMPT
        + f"\n\nYour previous response had validation errors. "
        f"Fix ONLY these issues and return the corrected JSON:\n{validation_error}"
    )