from backend.app.schemas.extraction import FloorPlanExtraction, RoomType
from backend.app.schemas.report import Finding, Category
from backend.app.services.engine.helpers import violation, tradeoff, observation, rooms_by_type

WINDOW_FLOOR_RATIO_MIN = 0.10   # NBC 2016 Cl. 8.1 — window area / floor area

# Rooms that MUST have natural light/ventilation
HABITABLE_TYPES = {
    RoomType.BEDROOM,
    RoomType.MASTER_BEDROOM,
    RoomType.LIVING,
    RoomType.KITCHEN,
}


def run(extraction: FloorPlanExtraction) -> list[Finding]:
    findings: list[Finding] = []

    for room in extraction.rooms:
        # ── VENT_001: Rooms with zero external walls ─────────────
        if room.type in HABITABLE_TYPES and not room.external_walls:
            findings.append(violation(
                rule_id="VENT_001",
                category=Category.VENTILATION,
                title=f"No natural ventilation — {room.name}",
                detail=(
                    f"{room.name} has no external walls. "
                    f"NBC 2016 requires all habitable rooms to have "
                    f"at least one external wall for natural light and ventilation. "
                    f"This room will rely entirely on mechanical ventilation."
                ),
                room_names=[room.name],
            ))

        # ── VENT_002: Window-to-floor-area ratio ─────────────────
        if room.type in HABITABLE_TYPES and room.area_sqm > 0:
            window_area = sum(
                w.width_m * 1.2  # assume standard 1.2m height
                for w in room.windows
            )
            ratio = window_area / room.area_sqm
            if room.windows and ratio < WINDOW_FLOOR_RATIO_MIN:
                findings.append(violation(
                    rule_id="VENT_002",
                    category=Category.VENTILATION,
                    title=f"Insufficient window area — {room.name}",
                    detail=(
                        f"{room.name} has a window-to-floor ratio of {ratio:.1%}. "
                        f"NBC 2016 Cl. 8.1 requires at least {WINDOW_FLOOR_RATIO_MIN:.0%}. "
                        f"Insufficient natural light will make the room feel dark "
                        f"and increase electricity costs."
                    ),
                    room_names=[room.name],
                ))
            elif not room.windows and room.type in HABITABLE_TYPES:
                findings.append(violation(
                    rule_id="VENT_002",
                    category=Category.VENTILATION,
                    title=f"No windows — {room.name}",
                    detail=(
                        f"{room.name} has no windows. "
                        f"NBC 2016 Cl. 8.1 requires windows in all habitable rooms."
                    ),
                    room_names=[room.name],
                ))

        # ── VENT_003: Cross-ventilation check ────────────────────
        if room.type in HABITABLE_TYPES and room.windows:
            unique_walls = {w.wall for w in room.windows}
            if len(unique_walls) < 2 and room.external_walls:
                findings.append(tradeoff(
                    rule_id="VENT_003",
                    category=Category.VENTILATION,
                    title=f"No cross-ventilation — {room.name}",
                    detail=(
                        f"{room.name} has windows on only one wall ({list(unique_walls)[0]}). "
                        f"Cross-ventilation requires openings on at least two walls — "
                        f"without it, the room will trap heat and have poor air circulation."
                    ),
                    room_names=[room.name],
                ))
            elif len(unique_walls) >= 2:
                findings.append(observation(
                    rule_id="VENT_003_POS",
                    category=Category.VENTILATION,
                    title=f"Good cross-ventilation — {room.name}",
                    detail=(
                        f"{room.name} has windows on {len(unique_walls)} walls, "
                        f"enabling natural cross-ventilation."
                    ),
                    room_names=[room.name],
                    positive=True,
                ))

    return findings