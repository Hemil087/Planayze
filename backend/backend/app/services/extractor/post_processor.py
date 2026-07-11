def fill_missing_fields(raw: dict) -> dict:
    """
    Fill in fields Gemini commonly omits before schema validation.
    This prevents retries on predictably missing fields.
    """
    rooms = raw.get("rooms", [])

    # Fix rooms missing dimensions
    for room in rooms:
        area = room.get("area_sqm")
        length = room.get("length_m")
        width = room.get("width_m")

        if area and not length and not width:
            # estimate a square-ish room from area
            import math
            room["length_m"] = round(math.sqrt(area * 1.2), 2)
            room["width_m"]  = round(math.sqrt(area / 1.2), 2)
        elif area and length and not width:
            room["width_m"] = round(area / length, 2) if length else 2.5
        elif area and width and not length:
            room["length_m"] = round(area / width, 2) if width else 3.0
        elif not area and length and width:
            room["area_sqm"] = round(length * width, 2)
        elif not area and not length and not width:
            room["area_sqm"] = 10.0
            room["length_m"] = 3.5
            room["width_m"]  = 2.8

    # Fix missing top-level fields
    total_area = sum(r.get("area_sqm", 0) for r in rooms)

    if "total_built_up_sqm" not in raw or not raw["total_built_up_sqm"]:
        raw["total_built_up_sqm"] = round(total_area * 1.15, 2)  # ~15% for walls

    if "total_carpet_sqm" not in raw or not raw["total_carpet_sqm"]:
        raw["total_carpet_sqm"] = round(raw["total_built_up_sqm"] * 0.85, 2)

    # Ensure carpet never exceeds built-up
    if raw["total_carpet_sqm"] > raw["total_built_up_sqm"]:
        raw["total_carpet_sqm"] = round(raw["total_built_up_sqm"] * 0.85, 2)

    if "orientation_north" not in raw or raw["orientation_north"] is None:
        raw["orientation_north"] = 0.0

    if "confidence_score" not in raw or raw["confidence_score"] is None:
        raw["confidence_score"] = 0.5

    if "floor" not in raw or raw["floor"] is None:
        raw["floor"] = 0

    return raw


# Room type coercion map — Gemini sometimes uses non-standard names
ROOM_TYPE_COERCE = {
    "DINING_ROOM": "LIVING",
    "DINING": "LIVING",
    "SITTING_ROOM": "LIVING",
    "LOUNGE": "LIVING",
    "HALL": "CORRIDOR",
    "HALLWAY": "CORRIDOR",
    "FOYER": "CORRIDOR",
    "ENTRANCE_HALL": "CORRIDOR",
    "STORE": "UTILITY",
    "STOREROOM": "UTILITY",
    "STORAGE": "UTILITY",
    "WC": "TOILET",
    "WASHROOM": "BATHROOM",
    "POWDER_ROOM": "TOILET",
    "LAUNDRY": "UTILITY",
    "TERRACE": "BALCONY",
    "VERANDAH": "BALCONY",
}


def coerce_room_types(raw: dict) -> dict:
    """Map non-standard Gemini room types to our RoomType enum values."""
    for room in raw.get("rooms", []):
        room_type = room.get("type", "").upper()
        if room_type in ROOM_TYPE_COERCE:
            room["type"] = ROOM_TYPE_COERCE[room_type]
    return raw
