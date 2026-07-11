from backend.app.schemas.extraction import FloorPlanExtraction, RoomType
from backend.app.schemas.report import Finding, Category
from backend.app.services.engine.helpers import violation, observation, rooms_by_type

# NBC 2016 minimum room sizes (sqm)
NBC_MINIMUMS = {
    RoomType.MASTER_BEDROOM: 9.5,
    RoomType.BEDROOM:        7.5,
    RoomType.LIVING:         9.5,
    RoomType.KITCHEN:        4.5,
}

NBC_LABELS = {
    RoomType.MASTER_BEDROOM: "master bedroom",
    RoomType.BEDROOM:        "bedroom",
    RoomType.LIVING:         "living room",
    RoomType.KITCHEN:        "kitchen",
}

# Queen bed (1.5m × 2.0m) + 0.9m clearance on 3 sides
QUEEN_BED_MIN_LONG  = 2.0 + 0.9   # 2.9m
QUEEN_BED_MIN_SHORT = 1.5 + 0.9   # 2.4m


def fits_queen_bed(room) -> bool:
    """
    Check if a queen bed (1.5 × 2.0m) with 0.9m clearance fits
    in the room in either orientation.
    """
    l, w = room.length_m, room.width_m
    orientation_1 = l >= QUEEN_BED_MIN_LONG  and w >= QUEEN_BED_MIN_SHORT
    orientation_2 = l >= QUEEN_BED_MIN_SHORT and w >= QUEEN_BED_MIN_LONG
    return orientation_1 or orientation_2


def run(extraction: FloorPlanExtraction) -> list[Finding]:
    findings: list[Finding] = []

    for room_type, min_sqm in NBC_MINIMUMS.items():
        rooms = rooms_by_type(extraction, room_type)
        label = NBC_LABELS[room_type]

        for room in rooms:
            # ── SIZE_001–004: NBC minimum size check ─────────────
            if room.area_sqm < min_sqm:
                findings.append(violation(
                    rule_id=f"SIZE_{room_type.value[:3]}",
                    category=Category.SIZE_ADEQUACY,
                    title=f"Undersized {label} — {room.name}",
                    detail=(
                        f"{room.name} is {room.area_sqm:.1f} sqm. "
                        f"NBC 2016 requires a minimum of {min_sqm} sqm "
                        f"for a {label}. This room is "
                        f"{min_sqm - room.area_sqm:.1f} sqm below the standard."
                    ),
                    room_names=[room.name],
                ))
            else:
                findings.append(observation(
                    rule_id=f"SIZE_{room_type.value[:3]}_POS",
                    category=Category.SIZE_ADEQUACY,
                    title=f"Adequately sized {label} — {room.name}",
                    detail=(
                        f"{room.name} is {room.area_sqm:.1f} sqm — "
                        f"meets the NBC 2016 minimum of {min_sqm} sqm."
                    ),
                    room_names=[room.name],
                    positive=True,
                ))

    # ── SIZE_005: Furniture feasibility — queen bed check ────────
    bedroom_types = [RoomType.BEDROOM, RoomType.MASTER_BEDROOM]
    for room in rooms_by_type(extraction, *bedroom_types):
        if not fits_queen_bed(room):
            findings.append(violation(
                rule_id="SIZE_005",
                category=Category.SIZE_ADEQUACY,
                title=f"Queen bed won't fit — {room.name}",
                detail=(
                    f"{room.name} is {room.length_m}m × {room.width_m}m. "
                    f"A queen bed (1.5 × 2.0m) with 0.9m clearance on three sides "
                    f"requires at least {QUEEN_BED_MIN_LONG}m × {QUEEN_BED_MIN_SHORT}m. "
                    f"Only a single bed will fit comfortably."
                ),
                room_names=[room.name],
            ))

    return findings