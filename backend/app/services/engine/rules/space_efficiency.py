from backend.app.schemas.extraction import FloorPlanExtraction, RoomType
from backend.app.schemas.report import Finding, Category
from backend.app.services.engine.helpers import violation, tradeoff, observation, rooms_by_type

CARPET_RATIO_MIN = 0.70        # RERA minimum carpet-to-built-up ratio
DEAD_SPACE_MAX   = 0.15        # max corridor/dead space as % of built-up
PROPORTION_MAX   = 2.5         # max length/width ratio before room is awkward


def run(extraction: FloorPlanExtraction) -> list[Finding]:
    findings: list[Finding] = []

    # ── SPACE_001: Carpet-to-built-up ratio ─────────────────────
    if extraction.total_built_up_sqm > 0:
        ratio = extraction.total_carpet_sqm / extraction.total_built_up_sqm
        if ratio < CARPET_RATIO_MIN:
            findings.append(violation(
                rule_id="SPACE_001",
                category=Category.SPACE_EFFICIENCY,
                title="Low carpet-to-built-up ratio",
                detail=(
                    f"Carpet area is {ratio:.0%} of built-up area. "
                    f"RERA mandates a minimum of {CARPET_RATIO_MIN:.0%}. "
                    f"This means {(1 - ratio):.0%} of what you pay for is walls, "
                    f"shafts, and common areas — not usable space."
                ),
                room_names=["Entire Floor Plan"],
            ))
        elif ratio >= 0.75:
            findings.append(observation(
                rule_id="SPACE_001_POS",
                category=Category.SPACE_EFFICIENCY,
                title="Good space efficiency",
                detail=(
                    f"Carpet area is {ratio:.0%} of built-up area — "
                    f"above the RERA minimum of {CARPET_RATIO_MIN:.0%}."
                ),
                room_names=["Entire Floor Plan"],
                positive=True,
            ))

    # ── SPACE_002: Corridor / dead space percentage ──────────────
    corridors = rooms_by_type(extraction, RoomType.CORRIDOR)
    corridor_area = sum(r.area_sqm for r in corridors)
    if extraction.total_built_up_sqm > 0:
        dead_ratio = corridor_area / extraction.total_built_up_sqm
        if dead_ratio > DEAD_SPACE_MAX and corridors:
            findings.append(tradeoff(
                rule_id="SPACE_002",
                category=Category.SPACE_EFFICIENCY,
                title="Excessive corridor / circulation space",
                detail=(
                    f"Corridors occupy {dead_ratio:.0%} of built-up area "
                    f"({corridor_area:.1f} sqm). "
                    f"Above {DEAD_SPACE_MAX:.0%} is considered wasteful — "
                    f"this space adds to your cost without being liveable."
                ),
                room_names=[r.name for r in corridors],
            ))

    # ── SPACE_003: Room proportion check ────────────────────────
    for room in extraction.rooms:
        if room.width_m > 0:
            proportion = room.length_m / room.width_m
            if proportion > PROPORTION_MAX:
                findings.append(tradeoff(
                    rule_id="SPACE_003",
                    category=Category.SPACE_EFFICIENCY,
                    title=f"Awkward room proportions — {room.name}",
                    detail=(
                        f"{room.name} is {room.length_m}m × {room.width_m}m "
                        f"(ratio {proportion:.1f}:1). "
                        f"Rooms with length/width above {PROPORTION_MAX}:1 are "
                        f"difficult to furnish and feel tunnel-like."
                    ),
                    room_names=[room.name],
                ))

    return findings